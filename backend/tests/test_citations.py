from app.generation.grounding import validate_citations
from app.models.chat import Citation, GroundedAnswer


def test_validate_citations_true_when_all_ids_in_retrieved_set():
    answer = GroundedAnswer(answerable=True, answer="...", citations=[Citation(chunk_id="c1")])
    assert validate_citations(answer, retrieved_chunk_ids={"c1", "c2"}) is True


def test_validate_citations_false_when_id_missing_from_retrieved_set():
    answer = GroundedAnswer(answerable=True, answer="...", citations=[Citation(chunk_id="fabricated")])
    assert validate_citations(answer, retrieved_chunk_ids={"c1", "c2"}) is False


def test_valid_chunk_id_resolves_in_vector_store(store):
    chunk = store.get_chunk("structure_aware", "sourdough_country_2kg_structure_aware_ingredients_001")
    assert chunk is not None
    assert chunk.metadata.recipe_id == "sourdough_country_2kg"
    assert "Fine Sea Salt" in chunk.text


def test_invalid_chunk_id_does_not_resolve_in_vector_store(store):
    chunk = store.get_chunk("structure_aware", "this_chunk_id_does_not_exist_999")
    assert chunk is None


def test_citation_recipe_mismatch_is_detectable(store):
    # citing a real chunk_id but from the WRONG recipe than claimed
    chunk = store.get_chunk("structure_aware", "brioche_sourdough_900g_structure_aware_ingredients_001")
    assert chunk is not None
    assert chunk.metadata.recipe_id != "sourdough_country_2kg"
