from pathlib import Path
from typing import Any

import chromadb

from app.core.constants import KNOWN_DIETARY_TAGS, dietary_flag_key
from app.models.chunk import Chunk, ChunkingStrategy, ChunkMetadata
from app.models.search import SearchFilters

COLLECTION_NAMES: dict[ChunkingStrategy, str] = {
    "current": "recipe_chunks_current",
    "structure_aware": "recipe_chunks_structure_aware",
}


def build_where_clause(filters: SearchFilters | None) -> dict[str, Any] | None:
    """Translate SearchFilters into a ChromaDB `where` clause.

    This is executed BY the vector database at query time (a real ANN +
    metadata filter), never as a Python post-filter over already-returned
    results.
    """
    if filters is None or not filters.dietary_tags:
        return None

    conditions = [{dietary_flag_key(tag): True} for tag in filters.dietary_tags]
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def _chunk_to_stored_metadata(metadata: ChunkMetadata) -> dict[str, Any]:
    stored: dict[str, Any] = {
        "source_file": metadata.source_file,
        "recipe_id": metadata.recipe_id,
        "cuisine": metadata.cuisine,
        "section": metadata.section,
        "chunking_strategy": metadata.chunking_strategy,
        "dietary_tags": ",".join(metadata.dietary_tags),
    }
    tag_set = set(metadata.dietary_tags)
    for tag in KNOWN_DIETARY_TAGS:
        stored[dietary_flag_key(tag)] = tag in tag_set
    return stored


def _stored_metadata_to_chunk_metadata(chunk_id: str, stored: dict[str, Any]) -> ChunkMetadata:
    dietary_tags_str = stored.get("dietary_tags", "") or ""
    dietary_tags = [t for t in dietary_tags_str.split(",") if t]
    return ChunkMetadata(
        chunk_id=chunk_id,
        source_file=stored["source_file"],
        recipe_id=stored["recipe_id"],
        cuisine=stored["cuisine"],
        dietary_tags=dietary_tags,
        section=stored["section"],
        chunking_strategy=stored["chunking_strategy"],
    )


class RetrievedChunk:
    def __init__(self, chunk_id: str, text: str, metadata: ChunkMetadata, score: float):
        self.chunk_id = chunk_id
        self.text = text
        self.metadata = metadata
        self.score = score


class ChromaStore:
    """Wraps a persistent ChromaDB client with two isolated collections,
    one per chunking strategy, sharing the same embedding model, embedding
    dimension, and similarity metric (cosine) so the only experimental
    variable between them is the chunking strategy itself.
    """

    def __init__(self, persist_directory: Path):
        persist_directory.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(persist_directory))

    def get_collection(self, strategy: ChunkingStrategy):
        return self.client.get_or_create_collection(
            name=COLLECTION_NAMES[strategy],
            metadata={"hnsw:space": "cosine"},
        )

    def reset_collection(self, strategy: ChunkingStrategy) -> None:
        try:
            self.client.delete_collection(COLLECTION_NAMES[strategy])
        except Exception:
            pass

    def add_chunks(
        self, strategy: ChunkingStrategy, chunks: list[Chunk], embeddings: list[list[float]]
    ) -> None:
        if not chunks:
            return
        collection = self.get_collection(strategy)
        collection.add(
            ids=[c.chunk_id for c in chunks],
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            metadatas=[_chunk_to_stored_metadata(c.metadata) for c in chunks],
        )

    def count(self, strategy: ChunkingStrategy) -> int:
        return self.get_collection(strategy).count()

    def get_chunk(self, strategy: ChunkingStrategy, chunk_id: str) -> RetrievedChunk | None:
        collection = self.get_collection(strategy)
        result = collection.get(ids=[chunk_id], include=["documents", "metadatas"])
        if not result["ids"]:
            return None
        metadata = _stored_metadata_to_chunk_metadata(chunk_id, result["metadatas"][0])
        return RetrievedChunk(chunk_id=chunk_id, text=result["documents"][0], metadata=metadata, score=1.0)

    def query(
        self,
        strategy: ChunkingStrategy,
        query_embedding: list[float],
        top_k: int,
        filters: SearchFilters | None = None,
    ) -> list[RetrievedChunk]:
        collection = self.get_collection(strategy)
        where = build_where_clause(filters)
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        ids = result["ids"][0]
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]

        retrieved = []
        for chunk_id, text, stored_metadata, distance in zip(ids, documents, metadatas, distances):
            metadata = _stored_metadata_to_chunk_metadata(chunk_id, stored_metadata)
            score = 1.0 - distance  # cosine distance -> cosine similarity
            retrieved.append(RetrievedChunk(chunk_id=chunk_id, text=text, metadata=metadata, score=score))
        return retrieved
