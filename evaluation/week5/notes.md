# Week 5 — Open-Coding Notes

## How this file was built (read before writing anything)

1. `backend/scripts/generate_traces.py` ran 95 realistic recipe questions
   (direct facts, paraphrases, cross-recipe comparisons, negation,
   ambiguous no-recipe-named questions, scaling/math, aggregation,
   substitution previews, and out-of-corpus nutrition questions) through
   the **real** `/api/chat` pipeline — nothing below is hand-written or
   simulated. **Assumption (disclosed):** no historical user-question log
   exists for this app yet, so this script is the stand-in for "the
   assistant running all week," same honest-assumption style as the rest
   of this project's `results.md`. 95 traces were generated, not "past a
   thousand" — this is a smaller, purpose-built app, so the flavor text in
   the task brief is treated as scene-setting, not a literal target.
2. `backend/scripts/sample_traces.py --seed 42 --n 20` drew the seeded
   random sample below (seed and full population size are in
   `sample.json`, committed alongside this file).
3. `backend/scripts/replay_trace.py` replayed the first sampled trace
   purely from its own stored fields — see **Replay Evidence** below.

## What's left for you to do

For each of the 20 rows below, read the question/answer/citations (or open
`traces.jsonl` and search for the `trace_id` for the full record — retrieved
chunk text, scores, raw LLM output, prompt) and write **one honest sentence
describing what you SAW** in the blank `Observation:` line. Not a category,
not a fix — just what happened. "I don't know why this failed" is fine.
Zero code changes while you do this (the zero is graded).

---

## Seeded sample

Seed: **42** · Population: **95** traces · Sampled: **20** (see `sample.json`)

### 1. `da8b0cc9071b4da68143a7d473878020`
**Q:** Can I replace the walnuts in the Cinnamon Raisin Walnut Sourdough with a different nut?
**A:** Contains gluten (wheat) and tree nuts (walnuts). Contains no dairy or egg.
**Citations:** `cinnamon_raisin_walnut_800g_structure_aware_allergens_003` · Refused: No
**Observation:**

### 2. `bafac406db2940178943ac0ff0d91f67`
**Q:** What temperature should the oven be for baking the Rosemary Olive Focaccia?
**A:** 6. Preheat the oven with a baking stone to 230C (450F). Bake for 40-45 minutes until the crust is deep brown and the loaf sounds hollow when tapped.
**Citations:** `rye_sourdough_900g_structure_aware_method_002` · Refused: No
**Observation:**

### 3. `15e7053eb97e4a42bb40af658cbbfc8a`
**Q:** How long does the Sourdough Country Loaf bake for?
**A:** 7. Preheat a covered Dutch oven to 250C (480F). Score the cold loaf and bake covered for 20 minutes, then uncovered for a further 20-25 minutes until deeply browned.
**Citations:** `sourdough_country_2kg_structure_aware_method_002` · Refused: No
**Observation:**

### 4. `e7825230392e4b6fbd4b7c8054ec5340`
**Q:** What does step 2 of the Sourdough Brioche Loaf method involve?
**A:** Method:
**Citations:** `brioche_sourdough_900g_structure_aware_method_002` · Refused: No
**Observation:**

### 5. `1493c73d91ef41c1b2889e9e60b3f5e6`
**Q:** What is step 3 of the Whole Wheat Flaxseed Sourdough method?
**A:** Method:
**Citations:** `whole_wheat_flaxseed_1800g_structure_aware_method_002` · Refused: No
**Observation:**

### 6. `e8a5423d34a743d39ed59459f68f4259`
**Q:** What is the baker's percentage of salt in the Whole Wheat Flaxseed Sourdough?
**A:** Fine Sea Salt: 20g (2%)
**Citations:** `whole_wheat_flaxseed_1800g_structure_aware_ingredients_001` · Refused: No
**Observation:**

### 7. `fc2f487b4360418491baa9f21c0589aa`
**Q:** What allergens does the Cinnamon Raisin Walnut Sourdough contain?
**A:** Allergens:
**Citations:** `cinnamon_raisin_walnut_800g_structure_aware_allergens_003` · Refused: No
**Observation:**

### 8. `37417336894b45b1b6f2382396f6f0cc`
**Q:** What is step 3 of the Rosemary Olive Focaccia method?
**A:** Method:
**Citations:** `rosemary_olive_focaccia_1500g_structure_aware_method_002` · Refused: No
**Observation:**

### 9. `ae7a673b35924f9eaea2d858d14bca1d`
**Q:** What is the baker's percentage of salt in the Rosemary Olive Focaccia?
**A:** Fine Sea Salt: 16g (2%)
**Citations:** `rosemary_olive_focaccia_1500g_structure_aware_ingredients_001` · Refused: No
**Observation:**

### 10. `b065603b48bc4af99cf4a3df3c4be18c`
**Q:** What is the sodium content per serving of the Rosemary Olive Focaccia?
**A:** I cannot answer this from the provided recipes.
**Citations:** none · Refused: Yes (pre-LLM, no lexical support)
**Observation:**

### 11. `e19cca5dc9074ea3b925e3000032b18a`
**Q:** Is the Sourdough Brioche Loaf vegan?
**A:** I cannot answer this from the provided recipes.
**Citations:** none · Refused: Yes (pre-LLM, no lexical support)
**Observation:**

