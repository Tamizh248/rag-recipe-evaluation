"""Deterministic keyword detection the rule-based decision-maker
(app.agent.agent's local stand-in) uses to decide which tool to call next -
no LLM involved in this file, same spirit as the sample rag-poc project's
app/agent/intent.py.
"""

import re

from app.substitution.tables import Allergen, Diet

_DIET_SYNONYMS: dict[Diet, list[str]] = {
    Diet.VEGAN: ["vegan"],
    Diet.DAIRY_FREE: ["dairy-free", "dairy free"],
    Diet.EGG_FREE: ["egg-free", "egg free", "eggless"],
    Diet.NUT_FREE: ["nut-free", "nut free"],
    Diet.GLUTEN_FREE: ["gluten-free", "gluten free"],
}

_ALLERGEN_INTENT_RE = re.compile(r"allerg", re.IGNORECASE)

# A stated allergy CONCERN ("I'm allergic to nuts") is a different signal
# than a stated diet LABEL ("nut-free version") - the agent's cascade uses
# this to catch a substitute that's technically diet-compliant but still
# lands on something the user separately said they must avoid.
_ALLERGY_CONCERN_SYNONYMS: dict[Allergen, list[str]] = {
    Allergen.TREE_NUTS: ["nut allergy", "nut-allergic", "allergic to nuts", "allergic to tree nuts"],
    Allergen.DAIRY: ["dairy allergy", "allergic to dairy", "lactose intolerant"],
    Allergen.EGGS: ["egg allergy", "allergic to eggs"],
    Allergen.GLUTEN: ["gluten allergy", "celiac", "gluten intolerant"],
}

# Alias -> canonical ingredient name, exactly as it appears in the recipe
# cards' ingredient tables (app.substitution.tables' keys). Longest aliases
# are matched first so "unsalted butter" wins over a bare "butter".
_INGREDIENT_ALIASES: dict[str, str] = {
    "unsalted butter": "unsalted butter",
    "butter": "unsalted butter",
    "whole milk": "whole milk",
    "milk": "whole milk",
    "eggs (whole)": "eggs (whole)",
    "eggs": "eggs (whole)",
    "egg": "eggs (whole)",
    "honey": "honey",
    "walnuts (chopped)": "walnuts (chopped)",
    "walnuts": "walnuts (chopped)",
    "bread flour": "bread flour",
    "whole wheat flour": "whole wheat flour",
    "dark rye flour": "dark rye flour",
    "rye flour": "dark rye flour",
    "flaxseed (ground)": "flaxseed (ground)",
    "flaxseed": "flaxseed (ground)",
    "fresh rosemary": "fresh rosemary",
    "rosemary": "fresh rosemary",
    "caraway seeds": "caraway seeds",
    "caraway": "caraway seeds",
    "extra virgin olive oil": "extra virgin olive oil",
    "olive oil": "extra virgin olive oil",
    "active sourdough starter": "active sourdough starter",
    "active rye starter": "active rye starter",
}


def detect_diets(query: str) -> list[Diet]:
    """Every diet constraint named in the query, in the order its FIRST
    synonym appears - order matters for the cascade (whichever constraint
    is stated first is resolved first)."""
    lowered = query.lower()
    found: list[tuple[int, Diet]] = []
    for diet, synonyms in _DIET_SYNONYMS.items():
        best_index = min((lowered.find(s) for s in synonyms if s in lowered), default=None)
        if best_index is not None:
            found.append((best_index, diet))
    return [diet for _, diet in sorted(found)]


def mentions_allergen_intent(query: str) -> bool:
    return bool(_ALLERGEN_INTENT_RE.search(query))


def detect_allergy_concerns(query: str) -> list[Allergen]:
    lowered = query.lower()
    return [allergen for allergen, synonyms in _ALLERGY_CONCERN_SYNONYMS.items() if any(s in lowered for s in synonyms)]


def detect_target_ingredient(query: str, candidate_ingredients: set[str] | None = None) -> str | None:
    """The longest ingredient alias mentioned in the query, restricted to
    `candidate_ingredients` (a specific recipe's real ingredient list) when
    given. Returns the CANONICAL ingredient name (the tables.py key), not
    the alias text that matched."""
    lowered = query.lower()
    best_alias, best_canonical = None, None
    for alias, canonical in _INGREDIENT_ALIASES.items():
        if candidate_ingredients is not None and canonical not in candidate_ingredients:
            continue
        if alias in lowered and (best_alias is None or len(alias) > len(best_alias)):
            best_alias, best_canonical = alias, canonical
    return best_canonical
