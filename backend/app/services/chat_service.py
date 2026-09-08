from app.core.logging import get_logger
from app.generation.grounding import (
    REFUSAL_ANSWER,
    enforce_refusal_policy,
    has_lexical_support,
    parse_llm_response,
)
from app.generation.llm import LLMProvider
from app.generation.prompts import build_grounding_prompt
from app.models.chat import ChatResponse, GroundedAnswer
from app.models.search import SearchFilters
from app.retrieval.retriever import Retriever

logger = get_logger(__name__)


class ChatService:
    """Orchestrates: retrieve -> deterministic pre-check -> LLM -> post-check.

    The pre/post grounding checks (app.generation.grounding) run
    regardless of which LLMProvider is configured, so refusal safety does
    not depend solely on the LLM following its prompt instructions.
    """

    def __init__(self, retriever: Retriever, llm_provider: LLMProvider, top_k: int):
        self.retriever = retriever
        self.llm_provider = llm_provider
        self.top_k = top_k

    def answer(
        self, question: str, strategy: str, filters: SearchFilters | None = None
    ) -> ChatResponse:
        retrieved = self.retriever.search(question, strategy=strategy, top_k=self.top_k, filters=filters)
        retrieved_ids = {c.chunk_id for c in retrieved}

        if not has_lexical_support(question, retrieved):
            logger.info("Refusing (no lexical support in retrieved context): %r", question)
            return self._to_response(REFUSAL_ANSWER, retrieved_ids)

        prompt = build_grounding_prompt(question, retrieved)
        parsed = parse_llm_response(self.llm_provider.generate(prompt))

        if parsed is None:
            retry_prompt = prompt + "\n\nReminder: respond with ONLY the JSON object, no other text."
            parsed = parse_llm_response(self.llm_provider.generate(retry_prompt))

        if parsed is None:
            logger.warning("LLM output could not be parsed after retry; refusing")
            return self._to_response(REFUSAL_ANSWER, retrieved_ids)

        final_answer = enforce_refusal_policy(parsed, retrieved_ids)
        return self._to_response(final_answer, retrieved_ids)

    @staticmethod
    def _to_response(answer: GroundedAnswer, retrieved_ids: set[str]) -> ChatResponse:
        return ChatResponse(
            answer=answer.answer,
            refused=not answer.answerable,
            citations=answer.citations,
            retrieved_chunk_ids=sorted(retrieved_ids),
        )
