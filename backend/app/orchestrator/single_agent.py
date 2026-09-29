"""The single-agent baseline for Week 10's race: the SAME 3 tool calls the
orchestrator's two workers make between them (search, substitute, check
allergens), made directly by one agent in one context - no task dispatch,
no hand-off, no synthesis step, because there's only ever one place that
needs to read the result. Every token here is counted the same way
(app.core.tokens.count_tokens on the tool's real JSON result) so the
comparison against app/orchestrator/orchestrator.py is apples to apples.
"""

import time

from app.agent.mcp_client import get_mcp_client
from app.core.tokens import count_tokens
from app.models.chat import Citation
from app.models.substitution import SubstitutionResponse


def _refusal_response(message: str) -> SubstitutionResponse:
    return SubstitutionResponse(
        answer=message,
        refused=True,
        substitute_ingredient=None,
        adapted_ingredients=[],
        adapted_method="",
        oven="",
        servings="",
        allergens="",
        citations=[],
    )


def run_single_agent(recipe_id: str, ingredient: str, diet: str) -> tuple[SubstitutionResponse, dict]:
    start = time.perf_counter()
    tokens = 0

    get_mcp_client().call_tool("search_recipes", {"query": f"{ingredient} {recipe_id}"})
    sub_result = get_mcp_client().call_tool(
        "substitute_ingredient", {"recipe_id": recipe_id, "ingredient": ingredient, "diet": diet}
    )
    tokens += count_tokens(str(sub_result))

    if "error" in sub_result:
        response = _refusal_response(sub_result["error"])
        return response, {"tokens": tokens, "latency_s": time.perf_counter() - start}

    substitute = sub_result.get("substitute_ingredient")
    allergen_result = get_mcp_client().call_tool("get_allergen_profile", {"ingredient": substitute})
    tokens += count_tokens(str(allergen_result))

    answer = f"Use {substitute} instead of {ingredient}. {sub_result.get('allergens', '')}".strip()
    response = SubstitutionResponse(
        answer=answer,
        refused=False,
        substitute_ingredient=substitute,
        adapted_ingredients=sub_result.get("adapted_ingredients", []),
        adapted_method=sub_result.get("adapted_method", ""),
        oven="",
        servings=sub_result.get("servings", ""),
        allergens=sub_result.get("allergens", ""),
        citations=[Citation(chunk_id=c) for c in sub_result.get("citations", [])],
    )
    return response, {"tokens": tokens, "latency_s": time.perf_counter() - start}
