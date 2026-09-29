"""MCP server standing in for the "content team's" third-party ingredient
database (Week 9's "server two") - lookup by ingredient name, allergen
flags, and nutrition per 100g. Deliberately self-contained: no import of
this app's own code, since narratively this is someone else's server
running with its own data, not ours - see risk_note.md for what that
actually means for trust/blast-radius.

This is a disclosed local stand-in for a real external service (no such
public API was available to wire up for this project) - same "disclosed
stand-in" pattern as this project's LocalExtractiveProvider - but it is a
REAL, separate MCP server process, spoken to over real JSON-RPC, not an
in-process function call.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ingredient_db_server")

# Approximate per-100g values - illustrative data for this stand-in server,
# not a certified nutrition source.
_INGREDIENTS: dict[str, dict] = {
    "bread flour": {"allergens": ["gluten"], "nutrition_per_100g": {"calories": 361, "protein_g": 12.0, "fat_g": 1.5, "carbs_g": 73.0}},
    "whole wheat flour": {"allergens": ["gluten"], "nutrition_per_100g": {"calories": 340, "protein_g": 13.2, "fat_g": 2.5, "carbs_g": 72.0}},
    "dark rye flour": {"allergens": ["gluten"], "nutrition_per_100g": {"calories": 349, "protein_g": 10.3, "fat_g": 1.7, "carbs_g": 76.0}},
    "whole milk": {"allergens": ["dairy"], "nutrition_per_100g": {"calories": 61, "protein_g": 3.2, "fat_g": 3.3, "carbs_g": 4.8}},
    "unsalted butter": {"allergens": ["dairy"], "nutrition_per_100g": {"calories": 717, "protein_g": 0.9, "fat_g": 81.0, "carbs_g": 0.1}},
    "eggs": {"allergens": ["eggs"], "nutrition_per_100g": {"calories": 143, "protein_g": 12.6, "fat_g": 9.5, "carbs_g": 0.7}},
    "walnuts": {"allergens": ["tree-nuts"], "nutrition_per_100g": {"calories": 654, "protein_g": 15.2, "fat_g": 65.2, "carbs_g": 13.7}},
    "honey": {"allergens": [], "nutrition_per_100g": {"calories": 304, "protein_g": 0.3, "fat_g": 0.0, "carbs_g": 82.4}},
    "granulated sugar": {"allergens": [], "nutrition_per_100g": {"calories": 387, "protein_g": 0.0, "fat_g": 0.0, "carbs_g": 100.0}},
    "extra virgin olive oil": {"allergens": [], "nutrition_per_100g": {"calories": 884, "protein_g": 0.0, "fat_g": 100.0, "carbs_g": 0.0}},
    "raisins": {"allergens": [], "nutrition_per_100g": {"calories": 299, "protein_g": 3.1, "fat_g": 0.5, "carbs_g": 79.2}},
    "flaxseed": {"allergens": [], "nutrition_per_100g": {"calories": 534, "protein_g": 18.3, "fat_g": 42.2, "carbs_g": 28.9}},
    "caraway seeds": {"allergens": [], "nutrition_per_100g": {"calories": 333, "protein_g": 19.8, "fat_g": 14.6, "carbs_g": 49.9}},
    "fine sea salt": {"allergens": [], "nutrition_per_100g": {"calories": 0, "protein_g": 0.0, "fat_g": 0.0, "carbs_g": 0.0}},
    "creme fraiche": {"allergens": ["dairy"], "nutrition_per_100g": {"calories": 292, "protein_g": 2.5, "fat_g": 30.0, "carbs_g": 3.0}},
}


def _closest_match(name: str) -> str | None:
    key = name.strip().lower()
    candidates = [known for known in _INGREDIENTS if key in known or known in key]
    return candidates[0] if candidates else None


@mcp.tool()
def lookup_ingredient(name: str) -> dict:
    """Look up one ingredient's allergen flags and nutrition per 100g by
    name. Argument: the ingredient name."""
    key = name.strip().lower()
    if key in _INGREDIENTS:
        return {"ingredient": key, **_INGREDIENTS[key]}

    suggestion = _closest_match(key)
    if suggestion:
        raise ValueError(f"no ingredient matched {name!r}: try {suggestion!r}")
    raise ValueError(f"no ingredient matched {name!r}: not on file")


if __name__ == "__main__":
    mcp.run()
