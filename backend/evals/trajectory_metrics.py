"""Trajectory Metrics Engine (Week 8, deliverable 2) + the pass/fail rule
used by both trajectory_harness.py (deliverable 1) and the mitigation
script (deliverables 4-5). Same split as the sample rag-poc project's
evals/metrics.py: "cost" is reported as both real dollars (0 for
LLM_PROVIDER=local, real pricing for anthropic - app/agent/cost.py) and
tokens (this project's own approximate but always-populated cost proxy,
app/core/tokens.py), never a bare mean - a single 6-tool-call run must show
up in `max`, not get smoothed away.
"""

import statistics
from dataclasses import dataclass

from app.agent.state import AgentState
from evals.trajectory_cases import TrajectoryCase


@dataclass
class CaseRun:
    case: TrajectoryCase
    result: dict
    state: AgentState
    outcome_pass: bool = False

    @property
    def tool_call_sequence(self) -> list[str]:
        return [step.tool for step in self.state.steps]

    @property
    def called_tools(self) -> set[str]:
        return set(self.tool_call_sequence)


def trajectory_passed(run: CaseRun) -> tuple[bool, str]:
    """The path-set assertion: required tools all ran, forbidden ones never
    did, and the agent answered/refused as expected. Never looks at answer
    text - that's outcome_pass's job."""
    case = run.case
    called = run.called_tools

    missing = case.required_tools - called
    if missing:
        return False, f"missing required tool call(s): {sorted(missing)}"

    present_forbidden = case.forbidden_tools & called
    if present_forbidden:
        return False, f"called forbidden tool(s): {sorted(present_forbidden)}"

    answered = run.result["stop_reason"] == "goal_completed"
    if case.expect_answered and not answered:
        return False, f"expected an answer, got stop_reason={run.result['stop_reason']!r}"
    if not case.expect_answered and answered:
        return False, "expected a refusal, but the agent answered anyway"

    return True, "ok"


def tool_choice_accuracy(runs: list[CaseRun]) -> float:
    """% of tool-CALL steps that picked a tool considered valid for that
    case's request, across every step of every case."""
    total = valid = 0
    for run in runs:
        valid_tools = run.case.tools_considered_valid()
        for step in run.state.steps:
            total += 1
            if step.tool in valid_tools:
                valid += 1
    return valid / total if total else 0.0


def argument_validity_rate(runs: list[CaseRun]) -> float:
    """% of tool calls whose arguments were valid, i.e. the tool did not
    hand back an {"error": ...} dict (unknown ingredient, bad diet, no
    substitute on file). Same definition as the sample project's own
    metrics.py - it deliberately conflates "malformed" with "no data found",
    since both mean the call didn't produce usable evidence."""
    total = valid = 0
    for run in runs:
        for step in run.state.steps:
            total += 1
            if not (isinstance(step.result, dict) and "error" in step.result):
                valid += 1
    return valid / total if total else 0.0


def step_efficiency(runs: list[CaseRun]) -> dict:
    per_case = {run.case.id: len(run.state.steps) / run.case.optimal_tool_calls for run in runs}
    mean_ratio = statistics.mean(per_case.values()) if per_case else 0.0
    return {"per_case": per_case, "mean": mean_ratio}


def cost_distribution(runs: list[CaseRun]) -> dict:
    token_counts = [run.state.total_tokens for run in runs]
    cost_usd = [run.state.total_cost_usd for run in runs]
    if not token_counts:
        return {"tokens_p50": 0, "tokens_max": 0, "cost_usd_p50": 0.0, "cost_usd_max": 0.0, "per_case": {}}
    return {
        "tokens_p50": statistics.median(token_counts),
        "tokens_max": max(token_counts),
        "cost_usd_p50": statistics.median(cost_usd),
        "cost_usd_max": max(cost_usd),
        "per_case": {run.case.id: {"tokens": run.state.total_tokens, "cost_usd": run.state.total_cost_usd} for run in runs},
    }


def outcome_pass_rate(runs: list[CaseRun]) -> float:
    return sum(1 for run in runs if run.outcome_pass) / len(runs) if runs else 0.0


def trajectory_pass_rate(runs: list[CaseRun]) -> float:
    return sum(1 for run in runs if trajectory_passed(run)[0]) / len(runs) if runs else 0.0


def find_gap_cases(runs: list[CaseRun]) -> list[CaseRun]:
    """Outcome PASSED but trajectory FAILED - the right-answer-wrong-path
    cases (deliverable 3)."""
    return [run for run in runs if run.outcome_pass and not trajectory_passed(run)[0]]
