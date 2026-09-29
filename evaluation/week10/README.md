# Week 10 — Multi-Agent Race

All numbers are real output from `backend/scripts/race_week10.py`, run
against the actual single agent (`app/orchestrator/single_agent.py`) and
orchestrator (`app/orchestrator/orchestrator.py` + `workers.py`), both
calling the same real MCP tools (`app/agent/mcp_client.py`, Week 9) and
graded by the same Week 6 judge (`evals/judge.py`). Raw dump: `race_dump.json`.

## Same 10 Week-6 cases, not new ones

`backend/evals/week10_cases.py` picks a fixed 10-case subset of the real
Week 6 set (26 substitution cases exist, not literally 10 - see that
file's docstring for why and which 10 were chosen and why).

## The four numbers, both arms

See `race_table.md`. Pass rate: 80% vs 80% (tied - same pre-existing
judge limitation affects both, not new this week). Tokens: 2140 vs 4340 -
**2.0x multiplier**. Latency: roughly tied, orchestrator marginally
faster. Cost: $0/$0 (`LLM_PROVIDER=local` - neither arm makes an LLM call;
synthesis is deterministic in both, same rationale as the rest of this
project's local-mode design).

## Context re-send multiplier and the largest hand-off

**2.0x.** Largest single hand-off: **`substitution_worker -> orchestrator`
= 1948 tokens (45% of all hand-off tokens)** — the substitution result
itself (adapted ingredients, adapted method, servings, citations) is the
biggest single payload in the whole exchange, and the orchestrator pays to
receive it once from the worker, then pays again implicitly when the
synthesis step re-reads it to build the final answer. See `handoffs.log`
for every individual hand-off's token count.

## Injected worker failure

See `failure_case.md`. The orchestrator degraded to a caveated partial
answer when the allergen worker failed — it neither retried nor fabricated
an unverified claim.

## Verdict

See `verdict.md`: kill it for this workload, citing the tied pass rate and
the 2.0x token cost, with the sunk-cost bias named before the verdict is
given.
