"""Run 3 answerable + 3 unanswerable questions through the FULL grounded
generation pipeline (retrieval -> grounding -> LLM -> citation/refusal
checks) and save transcripts.

Usage:
    python scripts/evaluate_generation.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.embeddings.sentence_transformer import get_embedding_model
from app.generation.llm import get_llm_provider
from app.retrieval.retriever import Retriever
from app.services.chat_service import ChatService
from app.vectorstore.chroma_store import ChromaStore

BACKEND_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = BACKEND_DIR.parent / "evaluation"
QUESTIONS_PATH = EVAL_DIR / "questions.json"
OUTPUT_PATH = EVAL_DIR / "generation_dump.json"

# One ingredient, one method, one allergen question - a spread across
# question types, all with HIT@5 confirmed in search_dump.json.
ANSWERABLE_QUESTION_IDS = ["Q1", "Q5", "Q7"]
STRATEGY = "structure-aware"


def main() -> None:
    settings = get_settings()
    embedding_model = get_embedding_model()
    store = ChromaStore(settings.chroma_persist_path)
    retriever = Retriever(store, embedding_model)
    llm_provider = get_llm_provider(settings.llm_provider, settings.llm_api_key, settings.llm_model)
    chat_service = ChatService(retriever, llm_provider, top_k=settings.top_k)

    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    retrieval_questions = {q["id"]: q for q in data["retrieval_questions"]}
    unanswerable_questions = data["unanswerable_questions"]

    results = {
        "provider": settings.llm_provider,
        "model": settings.llm_model if settings.llm_provider == "anthropic" else "local-extractive (no API key)",
        "strategy": STRATEGY,
        "answerable": [],
        "unanswerable": [],
    }

    print("=== Answerable questions ===\n")
    for qid in ANSWERABLE_QUESTION_IDS:
        q = retrieval_questions[qid]
        response = chat_service.answer(q["question"], strategy=STRATEGY)
        entry = {
            "id": qid,
            "question": q["question"],
            "expected_recipe_id": q["expected_recipe_id"],
            "answer": response.answer,
            "refused": response.refused,
            "citations": [c.chunk_id for c in response.citations],
        }
        results["answerable"].append(entry)
        print(f"[{qid}] Q: {q['question']}")
        print(f"      A: {response.answer}")
        print(f"      Citations: {entry['citations']}")
        print(f"      Refused: {response.refused}\n")

    print("=== Unanswerable questions (must refuse) ===\n")
    for q in unanswerable_questions:
        response = chat_service.answer(q["question"], strategy=STRATEGY)
        entry = {
            "id": q["id"],
            "question": q["question"],
            "answer": response.answer,
            "refused": response.refused,
            "citations": [c.chunk_id for c in response.citations],
        }
        results["unanswerable"].append(entry)
        print(f"[{q['id']}] Q: {q['question']}")
        print(f"      A: {response.answer}")
        print(f"      Refused: {response.refused}\n")

    OUTPUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Full generation dump written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
