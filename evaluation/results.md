# Results: Recipe RAG Chunking Evaluation

All numbers in this document were produced by actually running the scripts in
`backend/scripts/` against the 6 recipe cards in `backend/data/recipes/`, using
`EMBEDDING_MODEL=all-MiniLM-L6-v2`, `TOP_K=5`, ChromaDB with cosine similarity,
and `LLM_PROVIDER=local` (the deterministic, no-API-key generation stand-in —
see [Section 6](#6-three-grounded-answers) for what that means and how to
regenerate this section with a real Claude model). Nothing below was
hand-edited after the scripts ran. Raw machine-readable dumps:
`evaluation/search_dump.json`, `evaluation/filter_dump.json`,
`evaluation/generation_dump.json`, `evaluation/citation_validation.json`.

## 1. Dataset

6 new recipe cards from a fermentation/bread-baking chapter were ingested —
**and only these 6** (Rule 3, Rule 7). No pre-existing/larger corpus was
re-indexed; `backend/scripts/ingest_recipes.py` is hard-pinned to the explicit
file list in `app/services/ingestion_service.py::RECIPE_FILES`, not "every
file in the directory," precisely so this can't silently drift.

| recipe_id | Title | dietary_tags | Ingredient rows |
|---|---|---|---|
| `sourdough_country_2kg` | Sourdough Country Loaf (2kg) | vegan | 4 |
| `rye_sourdough_900g` | Caraway Rye Sourdough (900g) | vegan | 5 |
| `rosemary_olive_focaccia_1500g` | Rosemary Olive Focaccia (1.5kg) | vegan | 7 |
| `brioche_sourdough_900g` | Sourdough Brioche Loaf (900g) | vegetarian, contains-dairy, contains-eggs | 7 |
| `cinnamon_raisin_walnut_800g` | Cinnamon Raisin Walnut Sourdough (800g) | vegetarian, contains-nuts | 8 |
| `whole_wheat_flaxseed_1800g` | Whole Wheat Flaxseed Sourdough (1.8kg) | vegan | 5 |

Every chunk carries `chunk_id, source_file, recipe_id, cuisine, dietary_tags,
section, chunking_strategy` (`app/models/chunk.py::ChunkMetadata`), validated
at ingestion time by `app/ingestion/metadata.py::validate_metadata` — a chunk
missing `source_file` (or any other required field) raises `IngestionError`
and aborts ingestion rather than being silently stored (tested in
`tests/test_metadata.py`).

The two collections were built from the **identical 6 documents**, same
embedding model, same embedding dimension, same similarity metric (cosine),
same `top_k` — the only variable is chunking strategy (Rules 4–6):

| Collection | Strategy | Chunks produced |
|---|---|---|
| `recipe_chunks_current` | Baseline: fixed-size character windows, `size=250, overlap=50` | 40 |
| `recipe_chunks_structure_aware` | Structure-aware: 1 chunk per logical unit (title / ingredients / method / allergens) | 24 |

**Assumption:** no source recipe files were supplied with the assignment, so
the 6 cards were authored from scratch as original sourdough/bread recipes
(bread is the domain where "baker's percentage" is a real, standard unit,
consistent with a "fermentation chapter"). See `README.md` for the full list
of assumptions.

## 2. Eight Questions

Written directly from the 6 source cards in `evaluation/questions.json`
**before** any chunking, embedding, or retrieval code was run (Rule 2) —
`app/ingestion`, `app/chunking`, `app/vectorstore` did not exist yet when
these were authored.

| ID | Question | Expected Recipe | Expected Section | Expected Answer |
|---|---|---|---|---|
| Q1 | How much salt, in grams, is used in the Sourdough Country Loaf recipe? | sourdough_country_2kg | ingredients | 20g (2%) |
| Q2 | What is the baker's percentage of walnuts in the Cinnamon Raisin Walnut Sourdough? | cinnamon_raisin_walnut_800g | ingredients | 15% |
| Q3 | How much active sourdough starter, in grams, is used in the Rosemary Olive Focaccia recipe? | rosemary_olive_focaccia_1500g | ingredients | 160g (20%) |
| Q4 | How long should the Sourdough Brioche dough bulk retard in the refrigerator before shaping? | brioche_sourdough_900g | method | 10 to 12 hours, overnight |
| Q5 | What vessel is used to bake the Sourdough Country Loaf? | sourdough_country_2kg | method | A covered Dutch oven |
| Q6 | When during the process should salt be added to the Caraway Rye Sourdough dough? | rye_sourdough_900g | method | After the 30-min autolyse, before the starter/caraway |
| Q7 | Which recipe contains tree nuts, and which nut is it? | cinnamon_raisin_walnut_800g | allergens | Walnuts, in the Cinnamon Raisin Walnut Sourdough |
| Q8 | How much total dough yield does the Whole Wheat Flaxseed Sourdough recipe produce? | whole_wheat_flaxseed_1800g | title | ~2080g dough (~1.8kg, two 900g boules) |

Distribution: 3 ingredient (Q1–Q3), 3 method (Q4–Q6), 1 allergen (Q7), 1 other/overview (Q8) — matches the recommended split.

## 3. Retrieval Evaluation (search-only, no LLM — Rule 8)

Produced by `backend/scripts/evaluate_retrieval.py`. A hit = at least one of
the top-5 chunks matches **both** the expected `recipe_id` and expected
`section`.

| Question | Current Chunker | Structure-Aware |
|---|---|---|
| Q1 | HIT | HIT |
| Q2 | HIT | HIT |
| Q3 | HIT | HIT |
| Q4 | HIT | HIT |
| Q5 | HIT | HIT |
| Q6 | HIT | HIT |
| Q7 | **MISS** | HIT |
| Q8 | HIT | HIT |

**Hit@5**
- Current Chunker: **7/8**
- Structure-Aware: **8/8**

Full per-question chunk IDs, scores, recipe IDs, and sections for both
strategies are in `evaluation/search_dump.json`.

## 4. Search Dump

Complete machine-readable retrieval results (all 8 questions × both
strategies × top-5, with real cosine scores): [`evaluation/search_dump.json`](./search_dump.json).

## 5. Metadata Filtering

`app/vectorstore/chroma_store.py::build_where_clause` translates
`filters.dietary_tags` into a native ChromaDB `where` clause (boolean
`dietary_<tag>` flags stored per chunk) — filtering happens **inside** the
ANN query, never as a Python post-filter over already-returned results (this
is asserted directly in `tests/test_retrieval.py::test_dietary_tag_filter_is_applied_at_the_database_level`).

`backend/scripts/evaluate_filter.py` searched a small set of candidate
queries (unfiltered vs. `dietary_tags=["vegan"]`) against the structure-aware
collection until it found one where Top-1 actually changes:

**Query:** *"Which bread pairs well with a cheese board?"*

| Rank | Unfiltered Top-5 | Score | Filtered Top-5 (`dietary_tags=["vegan"]`) | Score |
|---|---|---|---|---|
| 1 | `brioche_sourdough_900g_structure_aware_ingredients_001` (brioche, dairy+eggs) | 0.4163 | `sourdough_country_2kg_structure_aware_ingredients_001` (vegan) | 0.4022 |
| 2 | `brioche_sourdough_900g_structure_aware_allergens_003` (brioche, dairy+eggs) | 0.4145 | `sourdough_country_2kg_structure_aware_method_002` (vegan) | 0.3927 |
| 3 | `sourdough_country_2kg_structure_aware_ingredients_001` (vegan) | 0.4022 | `sourdough_country_2kg_structure_aware_allergens_003` (vegan) | 0.3876 |
| 4 | `sourdough_country_2kg_structure_aware_method_002` (vegan) | 0.3927 | `sourdough_country_2kg_structure_aware_title_000` (vegan) | 0.3539 |
| 5 | `sourdough_country_2kg_structure_aware_allergens_003` (vegan) | 0.3876 | `rye_sourdough_900g_structure_aware_method_002` (vegan) | 0.3310 |

Unfiltered, the buttery/egg-rich brioche wins Top-1 on pure semantic
similarity to "cheese board." With `dietary_tags=["vegan"]` applied, the
brioche chunks are excluded from the vector search entirely — Top-1 becomes
the vegan sourdough country loaf. Full dump: [`evaluation/filter_dump.json`](./filter_dump.json).

## 6. Three Grounded Answers

Produced end-to-end by `backend/scripts/evaluate_generation.py` through the
real retrieval → grounding → LLM → citation/refusal pipeline
(`app/services/chat_service.py`), strategy=structure-aware,
`LLM_PROVIDER=local`.

> **About the `local` provider:** no Anthropic/OpenAI API key was supplied
> for this run (see project setup), so `LLM_PROVIDER=local` was used — a
> deterministic, no-key extractive stand-in (`app/generation/llm.py::LocalExtractiveProvider`)
> that finds the retrieved-context line with the strongest whole-word overlap
> with the question and returns it verbatim with a citation. It exists so the
> full grounding/citation/refusal control flow could be exercised and
> reported truthfully without a paid key, not to simulate LLM-quality prose.
> To regenerate this section with real Claude output, set `LLM_PROVIDER=anthropic`
> and `LLM_API_KEY=<key>` in `backend/.env` and re-run the script — no other
> code changes needed, since `AnthropicProvider` implements the same
> `LLMProvider` interface.

**Q1** — *How much salt, in grams, is used in the Sourdough Country Loaf recipe?*
- Answer: `Fine Sea Salt: 20g (2%)`
- Citations: `sourdough_country_2kg_structure_aware_ingredients_001`
- Recipe: `sourdough_country_2kg`

**Q5** — *What vessel is used to bake the Sourdough Country Loaf?*
- Answer: `7. Preheat a covered Dutch oven to 250C (480F). Score the cold loaf and bake covered for 20 minutes, then uncovered for a further 20-25 minutes until deeply browned.`
- Citations: `sourdough_country_2kg_structure_aware_method_002`
- Recipe: `sourdough_country_2kg`

**Q7** — *Which recipe contains tree nuts, and which nut is it?*
- Answer: `Contains gluten (wheat) and tree nuts (walnuts). Contains no dairy or egg.`
- Citations: `cinnamon_raisin_walnut_800g_structure_aware_allergens_003`
- Recipe: `cinnamon_raisin_walnut_800g`

Full transcripts: [`evaluation/generation_dump.json`](./generation_dump.json).

### Citation validation

`backend/scripts/validate_citations.py` checked every citation above against
the live vector store: exists, belongs to the expected recipe, and the
cited chunk's text lexically supports the answer. Also ran one **synthetic
negative control** — a citation to a chunk_id that does not exist — to prove
the validator actually rejects bad citations rather than trivially passing:

| Question | chunk_id | Exists | Matches recipe | Supports answer | Result |
|---|---|---|---|---|---|
| Q1 | `sourdough_country_2kg_structure_aware_ingredients_001` | ✅ | ✅ | ✅ | **OK** |
| Q5 | `sourdough_country_2kg_structure_aware_method_002` | ✅ | ✅ | ✅ | **OK** |
| Q7 | `cinnamon_raisin_walnut_800g_structure_aware_allergens_003` | ✅ | ✅ | ✅ | **OK** |
| SYNTHETIC_NEGATIVE_CONTROL | `does_not_exist_chunk_999` | ❌ | — | — | **REJECTED** ✅ (correctly) |

`all_real_citations_valid: true`, `negative_control_correctly_rejected: true`.
Full report: [`evaluation/citation_validation.json`](./citation_validation.json).

## 7. Three Refusals

Same pipeline, same run, strategy=structure-aware. These 3 facts (protein,
calories, sodium) genuinely do not appear anywhere in any of the 6 recipe
cards — confirmed by grepping `backend/data/recipes/*.txt`.

**U1** — *What is the protein content per serving of the Sourdough Country Loaf?*
> "I cannot answer this from the provided recipes."

**U2** — *How many calories are in one slice of the Whole Wheat Flaxseed Sourdough?*
> "I cannot answer this from the provided recipes."

**U3** — *What is the sodium content per serving of the Sourdough Brioche Loaf?*
> "I cannot answer this from the provided recipes."

All three: `refused: true`, `citations: []`.

**How refusal is actually enforced** (Section 26 / Rule 9 — not just prompt
wording): `app/generation/grounding.py::has_lexical_support` runs **before**
the LLM is even called. It strips generic/recipe-title words (which trivially
co-occur in every chunk via the `Recipe: <title>` prefix) and checks whether
the retrieved context contains real evidence for what's being asked. If not,
the request is refused deterministically and the LLM is never invoked.
This matters here specifically: retrieval alone does *not* solve this — cosine
similarity for these 3 questions actually retrieved the *correct* recipe
(0.70–0.85 top-1 scores, on par with the answerable questions) because the
recipe name matches; the retrieved chunks simply don't contain the requested
fact. A retrieval-score threshold alone would have answered these
incorrectly. After the LLM responds (for answerable questions),
`enforce_refusal_policy` independently rejects any answer with zero
citations or a citation outside the retrieved set, regardless of what the
provider claims (`tests/test_grounding.py`).

## 8. Embarrassing Retrieval

**Question (Q7):** *"Which recipe contains tree nuts, and which nut is it?"*
- Expected: `cinnamon_raisin_walnut_800g` / `allergens`
- Current chunker actual top-5: `sourdough_country_2kg/allergens`,
  `whole_wheat_flaxseed_1800g/allergens`, `cinnamon_raisin_walnut_800g/method`,
  `cinnamon_raisin_walnut_800g/ingredients`, `sourdough_country_2kg/method`
  — **no chunk tagged `allergens` for the correct recipe appears at all.**

**Diagnosis:** the baseline chunker's fixed 250-character window landed such
that `cinnamon_raisin_walnut_800g`'s *entire* allergens sentence
("Contains gluten (wheat) and tree nuts (walnuts)...") ended up appended to
the tail of the previous window, which is majority "method" text — so the
whole chunk got labeled `section="method"` (see
`CurrentChunker._dominant_section`, which tags by character-overlap after
boundaries are already fixed). Confirmed directly against the stored chunk:

```
chunk_id: cinnamon_raisin_walnut_800g_current_method_006
metadata.section: "method"
text: "...Cool on a wire rack for at least 1 hour before slicing, as the
caramelized honey and raisins retain heat.

ALLERGENS:
Contains gluten (wheat) and tree nuts (walnuts). Contains no dairy or egg."
```

The allergen fact is physically present in the vector store, but under the
wrong `section` label, so the Hit@5 definition (recipe **and** section match)
correctly scores it a miss — and in a filtered UI ("show me allergen info"),
a user would never see it. This is a direct, measured instance of exactly the
failure mode Section 9 warns about: naive character splitting doesn't respect
logical document boundaries.

**A related, second finding** (not formally scored, found while probing the
[bonus scenario](#9-bonus) below): even where Hit@5 counts the baseline
chunker as a "hit," its chunks can still cause a **wrong-recipe** answer. For
Q5 ("What vessel is used to bake the Sourdough Country Loaf?") the baseline
top-5 includes `rye_sourdough_900g_current_method_004` (score 0.4802) ranked
*above* `sourdough_country_2kg_current_method_004` (score 0.4424) — two
different recipes' generic "preheat the oven / bake for N minutes" sentences
are close enough in embedding space, once stripped of their original
paragraph context by fixed-size windowing, that a naive downstream consumer
picks the wrong recipe's oven step. Structure-aware chunks never exhibit this
because every chunk is prefixed with `Recipe: <title>` and the full method is
kept as one contiguous, correctly-attributed unit.

## 9. Bonus

**Not observed.** The hypothesized scenario (structure-aware retrieves more
*precisely* but the resulting answer is *worse* because the isolated chunk
lacks surrounding context) was explicitly tested by running Q1, Q2, Q4, Q5,
Q6, and Q7 through the full generation pipeline under **both** strategies
(see raw comparison below) — structure-aware matched or beat the baseline
chunker's answer quality on every one of them. This makes sense given how the
structure-aware chunker is built: every chunk already contains its full
logical section (not a fragment) *plus* a `Recipe: <title>` prefix, so
"precise but context-starved" retrieval never actually happens here. Per the
project brief, this negative result is reported as-is rather than fabricated.

| Q | Current answer | Structure-Aware answer |
|---|---|---|
| Q1 | `Fine Sea Salt: 20g (2%)` ✅ | `Fine Sea Salt: 20g (2%)` ✅ |
| Q2 | `Walnuts (chopped): 75g (15%)` ✅ | `Walnuts (chopped): 75g (15%)` ✅ |
| Q4 | `ture for 1 hour, then refrigerate...` ⚠️ (mid-word truncated, see below) | `4. Bulk ferment at room temperature for 1 hour, then refrigerate...` ✅ |
| Q5 | Wrong recipe (`rye_sourdough_900g`) ❌ | `7. Preheat a covered Dutch oven...` ✅ |
| Q6 | Wrong recipe (`sourdough_country_2kg`) ❌ | `2. Add the fine sea salt after the autolyse...` ✅ |
| Q7 | Right recipe, but the chunk_id is labeled `section="method"` (see Section 8) | `Contains gluten (wheat) and tree nuts (walnuts)...` ✅ |

The Q4 baseline answer is a genuine, reproducible chunk-boundary artifact —
the stored chunk `brioche_sourdough_900g_current_method_004` literally begins
`"ture for 1 hour, ..."`, having been cut mid-word out of "**tempera-ture**"
by the fixed 250-character window. Structure-aware chunks never split
mid-word because their boundaries are logical sections, not character counts.

## 10. Chunking Decision

**Ship structure-aware.** Based on the measured results above, not an a
priori preference:

- **Retrieval:** 8/8 vs 7/8 Hit@5, and the one baseline miss (Q7) was not a
  close call — the correct chunk existed but was mislabeled due to
  boundary-crossing.
- **Generation quality:** across all 6 questions tested through the full
  pipeline under both strategies, structure-aware never underperformed, and
  the baseline produced 2 outright wrong-recipe answers plus 1 mid-word-
  truncated answer.
- **Self-containedness:** every structure-aware chunk carries its own
  `Recipe: <title>` prefix, so it stands alone under retrieval or citation
  display; baseline chunks are anonymous character windows that only make
  sense with their neighbors.
- **Fewer chunks, same corpus:** 24 vs 40 — a smaller, cleaner index with the
  same coverage.

**Honest tradeoffs against structure-aware** (why this isn't a free lunch):
- It requires a per-domain parser (`app/ingestion/parser.py`) that
  understands "title / ingredient table / method / allergens." It does not
  generalize to arbitrary documents the way the character-window baseline
  does — a new document type needs a new structure-aware chunker.
  `app/ingestion/parser.py::ParsedRecipe.is_well_formed` exists specifically
  to detect and flag documents the parser can't confidently structure, so
  malformed input degrades to a visible ingestion error rather than silent
  mis-chunking.
- Each structure-aware chunk is a whole section, so a recipe with an
  unusually long method (many more steps than these 6 cards have) could
  produce a chunk long enough to dilute the embedding or approach context
  limits — the current implementation deliberately does not sub-chunk long
  methods, which would need to change for recipes far larger than this
  corpus.
- The baseline's uniform chunk size is trivially tunable/predictable for
  cost and latency planning; structure-aware chunk sizes vary with recipe
  content.

For this recipe-card corpus and question set, those tradeoffs are outweighed
by the retrieval and generation quality gap.

## 11. Task B: Failure Separation and Hybrid Retrieval

### Golden set

The fixed Task B golden set is [`golden_set.jsonl`](./golden_set.jsonl). Each
line names a known chunk ID, so Hit@3 tests retrieval of the exact supporting
context rather than a recipe-level proxy. The repository contains no user
question log; these are manually authored user-style questions against the
six supplied recipe cards and are disclosed as such rather than presented as
historical user traffic. The set is fixed for the before/after comparison.

| ID | Question | Known-correct chunk_id |
|---|---|---|
| B1 | How many grams of ground flaxseed are in the Whole Wheat Flaxseed Sourdough? | `whole_wheat_flaxseed_1800g_structure_aware_ingredients_001` |
| B2 | What recipe has a 0.75% ingredient? | `rosemary_olive_focaccia_1500g_structure_aware_ingredients_001` |
| B3 | How many grams of caraway seeds are in the Caraway Rye Sourdough? | `rye_sourdough_900g_structure_aware_ingredients_001` |
| B4 | Where is 175C specified in the recipe cards? | `brioche_sourdough_900g_structure_aware_method_002` |
| B5 | What oven temperature in Celsius is used for the Sourdough Country Loaf? | `sourdough_country_2kg_structure_aware_method_002` |
| B6 | Which recipe uses 465F? | `whole_wheat_flaxseed_1800g_structure_aware_method_002` |
| B7 | How much active rye starter is used in the Caraway Rye Sourdough? | `rye_sourdough_900g_structure_aware_ingredients_001` |
| B8 | Which ingredient is listed at 12.5%? | `rosemary_olive_focaccia_1500g_structure_aware_ingredients_001` |
| B9 | How long does the Sourdough Brioche dough bulk retard in the refrigerator? | `brioche_sourdough_900g_structure_aware_method_002` |
| B10 | What vessel is used to bake the Sourdough Country Loaf? | `sourdough_country_2kg_structure_aware_method_002` |
| B11 | When is salt added to the Caraway Rye Sourdough dough? | `rye_sourdough_900g_structure_aware_method_002` |
| B12 | Which recipe contains tree nuts and which nut is named? | `cinnamon_raisin_walnut_800g_structure_aware_allergens_003` |

The exact-token cases include `flaxseed`, `0.75%`, `caraway`, `175C`,
`250C`, `465F`, `12.5%`, and `tree nuts`.

### Baseline inspection and labels

Dense-only cosine retrieval was evaluated at top-3 before enabling hybrid
retrieval. A miss is R when the known-correct chunk is absent from the
inspection view; no answer model is called in this search-only evaluation, so
there are no G labels. Every golden target is a verified stored chunk, so
there are no Not-In-Corpus labels.

| Label | Count | Inspection evidence |
|---|---:|---|
| R | 3 | B2, B4, and B6 are listed below. |
| G | 0 | Search-only evaluation; no generator ran. |
| Not-In-Corpus | 0 | All 12 `correct_chunk_id` values resolve in the structure-aware collection. |

- **B2 — R:** expected `rosemary_olive_focaccia_1500g_structure_aware_ingredients_001`; dense top-3 was Whole Wheat ingredients, Rye ingredients, Country ingredients.
- **B4 — R:** expected `brioche_sourdough_900g_structure_aware_method_002`; dense top-3 was Brioche ingredients, Country ingredients, Whole Wheat ingredients.
- **B6 — R:** expected `whole_wheat_flaxseed_1800g_structure_aware_method_002`; dense top-3 was Rosemary ingredients, Whole Wheat ingredients, Brioche ingredients.

### One retrieval change and measurement

The one change is **BM25 + reciprocal-rank fusion**, with `k=60`. The R tally
is entirely exact numeric/temperature retrieval misses, so lexical BM25 is
the targeted complement to dense similarity. Dense and lexical scores are
never added: each retriever contributes only a rank to RRF. No reranker,
embedding-model change, or MMR was introduced.

Measurements used the same 12 questions, `structure-aware` corpus, top-3,
five warmed query measurements per question, and `all-MiniLM-L6-v2` on CPU.
The run used a separate temporary Chroma directory because the development
server held the normal embedded Chroma directory open.

| Metric | Dense-only baseline | BM25 + dense RRF | Change |
|---|---:|---:|---:|
| Hit-rate@3 | 9/12 (75.0%) | 12/12 (100.0%) | +25.0 percentage points |
| p50 latency/query | 37.07 ms | 39.12 ms | +2.04 ms |

### Per-question outcome

| ID | Dense Hit@3 | Hybrid Hit@3 | Outcome |
|---|---|---|---|
| B1 | Yes | Yes | Unaffected hit |
| B2 | No | Yes | Fixed |
| B3 | Yes | Yes | Unaffected hit |
| B4 | No | Yes | Fixed |
| B5 | Yes | Yes | Unaffected hit |
| B6 | No | Yes | Fixed |
| B7 | Yes | Yes | Unaffected hit |
| B8 | Yes | Yes | Unaffected hit |
| B9 | Yes | Yes | Unaffected hit |
| B10 | Yes | Yes | Unaffected hit |
| B11 | Yes | Yes | Unaffected hit |
| B12 | Yes | Yes | Unaffected hit |

The original R failures B2 (`0.75%`), B4 (`175C`), and B6 (`465F`) were all
fixed. No original R failure was left untouched. B1, B3, B5, B7, B8, B9,
B10, B11, and B12 already hit under dense retrieval and remain hits.

**Shipping decision: ship BM25 + RRF.** It recovers all three observed R
failures and raises Hit@3 by 25.0 percentage points for a 2.04 ms p50 latency
increase on this corpus. Re-run `backend/scripts/evaluate_hybrid_retrieval.py`
to regenerate the machine-readable inspection dump for the configured local
Chroma directory.
