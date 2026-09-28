"""Deterministic assertions moved OUT of the LLM judge (Week 6, requirement
2). Each checks one mechanical property of a SubstitutionResponse - never a
judgment call, so `if` does it for free and never has an off day.

Only meaningful for answerable (non-refused) responses; refusal correctness
is checked separately by the harness against each case's expected_outcome.
"""

import re

from app.models.substitution import SubstitutionResponse
from app.substitution.tables import Allergen

_WEIGHT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*g\b")
_OVEN_UNITS_RE = re.compile(r"\d+\s*°?C.*\d+\s*°?F", re.IGNORECASE)


def substitute_appears_in_method_and_ingredients(response: SubstitutionResponse) -> tuple[bool, str]:
    """Every ingredient actually used in the adapted method must appear in
    the adapted ingredient list - operationalized here as: the substitute
    name introduced into the method must also appear in the ingredient
    list (and vice versa), since the substitute is the one ingredient this
    request changed."""
    if not response.substitute_ingredient:
        return False, "no substitute_ingredient on an answerable response"
    substitute = response.substitute_ingredient.lower()
    in_method = substitute in response.adapted_method.lower()
    in_ingredients = any(substitute in line.lower() for line in response.adapted_ingredients)
    if in_method and in_ingredients:
        return True, "substitute present in both adapted_method and adapted_ingredients"
    return False, f"substitute in method={in_method}, in ingredients={in_ingredients}"


def allergen_warning_present_when_needed(response: SubstitutionResponse, expected_allergens: set[Allergen]) -> tuple[bool, str]:
    allergens_text = response.allergens.lower()
    missing = [a.value for a in expected_allergens if a.value not in allergens_text]
    if missing:
        return False, f"allergens field missing: {missing} (field was: {response.allergens!r})"
    return True, f"all {len(expected_allergens)} expected allergen(s) present in allergens field"


def oven_temperature_has_units(response: SubstitutionResponse) -> tuple[bool, str]:
    if _OVEN_UNITS_RE.search(response.oven):
        return True, "oven field carries both C and F units"
    return False, f"oven field missing C/F units: {response.oven!r}"


def servings_are_echoed(response: SubstitutionResponse, expected_servings: str) -> tuple[bool, str]:
    if response.servings.strip() and response.servings.strip() in expected_servings:
        return True, "servings field echoes the original recipe's yield line"
    return False, f"servings field did not match expected yield: {response.servings!r} vs {expected_servings!r}"


def quantities_parse_as_numbers(response: SubstitutionResponse) -> tuple[bool, str]:
    data_lines = [
        line
        for line in response.adapted_ingredients
        if "|" in line and not line.strip().lower().startswith(("recipe:", "ingredient"))
    ]
    if not data_lines:
        return False, "no ingredient data lines found"
    bad = [line for line in data_lines if not _WEIGHT_RE.search(line)]
    if bad:
        return False, f"{len(bad)} ingredient line(s) had no numeric weight: {bad}"
    return True, f"all {len(data_lines)} ingredient line(s) carry a numeric, parseable weight"


ASSERTIONS = [
    substitute_appears_in_method_and_ingredients,
    oven_temperature_has_units,
    quantities_parse_as_numbers,
]
# allergen_warning_present_when_needed and servings_are_echoed take extra
# per-case expected values, so the harness calls them separately rather
# than through this uniform list.
