"""Measure dense-only versus BM25 + RRF retrieval on the Task B golden set.

Run from backend after ingesting the structure-aware collection:
    python scripts/evaluate_hybrid_retrieval.py
"""

import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.embeddings.sentence_transformer import get_embedding_model
from app.retrieval.retriever import RRF_K, Retriever
from app.vectorstore.chroma_store import ChromaStore

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_SET_PATH = ROOT / "evaluation" / "golden_set.jsonl"
OUTPUT_PATH = ROOT / "evaluation" / "hybrid_retrieval_dump.json"
STRATEGY = "structure-aware"
TOP_K = 3
MEASUREMENTS_PER_QUESTION = 5


def load_golden_set() -> list[dict]:
    return [
        json.loads(line)
        for line in GOLDEN_SET_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def retrieve_and_measure(retriever: Retriever, question: str, hybrid: bool) -> tuple[list, list[float]]:
    search = retriever.search if hybrid else retriever.search_dense
    # Warm the already-loaded embedding model and Chroma client; startup is not query latency.
    search(question, strategy=STRATEGY, top_k=TOP_K)
    latencies_ms = []
    result = []
    for _ in range(MEASUREMENTS_PER_QUESTION):
        started = time.perf_counter()
        result = search(question, strategy=STRATEGY, top_k=TOP_K)
        latencies_ms.append((time.perf_counter() - started) * 1000)
    return result, latencies_ms


def main() -> None:
    settings = get_settings()
    store = ChromaStore(settings.chroma_persist_path)
    if store.count("structure_aware") == 0:
        raise RuntimeError("Structure-aware collection is empty. Run scripts/ingest_recipes.py --strategy structure-aware first.")

    retriever = Retriever(store, get_embedding_model())
    questions = load_golden_set()
    records = []
    baseline_latencies = []
    hybrid_latencies = []

    for item in questions:
        dense_results, dense_times = retrieve_and_measure(retriever, item["question"], hybrid=False)
        hybrid_results, hybrid_times = retrieve_and_measure(retriever, item["question"], hybrid=True)
        dense_ids = [result.chunk_id for result in dense_results]
        hybrid_ids = [result.chunk_id for result in hybrid_results]
        expected = item["correct_chunk_id"]
        baseline_latencies.extend(dense_times)
        hybrid_latencies.extend(hybrid_times)

        # Every golden-set target is a known chunk in this corpus. A baseline miss
        # is therefore an R failure; G and Not-In-Corpus require no labels here.
        baseline_label = "R" if expected not in dense_ids else None
        evidence = (
            f"Correct chunk {expected} is absent from dense top-3: {dense_ids}."
            if baseline_label
            else None
        )
        records.append(
            {
                **item,
                "dense_top_3": dense_ids,
                "hybrid_top_3": hybrid_ids,
                "baseline_hit": expected in dense_ids,
                "after_hit": expected in hybrid_ids,
                "baseline_failure_label": baseline_label,
                "inspection_evidence": evidence,
                "outcome": (
                    "fixed" if expected not in dense_ids and expected in hybrid_ids
                    else "still-broken" if expected not in hybrid_ids
                    else "unaffected-hit"
                ),
            }
        )

    payload = {
        "golden_set": str(GOLDEN_SET_PATH.relative_to(ROOT)).replace("\\", "/"),
        "strategy": STRATEGY,
        "top_k": TOP_K,
        "retrieval_change": {"name": "BM25 + RRF", "rrf_k": RRF_K},
        "latency_measurements_per_question": MEASUREMENTS_PER_QUESTION,
        "baseline": {
            "name": "dense-only cosine retrieval",
            "hit_rate_at_3": sum(record["baseline_hit"] for record in records) / len(records),
            "p50_latency_ms": statistics.median(baseline_latencies),
        },
        "after": {
            "name": "BM25 + dense RRF retrieval",
            "hit_rate_at_3": sum(record["after_hit"] for record in records) / len(records),
            "p50_latency_ms": statistics.median(hybrid_latencies),
        },
        "failure_tally": {
            "R": sum(record["baseline_failure_label"] == "R" for record in records),
            "G": 0,
            "Not-In-Corpus": 0,
        },
        "questions": records,
    }
    print(json.dumps(payload, indent=2))
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
