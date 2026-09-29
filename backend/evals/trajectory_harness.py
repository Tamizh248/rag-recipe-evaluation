"""Shared runner: executes one TrajectoryCase against the real agent and
packages the result as a CaseRun. Used by run_week8_trajectory_eval.py and
run_week8_mitigation.py so neither re-implements "run the agent, check the
outcome".
"""

from app.agent.agent import run_agent_with_state
from evals.trajectory_cases import CASES, TrajectoryCase
from evals.trajectory_metrics import CaseRun


def run_case(case: TrajectoryCase) -> CaseRun:
    result, state = run_agent_with_state(case.question)
    outcome_pass = case.expect(result["answer"], result["stop_reason"])
    return CaseRun(case=case, result=result, state=state, outcome_pass=outcome_pass)


def run_all_cases() -> list[CaseRun]:
    return [run_case(case) for case in CASES]
