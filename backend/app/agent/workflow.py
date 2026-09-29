"""A fixed, non-agentic pipeline: same 3 tools, same model, same output
contract as run_agent_with_state() (agent.py) - but step 2 is ONE hardcoded
rule instead of a decision loop. Exists to race against the agent
(scripts/race_agent_vs_workflow.py): do these requests actually need a
decision loop, or does a fixed sequence get the same results for less cost?

Structural limitation, by design (this is the actual point of the race,
not a bug to fix): step 2 only ever resolves the FIRST diet named in the
request, and never re-checks whether the resulting substitute conflicts
with a separately stated allergy concern. A fixed pipeline has no way to
read step 2's own result and decide to run a 3rd, different step - only
the agent's decide loop (agent.py's cascade) can do that.
"""

import logging

from app.agent.agent import INSUFFICIENT_EVIDENCE_ANSWER, _compose_final_answer, _has_sufficient_evidence, _tool_argument_string
from app.agent.intent import detect_diets, detect_target_ingredient, mentions_allergen_intent
from app.agent.state import AgentState
from app.agent.tools import TOOLS_BY_NAME
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _fixed_step_2(state: AgentState) -> tuple[str, dict] | None:
    diets = detect_diets(state.user_query)
    target = detect_target_ingredient(state.user_query)
    recipe_id = None
    for entry in state.tool_results:
        if entry["tool"] == "search_recipes":
            chunks = entry["result"].get("chunks", [])
            if chunks:
                recipe_id = chunks[0]["recipe_id"]

    if diets and target and recipe_id:
        # Only the FIRST stated diet, ever - no loop over multiple diets,
        # no cascade if the substitute itself turns out to be a problem.
        return "substitute_ingredient", {"recipe_id": recipe_id, "ingredient": target, "diet": diets[0].value}
    if mentions_allergen_intent(state.user_query) and target:
        return "get_allergen_profile", {"ingredient": target}
    return None


def run_workflow(question: str) -> dict:
    settings = get_settings()
    state = AgentState(user_query=question)

    logger.info("[WORKFLOW] Step 1: search_recipes")
    search_result = TOOLS_BY_NAME["search_recipes"].invoke(question)
    state.tool_calls += 1
    state.retrieval_attempts += 1
    state.previous_actions.append(("search_recipes", str({"query": question})))
    state.best_relevance_score = search_result.get("best_relevance_score", 0.0)
    for chunk in search_result.get("chunks", []):
        state.chunks[chunk["chunk_id"]] = chunk
    state.record_step("search_recipes", {"query": question}, search_result)

    if not _has_sufficient_evidence(state):
        logger.info("[WORKFLOW] Stopping: insufficient_evidence")
        return {
            "answer": INSUFFICIENT_EVIDENCE_ANSWER,
            "sources": [],
            "stop_reason": "insufficient_evidence",
            "total_tokens": state.total_tokens,
            "total_cost_usd": state.total_cost_usd,
            "tool_calls": state.tool_calls,
            "steps": len(state.steps),
        }

    step_2 = _fixed_step_2(state)
    if step_2:
        tool_name, arguments = step_2
        logger.info("[WORKFLOW] Step 2 (fixed rule matched): %s(%s)", tool_name, arguments)
        argument_str = _tool_argument_string(tool_name, arguments)
        result = TOOLS_BY_NAME[tool_name].invoke(argument_str)
        state.tool_calls += 1
        state.record_step(tool_name, arguments, result)
    else:
        logger.info("[WORKFLOW] Step 2: no fixed rule matched, skipping")

    answer_text, tokens_used, cost_used = _compose_final_answer(state, settings)
    state.total_tokens += tokens_used
    state.total_cost_usd += cost_used
    sources = sorted({c["recipe_id"] for c in state.chunks.values() if c.get("recipe_id")})
    logger.info("[WORKFLOW] Stopping: goal_completed")
    return {
        "answer": answer_text,
        "sources": sources,
        "stop_reason": "goal_completed",
        "total_tokens": state.total_tokens,
        "total_cost_usd": state.total_cost_usd,
        "tool_calls": state.tool_calls,
        "steps": len(state.steps),
    }
