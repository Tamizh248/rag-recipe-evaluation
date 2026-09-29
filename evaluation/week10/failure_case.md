# Week 10 — Injected Worker Failure

**Case:** `S03` — `brioche_sourdough_900g` / `whole milk` / `vegan`. Chosen
deliberately: this is the one case in the 10 where the allergen worker's
finding (oat/almond milk introduces tree-nuts) is actually informative, so
a failed allergen worker here is a real test, not a no-op.

**Injection:** `app/orchestrator/workers.py::run_allergen_worker` raises
`WorkerError("allergen_worker returned 500 for ingredient='oat milk or almond milk'")`
instead of calling the real MCP tool — standing in for the allergen
worker's process returning HTTP 500.

## What the orchestrator actually did: **degraded to a caveated partial answer.**

It did **not** retry, and it did **not** fabricate an independent allergen
claim the worker never made.

**Single agent** (no worker to fail, calls `get_allergen_profile` itself):
> Use oat milk or almond milk instead of whole milk. Contains dairy, eggs, gluten, tree-nuts.

**Orchestrator, same case, allergen worker failing:**
> Use oat milk or almond milk instead of whole milk. Contains dairy, eggs, gluten, tree-nuts. NOTE: the independent allergen-verification worker failed (allergen_worker returned 500 for ingredient='oat milk or almond milk'); this allergen line is from the substitution worker only, not independently confirmed.

The allergen *line itself* is unchanged (it's the substitution worker's own
`allergens` field, computed deterministically and unaffected by the
allergen worker's crash) — what changes is that the orchestrator explicitly
says a second, independent check did **not** happen, rather than silently
presenting the same sentence as if it had been verified twice.

## Why this matters given the judge

Both arms' judge verdict is **FAIL** here regardless of the failure
injection — the Week 6 heuristic judge (`evals/judge.py`, its blind spots
disclosed in `evaluation/week6/judge_v1.txt`) flags the word "dairy" in the
allergens field as disqualifying for `vegan`, without knowing that dairy
survives from the *untouched* butter/eggs, not the swapped milk. That is a
pre-existing judge limitation, not something this week's failure injection
caused — see `race_table.md`'s pass-rate row, identical for both arms on
this case.
