# Week 9 — Tool Count Before -> After

Both counts are the live output of `app/agent/mcp_client.py`'s
`list_tools()`, which is populated ONLY from each configured server's real
`tools/list` response (`backend/mcp_servers/recipe_server.py` and, once
added, `ingredient_db_server.py`) — never from this project's own notes.

## Before (`mcp_config.json` with only `recipe_server`)

**3 tools:**
- `search_recipes` (server: `recipe_server`)
- `substitute_ingredient` (server: `recipe_server`)
- `get_allergen_profile` (server: `recipe_server`)

## After (`mcp_config.json` with `recipe_server` + `ingredient_db_server`)

**4 tools:**
- `search_recipes` (server: `recipe_server`)
- `substitute_ingredient` (server: `recipe_server`)
- `get_allergen_profile` (server: `recipe_server`)
- `lookup_ingredient` (server: `ingredient_db_server`) — **new**

## The one query that provably calls the new server's tool

```
>>> get_mcp_client().call_tool("lookup_ingredient", {"name": "walnuts"})
{'ingredient': 'walnuts', 'allergens': ['tree-nuts'],
 'nutrition_per_100g': {'calories': 654, 'protein_g': 15.2, 'fat_g': 65.2, 'carbs_g': 13.7}}
```

The tool name (`lookup_ingredient`) and its owning server (`ingredient_db_server`,
per `_tool_to_server` in `mcp_client.py`) are both visible directly in this
call — see `wire.json` / `wire_annotated.md` for the same call captured at
the raw JSON-RPC level.
