"""ONE command: reproduces the pre-mitigation behavior (toggling
app.agent.agent.ALWAYS_VERIFY_SUBSTITUTE_ALLERGENS back to True), runs the
trajectory eval, then runs it again with the shipped (mitigated) default,
and reports the top failure mode's count before -> after plus the price
paid, and the full per-mode regression table (deliverables 4-5).

Usage:
    python scripts/run_week8_mitigation.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.agent.agent as agent_module
from evals.trajectory_failure_modes import ALL_MODES, count_modes
from evals.trajectory_harness import run_all_cases
from evals.trajectory_metrics import cost_distribution, outcome_pass_rate, trajectory_pass_rate

EVAL_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "week8"
OUTPUT_PATH = EVAL_DIR / "mitigation_results.json"

AFFECTED_CASE_IDS = {"T03", "T04", "T08", "T09"}  # the step_inefficiency cases the mitigation targets


def main() -> None:
    agent_module.ALWAYS_VERIFY_SUBSTITUTE_ALLERGENS = True
    before_runs = run_all_cases()
    before_counts = count_modes(before_runs)
    before_cost = cost_distribution(before_runs)
    before_outcome, before_trajectory = outcome_pass_rate(before_runs), trajectory_pass_rate(before_runs)
    before_by_id = {run.case.id: run for run in before_runs}

    agent_module.ALWAYS_VERIFY_SUBSTITUTE_ALLERGENS = False
    after_runs = run_all_cases()
    after_counts = count_modes(after_runs)
    after_cost = cost_distribution(after_runs)
    after_outcome, after_trajectory = outcome_pass_rate(after_runs), trajectory_pass_rate(after_runs)
    after_by_id = {run.case.id: run for run in after_runs}

    top_mode = max(before_counts, key=before_counts.get)
    print(f"Top pre-mitigation failure mode: {top_mode!r} ({before_counts[top_mode]}/10 cases)\n")
    print(f"{top_mode}: before={before_counts[top_mode]}  after={after_counts[top_mode]}\n")

    print("=== Price paid (tokens per affected case) ===\n")
    total_before_tokens = total_after_tokens = 0
    for case_id in sorted(AFFECTED_CASE_IDS):
        b, a = before_by_id[case_id], after_by_id[case_id]
        print(f"  [{case_id}] steps {len(b.state.steps)} -> {len(a.state.steps)}   tokens {b.state.total_tokens} -> {a.state.total_tokens}")
        total_before_tokens += b.state.total_tokens
        total_after_tokens += a.state.total_tokens
    print(f"\n  total tokens across these {len(AFFECTED_CASE_IDS)} cases: {total_before_tokens} -> {total_after_tokens} "
          f"({total_after_tokens - total_before_tokens:+d})")
    print(
        "\n  Price paid for the mitigation: the automatic post-substitution allergen "
        "re-verification no longer runs when the request states no allergy concern. "
        "If an unstated allergy exists, the mitigated agent will no longer catch a "
        "conflicting substitute on its own for that case - the cascade only still "
        "fires when a concern IS stated (T05/T06, unaffected below)."
    )

    print(f"\nOutcome pass rate:    {before_outcome:.0%} -> {after_outcome:.0%}")
    print(f"Trajectory pass rate: {before_trajectory:.0%} -> {after_trajectory:.0%}")

    print("\n=== Per-mode regression table ===\n")
    print(f"{'mode':<28}{'before':>8}{'after':>8}   note")
    regressed_or_new = []
    for mode in ALL_MODES:
        before_n, after_n = before_counts[mode], after_counts[mode]
        note = ""
        if after_n > before_n:
            note = "WORSENED" if before_n > 0 else "NEW"
            regressed_or_new.append((mode, before_n, after_n, note))
        print(f"{mode:<28}{before_n:>8}{after_n:>8}   {note}")

    if regressed_or_new:
        print("\nModes that got worse or newly appeared:")
        for mode, b, a, note in regressed_or_new:
            print(f"  {mode}: {b} -> {a} ({note})")
    else:
        print("\nNo mode got worse and no new mode appeared. Checked all modes: " + ", ".join(ALL_MODES))

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(
            {
                "top_mode": top_mode,
                "top_mode_before": before_counts[top_mode],
                "top_mode_after": after_counts[top_mode],
                "before_counts": before_counts,
                "after_counts": after_counts,
                "before_cost": before_cost,
                "after_cost": after_cost,
                "before_outcome_pass_rate": before_outcome,
                "after_outcome_pass_rate": after_outcome,
                "before_trajectory_pass_rate": before_trajectory,
                "after_trajectory_pass_rate": after_trajectory,
                "regressed_or_new": regressed_or_new,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nWritten to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
