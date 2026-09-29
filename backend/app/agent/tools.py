"""The three tools the agent (and, identically, the fixed workflow) can
call. Each wraps existing, already-deterministic/grounded services - no
tool lets the LLM invent a chunk, a substitute, or an allergen. Same
single-string-argument, no-framework style as the sample rag-poc project's
app/agent/tools.py.
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.api.deps import get_retriever, get_substitution_service
from app.substitution.tables import Allergen, Diet, allergens_for


@dataclass
class Tool:
    name: str
    description: str
    func: Callable[[str], dict]

    def invoke(self, argument: str) -> dict:
        return self.func(argument)


def _search_recipes(query: str) -> dict:
    """Hybrid BM25 + dense retrieval over the recipe corpus (structure-aware
    chunking) - the same Retriever the chat/search APIs use."""
    retrieved = get_retriever().search(query, strategy="structure-aware", top_k=5)
    return {
        "chunks": [
            {
                "chunk_id": chunk.chunk_id,
                "recipe_id": chunk.metadata.recipe_id,
                "section": chunk.metadata.section,
                "text": chunk.text,
                "score": chunk.score,
            }
            for chunk in retrieved
        ],
        "best_relevance_score": max((chunk.score for chunk in retrieved), default=0.0),
    }


def _substitute_ingredient(argument: str) -> dict:
    """Look up a diet-appropriate substitute for exactly one ingredient in
    exactly one recipe, from the fixed table in app.substitution.tables -
    never a guess. Argument: "<recipe_id>, <ingredient>, <diet>"."""
    parts = [p.strip() for p in argument.split(",")]
    if len(parts) != 3:
        return {"error": f'Expected "<recipe_id>, <ingredient>, <diet>", got {argument!r}.'}
    recipe_id, ingredient, diet = parts
    response = get_substitution_service().substitute(recipe_id, ingredient, diet)
    if response.refused:
        return {"error": response.answer}
    return {
        "substitute_ingredient": response.substitute_ingredient,
        "allergens": response.allergens,
        "adapted_method": response.adapted_method,
        "servings": response.servings,
        "citations": [c.chunk_id for c in response.citations],
    }


def _get_allergen_profile(argument: str) -> dict:
    """Look up known allergens for exactly one ingredient - nothing else,
    and never tied to a specific recipe. Argument: the ingredient name."""
    ingredient = argument.strip().lower()
    if not ingredient:
        return {"error": "Expected an ingredient name."}
    allergens = allergens_for(ingredient)
    if not allergens:
        return {
            "ingredient": ingredient,
            "allergens": [],
            "note": "No allergen data on file for this ingredient - this is not a claim that it's allergen-free.",
        }
    return {"ingredient": ingredient, "allergens": [a.value for a in allergens]}


TOOLS = [
    Tool(
        name="search_recipes",
        description=(
            "Search the recipe corpus for passages relevant to a free-text query. "
            "Runs hybrid BM25 + dense retrieval. Argument: the search query."
        ),
        func=_search_recipes,
    ),
    Tool(
        name="substitute_ingredient",
        description=(
            "Look up a diet-appropriate substitute for exactly one ingredient in "
            "exactly one recipe - nothing else. Argument: "
            '"<recipe_id>, <ingredient>, <diet>", e.g. "brioche_sourdough_900g, whole milk, vegan". '
            "diet must be one of: " + ", ".join(d.value for d in Diet) + "."
        ),
        func=_substitute_ingredient,
    ),
    Tool(
        name="get_allergen_profile",
        description=(
            "Look up known allergens for exactly one ingredient - nothing else, "
            "and independent of any specific recipe. Argument: the ingredient name. "
            "Returns allergens from: " + ", ".join(a.value for a in Allergen) + "."
        ),
        func=_get_allergen_profile,
    ),
]
TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}
