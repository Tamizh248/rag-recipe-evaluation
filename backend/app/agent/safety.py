"""Safety limits for the agent loop. Four budgets are REQUIRED and checked
every iteration (Week 7, requirement 4): max iterations, max tokens, max
cost, wall-clock. Two extra ones (tool calls, repeated-action detection)
are kept from the sample project's app/agent/safety.py as additional
guardrails, not a substitute for the four required ones.
"""

from app.agent.state import AgentState

MAX_STEPS = 6  # "max iterations"
MAX_TOOL_CALLS = 8
MAX_ERRORS = 3
MAX_EXECUTION_TIME = 30  # seconds - "wall-clock"
MAX_TOKENS = 4000  # "max tokens" - total prompt+completion tokens (see app.core.tokens)
MAX_COST_USD = 0.05  # "max cost" - $0 for LLM_PROVIDER=local, real $ for anthropic


def check_safety_limits(state: AgentState) -> str | None:
    """Return the name of the first breached budget, or None if the agent
    may continue. Checked once at the top of every loop iteration."""
    if len(state.steps) >= MAX_STEPS:
        return "max_iterations"
    if state.tool_calls >= MAX_TOOL_CALLS:
        return "max_tool_calls"
    if state.errors >= MAX_ERRORS:
        return "max_errors"
    if state.elapsed_time >= MAX_EXECUTION_TIME:
        return "max_execution_time"
    if state.total_tokens >= MAX_TOKENS:
        return "max_tokens"
    if state.total_cost_usd >= MAX_COST_USD:
        return "max_cost"
    return None


def stable_arguments_key(arguments: dict) -> str:
    return str(sorted(arguments.items()))


def is_repeated_action(state: AgentState, tool: str, arguments: dict) -> bool:
    signature = (tool, stable_arguments_key(arguments))
    return signature in state.previous_actions
