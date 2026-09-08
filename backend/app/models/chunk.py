from typing import Literal

from pydantic import BaseModel, Field

Section = Literal["title", "ingredients", "method", "allergens"]
ChunkingStrategy = Literal["current", "structure_aware"]


class ChunkMetadata(BaseModel):
    chunk_id: str
    source_file: str
    recipe_id: str
    cuisine: str
    dietary_tags: list[str] = Field(default_factory=list)
    section: Section
    chunking_strategy: ChunkingStrategy


class Chunk(BaseModel):
    text: str
    metadata: ChunkMetadata

    @property
    def chunk_id(self) -> str:
        return self.metadata.chunk_id
