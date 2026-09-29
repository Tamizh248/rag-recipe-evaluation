# Week 9 — Docstring-as-Prompt + Recoverable Error (own server)

Tool: `substitute_ingredient` on **our own** `mcp_servers/recipe_server.py`
(not the third-party `ingredient_db_server.py`).

## Docstring rewrite

**Before** (`app/agent/agent.py`'s old in-process tool description, pre-Week 9):
```
"Look up a diet-appropriate substitute for exactly one ingredient in "
"exactly one recipe - nothing else. Argument: "
'"<recipe_id>, <ingredient>, <diet>", e.g. "brioche_sourdough_900g, whole milk, vegan". '
"diet must be one of: vegan, dairy-free, egg-free, nut-free, gluten-free."
```
A single sentence naming the argument format, nothing about what to do
when a call fails.

**After** (`mcp_servers/recipe_server.py::substitute_ingredient`, current):
```
"""Look up a diet-appropriate substitute for exactly one ingredient in
exactly one recipe. Use this whenever a request names both an ingredient
AND a dietary restriction for a specific recipe - never guess a
substitute yourself, this tool is the only source of truth for one.

Arguments:
- recipe_id: the exact recipe_id from a prior search_recipes result.
- ingredient: the ingredient's name AS IT APPEARS IN THAT RECIPE'S OWN
  ingredient table (e.g. "eggs (whole)", not just "eggs" - if you're not
  sure of the exact spelling, call search_recipes first and read it off
  the ingredients section).
- diet: exactly one of vegan, dairy-free, egg-free, nut-free, gluten-free.

If the ingredient name doesn't match this recipe's table exactly, the
error names the closest real entry to retry with (e.g. "no ingredient
matched 'eggs' in 'brioche_sourdough_900g': try 'eggs (whole)'") -
retry once with that suggestion rather than giving up. If diet has no
verified substitute on file, the error says so plainly; do not invent
one anyway.
"""
```
Written as instructions a model reads and follows — what to use it for,
when NOT to guess instead, exactly what each argument means, and what to
do when a call fails. This is literally the text `tools/list` returns as
this tool's `description` (see `wire_annotated.md` item 5) - there is no
separate prompt; the docstring *is* the prompt.

## Recoverable error path

The failure this targets: a caller (model or user) names an ingredient
close to, but not exactly matching, this recipe's own table spelling.

**Before** (`app/substitution/service.py`, prior to this week):
```python
if target not in ingredient_names:
    return self._to_response(
        _refusal(f"{recipe_id!r} does not list {ingredient!r} as an ingredient."), retrieved_ids
    )
```

**After** (current):
```python
if target not in ingredient_names:
    suggestion = next((name for name in ingredient_names if target in name or name in target), None)
    if suggestion:
        message = f"no ingredient matched {ingredient!r} in {recipe_id!r}: try {suggestion!r}"
    else:
        message = f"no ingredient matched {ingredient!r} in {recipe_id!r}: not in this recipe"
    return self._to_response(_refusal(message), retrieved_ids)
```

## Before/after transcript — same failing call

Call: `substitute_ingredient(recipe_id="brioche_sourdough_900g", ingredient="eggs", diet="vegan")`
(a real, near-miss call — the recipe's table says `"eggs (whole)"`)

**BEFORE:**
```
refused: True
answer: 'brioche_sourdough_900g' does not list 'eggs' as an ingredient.
```
A model (or the local deterministic composer) receiving this has no path
forward except giving up on the substitution entirely - the message names
what's wrong but not what to try instead. "Error 3"-shaped: technically
informative, practically a dead end.

**AFTER** (captured live from the running code, `git diff`-verifiable against `app/substitution/service.py`):
```
refused: True
answer: no ingredient matched 'eggs' in 'brioche_sourdough_900g': try 'eggs (whole)'
```
The exact same request now tells the caller precisely what to retry with.
A real Claude-driven agent (`LLM_PROVIDER=anthropic`) reading the updated
docstring's explicit instruction ("retry once with that suggestion rather
than giving up") would call `substitute_ingredient` again with
`ingredient="eggs (whole)"` and succeed on the second attempt, instead of
reporting failure to the user after the first.
