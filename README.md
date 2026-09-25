# Recipe RAG Evaluation

A small, production-structured RAG application that ingests 6 fermentation
(bread) recipe cards, indexes them with two different chunking strategies,
and measures which one retrieves and answers questions better — with real,
reproducible Hit@5 numbers, metadata filtering, grounded generation,
citation validation, and refusal handling. UI polish was explicitly
deprioritized; retrieval/generation correctness and measurement were not.

**The evaluation report is [`evaluation/results.md`](evaluation/results.md).**
Every number in it comes from actually running the scripts below against
this repo's 6 recipe cards.

## 1. Project Overview

- **Domain:** 6 original sourdough/bread recipe cards (title, ingredient
  table with weight + baker's percentage, method, allergen note).
- **Core question:** does a chunker that understands recipe structure
  (title / ingredient table / method / allergens) retrieve and answer
  better than a naive fixed-size character chunker, on the *same* 6
  documents with the *same* embedding model, similarity metric, and top_k?
- **Answer (measured, not assumed):** yes — see
  [`evaluation/results.md`](evaluation/results.md) §10 for the full
  reasoning and honest tradeoffs.

## 2. Architecture

```
Angular UI  --HTTP-->  FastAPI
                          |
              +-----------+-----------+
              |                       |
          Search API               Chat API
              |                       |
          Retriever               Grounding
              |                       |
          Vector DB                 LLM
              |
        Chunks + Metadata

Ingestion:
Recipe Cards -> Document Loader -> Parser -> Metadata
                                       |
                    +------------------+------------------+
                    |                                     |
              Current Chunker                 Structure-Aware Chunker
                    |                                     |
                Embeddings                            Embeddings
                    |                                     |
        recipe_chunks_current              recipe_chunks_structure_aware
```

Backend package layout (`backend/app/`):

```
api/          FastAPI routers: health, ingest, search, chat
core/         Pydantic settings, logging
models/       Chunk / Search / Chat Pydantic schemas
ingestion/    loader (txt/pdf/docx), parser, metadata validation
chunking/     Chunker ABC, CurrentChunker, StructureAwareChunker
embeddings/   Sentence Transformer wrapper
vectorstore/  ChromaDB wrapper (2 collections, metadata filtering)
retrieval/    Retriever (embeds query -> vector search)
generation/   LLMProvider ABC, prompts, grounding/refusal logic
services/     Ingestion / Search / Chat orchestration (used by both
              scripts/ and the FastAPI routers, so logic isn't duplicated)
```

## 3. Requirements

- Python 3.11+ (developed and tested on Python 3.14)
- Node.js + npm (for the Angular UI)
- ~500MB free disk for the `sentence-transformers`/`torch` dependencies and
  the downloaded `all-MiniLM-L6-v2` model (auto-downloaded on first run)
- No external services required — ChromaDB runs embedded/local (persists to
  `backend/data/chroma/`), no separate server to start.
- Optional: an Anthropic API key, only if you want real LLM-generated
  answers instead of the deterministic local fallback (see §5).

## 4. Installation

```bash
cd backend
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```
Linux/macOS:
```bash
source .venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

## 5. Environment Setup

```bash
cp ../.env.example .env      # from backend/, or copy .env.example -> backend/.env
```

Key variables (see `.env.example` for the full list with comments):

| Variable | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `local` | `local` = deterministic, no-API-key generation stand-in. `anthropic` = real Claude model. |
| `LLM_API_KEY` | (empty) | Required only if `LLM_PROVIDER=anthropic`. Never commit a real key. |
| `LLM_MODEL` | `claude-sonnet-5` | Anthropic model name, used only when `LLM_PROVIDER=anthropic`. |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence Transformers model, shared by ingestion and retrieval. |
| `CHROMA_PERSIST_DIRECTORY` | `./data/chroma` | Local ChromaDB storage path (relative to `backend/`). |
| `TOP_K` | `5` | Default retrieval depth. |
| `CURRENT_CHUNK_SIZE` / `CURRENT_CHUNK_OVERLAP` | `250` / `50` | Baseline chunker window/overlap, in characters. |
| `CORS_ORIGINS` | `http://localhost:4200` | Allowed origins for the Angular dev server. |

**About `LLM_PROVIDER=local`:** no paid API key was available while building
this project, so a second, real implementation of the `LLMProvider`
interface (`app/generation/llm.py::LocalExtractiveProvider`) was built: it's
deterministic, needs no key, and finds the retrieved-context line with the
strongest whole-word overlap with the question, returning it with a
citation. It exists so the grounding/citation/refusal pipeline could be
exercised and reported truthfully end-to-end (see `evaluation/results.md`)
rather than leaving that section unfinished. To use real Claude instead:

```bash
# in backend/.env
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-...
LLM_MODEL=claude-sonnet-5
```

No other code changes are needed — `ChatService` depends only on the
`LLMProvider` interface (`app/generation/llm.py`).

## 6. Vector Storage

ChromaDB runs embedded (no server process to start). It persists to
`backend/data/chroma/` on first ingestion. To reset everything, just delete
that directory — the next ingestion run recreates it.

## 7-9. Ingesting the 6 Recipe Cards

**Only these 6 cards are ever ingested** — `scripts/ingest_recipes.py` is
pinned to an explicit filename list
(`app/services/ingestion_service.py::RECIPE_FILES`), not "everything in the
directory," so it can never accidentally index a larger/older corpus.

From `backend/`, with the venv activated:

```bash
# both strategies (recommended - needed for the evaluation scripts below)
python scripts/ingest_recipes.py --strategy both

# or one at a time
python scripts/ingest_recipes.py --strategy current
python scripts/ingest_recipes.py --strategy structure-aware
```

This creates two independent ChromaDB collections,
`recipe_chunks_current` and `recipe_chunks_structure_aware`, from the same 6
documents, same embedding model, same similarity metric — only the chunking
strategy differs between them.

## 10. Retrieval Evaluation (Hit@5)

Does **not** call any LLM.

```bash
python scripts/evaluate_retrieval.py
```

Prints a per-question HIT/MISS table and the Hit@5 summary for both
strategies, and writes the full dump to `evaluation/search_dump.json`.

## 11. Metadata Filtering Evaluation

```bash
python scripts/evaluate_filter.py
```

Finds a query where the unfiltered Top-1 result differs from the
`dietary_tags`-filtered Top-1 result, and writes the full before/after
comparison to `evaluation/filter_dump.json`.

## 12. Generation Evaluation

Runs 3 answerable + 3 unanswerable questions through the full grounded
generation pipeline (retrieval → grounding → LLM → citation/refusal checks):

```bash
python scripts/evaluate_generation.py
```

Writes `evaluation/generation_dump.json`. Uses whatever `LLM_PROVIDER` is
configured in `.env` (see §5).

## 13. Citation Validation

```bash
python scripts/validate_citations.py
```

Checks every citation from `evaluation/generation_dump.json` against the
live vector store (exists / correct recipe / lexically supports the
answer), plus one synthetic negative-control citation to prove invalid
citations are actually rejected. Writes `evaluation/citation_validation.json`.

## 14. Running the FastAPI Backend

```bash
uvicorn app.main:app --reload
```

Serves on `http://localhost:8000` by default. Endpoints:

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/api/ingest` | Trigger ingestion (`{"strategy": "current" \| "structure-aware" \| "both"}`) |
| POST | `/api/search` | Search-only retrieval, no LLM |
| POST | `/api/chat` | Full grounded generation |

Example requests:

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"question": "How much salt is used in the Sourdough Country Loaf?", "top_k": 5, "strategy": "structure-aware", "filters": {}}'

curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What vessel is used to bake the Sourdough Country Loaf?", "strategy": "structure-aware", "filters": {}}'

curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"question": "Which bread pairs well with a cheese board?", "top_k": 5, "strategy": "structure-aware", "filters": {"dietary_tags": ["vegan"]}}'
```

## 15. Running the Angular UI

```bash
cd frontend/angular-app
npm install   # already run once during setup; re-run if node_modules is missing
npm start     # ng serve, http://localhost:4200
```

The UI (deliberately unstyled) has: a question box, a chunking-strategy
selector, a dietary-tag filter, an Ask button, the answer + citation list,
and an optional "show retrieved chunks" panel. It talks to the FastAPI
backend at `http://localhost:8000` (see `API_BASE` in
`frontend/angular-app/src/app/app.ts`) — start the backend first. CORS is
enabled on the backend for `http://localhost:4200` (`CORS_ORIGINS` in
`.env`).

> Verification note: this environment has no browser-automation tool
> available, so the UI was verified by (1) `ng build` succeeding, (2) the
> Angular unit tests passing, and (3) directly simulating the browser's CORS
> preflight + POST request from origin `http://localhost:4200` against a
> running backend and confirming a correct `200` + `access-control-allow-origin`
> response. A manual click-through in an actual browser is recommended
> before treating the UI as fully verified.

## 16. Running Tests

```bash
cd backend
pytest tests/ -v
```

26 tests across `test_metadata.py`, `test_chunking.py`, `test_retrieval.py`,
`test_grounding.py`, `test_citations.py` — all currently passing. Retrieval
tests use a real (temporary, isolated) ChromaDB instance and the real
embedding model, not mocks, so a passing suite means the actual vector
search and filtering behavior works, not just that functions were called.

Angular unit tests:
```bash
cd frontend/angular-app
npm test -- --watch=false
```

## Two Chunking Strategies

- **Current (baseline)** — `app/chunking/current_chunker.py`: fixed-size
  character windows (`CURRENT_CHUNK_SIZE`/`CURRENT_CHUNK_OVERLAP`) with no
  knowledge of recipe structure. A `section` label is still attached per
  chunk (schema requires it) by finding which known section span the
  window overlaps *most*, but that happens strictly after boundaries are
  already fixed by character count — it never influences where a chunk
  starts or ends. At the configured 250/50 window this baseline
  demonstrably splits an ingredient row away from its table header/title
  for longer ingredient tables (see `tests/test_chunking.py` and
  `evaluation/results.md` §8).
- **Structure-aware** — `app/chunking/structure_aware_chunker.py`: exactly
  one chunk per logical recipe unit (title/overview, full ingredient table,
  full method, allergens), each prefixed with `Recipe: <title>` so it's
  self-contained even retrieved in isolation. An ingredient row is never
  separated from its header or its recipe's title.

Both implement the same `Chunker` ABC (`app/chunking/base.py`), so the rest
of the pipeline (embeddings, vector store, retrieval, generation) is
identical code regardless of which strategy is used — chunking is the only
experimental variable.

## Hit@5

For each of the 8 predefined questions (`evaluation/questions.json`,
written before any retrieval code existed), the top-5 chunks retrieved for
that question are checked: a **hit** requires at least one of the top-5 to
match *both* the expected `recipe_id` and the expected `section`. Hit@5 is
the fraction of the 8 questions that hit. Computed by
`scripts/evaluate_retrieval.py`, never hand-edited — see
`evaluation/results.md` §3 for the actual measured numbers.

## Task B: Hybrid Retrieval Evaluation

Task B uses a separate, fixed 12-question golden set at
[`evaluation/golden_set.jsonl`](evaluation/golden_set.jsonl). Each record has
the expected `chunk_id`; six questions contain exact or unusual terms such as
`flaxseed`, `rosemary`, `caraway`, or a named oven temperature. The production
retriever uses the task's single retrieval change: lexical BM25 and dense
cosine rankings combined with reciprocal-rank fusion (RRF, `k=60`). The two
score scales are not added or averaged.

To reproduce the dense-only baseline and hybrid after-measurement using the
same questions:

```bash
cd backend
python scripts/ingest_recipes.py --strategy structure-aware
python scripts/evaluate_hybrid_retrieval.py
```

The script writes per-question top-3 inspection evidence, R/G/Not-In-Corpus
labels, hit-rate@3, and p50 query latency to
[`evaluation/hybrid_retrieval_dump.json`](evaluation/hybrid_retrieval_dump.json).
The Task B report is recorded in [`evaluation/results.md`](evaluation/results.md).

## Metadata Filtering

`dietary_tags` filtering is applied as a real ChromaDB `where` clause at
query time (`app/vectorstore/chroma_store.py::build_where_clause`), not as
Python post-filtering of already-returned results. Each dietary tag is
stored as its own boolean metadata flag per chunk (e.g. `dietary_vegan:
true`), since ChromaDB metadata values must be scalars, not lists — the
original tag list is also stored as a comma-joined string for display and
reconstructed back into a list on retrieval.

## Grounding / Refusal

The LLM is instructed to use only supplied context, never guess, never
invent quantities or missing nutritional data, cite every factual claim
with a real `chunk_id`, and refuse if the context is insufficient (see the
exact prompt in `app/generation/prompts.py` — no "use your best judgement"
language). But refusal safety does **not** rely solely on the LLM following
that instruction (`app/generation/grounding.py`):

1. **Before** calling the LLM: if the retrieved context has no real lexical
   evidence for what's being asked (beyond just matching the recipe name),
   refuse deterministically without an LLM call at all.
2. **After** the LLM responds: reject (force refusal) if it answered with
   zero citations, or with a citation to a `chunk_id` that wasn't actually
   retrieved.

This two-sided check matters in practice — for the 3 "unanswerable"
questions in this project (protein/calorie/sodium content), retrieval
actually finds the *correct* recipe with high similarity scores (0.70+,
comparable to answerable questions), since the recipe name matches; only
the content-level check catches that the specific fact isn't there. See
`evaluation/results.md` §7.

## Location of `results.md`

[`evaluation/results.md`](evaluation/results.md) — dataset description, all
8 questions, the full Hit@5 table, the metadata filtering demonstration,
3 grounded answers + citation validation, 3 refusal transcripts, an
embarrassing-retrieval failure analysis, the bonus-scenario experiment
(honestly reported as not observed), and the final chunking decision with
tradeoffs.

## Assumptions Made

1. **Recipe source data**: no source files were supplied with the
   assignment, so all 6 recipe cards (`backend/data/recipes/*.txt`) were
   authored from scratch as original sourdough/bread recipes — bread is the
   domain where "baker's percentage" is a standard, real unit, consistent
   with a "fermentation chapter."
2. **LLM provider**: no paid API key was available, so a second real
   `LLMProvider` implementation (`LocalExtractiveProvider`) was built as the
   default so the full pipeline is runnable and its results in
   `results.md` are real (not fabricated) end-to-end runs, clearly labeled
   as such. `AnthropicProvider` is fully implemented and used automatically
   once `LLM_PROVIDER=anthropic` + `LLM_API_KEY` are set.
3. **Baseline chunker window size**: `CURRENT_CHUNK_SIZE=250` /
   `CURRENT_CHUNK_OVERLAP=50` was chosen deliberately (rather than a larger,
   safer default) because it's the smallest window that still produces
   coherent chunks while actually reproducing the "ingredient row split
   from its header" failure mode the assignment describes — verified
   directly against the real recipe text, not asserted.
4. **Section labels for the baseline chunker**: since the metadata schema
   requires a `section` per chunk but the baseline chunker has no structural
   awareness by design, its chunks are labeled post-hoc by character-overlap
   with known section spans — a label, not a decision that ever affects
   chunk boundaries.
5. **Repository location**: built at `rag-recipe-evaluation/` as its own
   git repository, independent of any other files in the parent directory.
6. **Angular UI verification**: no browser-automation tool is available in
   this environment; the UI was verified via build success, unit tests, and
   a simulated real CORS request rather than a manual browser click-through
   (see §15).
