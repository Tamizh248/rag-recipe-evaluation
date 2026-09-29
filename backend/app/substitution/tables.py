"""Fixed substitution + allergen tables (Week 6) - not an LLM guess.

Mirrors the sample rag-poc project's app/agent/tools.py pattern: a
dietary/allergen swap either resolves against a fixed table the team
actually stands behind, or the app says "no substitute on file" - it never
lets a model invent a plausible-sounding swap for an ingredient/diet pair
nobody has verified.
"""

from enum import Enum


class Diet(str, Enum):
    VEGAN = "vegan"
    DAIRY_FREE = "dairy-free"
    EGG_FREE = "egg-free"
    NUT_FREE = "nut-free"
    GLUTEN_FREE = "gluten-free"


class Allergen(str, Enum):
    GLUTEN = "gluten"
    DAIRY = "dairy"
    EGGS = "eggs"
    TREE_NUTS = "tree-nuts"


# (ingredient, diet) -> substitute text. Keys are lowercased ingredient
# names exactly as they appear in the recipe cards' ingredient tables.
SUBSTITUTIONS: dict[tuple[str, str], str] = {
    ("unsalted butter", Diet.VEGAN.value): "vegan butter or coconut oil",
    ("unsalted butter", Diet.DAIRY_FREE.value): "vegan butter or coconut oil",
    ("whole milk", Diet.VEGAN.value): "oat milk or almond milk",
    ("whole milk", Diet.DAIRY_FREE.value): "oat milk or almond milk",
    ("eggs (whole)", Diet.VEGAN.value): "1 tbsp ground flaxseed + 3 tbsp water per egg (flax egg)",
    ("eggs (whole)", Diet.EGG_FREE.value): "1 tbsp ground flaxseed + 3 tbsp water per egg (flax egg)",
    ("honey", Diet.VEGAN.value): "maple syrup or agave syrup",
    ("walnuts (chopped)", Diet.NUT_FREE.value): "toasted sunflower seeds, or omit entirely",
    ("bread flour", Diet.GLUTEN_FREE.value): "a 1:1 gluten-free bread flour blend with added xanthan gum",
    ("whole wheat flour", Diet.GLUTEN_FREE.value): "a 1:1 gluten-free flour blend",
    ("dark rye flour", Diet.GLUTEN_FREE.value): "a 1:1 gluten-free flour blend (loses rye's characteristic flavor)",
}

# ingredient (lowercased) -> allergens it's a known source of. An ingredient
# missing from this table is NOT the same as "allergen-free" - it means no
# data is on file, same honesty rule as the sample project's tools.py.
ALLERGEN_PROFILES: dict[str, list[Allergen]] = {
    "bread flour": [Allergen.GLUTEN],
    "whole wheat flour": [Allergen.GLUTEN],
    "dark rye flour": [Allergen.GLUTEN],
    "whole milk": [Allergen.DAIRY],
    "unsalted butter": [Allergen.DAIRY],
    "eggs (whole)": [Allergen.EGGS],
    "walnuts (chopped)": [Allergen.TREE_NUTS],
}

# The substitute TEXT itself can introduce a different allergen (e.g. almond
# milk contains tree nuts) - fixed per substitute string, same non-invention
# rule as above. A substitute string missing here introduces none on file.
SUBSTITUTE_ALLERGENS: dict[str, list[Allergen]] = {
    "oat milk or almond milk": [Allergen.TREE_NUTS],
}


def allergens_for(ingredient: str) -> list[Allergen]:
    """Checks both the original-ingredient table AND the substitute-text
    table (get_allergen_profile is a general-purpose tool - the agent's
    cascade calls it on a previously-suggested SUBSTITUTE just as often as
    on an original recipe ingredient)."""
    key = ingredient.strip().lower()
    return ALLERGEN_PROFILES.get(key) or SUBSTITUTE_ALLERGENS.get(key, [])


def allergens_for_substitute(substitute: str) -> list[Allergen]:
    return SUBSTITUTE_ALLERGENS.get(substitute, [])


def find_substitute(ingredient: str, diet: str) -> str | None:
    return SUBSTITUTIONS.get((ingredient.strip().lower(), diet))


# Which allergen would disqualify a response from actually satisfying each
# diet - shared by the Week 6 judge heuristic (evals/judge.py) and the
# Week 7 agent's cascade detection (app/agent/agent.py), so both use the
# same definition of "this diet request wasn't really met".
DIET_DISQUALIFYING_ALLERGENS: dict[str, list[Allergen]] = {
    Diet.VEGAN.value: [Allergen.DAIRY, Allergen.EGGS],
    Diet.DAIRY_FREE.value: [Allergen.DAIRY],
    Diet.EGG_FREE.value: [Allergen.EGGS],
    Diet.NUT_FREE.value: [Allergen.TREE_NUTS],
    Diet.GLUTEN_FREE.value: [Allergen.GLUTEN],
}

# The diet that addresses a stated allergy concern - lets the agent turn
# "I'm allergic to nuts" into a concrete substitute_ingredient diet value.
ALLERGEN_TO_DIET: dict[Allergen, str] = {
    Allergen.TREE_NUTS: Diet.NUT_FREE.value,
    Allergen.DAIRY: Diet.DAIRY_FREE.value,
    Allergen.EGGS: Diet.EGG_FREE.value,
    Allergen.GLUTEN: Diet.GLUTEN_FREE.value,
}
