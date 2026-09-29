"""ONE command: runs the 10 trajectory cases (deliverable 1), the four
trajectory numbers (deliverable 2), and the outcome-vs-trajectory gap with
the named right-answer-wrong-path case (deliverable 3).

Usage:
    python scripts/run_week8_trajectory_eval.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.trajectory_failure_modes import classify, count_modes
from evals.trajectory_harness import run_all_cases
from evals.trajectory_metrics import (
    argument_validity_rate,
    cost_distribution,
    find_gap_cases,
    outcome_pass_rate,
    step_efficiency,
    tool_choice_accuracy,
    trajectory_passed,
    trajectory_pass_rate,
)

EVAL_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "week8"
OUTPUT_PATH = EVAL_DIR / "trajectory_eval_dump.json"


def main() -> None:
    runs = run_all_cases()

    print("=== Per-case trajectory results ===\n")
    for run in runs:
        passed, reason = trajectory_passed(run)
        print(
            f"[{run.case.id}] trajectory={'PASS' if passed else 'FAIL'} ({reason})  "
            f"outcome={'PASS' if run.outcome_pass else 'FAIL'}  "
            f"tools={[s.tool for s in run.state.steps]}  modes={sorted(classify(run))}"
        )

    cost = cost_distribution(runs)
    print("\n=== Four trajectory numbers ===\n")
    print(f"tool_choice_accuracy:  {tool_choice_accuracy(runs):.0%}")
    print(f"argument_validity_rate: {argument_validity_rate(runs):.0%}")
    print(f"step_efficiency (mean): {step_efficiency(runs)['mean']:.2f}")
    print(f"cost: tokens p50={cost['tokens_p50']} max={cost['tokens_max']}  usd p50=${cost['cost_usd_p50']:.6f} max=${cost['cost_usd_max']:.6f}")

    outcome = outcome_pass_rate(runs)
    trajectory = trajectory_pass_rate(runs)
    gap = outcome - trajectory
    print("\n=== Outcome-vs-trajectory gap ===\n")
    print(f"outcome_pass_rate:    {outcome:.0%}")
    print(f"trajectory_pass_rate: {trajectory:.0%}")
    print(f"gap:                  {gap:+.0%}")

    gap_cases = find_gap_cases(runs)
    for run in gap_cases:
        print(f"\nRight-answer-wrong-path case: [{run.case.id}] {run.case.question}")
        print(f"  answer: {run.result['answer'][:200]}")
        print(f"  tools actually called: {[s.tool for s in run.state.steps]}")
        print(f"  required but missing: {sorted(run.case.required_tools - run.called_tools)}")
        print(f"  why: {run.case.notes}")

    print("\n=== Failure-mode counts ===\n")
    for mode, count in count_modes(runs).items():
        print(f"  {mode:<28} {count}")

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    dump = {
        "per_case": [
            {
                "id": run.case.id,
                "trajectory_passed": trajectory_passed(run)[0],
                "outcome_pass": run.outcome_pass,
                "tools": [s.tool for s in run.state.steps],
                "modes": sorted(classify(run)),
                "tokens": run.state.total_tokens,
                "cost_usd": run.state.total_cost_usd,
            }
            for run in runs
        ],
        "tool_choice_accuracy": tool_choice_accuracy(runs),
        "argument_validity_rate": argument_validity_rate(runs),
        "step_efficiency": step_efficiency(runs),
        "cost_distribution": cost,
        "outcome_pass_rate": outcome,
        "trajectory_pass_rate": trajectory,
        "gap": gap,
        "gap_case_ids": [run.case.id for run in gap_cases],
        "mode_counts": count_modes(runs),
    }
    OUTPUT_PATH.write_text(json.dumps(dump, indent=2), encoding="utf-8")
    print(f"\nWritten to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
