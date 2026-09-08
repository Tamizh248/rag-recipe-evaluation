from app.chunking.base import Chunker, RecipeDocument
from app.ingestion.metadata import build_chunk_metadata
from app.models.chunk import Chunk


class StructureAwareChunker(Chunker):
    """Recipe-structure-aware chunker.

    Understands that a recipe card has four logical units: title/overview,
    ingredient table, method, and allergen note. Each unit becomes exactly
    one chunk, and every chunk is prefixed with the recipe title so it is
    self-contained even when retrieved in isolation. Critically, the entire
    ingredient table (header + every row) always travels together with the
    recipe title in a single chunk - an ingredient row is never split from
    its header or its parent recipe.
    """

    strategy = "structure_aware"

    def chunk(self, document: RecipeDocument) -> list[Chunk]:
        parsed = document.parsed
        chunks: list[Chunk] = []

        title_text = "\n".join(filter(None, [f"Recipe: {parsed.title}", parsed.overview_text]))
        if title_text.strip():
            metadata = build_chunk_metadata(parsed, self.strategy, "title", 0)
            chunks.append(Chunk(text=title_text.strip(), metadata=metadata))

        if parsed.ingredient_rows:
            lines = [f"Recipe: {parsed.title}", "Ingredients:"]
            if parsed.ingredient_header:
                lines.append(parsed.ingredient_header)
            lines.extend(parsed.ingredient_rows)
            metadata = build_chunk_metadata(parsed, self.strategy, "ingredients", 1)
            chunks.append(Chunk(text="\n".join(lines), metadata=metadata))

        if parsed.method_steps:
            lines = [f"Recipe: {parsed.title}", "Method:"]
            lines.extend(f"{i + 1}. {step}" for i, step in enumerate(parsed.method_steps))
            metadata = build_chunk_metadata(parsed, self.strategy, "method", 2)
            chunks.append(Chunk(text="\n".join(lines), metadata=metadata))

        if parsed.allergens_text:
            lines = [f"Recipe: {parsed.title}", "Allergens:", parsed.allergens_text]
            metadata = build_chunk_metadata(parsed, self.strategy, "allergens", 3)
            chunks.append(Chunk(text="\n".join(lines), metadata=metadata))

        return chunks
