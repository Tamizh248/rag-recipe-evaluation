"""Week 6 eval set: 25 substitution cases + 2 regression cases pinned to real
Week-5 traces.

Mode tags: the task asks for each case to be tagged with a Week-5 taxonomy
mode. `evaluation/week5/taxonomy.md` is still a blank template (not filled
in yet), so the `mode` values below are PROVISIONAL, substitution-domain
placeholders describing the actual outcome each case exercises - not a
substitute for the real taxonomy. Once taxonomy.md is filled in and
committed, rename these to match it (or add a mapping) so this eval set
and the Week-5 taxonomy speak the same language; the harness (harness.py)
only ever groups by whatever string is in `mode`, so renaming is a
one-line change per case, not a rewrite.
"""

from dataclasses import dataclass, field

from app.substitution.tables import Allergen


@dataclass(frozen=True)
class SubstitutionCase:
    id: str
    recipe_id: str
    ingredient: str
    diet: str
    expect_answerable: bool
    mode: str
    notes: str = ""
    # Only meaningful when expect_answerable=True - the deterministic ground
    # truth the assertions check the generated answer against.
    expected_allergens: frozenset = field(default_factory=frozenset)
    expected_servings: str | None = None


CASES: list[SubstitutionCase] = [
    # --- answerable: a verified substitute exists on file ---
    SubstitutionCase(
        "S01", "brioche_sourdough_900g", "unsalted butter", "vegan", True, "verified_substitute_applied",
        expected_allergens=frozenset({Allergen.GLUTEN, Allergen.DAIRY, Allergen.EGGS}),
        expected_servings="Yields approximately 1060g of dough, enough for one 900g pan loaf.",
        notes="dairy is retained (whole milk is still in the recipe) even after butter is removed.",
    ),
    SubstitutionCase(
        "S02", "brioche_sourdough_900g", "unsalted butter", "dairy-free", True, "verified_substitute_applied",
        expected_allergens=frozenset({Allergen.GLUTEN, Allergen.DAIRY, Allergen.EGGS}),
        expected_servings="Yields approximately 1060g of dough, enough for one 900g pan loaf.",
    ),
    SubstitutionCase(
        "S03", "brioche_sourdough_900g", "whole milk", "vegan", True, "substitute_introduces_new_allergen",
        expected_allergens=frozenset({Allergen.GLUTEN, Allergen.DAIRY, Allergen.EGGS, Allergen.TREE_NUTS}),
        expected_servings="Yields approximately 1060g of dough, enough for one 900g pan loaf.",
        notes="oat/almond milk substitute introduces tree-nuts, which was NOT in the original allergen list.",
    ),
    SubstitutionCase(
        "S04", "brioche_sourdough_900g", "whole milk", "dairy-free", True, "substitute_introduces_new_allergen",
        expected_allergens=frozenset({Allergen.GLUTEN, Allergen.DAIRY, Allergen.EGGS, Allergen.TREE_NUTS}),
        expected_servings="Yields approximately 1060g of dough, enough for one 900g pan loaf.",
    ),
    SubstitutionCase(
        "S05", "brioche_sourdough_900g", "eggs (whole)", "vegan", True, "verified_substitute_applied",
        expected_allergens=frozenset({Allergen.GLUTEN, Allergen.DAIRY}),
        expected_servings="Yields approximately 1060g of dough, enough for one 900g pan loaf.",
    ),
    SubstitutionCase(
        "S06", "brioche_sourdough_900g", "eggs (whole)", "egg-free", True, "verified_substitute_applied",
        expected_allergens=frozenset({Allergen.GLUTEN, Allergen.DAIRY}),
        expected_servings="Yields approximately 1060g of dough, enough for one 900g pan loaf.",
    ),
    SubstitutionCase(
        "S07", "cinnamon_raisin_walnut_800g", "honey", "vegan", True, "verified_substitute_applied",
        expected_allergens=frozenset({Allergen.GLUTEN, Allergen.TREE_NUTS}),
        expected_servings="Yields approximately 1170g of dough, enough for one 800g pan loaf.",
    ),
    SubstitutionCase(
        "S08", "cinnamon_raisin_walnut_800g", "walnuts (chopped)", "nut-free", True, "allergen_correctly_dropped",
        expected_allergens=frozenset({Allergen.GLUTEN}),
        expected_servings="Yields approximately 1170g of dough, enough for one 800g pan loaf.",
        notes="tree-nuts must be ABSENT from the adapted allergen line once walnuts are swapped out.",
    ),
    SubstitutionCase(
        "S09", "sourdough_country_2kg", "bread flour", "gluten-free", True, "verified_substitute_applied",
        expected_allergens=frozenset(),
        expected_servings="Yields approximately 1970g of dough, enough for two 1kg boules.",
        notes="gluten must be ABSENT from the adapted allergen line.",
    ),
    SubstitutionCase(
        "S10", "whole_wheat_flaxseed_1800g", "whole wheat flour", "gluten-free", True, "verified_substitute_applied",
        expected_allergens=frozenset(),
        expected_servings="Yields approximately 2080g of dough, enough for two 900g boules (about 1.8kg total).",
    ),
    SubstitutionCase(
        "S11", "rye_sourdough_900g", "dark rye flour", "gluten-free", True, "verified_substitute_applied",
        expected_allergens=frozenset(),
        expected_servings="Yields approximately 1075g of dough, enough for one 900g batard.",
    ),
    SubstitutionCase(
        "S12", "rosemary_olive_focaccia_1500g", "bread flour", "gluten-free", True, "verified_substitute_applied",
        expected_allergens=frozenset(),
        expected_servings="Yields one 1.5kg tray focaccia (approximately 33cm x 23cm).",
    ),
    # --- refusal: ingredient not in this recipe at all ---
    SubstitutionCase("S13", "brioche_sourdough_900g", "ground cinnamon", "vegan", False, "ingredient_not_in_recipe"),
    SubstitutionCase("S14", "sourdough_country_2kg", "walnuts (chopped)", "nut-free", False, "ingredient_not_in_recipe"),
    # --- refusal: ingredient real, but no verified substitute for this diet ---
    SubstitutionCase("S15", "cinnamon_raisin_walnut_800g", "ground cinnamon", "vegan", False, "no_substitute_on_file"),
    SubstitutionCase("S16", "rosemary_olive_focaccia_1500g", "fresh rosemary", "vegan", False, "no_substitute_on_file"),
    SubstitutionCase("S17", "sourdough_country_2kg", "active sourdough starter", "gluten-free", False, "no_substitute_on_file"),
    SubstitutionCase("S18", "rye_sourdough_900g", "caraway seeds", "nut-free", False, "no_substitute_on_file"),
    SubstitutionCase("S19", "whole_wheat_flaxseed_1800g", "flaxseed (ground)", "vegan", False, "no_substitute_on_file"),
    SubstitutionCase("S20", "rosemary_olive_focaccia_1500g", "extra virgin olive oil", "nut-free", False, "no_substitute_on_file"),
    SubstitutionCase(
        "S21", "sourdough_country_2kg", "bread flour", "vegan", False, "no_substitute_on_file",
        notes="ingredient is already diet-compliant, but the table has no (bread flour, vegan) entry - "
        "must still refuse rather than assume 'no swap needed'.",
    ),
    SubstitutionCase("S22", "cinnamon_raisin_walnut_800g", "walnuts (chopped)", "vegan", False, "no_substitute_on_file",
                      notes="table only has (walnuts, nut-free), not (walnuts, vegan) - diet-specific, not ingredient-specific."),
    SubstitutionCase("S23", "brioche_sourdough_900g", "unsalted butter", "gluten-free", False, "no_substitute_on_file"),
    SubstitutionCase("S24", "brioche_sourdough_900g", "eggs (whole)", "nut-free", False, "no_substitute_on_file"),
    # --- refusal: bad input ---
    SubstitutionCase("S25", "sourdough_country_2kg", "bread flour", "nonsense-diet", False, "invalid_diet_value"),
    SubstitutionCase("S26", "this_recipe_does_not_exist", "bread flour", "vegan", False, "recipe_not_found"),
]

