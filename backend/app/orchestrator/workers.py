"""Two narrow-scoped workers the orchestrator delegates to (Week 10). Each
is given ONLY what its one job needs - not the whole recipe corpus, not
the other worker's task - so any measured token overhead reflects the real
cost of the hand-off protocol itself, not a padded context strategy (the
task's own common-mistakes list warns against exactly that).

Both workers call the SAME MCP tools (app/agent/mcp_client.py) the single
agent (single_agent.py) calls directly - the only difference this week
measures is decomposition + hand-offs, not different tools or a different
recipe corpus.
"""

from app.agent.mcp_client import get_mcp_client
from app.orchestrator.handoff import HandoffLog


class WorkerError(Exception):
    """Raised when a worker fails (Week 10, requirement 4 - the injected
    allergen-worker failure raises this, standing in for a 500)."""


def run_substitution_worker(case_id: str, recipe_id: str, ingredient: str, diet: str, log: HandoffLog) -> dict:
    task = {"recipe_id": recipe_id, "ingredient": ingredient, "diet": diet}
    log.record(case_id, "orchestrator", "substitution_worker", task, note="task dispatch")

    get_mcp_client().call_tool("search_recipes", {"query": f"{ingredient} {recipe_id}"})
    result = get_mcp_client().call_tool("substitute_ingredient", task)

    log.record(case_id, "substitution_worker", "orchestrator", result, note="result")
    return result


def run_allergen_worker(case_id: str, ingredient: str, log: HandoffLog, simulate_failure: bool = False) -> dict:
    task = {"ingredient": ingredient}
    log.record(case_id, "orchestrator", "allergen_worker", task, note="task dispatch")

    if simulate_failure:
        raise WorkerError(f"allergen_worker returned 500 for ingredient={ingredient!r}")

    result = get_mcp_client().call_tool("get_allergen_profile", {"ingredient": ingredient})
    log.record(case_id, "allergen_worker", "orchestrator", result, note="result")
    return result
