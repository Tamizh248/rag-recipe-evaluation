"""The agent: repeatedly decides which tool to call, executes it, and
updates state, until the request is answered or a safety budget stops it
(app.agent.safety). Same decide/act/observe shape as the sample rag-poc
project's app/agent/agent.py.

Decision-making: with LLM_PROVIDER=anthropic, a real Claude call decides
the next action from the DECIDE_PROMPT below - a genuine agent loop. With
LLM_PROVIDER=local (the default, no API key configured), there is no local
reasoning model in this project to decide with (unlike app.generation.llm's
LocalExtractiveProvider, which only extracts - it can't choose an action),
so `_rule_based_decide` is a disclosed, deterministic stand-in. It still
performs genuine multi-step, state-dependent chaining (see the cascade
below) that `app.agent.workflow`'s FIXED single-rule step 2 structurally
cannot do - that gap is what Week 7's race is measuring.
"""

import json
import logging
from types import SimpleNamespace

from app.agent.cost import estimate_cost
from app.agent.intent import detect_allergy_concerns, detect_diets, detect_target_ingredient, mentions_allergen_intent
from app.agent.mcp_client import get_mcp_client
from app.agent.safety import check_safety_limits, is_repeated_action, stable_arguments_key
from app.agent.state import AgentState
from app.core.config import get_settings
from app.core.tokens import count_tokens
from app.generation.grounding import has_lexical_support
from app.generation.llm import AnthropicProvider
from app.substitution.tables import ALLERGEN_TO_DIET

logger = logging.getLogger(__name__)

INSUFFICIENT_EVIDENCE_ANSWER = "I couldn't find sufficient evidence to answer this request."

# Week 8 mitigation (evals/trajectory_failure_modes.py's STEP_INEFFICIENCY -
# the top mode by count: T03/T04/T08/T09 in evals/trajectory_cases.py all
# ran an unconditional post-substitution get_allergen_profile check even
# though none of those requests stated an allergy concern for it to guard
# against). Toggled True by scripts/run_week8_mitigation.py to reproduce
# the pre-mitigation behavior for its before/after comparison; never
# toggled True in production - see the cascade check in _rule_based_decide.
ALWAYS_VERIFY_SUBSTITUTE_ALLERGENS = False

DECIDE_PROMPT = (
    "You are an agent handling a recipe-adaptation request. Decide the single next action.\n\n"
    "Request: {question}\n\n"
    "Actions taken so far:\n{history}\n\n"
    "Evidence sufficient so far: {sufficient}\n\n"
    "Available tools (discovered live via MCP tools/list - there may be more than the ones "
    "you've seen used before):\n{tool_list}\n\n"
    "Choose exactly one of:\n"
    '- a tool above, as `<tool name>: {{"arg1": "value1", ...}}` (a JSON object of its named arguments)\n'
    "- `answer` - enough evidence has been found\n"
    "- `give_up` - further tool calls will not help\n\n"
    "Never invent information the tools did not return. Reply with only the chosen action, nothing else."
)

FINAL_ANSWER_PROMPT = (
    "Answer the user's request using only the information returned by the tools below. "
    "Never invent details the tools did not return.\n\n"
    "Request: {question}\n\n"
    "Tool results:\n{results}\n\n"
    "Answer:"
)


def _resolve_recipe_id(state: AgentState) -> str | None:
    for entry in state.tool_results:
        if entry["tool"] == "search_recipes":
            chunks = entry["result"].get("chunks", [])
            if chunks:
                return chunks[0]["recipe_id"]
    return None


def _completed_diets_for_target(state: AgentState, target: str) -> set[str]:
    return {
        step.arguments.get("diet")
        for step in state.steps
        if step.tool == "substitute_ingredient" and step.arguments.get("ingredient") == target
    }


def _successful_substitute_results(state: AgentState, target: str) -> list[dict]:
    return [
        step.result
        for step in state.steps
        if step.tool == "substitute_ingredient"
        and step.arguments.get("ingredient") == target
        and isinstance(step.result, dict)
        and "error" not in step.result
    ]


def _allergen_check_result(state: AgentState, ingredient_text: str) -> dict | None:
    for step in state.steps:
        if step.tool == "get_allergen_profile" and step.arguments.get("ingredient") == ingredient_text:
            return step.result
    return None


