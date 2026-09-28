from app.core.logging import get_logger
from app.generation.grounding import enforce_refusal_policy, has_lexical_support, parse_llm_response
from app.generation.llm import LLMProvider
from app.generation.prompts import build_generic_grounding_prompt
from app.models.chat import ChatResponse, GroundedAnswer
from app.retrieval.retriever import Retriever

logger = get_logger(__name__)

GENERIC_REFUSAL_ANSWER = GroundedAnswer(
    answerable=False,
    answer="I cannot answer this from the uploaded documents.",
    citations=[],
)


class UploadedChatService:
    """Same retrieve -> pre-check -> LLM -> post-check shape as ChatService,
    pointed at the generic uploaded-documents collection instead of the
    recipe collections, with domain-neutral prompt wording and refusal text.
    """

    def __init__(self, retriever: Retriever, llm_provider: LLMProvider, top_k: int):
        self.retriever = retriever
        self.llm_provider = llm_provider
        self.top_k = top_k

    def answer(self, question: str, doc_id: str | None = None) -> ChatResponse:
        retrieved = self.retriever.search_uploaded(question, top_k=self.top_k, doc_id=doc_id)
        retrieved_ids = {c.chunk_id for c in retrieved}

        if not has_lexical_support(question, retrieved):
            logger.info("Refusing (no lexical support in retrieved context): %r", question)
            return self._to_response(GENERIC_REFUSAL_ANSWER, retrieved_ids)

        prompt = build_generic_grounding_prompt(question, retrieved)
        parsed = parse_llm_response(self.llm_provider.generate(prompt))

        if parsed is None:
            retry_prompt = prompt + "\n\nReminder: respond with ONLY the JSON object, no other text."
            parsed = parse_llm_response(self.llm_provider.generate(retry_prompt))

        if parsed is None:
            logger.warning("LLM output could not be parsed after retry; refusing")
            return self._to_response(GENERIC_REFUSAL_ANSWER, retrieved_ids)

        final_answer = enforce_refusal_policy(parsed, retrieved_ids, refusal_answer=GENERIC_REFUSAL_ANSWER)
        return self._to_response(final_answer, retrieved_ids)

    @staticmethod
    def _to_response(answer: GroundedAnswer, retrieved_ids: set[str]) -> ChatResponse:
        return ChatResponse(
            answer=answer.answer,
            refused=not answer.answerable,
            citations=answer.citations,
            retrieved_chunk_ids=sorted(retrieved_ids),
        )
