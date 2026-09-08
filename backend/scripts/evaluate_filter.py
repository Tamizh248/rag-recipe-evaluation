"""Demonstrate that dietary_tags metadata filtering actually changes retrieval.

Tries a small set of candidate queries against the structure-aware
collection, unfiltered vs filtered by dietary_tags=["vegan"], and reports
the first one where the unfiltered Top-1 chunk differs from the filtered
Top-1 chunk. The filter is applied as a real ChromaDB `where` clause (see
app/vectorstore/chroma_store.py:build_where_clause), never as a Python
post-filter over already-retrieved results.

Usage:
    python scripts/evaluate_filter.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.embeddings.sentence_transformer import get_embedding_model
from app.models.search import SearchFilters
from app.retrieval.retriever import Retriever
from app.vectorstore.chroma_store import ChromaStore

BACKEND_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = BACKEND_DIR.parent / "evaluation"
OUTPUT_PATH = EVAL_DIR / "filter_dump.json"

CANDIDATE_QUERIES = [
    "Which bread recipe uses an enriched dough with a soft crumb?",
    "Which recipe would work well for a rich, buttery breakfast bread?",
    "Which bread pairs well with a cheese board?",
]

STRATEGY = "structure-aware"
FILTER_TAGS = ["vegan"]


def format_result(r) -> dict:
    return {
        "chunk_id": r.chunk_id,
        "score": round(r.score, 4),
        "recipe_id": r.metadata.recipe_id,
        "section": r.metadata.section,
        "dietary_tags": r.metadata.dietary_tags,
    }


def main() -> None:
    settings = get_settings()
    embedding_model = get_embedding_model()
    store = ChromaStore(settings.chroma_persist_path)
    retriever = Retriever(store, embedding_model)

    for query in CANDIDATE_QUERIES:
        unfiltered = retriever.search(query, strategy=STRATEGY, top_k=settings.top_k)
        filtered = retriever.search(
            query,
            strategy=STRATEGY,
            top_k=settings.top_k,
            filters=SearchFilters(dietary_tags=FILTER_TAGS),
        )

        if not unfiltered or not filtered:
            continue

        if unfiltered[0].chunk_id != filtered[0].chunk_id:
            report = {
                "query": query,
                "strategy": STRATEGY,
                "filter": {"dietary_tags": FILTER_TAGS},
                "unfiltered_top_5": [format_result(r) for r in unfiltered],
                "filtered_top_5": [format_result(r) for r in filtered],
                "unfiltered_top_1": format_result(unfiltered[0]),
                "filtered_top_1": format_result(filtered[0]),
            }
            OUTPUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(f"Query: {query}")
            print(f"Unfiltered Top-1: {unfiltered[0].chunk_id} (recipe={unfiltered[0].metadata.recipe_id}, "
                  f"tags={unfiltered[0].metadata.dietary_tags})")
            print(f"Filtered Top-1 (dietary_tags={FILTER_TAGS}): {filtered[0].chunk_id} "
                  f"(recipe={filtered[0].metadata.recipe_id}, tags={filtered[0].metadata.dietary_tags})")
            print(f"\nFull report written to {OUTPUT_PATH}")
            return

    raise RuntimeError(
        "None of the candidate queries produced a Top-1 change under the dietary_tags filter. "
        "Add more candidate queries to CANDIDATE_QUERIES."
    )


if __name__ == "__main__":
    main()
