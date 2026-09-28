"""ONE command that runs the full Week 6 eval set (requirement 1): 26
substitution cases + 2 regression cases pinned to real Week-5 traces,
printing pass rate by mode. No LLM judge here - this is the deterministic
assertions + outcome-correctness pass, see run_judge.py for the separate
LLM-judge validation exercise.

Usage:
    python scripts/run_week6_eval.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.harness import pass_rate_by_mode, run_all_regression_cases, run_all_substitution_cases

EVAL_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "week6"
OUTPUT_PATH = EVAL_DIR / "eval_dump.json"


def main() -> None:
    runs = run_all_substitution_cases()
    regression_runs = run_all_regression_cases()

    print("=== Substitution cases ===\n")
    for run in runs:
        status = "PASS" if run.passed else "FAIL"
        print(f"[{run.case.id}] {status}  {run.case.recipe_id} / {run.case.ingredient!r} / {run.case.diet}  (mode={run.case.mode})")
        if not run.outcome_correct:
            print(f"       outcome mismatch: expected_answerable={run.case.expect_answerable}, refused={run.response.refused}")
        for name, ok, detail in run.assertion_results:
            if not ok:
                print(f"       FAILED assertion {name}: {detail}")

    print("\n=== Regression cases (pinned to real Week-5 traces) ===\n")
    for run in regression_runs:
        status = "PASS" if run.passed else "FAIL"
        print(f"[{run.case.id}] {status}  trace={run.case.source_trace_id}  mode={run.case.mode}")
        print(f"       {run.detail}")

    table = pass_rate_by_mode(runs, regression_runs)
    print("\n=== Pass rate by mode ===\n")
    total_pass = sum(m["pass"] for m in table.values())
    total_n = sum(m["total"] for m in table.values())
    for mode, stats in table.items():
        print(f"  {mode:<40} {stats['pass']}/{stats['total']}  ({stats['pass_rate']:.0%})")
    print(f"\n  {'OVERALL':<40} {total_pass}/{total_n}  ({total_pass / total_n:.0%})")

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    dump = {
        "substitution_cases": [
            {
                "id": run.case.id,
                "recipe_id": run.case.recipe_id,
                "ingredient": run.case.ingredient,
                "diet": run.case.diet,
                "mode": run.case.mode,
                "expect_answerable": run.case.expect_answerable,
                "refused": run.response.refused,
                "answer": run.response.answer,
                "substitute_ingredient": run.response.substitute_ingredient,
                "allergens": run.response.allergens,
                "passed": run.passed,
                "assertion_results": run.assertion_results,
            }
            for run in runs
        ],
        "regression_cases": [
            {
                "id": run.case.id,
                "source_trace_id": run.case.source_trace_id,
                "mode": run.case.mode,
                "passed": run.passed,
                "detail": run.detail,
                "answer": run.answer,
                "citations": run.citations,
            }
            for run in regression_runs
        ],
        "pass_rate_by_mode": table,
    }
    OUTPUT_PATH.write_text(json.dumps(dump, indent=2), encoding="utf-8")
    print(f"\nWritten to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
