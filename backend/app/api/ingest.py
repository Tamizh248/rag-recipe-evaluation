from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_store
from app.chunking.current_chunker import CurrentChunker
from app.chunking.structure_aware_chunker import StructureAwareChunker
from app.core.config import get_settings
from app.embeddings.sentence_transformer import get_embedding_model
from app.services.ingestion_service import ingest_recipes
from app.vectorstore.chroma_store import ChromaStore

router = APIRouter()


class IngestRequest(BaseModel):
    strategy: Literal["current", "structure-aware", "both"] = "both"


class IngestResultItem(BaseModel):
    strategy: str
    recipe_count: int
    chunk_count: int


class IngestResponse(BaseModel):
    results: list[IngestResultItem]


def _build_chunker(strategy: str):
    settings = get_settings()
    if strategy == "current":
        return CurrentChunker(
            chunk_size=settings.current_chunk_size, chunk_overlap=settings.current_chunk_overlap
        )
    return StructureAwareChunker()


@router.post("/api/ingest", response_model=IngestResponse)
def ingest(
    request: IngestRequest = IngestRequest(), store: ChromaStore = Depends(get_store)
) -> IngestResponse:
    settings = get_settings()
    embedding_model = get_embedding_model()
    strategies = ["current", "structure-aware"] if request.strategy == "both" else [request.strategy]

    results = []
    for strategy in strategies:
        chunker = _build_chunker(strategy)
        result = ingest_recipes(settings.recipes_dir, chunker, embedding_model, store)
        results.append(
            IngestResultItem(strategy=strategy, recipe_count=result.recipe_count, chunk_count=result.chunk_count)
        )
    return IngestResponse(results=results)
