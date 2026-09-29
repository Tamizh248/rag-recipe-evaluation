"""Runs the Week 7 race: same 10 requests (evals/agent_cases.py) through
run_agent_with_state() and run_workflow(), same tools, same model, same
output contract - only the decision step differs. Reports the four
required numbers per system: pass rate, p50 latency, total tokens, cost
per request.
"""

import statistics
import time
from dataclasses import dataclass

from app.agent.agent import run_agent_with_state
from app.agent.workflow import run_workflow
from evals.agent_cases import CASES, RaceCase


@dataclass
class RunResult:
    case: RaceCase
    answer: str
    stop_reason: str
    tool_sequence: list[str]
    latency_ms: float
    tokens: int
    cost_usd: float
    passed: bool


def _run_agent(case: RaceCase) -> RunResult:
    start = time.perf_counter()
    result, state = run_agent_with_state(case.question)
    latency_ms = (time.perf_counter() - start) * 1000
    passed = case.expect(result["answer"], result["stop_reason"])
    return RunResult(
        case=case,
        answer=result["answer"],
        stop_reason=result["stop_reason"],
        tool_sequence=[s.tool for s in state.steps],
        latency_ms=latency_ms,
        tokens=result["total_tokens"],
        cost_usd=result["total_cost_usd"],
        passed=passed,
    )


def _run_workflow(case: RaceCase) -> RunResult:
    start = time.perf_counter()
    result = run_workflow(case.question)
    latency_ms = (time.perf_counter() - start) * 1000
    passed = case.expect(result["answer"], result["stop_reason"])
    return RunResult(
        case=case,
        answer=result["answer"],
        stop_reason=result["stop_reason"],
        tool_sequence=[],  # workflow doesn't expose a step-by-step trace the same way; steps count is enough here
        latency_ms=latency_ms,
        tokens=result["total_tokens"],
        cost_usd=result["total_cost_usd"],
        passed=passed,
    )


def run_race() -> dict[str, list[RunResult]]:
    return {
        "agent": [_run_agent(case) for case in CASES],
        "workflow": [_run_workflow(case) for case in CASES],
    }


def summarize(results: list[RunResult]) -> dict:
    latencies = [r.latency_ms for r in results]
    return {
        "pass_rate": sum(r.passed for r in results) / len(results),
        "p50_latency_ms": statistics.median(latencies),
        "total_tokens": sum(r.tokens for r in results),
        "cost_per_request_usd": sum(r.cost_usd for r in results) / len(results),
    }
