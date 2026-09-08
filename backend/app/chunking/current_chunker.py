from app.chunking.base import Chunker, RecipeDocument
from app.ingestion.metadata import build_chunk_metadata
from app.ingestion.parser import get_section_spans
from app.models.chunk import Chunk, Section


class CurrentChunker(Chunker):
    """Baseline / naive chunker: fixed-size character windows with overlap.

    This chunker has NO knowledge of recipe structure. It slides a
    fixed-size window over the raw document text regardless of where
    section boundaries (title / ingredients / method / allergens) fall, so
    it will happily split an ingredient row away from its table header, or
    glue the tail of one section to the head of the next.

    A `section` label is still attached to each chunk (required by the
    metadata schema) by finding which known section span the chunk
    overlaps most - but that labeling happens AFTER chunk boundaries are
    already fixed by character count alone, and never influences where a
    chunk starts or ends.
    """

    strategy = "current"

    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 80):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be >= 0 and smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, document: RecipeDocument) -> list[Chunk]:
        parsed = document.parsed
        body = document.body
        text_len = len(body)
        if text_len == 0:
            return []

        spans = get_section_spans(body)
        step = self.chunk_size - self.chunk_overlap

        chunks: list[Chunk] = []
        index = 0
        start = 0
        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            piece = body[start:end].strip()
            if piece:
                section = self._dominant_section(spans, start, end)
                metadata = build_chunk_metadata(parsed, self.strategy, section, index)
                chunks.append(Chunk(text=piece, metadata=metadata))
                index += 1
            if end == text_len:
                break
            start += step

        return chunks

    @staticmethod
    def _dominant_section(spans: dict[str, tuple[int, int]], start: int, end: int) -> Section:
        best_section: Section = "title"
        best_overlap = -1
        for section, (s_start, s_end) in spans.items():
            overlap = min(end, s_end) - max(start, s_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_section = section  # type: ignore[assignment]
        return best_section
