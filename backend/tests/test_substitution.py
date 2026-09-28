from evals import assertions


def test_valid_substitution_swaps_ingredient_and_keeps_other_allergens(substitution_service):
    response = substitution_service.substitute("brioche_sourdough_900g", "unsalted butter", "vegan")

    assert response.refused is False
    assert response.substitute_ingredient == "vegan butter or coconut oil"
    assert any("vegan butter or coconut oil" in line for line in response.adapted_ingredients)
    # dairy must survive - whole milk is still in this recipe, only butter was swapped
    assert "dairy" in response.allergens.lower()


def test_substitute_can_introduce_a_new_allergen(substitution_service):
    response = substitution_service.substitute("brioche_sourdough_900g", "whole milk", "vegan")

    assert response.refused is False
    assert "tree-nuts" in response.allergens.lower()


def test_removed_allergen_is_dropped_when_no_other_ingredient_carries_it(substitution_service):
    response = substitution_service.substitute("cinnamon_raisin_walnut_800g", "walnuts (chopped)", "nut-free")

    assert response.refused is False
    assert "tree-nuts" not in response.allergens.lower()


def test_refuses_when_ingredient_not_in_recipe(substitution_service):
    response = substitution_service.substitute("brioche_sourdough_900g", "ground cinnamon", "vegan")
    assert response.refused is True


def test_refuses_when_no_substitute_on_file(substitution_service):
    response = substitution_service.substitute("rosemary_olive_focaccia_1500g", "fresh rosemary", "vegan")
    assert response.refused is True


def test_refuses_on_unknown_diet(substitution_service):
    response = substitution_service.substitute("sourdough_country_2kg", "bread flour", "nonsense-diet")
    assert response.refused is True


def test_refuses_on_unknown_recipe(substitution_service):
    response = substitution_service.substitute("does_not_exist", "bread flour", "vegan")
    assert response.refused is True


def test_citations_all_belong_to_the_requested_recipe(substitution_service):
    response = substitution_service.substitute("rye_sourdough_900g", "dark rye flour", "gluten-free")
    assert response.refused is False
    assert all(c.chunk_id.startswith("rye_sourdough_900g") for c in response.citations)


def test_deterministic_assertions_pass_on_a_real_valid_substitution(substitution_service):
    response = substitution_service.substitute("sourdough_country_2kg", "bread flour", "gluten-free")
    for fn in assertions.ASSERTIONS:
        ok, detail = fn(response)
        assert ok, detail
