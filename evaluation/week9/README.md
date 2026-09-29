# Week 9 — MCP

Real MCP throughout: two actual server subprocesses speaking JSON-RPC over
stdio (`backend/mcp_servers/recipe_server.py`, `ingredient_db_server.py`),
discovered and called by a real client (`backend/app/agent/mcp_client.py`)
- no in-process shortcuts. This replaced the direct in-process tool calls
`app/agent/agent.py` used through Week 8.

## What changed structurally

- `backend/app/agent/tools.py` is no longer imported by the agent/workflow
  at all - it's now purely the implementation library `recipe_server.py`
  wraps. Discovery/dispatch goes exclusively through `mcp_client.py`.
- `app/agent/agent.py` and `workflow.py` only ever call
  `get_mcp_client().list_tools()` / `.call_tool(name, arguments)` - nothing
  in either file names a specific server.

## Deliverables

| File | What it proves |
|---|---|
| `agent_diff.txt` | `app/agent/agent.py` is byte-identical before and after adding `ingredient_db_server` to `mcp_config.json` - config-only swap |
| `tool_count.md` | 3 tools -> 4 tools, with names, from real `tools/list` output, plus the one query that calls the new tool |
| `wire.json` / `wire_annotated.md` | the raw `initialize` -> `tools/list` -> `tools/call` exchange against the new server, every top-level field annotated, and where the model call does/doesn't happen |
| `error_before_after.md` | `substitute_ingredient`'s docstring rewritten as explicit model instructions, and its "ingredient not found" error made recoverable (names the closest real match instead of just refusing) |
| `risk_note.md` | 5-line supply-chain risk note for `ingredient_db_server` |

## A note on what's simulated vs real

The MCP protocol, both server processes, and the client are all real - two
genuine separate OS processes exchanging real JSON-RPC. What's simulated is
the *content*: no public ingredient-nutrition API was wired up, so
`ingredient_db_server.py` is a disclosed local stand-in with a small fixed
dataset (same "disclosed stand-in" pattern as this project's
`LocalExtractiveProvider` elsewhere) standing in for "the content team's
server" the task's problem statement describes.
