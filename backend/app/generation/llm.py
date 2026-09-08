import json
import re
from abc import ABC, abstractmethod

from app.core.logging import get_logger

logger = get_logger(__name__)

REFUSAL_JSON = json.dumps(
    {"answerable": False, "answer": "I cannot answer this from the provided recipes.", "citations": []}
)

# Words that appear in almost every recipe's title/text but carry no
# information about WHAT is being asked (only WHICH recipe). Excluded when
# scoring lexical evidence so that e.g. matching "sourdough" alone doesn't
# count as support for a question about protein content.
GENERIC_DOMAIN_WORDS = {
    "recipe", "bread", "loaf", "dough", "sourdough", "yields", "approximately",
    "sourdough", "country", "rye", "caraway", "rosemary", "olive", "focaccia",
    "brioche", "cinnamon", "raisin", "walnut", "whole", "wheat", "flaxseed",
}
STOPWORDS = {
    "what", "which", "how", "does", "do", "is", "are", "the", "a", "an", "of",
    "in", "for", "to", "and", "or", "with", "this", "that", "much", "many",
    "per", "should", "when", "during", "process", "be", "it",
    # generic quantifiers / number words: high document frequency across
    # every recipe ("one loaf", "two pieces", ...), so they carry no real
    # evidence about what is being asked and must not count as lexical support.
    "one", "two", "three", "four", "five", "first", "second", "third",
    "each", "every", "also", "about", "than", "into", "onto", "out", "over",
}


def extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z']+", text.lower())
    return [w for w in words if len(w) > 2 and w not in STOPWORDS]


def content_keywords(question: str) -> list[str]:
    return [w for w in extract_keywords(question) if w not in GENERIC_DOMAIN_WORDS]


def _word_set(text: str) -> set[str]:
    """Whole-word tokenization for matching (NOT substring containment).

    A naive substring check (`"bake" in "Baker's Percentage"`) produces false
    positives like matching "bake" inside "Baker's" - this returns a real
    word set so keyword matching requires whole-word equality.
    """
    return set(re.findall(r"[a-zA-Z']+", text.lower()))


def _is_table_header_row(line: str) -> bool:
    """Ingredient-table header rows ("Ingredient | Weight | Baker's Percentage")
    carry no factual content themselves and must never be selected as an answer.
    """
    first_cell = line.split("|", 1)[0].strip().lower()
    return first_cell == "ingredient"


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return raw completion text (expected to be the JSON contract described in prompts.py)."""
        raise NotImplementedError


class AnthropicProvider(LLMProvider):
    """Real LLM provider backed by the Anthropic Claude API."""

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("AnthropicProvider requires LLM_API_KEY to be set")
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def generate(self, prompt: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")


class LocalExtractiveProvider(LLMProvider):
    """Deterministic, no-API-key generation stand-in.

    Parses the same grounding prompt a real LLM would receive, finds the
    context line with the strongest lexical overlap with the question's
    content keywords, and returns it (with a citation) as the answer. If
    nothing overlaps it refuses.

    This exists so the full grounding / citation-validation / refusal
    pipeline can be exercised and reported truthfully without requiring a
    paid API key. It is intentionally simple and will produce lower-quality
    prose than a real LLM - see results.md for how to switch to
    AnthropicProvider once LLM_API_KEY is configured.
    """

    CHUNK_BLOCK_RE = re.compile(r"\[chunk_id:\s*(?P<chunk_id>[^\]]+)\]\n(?P<text>.*?)(?=\n\n---\n\n|\n\nQUESTION:)", re.DOTALL)
    QUESTION_RE = re.compile(r"QUESTION:\n(?P<question>.*)", re.DOTALL)

    def generate(self, prompt: str) -> str:
        question_match = self.QUESTION_RE.search(prompt)
        question = question_match.group("question").strip() if question_match else ""
        chunks = self._parse_context_chunks(prompt)

        keywords = content_keywords(question)
        best_chunk_id, best_line, best_score = None, None, 0

        for chunk_id, text in chunks:
            for line in text.splitlines():
                line = line.strip()
                if not line or _is_table_header_row(line):
                    continue
                line_words = _word_set(line)
                score = sum(1 for kw in keywords if kw in line_words)
                if score > best_score:
                    best_score = score
                    best_chunk_id = chunk_id
                    best_line = line

        if best_score == 0 or best_chunk_id is None:
            return REFUSAL_JSON

        answer_text = self._format_answer(best_line)
        return json.dumps(
            {
                "answerable": True,
                "answer": answer_text,
                "citations": [{"chunk_id": best_chunk_id}],
            }
        )

    @staticmethod
    def _format_answer(line: str) -> str:
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) == 3:
                name, weight, pct = parts
                return f"{name}: {weight} ({pct})"
        return line

    @classmethod
    def _parse_context_chunks(cls, prompt: str) -> list[tuple[str, str]]:
        return [(m.group("chunk_id").strip(), m.group("text").strip()) for m in cls.CHUNK_BLOCK_RE.finditer(prompt)]


def get_llm_provider(provider_name: str, api_key: str, model: str) -> LLMProvider:
    if provider_name == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model)
    if provider_name == "local":
        return LocalExtractiveProvider()
    raise ValueError(f"Unknown LLM_PROVIDER: {provider_name}")
