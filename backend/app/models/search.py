from typing import Literal

from pydantic import BaseModel, Field

from app.models.chunk import ChunkMetadata

Strategy = Literal["current", "structure-aware"]


class SearchFilters(BaseModel):
    dietary_tags: list[str] | None = None


class SearchRequest(BaseModel):
    question: str
    top_k: int = 5
    strategy: Strategy = "structure-aware"
    filters: SearchFilters = Field(default_factory=SearchFilters)


class SearchResultItem(BaseModel):
    chunk_id: str
    score: float
    recipe_id: str
    section: str
    source_file: str
    text: str
    metadata: ChunkMetadata


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
