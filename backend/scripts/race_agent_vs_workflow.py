"""ONE command: races the agent against the fixed workflow over the same
10 requests, prints the 4-number table for both arms, and separately runs
one deliberately over-constrained request to capture a clean budget
termination log (requirement 4).

Usage:
    python scripts/race_agent_vs_workflow.py
"""
import csv
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.agent import run_agent_with_state
from evals.race import run_race, summarize

EVAL_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "week7"

BUDGET_DEMO_QUESTION = (
    "I need this vegan, dairy-free, egg-free, nut-free, and gluten-free - "
    "what should I use instead of the whole milk in the Sourdough Brioche Loaf?"
)


def run_budget_demo() -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    log_path = EVAL_DIR / "budget_termination.log"

    handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

    logging.getLogger(__name__).info("[DEMO] Question: %s", BUDGET_DEMO_QUESTION)
    result, state = run_agent_with_state(BUDGET_DEMO_QUESTION)
    logging.getLogger(__name__).info("[DEMO] Tool sequence: %s", [s.tool for s in state.steps])
    logging.getLogger(__name__).info("[DEMO] Final result: stop_reason=%s answer=%r", result["stop_reason"], result["answer"])

    logging.getLogger().removeHandler(handler)
    handler.close()

    assert result["stop_reason"] == "max_iterations", f"expected a clean max_iterations trip, got {result['stop_reason']!r}"
    print(f"Budget-termination demo: stop_reason={result['stop_reason']!r} after {len(state.steps)} tool calls.")
    print(f"Log written to {log_path}")


def _warm_up() -> None:
    """Force lazy singletons (embedding model, vector store) to initialize
    BEFORE timing starts - otherwise whichever case runs first pays a
    one-time load cost that has nothing to do with agent-vs-workflow and
    would wrongly dominate that arm's p50 latency."""
    run_agent_with_state("What temperature should I bake the Sourdough Country Loaf at?")


def main() -> None:
    _warm_up()
    results = run_race()

    print("=== Per-case results ===\n")
    rows = []
    for agent_run, workflow_run in zip(results["agent"], results["workflow"]):
        case = agent_run.case
        print(f"[{case.id}] {case.question}")
        print(f"   AGENT    pass={agent_run.passed}  tools={agent_run.tool_sequence}  latency={agent_run.latency_ms:.0f}ms  tokens={agent_run.tokens}  cost=${agent_run.cost_usd:.6f}")
        print(f"   WORKFLOW pass={workflow_run.passed}  latency={workflow_run.latency_ms:.0f}ms  tokens={workflow_run.tokens}  cost=${workflow_run.cost_usd:.6f}")
        rows.append(
            {
                "id": case.id,
                "requires_cascade": case.requires_cascade,
                "agent_pass": agent_run.passed,
                "agent_latency_ms": round(agent_run.latency_ms, 1),
                "agent_tokens": agent_run.tokens,
                "agent_cost_usd": agent_run.cost_usd,
                "workflow_pass": workflow_run.passed,
                "workflow_latency_ms": round(workflow_run.latency_ms, 1),
                "workflow_tokens": workflow_run.tokens,
                "workflow_cost_usd": workflow_run.cost_usd,
            }
        )

    agent_summary = summarize(results["agent"])
    workflow_summary = summarize(results["workflow"])

    print("\n=== Summary (4 numbers x 2 arms) ===\n")
    print(f"{'metric':<20}{'agent':>15}{'workflow':>15}")
    print(f"{'pass_rate':<20}{agent_summary['pass_rate']:>15.0%}{workflow_summary['pass_rate']:>15.0%}")
    print(f"{'p50_latency_ms':<20}{agent_summary['p50_latency_ms']:>15.1f}{workflow_summary['p50_latency_ms']:>15.1f}")
    print(f"{'total_tokens':<20}{agent_summary['total_tokens']:>15}{workflow_summary['total_tokens']:>15}")
    print(f"{'cost_per_request':<20}{agent_summary['cost_per_request_usd']:>15.6f}{workflow_summary['cost_per_request_usd']:>15.6f}")

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = EVAL_DIR / "race.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nPer-case rows written to {csv_path}")

    summary_path = EVAL_DIR / "race_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "agent", "workflow"])
        writer.writerow(["pass_rate", agent_summary["pass_rate"], workflow_summary["pass_rate"]])
        writer.writerow(["p50_latency_ms", agent_summary["p50_latency_ms"], workflow_summary["p50_latency_ms"]])
        writer.writerow(["total_tokens", agent_summary["total_tokens"], workflow_summary["total_tokens"]])
        writer.writerow(["cost_per_request_usd", agent_summary["cost_per_request_usd"], workflow_summary["cost_per_request_usd"]])
    print(f"Summary written to {summary_path}")

    print()
    run_budget_demo()


if __name__ == "__main__":
    main()
