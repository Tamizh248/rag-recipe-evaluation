from app.chunking.base import RecipeDocument
from app.chunking.current_chunker import CurrentChunker
from app.chunking.structure_aware_chunker import StructureAwareChunker
from app.ingestion.loader import load_documents
from app.ingestion.parser import parse_recipe, strip_frontmatter


def _load(settings, filename):
    docs = {d.source_file: d for d in load_documents(settings.recipes_dir)}
    doc = docs[filename]
    parsed = parse_recipe(doc.source_file, doc.text)
    return RecipeDocument(parsed=parsed, body=strip_frontmatter(doc.text))


def test_structure_aware_chunker_keeps_title_header_and_rows_together(settings):
    rdoc = _load(settings, "sourdough_country_2kg.txt")
    chunks = StructureAwareChunker().chunk(rdoc)
    ingredients_chunk = next(c for c in chunks if c.metadata.section == "ingredients")

    assert "Recipe: Sourdough Country Loaf" in ingredients_chunk.text
    assert "Ingredient | Weight | Baker's Percentage" in ingredients_chunk.text
    assert "Fine Sea Salt | 20g | 2%" in ingredients_chunk.text
    # every other ingredient row for this recipe must be present too
    assert "Bread Flour | 1000g | 100%" in ingredients_chunk.text
    assert "Water | 750g | 75%" in ingredients_chunk.text
    assert "Active Sourdough Starter | 200g | 20%" in ingredients_chunk.text


def test_structure_aware_chunker_produces_exactly_one_chunk_per_section(settings):
    rdoc = _load(settings, "brioche_sourdough_900g.txt")
    chunks = StructureAwareChunker().chunk(rdoc)
    sections = [c.metadata.section for c in chunks]
    assert sections == ["title", "ingredients", "method", "allergens"]


def test_current_chunker_can_separate_a_row_from_its_header(settings):
    """Documents the known baseline-chunker weakness (see results.md): with
    small enough windows, a naive fixed-size split CAN isolate an ingredient
    row from its table header and recipe title. This is the exact failure
    mode the structure-aware chunker is designed to avoid.
    """
    rdoc = _load(settings, "cinnamon_raisin_walnut_800g.txt")
    chunks = CurrentChunker(chunk_size=250, chunk_overlap=50).chunk(rdoc)
    ingredient_chunks = [c for c in chunks if c.metadata.section == "ingredients"]

    assert len(ingredient_chunks) >= 2
    tail_chunk = ingredient_chunks[-1]
    assert "Walnuts (chopped) | 75g | 15%" in tail_chunk.text
    assert "Ingredient | Weight | Baker's Percentage" not in tail_chunk.text
    assert "Recipe: Cinnamon Raisin Walnut Sourdough" not in tail_chunk.text


def test_current_chunker_has_no_special_knowledge_of_section_boundaries(settings):
    """The baseline chunker's boundaries must be pure character-count math,
    unaffected by where section headers fall.
    """
    rdoc = _load(settings, "rye_sourdough_900g.txt")
    chunker = CurrentChunker(chunk_size=250, chunk_overlap=50)
    chunks = chunker.chunk(rdoc)
    step = chunker.chunk_size - chunker.chunk_overlap
    for i, chunk in enumerate(chunks[:-1]):
        expected_start = i * step
        # chunk text is a stripped slice of body[expected_start:expected_start+chunk_size]
        raw_slice = rdoc.body[expected_start : expected_start + chunker.chunk_size]
        assert chunk.text == raw_slice.strip()