assert len(CASES) >= 25, f"expected at least 25 substitution cases, got {len(CASES)}"

CASES_BY_ID = {case.id: case for case in CASES}


@dataclass(frozen=True)
class RegressionCase:
    """Pinned to one real Week-5 trace (evaluation/week5/traces.jsonl) that
    was observed failing - not a synthetic example. Re-runs the SAME
    question through the live ChatService and checks, mechanically, whether
    that specific failure still reproduces."""
    id: str
    source_trace_id: str
    question: str
    mode: str
    original_buggy_answer: str
    check_description: str


REGRESSION_CASES: list[RegressionCase] = [
    RegressionCase(
        id="R01",
        source_trace_id="e7825230392e4b6fbd4b7c8054ec5340",
        question="What does step 2 of the Sourdough Brioche Loaf method involve?",
        mode="header_line_as_answer",
        original_buggy_answer="Method:",
        check_description="answer must not be the bare section header 'Method:' again",
    ),
    RegressionCase(
        id="R02",
        source_trace_id="bafac406db2940178943ac0ff0d91f67",
        question="What temperature should the oven be for baking the Rosemary Olive Focaccia?",
        mode="wrong_recipe_citation",
        original_buggy_answer="6. Preheat the oven with a baking stone to 230C (450F). Bake for 40-45 minutes until the crust is deep brown and the loaf sounds hollow when tapped.",
        check_description="citation must belong to rosemary_olive_focaccia_1500g, not a different recipe",
    ),
]