def _has_sufficient_evidence(state: AgentState) -> bool:
    """Same lexical-support check the chat pipeline uses (app.generation.
    grounding), not a raw retrieval score - the retriever's RRF-fused
    scores (app/retrieval/retriever.py, k=60) live on a tiny 0-0.03 scale,
    nothing like a 0-1 cosine similarity, so a numeric cutoff here would
    either be miscalibrated or just reimplement this same check worse."""
    if not state.chunks:
        return False
    chunk_texts = [SimpleNamespace(text=c["text"]) for c in state.chunks.values()]
    return has_lexical_support(state.user_query, chunk_texts)


def _rule_based_decide(state: AgentState) -> tuple[str, dict]:
    searched = any(step.tool == "search_recipes" for step in state.steps)
    if not searched:
        return "search_recipes", {"query": state.user_query}

    if not _has_sufficient_evidence(state):
        return "give_up", {}

    recipe_id = _resolve_recipe_id(state)
    diets = detect_diets(state.user_query)
    target = detect_target_ingredient(state.user_query)
    allergy_concerns = detect_allergy_concerns(state.user_query)

    if recipe_id is None or target is None or not diets:
        if mentions_allergen_intent(state.user_query) and target and _allergen_check_result(state, target) is None:
            return "get_allergen_profile", {"ingredient": target}
        return "answer", {}

    completed = _completed_diets_for_target(state, target)
    for diet in diets:
        if diet.value not in completed:
            return "substitute_ingredient", {"recipe_id": recipe_id, "ingredient": target, "diet": diet.value}

    # Every stated diet has been attempted at least once for the target
    # ingredient. Cascade: a successful substitute can still conflict with
    # a SEPARATELY stated allergy concern (not phrased as a diet keyword) -
    # this is the "step 3 depends on what step 2 found" case the fixed
    # workflow cannot replicate, since it only ever runs one fixed rule.
    #
    # Only worth checking at all if the request actually stated an allergy
    # concern (or the pre-mitigation flag forces it) - otherwise this is
    # exactly the unconditional, nothing-hinges-on-it verification step
    # Week 8's STEP_INEFFICIENCY finding is about.
    if allergy_concerns or ALWAYS_VERIFY_SUBSTITUTE_ALLERGENS:
        for result in _successful_substitute_results(state, target):
            substitute_text = result.get("substitute_ingredient")
            if not substitute_text:
                continue
            checked = _allergen_check_result(state, substitute_text)
            if checked is None:
                return "get_allergen_profile", {"ingredient": substitute_text}
            substitute_allergens = set(checked.get("allergens", []))
            for concern in allergy_concerns:
                cascade_diet = ALLERGEN_TO_DIET[concern]
                if concern.value in substitute_allergens and cascade_diet not in completed:
                    return "substitute_ingredient", {"recipe_id": recipe_id, "ingredient": target, "diet": cascade_diet}

    return "answer", {}


def _llm_decide(state: AgentState, settings) -> tuple[str, dict]:
    history = (
        "\n".join(f"{s.step}. {s.tool}: {json.dumps(s.arguments)} -> {str(s.result)[:200]}" for s in state.steps)
        or "(none yet)"
    )
    tools = get_mcp_client().list_tools()
    prompt = DECIDE_PROMPT.format(
        question=state.user_query,
        history=history,
        sufficient=_has_sufficient_evidence(state),
        tool_list="\n".join(f"- {t.name}: {t.description}" for t in tools),
    )
    provider = AnthropicProvider(api_key=settings.llm_api_key, model=settings.llm_model)
    text = provider.generate(prompt).strip()
    state.total_tokens += count_tokens(prompt) + count_tokens(text)
    state.total_cost_usd += estimate_cost("anthropic", settings.llm_model, count_tokens(prompt), count_tokens(text))

    tool_names = {t.name for t in tools}
    name, _, argument = text.partition(":")
    name = name.strip().lower()
    argument = argument.strip()
    if name in tool_names and argument:
        try:
            return name, json.loads(argument)
        except json.JSONDecodeError:
            logger.warning("[AGENT] Could not parse tool arguments as JSON: %r", argument)
    if name in ("answer", "give_up"):
        return name, {}

    logger.warning("[AGENT] Unusable decision %r", text)
    return ("answer", {}) if _has_sufficient_evidence(state) else ("give_up", {})


def _decide_next_action(state: AgentState, settings) -> tuple[str, dict]:
    if settings.llm_provider == "anthropic":
        return _llm_decide(state, settings)
    return _rule_based_decide(state)


