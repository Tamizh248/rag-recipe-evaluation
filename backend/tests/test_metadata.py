import pytest

from app.chunking.base import RecipeDocument
from app.chunking.current_chunker import CurrentChunker
from app.chunking.structure_aware_chunker import StructureAwareChunker
from app.ingestion.loader import load_documents
from app.ingestion.metadata import IngestionError, validate_metadata
from app.ingestion.parser import parse_recipe, strip_frontmatter
from app.models.chunk import ChunkMetadata

REQUIRED_FIELDS = ("source_file", "recipe_id", "cuisine", "dietary_tags")


def _all_recipe_documents(settings):
    docs = load_documents(settings.recipes_dir)
    result = []
    for doc in docs:
        parsed = parse_recipe(doc.source_file, doc.text)
        body = strip_frontmatter(doc.text)
        result.append(RecipeDocument(parsed=parsed, body=body))
    return result


def test_current_chunker_chunks_have_required_metadata(settings):
    chunker = CurrentChunker(chunk_size=settings.current_chunk_size, chunk_overlap=settings.current_chunk_overlap)
    for rdoc in _all_recipe_documents(settings):
        chunks = chunker.chunk(rdoc)
        assert chunks, f"no chunks produced for {rdoc.parsed.source_file}"
        for chunk in chunks:
            assert chunk.metadata.source_file, f"missing source_file on {chunk.chunk_id}"
            assert chunk.metadata.recipe_id, f"missing recipe_id on {chunk.chunk_id}"
            assert chunk.metadata.cuisine, f"missing cuisine on {chunk.chunk_id}"
            assert isinstance(chunk.metadata.dietary_tags, list)


def test_structure_aware_chunker_chunks_have_required_metadata(settings):
    chunker = StructureAwareChunker()
    for rdoc in _all_recipe_documents(settings):
        chunks = chunker.chunk(rdoc)
        assert len(chunks) == 4, f"expected 4 structural chunks for {rdoc.parsed.source_file}"
        for chunk in chunks:
            assert chunk.metadata.source_file, f"missing source_file on {chunk.chunk_id}"
            assert chunk.metadata.recipe_id, f"missing recipe_id on {chunk.chunk_id}"
            assert chunk.metadata.cuisine, f"missing cuisine on {chunk.chunk_id}"
            assert isinstance(chunk.metadata.dietary_tags, list)
            assert len(chunk.metadata.dietary_tags) > 0


def test_all_six_recipes_produce_vegan_or_vegetarian_tag(settings):
    # Sanity check that front-matter dietary_tags actually made it through parsing.
    for rdoc in _all_recipe_documents(settings):
        tags = rdoc.parsed.dietary_tags
        assert "vegan" in tags or "vegetarian" in tags


def test_chunk_missing_source_file_is_ingestion_failure():
    metadata = ChunkMetadata(
        chunk_id="x_current_title_000",
        source_file="",
        recipe_id="x",
        cuisine="bread",
        dietary_tags=["vegan"],
        section="title",
        chunking_strategy="current",
    )
    with pytest.raises(IngestionError):
        validate_metadata(metadata)
