"""Ingest the 6 fermentation recipe cards using one chunking strategy.

Usage:
    python scripts/ingest_recipes.py --strategy current
    python scripts/ingest_recipes.py --strategy structure-aware
    python scripts/ingest_recipes.py --strategy both   # ingest into both collections
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.chunking.current_chunker import CurrentChunker
from app.chunking.structure_aware_chunker import StructureAwareChunker
from app.core.config import get_settings
from app.embeddings.sentence_transformer import get_embedding_model
from app.services.ingestion_service import ingest_recipes
from app.vectorstore.chroma_store import ChromaStore


def build_chunker(strategy: str, settings):
    if strategy == "current":
        return CurrentChunker(
            chunk_size=settings.current_chunk_size,
            chunk_overlap=settings.current_chunk_overlap,
        )
    if strategy == "structure-aware":
        return StructureAwareChunker()
    raise ValueError(f"Unknown strategy: {strategy}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strategy",
        choices=["current", "structure-aware", "both"],
        default="both",
        help="Which chunking strategy to ingest with (default: both)",
    )
    args = parser.parse_args()

    settings = get_settings()
    embedding_model = get_embedding_model()
    store = ChromaStore(settings.chroma_persist_path)

    strategies = ["current", "structure-aware"] if args.strategy == "both" else [args.strategy]

    for strategy in strategies:
        chunker = build_chunker(strategy, settings)
        result = ingest_recipes(
            recipes_dir=settings.recipes_dir,
            chunker=chunker,
            embedding_model=embedding_model,
            store=store,
        )
        print(f"[{strategy}] ingested {result.recipe_count} recipes -> {result.chunk_count} chunks")
        for chunk_id in result.chunk_ids:
            print(f"    {chunk_id}")


if __name__ == "__main__":
    main()