def _execute_tool(state: AgentState, tool_name: str, arguments: dict) -> None:
    if is_repeated_action(state, tool_name, arguments):
        state.stop_reason = "repeated_action"
        return

    state.previous_actions.append((tool_name, stable_arguments_key(arguments)))
    state.tool_calls += 1
    if tool_name == "search_recipes":
        state.retrieval_attempts += 1

    try:
        result = get_mcp_client().call_tool(tool_name, arguments)
    except Exception as exc:  # noqa: BLE001
        logger.exception("[AGENT] MCP tool call %s failed", tool_name)
        state.errors += 1
        result = {"error": str(exc)}

    if tool_name == "search_recipes" and isinstance(result, dict):
        state.best_relevance_score = max(state.best_relevance_score, result.get("best_relevance_score", 0.0))
        for chunk in result.get("chunks", []):
            state.chunks[chunk["chunk_id"]] = chunk

    state.record_step(tool_name, arguments, result)


def _summarize_tool_result(entry: dict) -> str:
    tool, result = entry["tool"], entry["result"]
    if tool == "search_recipes" and isinstance(result, dict):
        return "\n\n".join(c["text"] for c in result.get("chunks", [])[:2])
    return str(result)


def _local_compose_answer(state: AgentState) -> str:
    parts: list[str] = []
    for entry in state.tool_results:
        tool, result = entry["tool"], entry["result"]
        if not isinstance(result, dict):
            continue
        if tool == "substitute_ingredient":
            parts.append(result["error"] if "error" in result else f"Use {result['substitute_ingredient']} instead. {result['allergens']}")
        elif tool == "get_allergen_profile":
            parts.append(
                f"{result['ingredient']} is a known source of: {', '.join(result['allergens'])}."
                if result.get("allergens")
                else result.get("note", "")
            )
    if not parts and state.chunks:
        # No substitution/allergen tool ran - this was a pure fact lookup,
        # so answer from the BEST-scoring retrieved chunk (never an
        # arbitrary one - dict insertion order is not relevance order).
        best_chunk = max(state.chunks.values(), key=lambda c: c.get("score", 0.0))
        parts.append(best_chunk["text"])
    return " ".join(p for p in parts if p) or INSUFFICIENT_EVIDENCE_ANSWER


def _compose_final_answer(state: AgentState, settings) -> tuple[str, int, float]:
    if settings.llm_provider == "anthropic":
        results_text = "\n\n".join(f"{e['tool']}({e['arguments']}) ->\n{_summarize_tool_result(e)}" for e in state.tool_results)
        provider = AnthropicProvider(api_key=settings.llm_api_key, model=settings.llm_model)
        prompt = FINAL_ANSWER_PROMPT.format(question=state.user_query, results=results_text)
        text = provider.generate(prompt)
        tokens = count_tokens(prompt) + count_tokens(text)
        cost = estimate_cost("anthropic", settings.llm_model, count_tokens(prompt), count_tokens(text))
        return text, tokens, cost

    text = _local_compose_answer(state)
    return text, count_tokens(text), 0.0


def _finalize(state: AgentState, stop_reason: str, answered: bool, settings) -> dict:
    if not answered:
        return {
            "answer": INSUFFICIENT_EVIDENCE_ANSWER,
            "sources": [],
            "stop_reason": stop_reason,
            "total_tokens": state.total_tokens,
            "total_cost_usd": state.total_cost_usd,
            "tool_calls": state.tool_calls,
            "steps": len(state.steps),
        }

    answer_text, tokens_used, cost_used = _compose_final_answer(state, settings)
    state.total_tokens += tokens_used
    state.total_cost_usd += cost_used
    sources = sorted({c["recipe_id"] for c in state.chunks.values() if c.get("recipe_id")})
    return {
        "answer": answer_text,
        "sources": sources,
        "stop_reason": "goal_completed",
        "total_tokens": state.total_tokens,
        "total_cost_usd": state.total_cost_usd,
        "tool_calls": state.tool_calls,
        "steps": len(state.steps),
    }


def run_agent_with_state(question: str) -> tuple[dict, AgentState]:
    state = AgentState(user_query=question)
    settings = get_settings()

    while True:
        stop_reason = check_safety_limits(state)
        if stop_reason:
            logger.info("[AGENT] Budget hit: %s", stop_reason)
            return _finalize(state, stop_reason, answered=False, settings=settings), state

        action, arguments = _decide_next_action(state, settings)

        if action == "answer":
            return _finalize(state, "goal_completed", answered=True, settings=settings), state
        if action == "give_up":
            return _finalize(state, "give_up", answered=False, settings=settings), state

        _execute_tool(state, action, arguments)
        if state.stop_reason:
            return _finalize(state, state.stop_reason, answered=False, settings=settings), state
