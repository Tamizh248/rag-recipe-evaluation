from app.ingestion.parser import ParsedRecipe
from app.models.chunk import ChunkingStrategy, ChunkMetadata, Section

REQUIRED_FIELDS = ("chunk_id", "source_file", "recipe_id", "cuisine", "section", "chunking_strategy")


class IngestionError(Exception):
    """Raised when a document or chunk fails metadata validation."""


def build_chunk_id(recipe_id: str, strategy: ChunkingStrategy, section: Section, index: int) -> str:
    return f"{recipe_id}_{strategy}_{section}_{index:03d}"


def build_chunk_metadata(
    parsed: ParsedRecipe,
    strategy: ChunkingStrategy,
    section: Section,
    index: int,
) -> ChunkMetadata:
    metadata = ChunkMetadata(
        chunk_id=build_chunk_id(parsed.recipe_id, strategy, section, index),
        source_file=parsed.source_file,
        recipe_id=parsed.recipe_id,
        cuisine=parsed.cuisine,
        dietary_tags=parsed.dietary_tags,
        section=section,
        chunking_strategy=strategy,
    )
    validate_metadata(metadata)
    return metadata


def validate_metadata(metadata: ChunkMetadata) -> None:
    for field_name in REQUIRED_FIELDS:
        value = getattr(metadata, field_name)
        if not value:
            raise IngestionError(
                f"Ingestion failure: chunk metadata missing required field '{field_name}' "
                f"(chunk_id={metadata.chunk_id!r})"
            )


def validate_parsed_recipe(parsed: ParsedRecipe) -> None:
    if not parsed.recipe_id:
        raise IngestionError(f"Ingestion failure: could not determine recipe_id for {parsed.source_file}")
    if not parsed.cuisine:
        raise IngestionError(f"Ingestion failure: missing 'cuisine' front-matter in {parsed.source_file}")
    if not parsed.is_well_formed:
        raise IngestionError(
            f"Ingestion failure: {parsed.source_file} is missing one or more required sections "
            f"(title/ingredients/method/allergens)"
        )
