from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.ingestion.parser import ParsedRecipe
from app.models.chunk import Chunk, ChunkingStrategy


@dataclass
class RecipeDocument:
    """A loaded + parsed recipe, ready to be chunked."""

    parsed: ParsedRecipe
    body: str  # raw source text with front-matter stripped


class Chunker(ABC):
    strategy: ChunkingStrategy

    @abstractmethod
    def chunk(self, document: RecipeDocument) -> list[Chunk]:
        """Split a single recipe document into chunks with metadata attached."""
        raise NotImplementedError
