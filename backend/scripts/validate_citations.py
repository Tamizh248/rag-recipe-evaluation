"""Validate every citation produced in evaluation/generation_dump.json.

For each citation checks:
  1. The chunk_id exists in the vector store.
  2. It belongs to the recipe the question was about.
  3. The cited chunk's text actually contains lexical support for the
     claimed answer (not just any chunk from the right recipe).

Also runs one synthetic check with a chunk_id that is known not to exist,
to prove the validator actually rejects invalid citations rather than
trivially passing everything (Rule 10).

Usage:
    python scripts/validate_citations.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.generation.llm import content_keywords
from app.vectorstore.chroma_store import ChromaStore

BACKEND_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = BACKEND_DIR.parent / "evaluation"
GENERATION_DUMP_PATH = EVAL_DIR / "generation_dump.json"
OUTPUT_PATH = EVAL_DIR / "citation_validation.json"

STRATEGY_INTERNAL = "structure_aware"


def check_citation(store: ChromaStore, question_id: str, chunk_id: str, answer: str, expected_recipe_id: str | None) -> dict:
    chunk = store.get_chunk(STRATEGY_INTERNAL, chunk_id)
    if chunk is None:
        return {"question_id": question_id, "chunk_id": chunk_id, "exists": False, "valid": False, "reason": "chunk_id does not exist in the vector store"}

    result = {"question_id": question_id, "chunk_id": chunk_id, "exists": True, "recipe_id": chunk.metadata.recipe_id}

    matches_recipe = expected_recipe_id is None or chunk.metadata.recipe_id == expected_recipe_id
    result["matches_expected_recipe"] = matches_recipe

    answer_keywords = set(content_keywords(answer))
    chunk_text_lower = chunk.text.lower()
    overlap = sorted(kw for kw in answer_keywords if kw in chunk_text_lower)
    result["overlap_keywords"] = overlap
    result["supports_answer"] = len(overlap) > 0

    result["valid"] = matches_recipe and result["supports_answer"]
    if not result["valid"]:
        reasons = []
        if not matches_recipe:
            reasons.append("chunk belongs to a different recipe than expected")
        if not result["supports_answer"]:
            reasons.append("chunk text has no lexical overlap with the answer")
        result["reason"] = "; ".join(reasons)
    return result


def main() -> None:
    settings = get_settings()
    store = ChromaStore(settings.chroma_persist_path)
    data = json.loads(GENERATION_DUMP_PATH.read_text(encoding="utf-8"))

    checks = []
    for entry in data["answerable"]:
        for chunk_id in entry["citations"]:
            checks.append(
                check_citation(store, entry["id"], chunk_id, entry["answer"], entry.get("expected_recipe_id"))
            )

    # Synthetic negative control: a citation that should never validate.
    checks.append(
        check_citation(store, "SYNTHETIC_NEGATIVE_CONTROL", "does_not_exist_chunk_999", "irrelevant", None)
    )

    all_real_citations_valid = all(c["valid"] for c in checks[:-1]) if len(checks) > 1 else True
    negative_control_correctly_rejected = checks[-1]["valid"] is False

    report = {
        "checks": checks,
        "all_real_citations_valid": all_real_citations_valid,
        "negative_control_correctly_rejected": negative_control_correctly_rejected,
    }
    OUTPUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    for c in checks:
        status = "OK" if c["valid"] else "REJECTED"
        print(f"[{status}] {c['question_id']} chunk_id={c['chunk_id']}" + (f" - {c['reason']}" if not c["valid"] else ""))

    print(f"\nAll real citations valid: {all_real_citations_valid}")
    print(f"Negative control correctly rejected: {negative_control_correctly_rejected}")
    print(f"Full report written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