### 12. `cedd485c45244775819fbf8a1d62e753`
**Q:** What is step 3 of the Caraway Rye Sourdough method?
**A:** Method:
**Citations:** `rye_sourdough_900g_structure_aware_method_002` · Refused: No
**Observation:**

### 13. `cc661ea9fa734794b1c583a6de6e9b52`
**Q:** Which recipes contain tree nuts?
**A:** Contains gluten (wheat) and tree nuts (walnuts). Contains no dairy or egg.
**Citations:** `cinnamon_raisin_walnut_800g_structure_aware_allergens_003` · Refused: No
**Observation:**

### 14. `9ed1722ff15645598b317d1480812c0a`
**Q:** Is the oven temperature for the Sourdough Country Loaf higher or lower than for the Rosemary Olive Focaccia?
**A:** I cannot answer this from the provided recipes.
**Citations:** none · Refused: Yes (pre-LLM, no lexical support)
**Observation:**

### 15. `c59f4569514f41b6bbcbc1fac4a6a524`
**Q:** What allergens does the Sourdough Country Loaf contain?
**A:** Allergens:
**Citations:** `sourdough_country_2kg_structure_aware_allergens_003` · Refused: No
**Observation:**

### 16. `0f19320d592c4d26a6f12d3005ded11b`
**Q:** How long does the Cinnamon Raisin Walnut Sourdough bake for?
**A:** 7. Bake in a preheated Dutch oven at 230C (450F), covered for 20 minutes and uncovered for 15-20 minutes until deep golden brown.
**Citations:** `cinnamon_raisin_walnut_800g_structure_aware_method_002` · Refused: No
**Observation:**

### 17. `90669c55e4a14228941b84a85722bf2d`
**Q:** What is step 3 of the Cinnamon Raisin Walnut Sourdough method?
**A:** Method:
**Citations:** `cinnamon_raisin_walnut_800g_structure_aware_method_002` · Refused: No
**Observation:**

### 18. `e0df384736ee4bf2a8d782341e19cd5e`
**Q:** How much salt would I need for a half-batch of the Caraway Rye Sourdough?
**A:** 2. Add the fine sea salt after the autolyse, then mix in the active rye starter and caraway seeds until evenly distributed.
**Citations:** `rye_sourdough_900g_structure_aware_method_002` · Refused: No
**Observation:**

### 19. `2b03407c4ddc4dec81c2040dd35ad963`
**Q:** How many of the six recipes are vegan?
**A:** I cannot answer this from the provided recipes.
**Citations:** none · Refused: Yes (pre-LLM, no lexical support)
**Observation:**

### 20. `eedd4f7009394805acd7ed4d9449b5d6`
**Q:** Is the Sourdough Country Loaf dairy-free?
**A:** Contains gluten (wheat). Produced in a facility that also processes tree nuts. Contains no dairy, egg, or soy.
**Citations:** `sourdough_country_2kg_structure_aware_allergens_003` · Refused: No
**Observation:**

---

## Replay Evidence

Trace replayed: `da8b0cc9071b4da68143a7d473878020` (full detail in
`replay_da8b0cc9071b4da68143a7d473878020.json`, produced by
`backend/scripts/replay_trace.py --random --seed 42`).

**Original:**
- refused_pre_llm: `False`
- raw_llm_output: `{"answerable": true, "answer": "Contains gluten (wheat) and tree nuts (walnuts). Contains no dairy or egg.", "citations": [{"chunk_id": "cinnamon_raisin_walnut_800g_structure_aware_allergens_003"}]}`
- answer: `Contains gluten (wheat) and tree nuts (walnuts). Contains no dairy or egg.`

**Replayed (recomputed only from this trace's own stored `prompt`, retrieved
chunk text, and model/provider fields — no vector store or embedding call):**
- replayed_refused_pre_llm: `False`
- replayed_raw_output: `{"answerable": true, "answer": "Contains gluten (wheat) and tree nuts (walnuts). Contains no dairy or egg.", "citations": [{"chunk_id": "cinnamon_raisin_walnut_800g_structure_aware_allergens_003"}]}`
- raw_output_matches_original: `True`

**Fields that had to be ADDED to `app/core/tracing.py::TraceRecord` to make
this replay possible** (none of this existed before Week 5):
- `prompt_version`, the exact `prompt` sent to the LLM, and `raw_llm_output`
- `retrieved` as full `{chunk_id, score, recipe_id, section, text}` records
  (not just ids/scores) — text is required so `has_lexical_support` can be
  recomputed without re-querying the vector store
- `model_provider` / `model_name`, so replay reconstructs the exact same
  `LLMProvider` implementation

**Could not be reconstructed:** nothing for this trace — the `local`
provider is fully deterministic, so replay reproduced the original output
byte-for-byte. If `LLM_PROVIDER=anthropic` is ever used in production, note
here that provider calls are not guaranteed bit-for-bit reproducible even
with an identical prompt, and say so honestly rather than claiming a false
match.

---

## Your dated prediction

Write it in `prediction.md`, not here — see that file for the required
format. Commit it before you start any fix.
