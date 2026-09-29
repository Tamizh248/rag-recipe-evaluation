# Week 8 — Trajectory Evals

All numbers below are real output from `backend/scripts/run_week8_trajectory_eval.py`
and `backend/scripts/run_week8_mitigation.py`, run against the actual agent
(`backend/app/agent/agent.py`). Raw dumps: `trajectory_eval_dump.json`,
`mitigation_results.json`.

## 1. The 10 cases

`backend/evals/trajectory_cases.py` — `required_tools` is a SET, not a
sequence: T05/T06 both cascade (search → substitute → check allergen →
substitute again) but the exact diet value attempted first differs by
phrasing, and that's accepted as the same valid trajectory rather than
over-asserted into two "different" required sequences.

## 2. Four trajectory numbers

| Metric | Value |
|---|---|
| Tool-choice accuracy | 100% |
| Argument validity rate | 90% (the 2 "invalid" calls are T05/T06's cascade attempt correctly finding no cross-diet substitute on file - a real refusal, not a hallucinated argument; see `argument_validity_rate`'s docstring for why this metric counts that as "invalid" anyway) |
| Step efficiency (mean) | 0.95 (post-mitigation; was 1.15 before - see §4) |
| Cost | tokens: p50=25.5, max=227 · USD: p50=$0, max=$0 (LLM_PROVIDER=local costs nothing per request; see `app/agent/cost.py`) |

## 3. Outcome-vs-trajectory gap

**Gap: outcome 100% − trajectory 90% = +10%.**

Right-answer-wrong-path case: **T07** — *"I'm vegan - what should I use
instead of the granulated sugar in the Sourdough Brioche Loaf?"* The agent
never called `substitute_ingredient` at all (`granulated sugar` has no
entry in `app/agent/intent.py`'s fixed ingredient-alias table, so
`detect_target_ingredient()` returns `None`), and instead answered from
the raw retrieved ingredient-list chunk - which happens to already contain
the words "granulated sugar", so this case's outcome check passes even
though no substitution was ever attempted, verified, or refused. A
stricter outcome check (e.g. requiring the word "substitute" or a citation
to a `substitute_ingredient` tool result) would have caught this; the
lenient one here doesn't - which is exactly Week 8's point.

## 4. The one mitigation

**Top failure mode: `step_inefficiency`, 4/10 cases (T03, T04, T08, T09).**
Each ran an unconditional post-substitution `get_allergen_profile` check
even though none of those 4 requests stated an allergy concern for it to
guard against.

**Mitigation:** `app/agent/agent.py`'s cascade-check now only runs when the
request stated an allergy concern (`ALWAYS_VERIFY_SUBSTITUTE_ALLERGENS`
toggled `False` by default; the mitigation script flips it `True` to
reproduce the "before" state).

| | Before | After |
|---|---:|---:|
| `step_inefficiency` count | 4/10 | 0/10 |
| Tokens (T03+T04+T08+T09 combined) | 167 | 84 |

**Price paid:** the automatic post-substitution allergen re-verification no
longer runs when no allergy concern is stated. If a user has an unstated
allergy, the mitigated agent will no longer catch a conflicting substitute
on its own for that class of request - the cascade only still fires when a
concern IS stated (T05/T06, unaffected).

## 5. Regression check

| Mode | Before | After |
|---|---:|---:|
| tool_bypass | 1 | 1 |
| wrong_tool_choice | 0 | 0 |
| argument_hallucination | 2 | 2 |
| repeated_action_stuck | 0 | 0 |
| gave_up_too_early | 0 | 0 |
| fabrication_without_evidence | 0 | 0 |
| step_inefficiency | 4 | 0 |

**No mode got worse and no new mode appeared.** Outcome pass rate stayed
100% → 100%; trajectory pass rate stayed 90% → 90% (T07's `tool_bypass` is
untouched by this mitigation - a separate, disclosed alias-coverage gap,
not something this fix was meant to address).
