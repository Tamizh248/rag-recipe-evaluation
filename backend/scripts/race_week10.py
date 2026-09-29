"""ONE command: races the single agent against the orchestrator over the
SAME 10 Week-6 cases, with the same judge (evals/judge.py), and reports all
four numbers for both arms, the context re-send multiplier, and the
injected worker-failure behavior.

Usage:
    python scripts/race_week10.py
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.judge import judge_case
from evals.week10_cases import FAILURE_INJECTION_CASE_ID, WEEK10_CASES
from app.orchestrator.handoff import HandoffLog
from app.orchestrator.orchestrator import run_orchestrator
from app.orchestrator.single_agent import run_single_agent

EVAL_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "week10"


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, round(pct / 100 * (len(ordered) - 1))))
    return ordered[rank]


def _warm_up() -> None:
    """Force lazy singletons (embedding model, vector store, MCP server
    subprocess spawn) to initialize BEFORE timing starts - otherwise
    whichever case runs first pays a one-time load cost that has nothing
    to do with single-agent-vs-orchestrator and dominates p99 latency."""
    from app.agent.mcp_client import get_mcp_client

    get_mcp_client().call_tool("search_recipes", {"query": "warm up"})


def main() -> None:
    _warm_up()
    log = HandoffLog()

    single_rows, orchestrator_rows = [], []
    failure_case_report = None

    for case in WEEK10_CASES:
        single_response, single_meta = run_single_agent(case.recipe_id, case.ingredient, case.diet)
        single_pass, single_verdict = judge_case(case.recipe_id, case.ingredient, case.diet, single_response)
        single_rows.append(
            {
                "id": case.id,
                "latency_s": single_meta["latency_s"],
                "tokens": single_meta["tokens"],
                "pass": single_pass,
                "answer": single_response.answer,
            }
        )

        inject_failure = case.id == FAILURE_INJECTION_CASE_ID
        orch_response, orch_meta = run_orchestrator(
            case.id, case.recipe_id, case.ingredient, case.diet, log, simulate_allergen_worker_failure=inject_failure
        )
        orch_pass, orch_verdict = judge_case(case.recipe_id, case.ingredient, case.diet, orch_response)
        orchestrator_rows.append(
            {
                "id": case.id,
                "latency_s": orch_meta["latency_s"],
                "tokens": log.tokens_for_case(case.id),
                "pass": orch_pass,
                "answer": orch_response.answer,
                "worker_failure_behavior": orch_meta["worker_failure_behavior"],
            }
        )

        if inject_failure:
            failure_case_report = {
                "case_id": case.id,
                "recipe_id": case.recipe_id,
                "ingredient": case.ingredient,
                "diet": case.diet,
                "single_agent_answer": single_response.answer,
                "orchestrator_answer": orch_response.answer,
                "orchestrator_behavior": orch_meta["worker_failure_behavior"],
                "orchestrator_judge_pass": orch_pass,
                "orchestrator_judge_verdict": orch_verdict,
            }

    def summarize(rows: list[dict]) -> dict:
        latencies_ms = [r["latency_s"] * 1000 for r in rows]
        return {
            "pass_rate": sum(r["pass"] for r in rows) / len(rows),
            "p50_latency_ms": _percentile(latencies_ms, 50),
            "p99_latency_ms": _percentile(latencies_ms, 99),
            "total_tokens": sum(r["tokens"] for r in rows),
            "cost_per_question_usd": 0.0,  # LLM_PROVIDER=local: neither arm makes an LLM call; synthesis is deterministic
        }

    single_summary = summarize(single_rows)
    orch_summary = summarize(orchestrator_rows)
    multiplier = orch_summary["total_tokens"] / single_summary["total_tokens"] if single_summary["total_tokens"] else 0.0

    handoff_totals = log.totals_by_name()
    largest_handoff = max(handoff_totals, key=handoff_totals.get) if handoff_totals else None
    largest_share = handoff_totals[largest_handoff] / log.total_tokens() if largest_handoff else 0.0

    print("=== Per-case results ===\n")
    for s, o in zip(single_rows, orchestrator_rows):
        print(f"[{s['id']}] single: pass={s['pass']} tokens={s['tokens']}  |  orchestrator: pass={o['pass']} tokens={o['tokens']} behavior={o['worker_failure_behavior']}")

    print("\n=== Race table (4 numbers x 2 arms) ===\n")
    print(f"{'metric':<24}{'single_agent':>16}{'orchestrator':>16}")
    print(f"{'pass_rate':<24}{single_summary['pass_rate']:>16.0%}{orch_summary['pass_rate']:>16.0%}")
    print(f"{'p50_latency_ms':<24}{single_summary['p50_latency_ms']:>16.1f}{orch_summary['p50_latency_ms']:>16.1f}")
    print(f"{'p99_latency_ms':<24}{single_summary['p99_latency_ms']:>16.1f}{orch_summary['p99_latency_ms']:>16.1f}")
    print(f"{'total_tokens':<24}{single_summary['total_tokens']:>16}{orch_summary['total_tokens']:>16}")
    print(f"{'cost_per_question_usd':<24}{single_summary['cost_per_question_usd']:>16.6f}{orch_summary['cost_per_question_usd']:>16.6f}")

    print(f"\nContext re-send multiplier: {multiplier:.1f}x (orchestrator tokens / single-agent tokens)")
    print(f"Largest hand-off: {largest_handoff} = {handoff_totals.get(largest_handoff, 0)} tokens ({largest_share:.0%} of all hand-off tokens)")

    print("\n=== Injected worker failure ===\n")
    print(json.dumps(failure_case_report, indent=2))

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / "race_table.md").write_text(
        "# Week 10 - Race Table\n\n"
        f"| Metric | single_agent | orchestrator |\n|---|---:|---:|\n"
        f"| pass_rate | {single_summary['pass_rate']:.0%} | {orch_summary['pass_rate']:.0%} |\n"
        f"| p50_latency_ms | {single_summary['p50_latency_ms']:.1f} | {orch_summary['p50_latency_ms']:.1f} |\n"
        f"| p99_latency_ms | {single_summary['p99_latency_ms']:.1f} | {orch_summary['p99_latency_ms']:.1f} |\n"
        f"| total_tokens | {single_summary['total_tokens']} | {orch_summary['total_tokens']} |\n"
        f"| cost_per_question_usd | ${single_summary['cost_per_question_usd']:.6f} | ${orch_summary['cost_per_question_usd']:.6f} |\n\n"
        f"Context re-send multiplier: **{multiplier:.1f}x**\n\n"
        f"Largest hand-off: **{largest_handoff}** = {handoff_totals.get(largest_handoff, 0)} tokens "
        f"({largest_share:.0%} of all hand-off tokens)\n\n"
        f"All hand-off totals: {json.dumps(handoff_totals, indent=2)}\n"
        f"\nSame 10 Week-6 cases used (evals/week10_cases.py): {[c.id for c in WEEK10_CASES]}\n",
        encoding="utf-8",
    )
    (EVAL_DIR / "handoffs.log").write_text("\n".join(log.to_lines()), encoding="utf-8")
    (EVAL_DIR / "failure_case.json").write_text(json.dumps(failure_case_report, indent=2), encoding="utf-8")
    (EVAL_DIR / "race_dump.json").write_text(
        json.dumps({"single_agent": single_rows, "orchestrator": orchestrator_rows}, indent=2), encoding="utf-8"
    )
    print(f"\nWritten to {EVAL_DIR}")


if __name__ == "__main__":
    main()
