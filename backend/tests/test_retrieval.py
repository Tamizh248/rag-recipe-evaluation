from app.models.search import SearchFilters


def test_search_returns_requested_fields(retriever):
    results = retriever.search(
        "How much salt is used in the Sourdough Country Loaf?", strategy="structure-aware", top_k=5
    )
    assert results
    for r in results:
        assert r.chunk_id
        assert isinstance(r.score, float)
        assert r.metadata.recipe_id
        assert r.metadata.section
        assert r.metadata.source_file
        assert r.text


def test_search_respects_top_k(retriever):
    results = retriever.search("bread", strategy="structure-aware", top_k=2)
    assert len(results) <= 2


def test_top_result_for_salt_question_is_sourdough_country(retriever):
    results = retriever.search(
        "How much salt, in grams, is used in the Sourdough Country Loaf recipe?",
        strategy="structure-aware",
        top_k=5,
    )
    assert results[0].metadata.recipe_id == "sourdough_country_2kg"
    assert results[0].metadata.section == "ingredients"


def test_dietary_tag_filter_is_applied_at_the_database_level(retriever):
    unfiltered = retriever.search("bread with butter and eggs", strategy="structure-aware", top_k=6)
    filtered = retriever.search(
        "bread with butter and eggs",
        strategy="structure-aware",
        top_k=6,
        filters=SearchFilters(dietary_tags=["vegan"]),
    )

    unfiltered_recipe_ids = {r.metadata.recipe_id for r in unfiltered}
    filtered_recipe_ids = {r.metadata.recipe_id for r in filtered}

    # the non-vegan brioche recipe must appear unfiltered but never under the vegan filter
    assert "brioche_sourdough_900g" in unfiltered_recipe_ids
    assert "brioche_sourdough_900g" not in filtered_recipe_ids
    for r in filtered:
        assert "vegan" in r.metadata.dietary_tags


def test_current_vs_structure_aware_use_isolated_collections(retriever):
    current_results = retriever.search("salt", strategy="current", top_k=5)
    structure_results = retriever.search("salt", strategy="structure-aware", top_k=5)
    assert all(r.metadata.chunking_strategy == "current" for r in current_results)
    assert all(r.metadata.chunking_strategy == "structure_aware" for r in structure_results)
