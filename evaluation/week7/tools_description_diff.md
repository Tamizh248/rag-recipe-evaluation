# Week 7 — Third Tool

No agent existed before this week (Weeks 3-6 built retrieval, evals, and
the substitution feature, but no tool-calling loop), so this is the whole
tool set's first version - `get_allergen_profile` is the third tool added
alongside the two the agent needs at minimum (`search_recipes`,
`substitute_ingredient`), all defined in `backend/app/agent/tools.py`.

```python
Tool(
    name="search_recipes",
    description=(
        "Search the recipe corpus for passages relevant to a free-text query. "
        "Runs hybrid BM25 + dense retrieval. Argument: the search query."
    ),
),
Tool(
    name="substitute_ingredient",
    description=(
        "Look up a diet-appropriate substitute for exactly one ingredient in "
        "exactly one recipe - nothing else. Argument: "
        '"<recipe_id>, <ingredient>, <diet>", e.g. "brioche_sourdough_900g, whole milk, vegan". '
        "diet must be one of: vegan, dairy-free, egg-free, nut-free, gluten-free."
    ),
),
Tool(
    name="get_allergen_profile",  # <-- the third tool
    description=(
        "Look up known allergens for exactly one ingredient - nothing else, "
        "and independent of any specific recipe. Argument: the ingredient name. "
        "Returns allergens from: gluten, dairy, eggs, tree-nuts."
    ),
),
```

Each description names exactly one job and uses an enum for its
constrained parameter (`diet`, `allergens`), and none overlap:
`search_recipes` returns unstructured passages; `substitute_ingredient`
changes one ingredient in one recipe; `get_allergen_profile` reports facts
about one ingredient, tied to no recipe, and never changes anything. The
overlap that would have been easy to introduce - `get_allergen_profile`
being recipe-scoped like `substitute_ingredient` - was deliberately avoided
so the agent can call it on a *substitute the recipe never contained*
(the cascade in `app/agent/agent.py`), which a recipe-scoped version
couldn't do.
