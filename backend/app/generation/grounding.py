import json

import re

from app.core.logging import get_logger
from app.generation.llm import content_keywords
from app.models.chat import GroundedAnswer
from app.vectorstore.chroma_store import RetrievedChunk

logger = get_logger(__name__)

REFUSAL_ANSWER = GroundedAnswer(
    answerable=False,
    answer="I cannot answer this from the provided recipes.",
    citations=[],
)


def has_lexical_support(question: str, chunks: list[RetrievedChunk]) -> bool:
    """Deterministic pre-check (Rule/Section 26): does the retrieved context
    actually contain evidence for what's being ASKED (not just the right
    recipe name)? Runs before the LLM is even called.
    """
    keywords = content_keywords(question)
    if not keywords or not chunks:
        return False
    combined_words = set(re.findall(r"[a-zA-Z']+", " ".join(c.text.lower() for c in chunks)))
    return any(kw in combined_words for kw in keywords)


def parse_llm_response(raw_text: str) -> GroundedAnswer | None:
    """Parse + validate the LLM's raw output against the GroundedAnswer schema.
    Returns None if parsing/validation fails (caller decides how to react).
    """
    text = raw_text.strip()
    # Be tolerant of a model wrapping the JSON in a code fence.
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        data = json.loads(text)
        return GroundedAnswer.model_validate(data)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse LLM response as GroundedAnswer: %s", exc)
        return None


def validate_citations(answer: GroundedAnswer, retrieved_chunk_ids: set[str]) -> bool:
    """Every citation must resolve to a chunk that was actually retrieved (Rule 10)."""
    return all(c.chunk_id in retrieved_chunk_ids for c in answer.citations)


def enforce_refusal_policy(answer: GroundedAnswer, retrieved_chunk_ids: set[str]) -> GroundedAnswer:
    """Application-level safety net applied AFTER the LLM responds, regardless
    of provider. Forces a refusal if the LLM violated grounding rules.
    """
    if not answer.answerable:
        return REFUSAL_ANSWER

    if not answer.citations:
        logger.warning("Rejecting answer with no citations for a factual claim")
        return REFUSAL_ANSWER

    if not validate_citations(answer, retrieved_chunk_ids):
        logger.warning("Rejecting answer citing a chunk_id outside the retrieved context: %s", answer.citations)
        return REFUSAL_ANSWER

    return answer
