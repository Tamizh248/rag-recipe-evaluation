"""The 3 tool IMPLEMENTATIONS backing mcp_servers/recipe_server.py (Week 9)
- each wraps existing, already-deterministic/grounded services, so no tool
lets a model invent a chunk, a substitute, or an allergen.

As of Week 9, the agent (app/agent/agent.py) and workflow no longer import
this module or call these functions in-process - they go through the real
MCP protocol instead (app/agent/mcp_client.py), and recipe_server.py is the
only caller of the three functions below. Kept as a separate module from
the MCP server file so the actual retrieval/substitution/allergen logic
isn't duplicated if a second server ever needs it.
"""

from app.api.deps import get_retriever, get_substitution_service
from app.substitution.tables import allergens_for


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
