"""Search-only retrieval evaluation. Does NOT call any LLM (Rule 8).

Runs the same 8 predefined questions (evaluation/questions.json) against
both the "current" and "structure-aware" collections, using identical
embedding model, top_k, and similarity metric for both - the only variable
is the chunking strategy. Writes the full per-question retrieval dump to
evaluation/search_dump.json and prints a Hit@5 summary.

Usage:
    python scripts/evaluate_retrieval.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.embeddings.sentence_transformer import get_embedding_model
from app.retrieval.retriever import Retriever
from app.vectorstore.chroma_store import ChromaStore

BACKEND_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = BACKEND_DIR.parent / "evaluation"
QUESTIONS_PATH = EVAL_DIR / "questions.json"
SEARCH_DUMP_PATH = EVAL_DIR / "search_dump.json"

STRATEGIES = ["current", "structure-aware"]


def is_hit(results: list[dict], expected_recipe_id: str, expected_section: str) -> bool:
    return any(
        r["recipe_id"] == expected_recipe_id and r["section"] == expected_section
        for r in results
    )


def main() -> None:
    settings = get_settings()
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))["retrieval_questions"]

    embedding_model = get_embedding_model()
    store = ChromaStore(settings.chroma_persist_path)
    retriever = Retriever(store, embedding_model)

    for strategy in STRATEGIES:
        internal = "current" if strategy == "current" else "structure_aware"
        count = store.count(internal)
        if count == 0:
            raise RuntimeError(
                f"Collection for strategy={strategy!r} is empty. Run "
                f"scripts/ingest_recipes.py --strategy {strategy} first."
            )

    dump = {"top_k": settings.top_k, "embedding_model": settings.embedding_model, "questions": []}
    hits = {s: 0 for s in STRATEGIES}
    per_question_rows = []

    for q in questions:
        question_entry = {
            "id": q["id"],
            "question": q["question"],
            "expected_recipe_id": q["expected_recipe_id"],
            "expected_section": q["expected_section"],
            "results": {},
        }
        row = {"id": q["id"]}

        for strategy in STRATEGIES:
            retrieved = retriever.search(q["question"], strategy=strategy, top_k=settings.top_k)
            results_payload = [
                {
                    "chunk_id": r.chunk_id,
                    "score": round(r.score, 4),
                    "recipe_id": r.metadata.recipe_id,
                    "section": r.metadata.section,
                }
                for r in retrieved
            ]
            hit = is_hit(results_payload, q["expected_recipe_id"], q["expected_section"])
            if hit:
                hits[strategy] += 1

            question_entry["results"][strategy] = {"hit": hit, "top_k": results_payload}
            row[strategy] = "HIT" if hit else "MISS"

        dump["questions"].append(question_entry)
        per_question_rows.append(row)

    dump["hit_at_5"] = {s: f"{hits[s]}/{len(questions)}" for s in STRATEGIES}

    SEARCH_DUMP_PATH.write_text(json.dumps(dump, indent=2), encoding="utf-8")

    print(f"{'Question':<8}{'Current':<10}{'Structure-Aware':<18}")
    for row in per_question_rows:
        print(f"{row['id']:<8}{row['current']:<10}{row['structure-aware']:<18}")
    print()
    for strategy in STRATEGIES:
        print(f"{strategy}: {hits[strategy]}/{len(questions)}")
    print(f"\nFull dump written to {SEARCH_DUMP_PATH}")


if __name__ == "__main__":
    main()
