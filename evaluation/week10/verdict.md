# Week 10 — Verdict

**Kill it for this workload.**

Pass rate is identical, 80% vs 80% — the orchestrator fixes nothing the
single agent got wrong (both fail the same judge check on the same case,
for the same pre-existing judge limitation). Total tokens are **2140 vs
4340 — a 2.0x multiplier** — for zero quality gain. Latency doesn't even
favor the single agent here (p50 53.9ms vs 50.2ms, p99 84.5ms vs 80.5ms,
orchestrator marginally faster) — at this scale, network/process overhead
per tool call dominates, not synthesis cost, so decomposition buys nothing
on the one number it might plausibly have won.

Naming the bias before it can distort this verdict: a full week was spent
building the orchestrator, the hand-off log, the worker-failure handling -
that effort is a sunk cost and is not a reason to ship it. The only
question is whether tomorrow's marginal token/latency cost is worth
tomorrow's marginal benefit, and on these 10 cases it measurably is not.

The one thing worth keeping: the orchestrator's failure-injection result
(`failure_case.md`) — a worker crash degraded to a caveated partial answer
rather than a fabricated claim. That's a real property worth having *if*
a workload ever needs two independent, fallible verifiers. This one
doesn't: `get_allergen_profile` is one deterministic table lookup, not
independent evidence a single agent couldn't gather itself in the same
call.
