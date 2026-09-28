from app.core.logging import get_logger
from app.core.tracing import RetrievedChunkTrace, TraceLogger, TraceRecord, get_trace_logger, new_trace_id, now_iso
from app.generation.grounding import (
    REFUSAL_ANSWER,
    enforce_refusal_policy,
    has_lexical_support,
    parse_llm_response,
)
from app.generation.llm import LLMProvider
from app.generation.prompts import PROMPT_VERSION, build_grounding_prompt
from app.models.chat import ChatResponse, GroundedAnswer
from app.models.search import SearchFilters
from app.retrieval.retriever import Retriever
from app.vectorstore.chroma_store import RetrievedChunk

logger = get_logger(__name__)


class ChatService:
    """Orchestrates: retrieve -> deterministic pre-check -> LLM -> post-check.

    The pre/post grounding checks (app.generation.grounding) run
    regardless of which LLMProvider is configured, so refusal safety does
    not depend solely on the LLM following its prompt instructions.

    Every call also appends one trace record (app.core.tracing) - the raw
    material Week 5's error analysis reads.
    """

    def __init__(
        self,
        retriever: Retriever,
        llm_provider: LLMProvider,
        top_k: int,
        model_provider: str = "unknown",
        model_name: str = "unknown",
        trace_logger: TraceLogger | None = None,
    ):
        self.retriever = retriever
        self.llm_provider = llm_provider
        self.top_k = top_k
        self.model_provider = model_provider
        self.model_name = model_name
        # Defaults to the shared production trace log (evaluation/week5/traces.jsonl).
        # Tests pass their own TraceLogger pointed at a tmp_path so pytest runs
        # never mix synthetic test traffic into the real Week-5 trace sample.
        self.trace_logger = trace_logger or get_trace_logger()

    def answer(
        self, question: str, strategy: str, filters: SearchFilters | None = None
    ) -> ChatResponse:
        retrieved = self.retriever.search(question, strategy=strategy, top_k=self.top_k, filters=filters)
        retrieved_ids = {c.chunk_id for c in retrieved}
        trace = self._start_trace(question, strategy, filters, retrieved)

        if not has_lexical_support(question, retrieved):
            logger.info("Refusing (no lexical support in retrieved context): %r", question)
            trace.refused_pre_llm = True
            trace.answerable = False
            trace.answer = REFUSAL_ANSWER.answer
            trace.final_refused = True
            self.trace_logger.log(trace)
            return self._to_response(REFUSAL_ANSWER, retrieved_ids)

        prompt = build_grounding_prompt(question, retrieved)
        trace.llm_called = True
        raw_output = self.llm_provider.generate(prompt)
        parsed = parse_llm_response(raw_output)

        if parsed is None:
            trace.parse_retried = True
            prompt = prompt + "\n\nReminder: respond with ONLY the JSON object, no other text."
            raw_output = self.llm_provider.generate(prompt)
            parsed = parse_llm_response(raw_output)

        trace.prompt = prompt
        trace.raw_llm_output = raw_output

        if parsed is None:
            logger.warning("LLM output could not be parsed after retry; refusing")
            trace.answerable = False
            trace.answer = REFUSAL_ANSWER.answer
            trace.final_refused = True
            self.trace_logger.log(trace)
            return self._to_response(REFUSAL_ANSWER, retrieved_ids)

        final_answer = enforce_refusal_policy(parsed, retrieved_ids)
        trace.answerable = final_answer.answerable
        trace.answer = final_answer.answer
        trace.citations = [c.chunk_id for c in final_answer.citations]
        trace.final_refused = not final_answer.answerable
        self.trace_logger.log(trace)
        return self._to_response(final_answer, retrieved_ids)

    def _start_trace(
        self,
        question: str,
        strategy: str,
        filters: SearchFilters | None,
        retrieved: list[RetrievedChunk],
    ) -> TraceRecord:
        return TraceRecord(
            trace_id=new_trace_id(),
            timestamp=now_iso(),
            prompt_version=PROMPT_VERSION,
            question=question,
            strategy=strategy,
            dietary_tag_filters=list(filters.dietary_tags) if filters and filters.dietary_tags else [],
            retrieved=[
                RetrievedChunkTrace(
                    chunk_id=c.chunk_id,
                    score=c.score,
                    recipe_id=c.metadata.recipe_id,
                    section=c.metadata.section,
                    text=c.text,
                )
                for c in retrieved
            ],
            model_provider=self.model_provider,
            model_name=self.model_name,
            refused_pre_llm=False,
        )

    @staticmethod
    def _to_response(answer: GroundedAnswer, retrieved_ids: set[str]) -> ChatResponse:
        return ChatResponse(
            answer=answer.answer,
            refused=not answer.answerable,
            citations=answer.citations,
            retrieved_chunk_ids=sorted(retrieved_ids),
        )
