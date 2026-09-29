# Week 7 — Verdict

Decision rule: does the path vary by input? For 7/10 requests (A01-A04,
A08-A10) it doesn't — one fact lookup, one substitution, or one allergen
check always suffices, and the fixed workflow matches the agent's
correctness there for ~7ms less p50 latency (41.5ms vs 48.8ms) and ~40%
fewer tokens (378 vs 557), both at $0/request under the local provider.

For 3/10 (A05-A07), the path genuinely varies: a substitute that satisfies
the *first* stated constraint (vegan) turns out to conflict with a
*second*, separately stated one (a nut allergy) — discoverable only by
reading the first substitution's own result. The workflow's single
hardcoded step can't re-branch on its own output; it scored 0/3 on these,
silently handing a nut-allergic user a substitute that contains tree nuts.
The agent scored 3/3, correctly surfacing the conflict instead.

**Verdict: the "conflicting-constraint" request class forces an agent.**
Everything else here should ship as the workflow.
