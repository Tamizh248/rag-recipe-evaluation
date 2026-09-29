# Week 9 — Raw JSON-RPC Exchange, Hand-Annotated

Captured by `backend/scripts/capture_mcp_wire.py` talking newline-delimited
JSON-RPC directly to `ingredient_db_server.py`'s stdin/stdout, bypassing
the `mcp` SDK's `ClientSession` entirely — every message below is
verbatim wire content, not a library's summary of it (raw dump:
[`wire.json`](./wire.json)).

## 1. `initialize` (client -> server)

```json
{"jsonrpc": "2.0", "id": 1, "method": "initialize",
 "params": {"protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "week9-wire-capture", "version": "0.1"}}}
```

- `jsonrpc`: protocol marker — every message on this transport is JSON-RPC 2.0.
- `id`: 1 — this request's correlation id; the matching response echoes it back.
- `method`: `initialize` — the first message of any MCP session, always.
- `params.protocolVersion`: the MCP spec version *this client* speaks — the server can accept it or downgrade.
- `params.capabilities`: what optional protocol features the client supports (empty here — this capture script is minimal, no sampling/roots support).
- `params.clientInfo`: free-form client identity, for the server's own logging — never authentication.

## 2. `initialize` response (server -> client)

```json
{"jsonrpc": "2.0", "id": 1,
 "result": {"protocolVersion": "2025-06-18",
            "capabilities": {"experimental": {}, "prompts": {"listChanged": false},
                              "resources": {"subscribe": false, "listChanged": false},
                              "tools": {"listChanged": false}},
            "serverInfo": {"name": "ingredient_db_server", "version": "1.30.0"}}}
```

- `id`: 1 — matches the request; this is its response, not a new message.
- `result.protocolVersion`: the version the server actually agreed to use (matched ours here).
- `result.capabilities.tools.listChanged: false`: this server won't push a notification if its tool list changes later — a client must re-poll `tools/list` to notice.
- `result.capabilities.prompts` / `.resources`: declared but unused by this server (`FastMCP` advertises them by default even with zero prompts/resources registered).
- `result.serverInfo`: identifies which server process answered — `name` comes straight from `FastMCP("ingredient_db_server")` in the server's own source, `version` is the installed `mcp` package's version, not this project's.

## 3. `notifications/initialized` (client -> server)

```json
{"jsonrpc": "2.0", "method": "notifications/initialized"}
```

- No `id`: a **notification**, not a request — the protocol requires no response, and none was sent. This is the client formally confirming the handshake is complete; a server may reject earlier calls that arrive before this.

## 4. `tools/list` (client -> server)

```json
{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
```

- The discovery call. `params: {}` — this server has few enough tools that pagination (a `cursor` param) never comes up.

## 5. `tools/list` response (server -> client)

```json
{"jsonrpc": "2.0", "id": 2,
 "result": {"tools": [{"name": "lookup_ingredient",
                        "description": "Look up one ingredient's allergen flags and nutrition per 100g by\nname. Argument: the ingredient name.",
                        "inputSchema": {"properties": {"name": {"title": "Name", "type": "string"}},
                                        "required": ["name"], "title": "lookup_ingredientArguments", "type": "object"}}]}}
```

- `result.tools`: one entry per `@mcp.tool()`-decorated function in `ingredient_db_server.py` — exactly 1 here.
- `.description`: taken **verbatim from the Python docstring** — this is literally the prompt text a model sees when deciding whether to call this tool; there is no separate "description" field to author.
- `.inputSchema`: a JSON Schema auto-generated from the function's type hints (`name: str` -> `{"type": "string"}`, no default -> `"required": ["name"]`) — the server never hand-writes this, and a model is expected to construct `arguments` that validate against it.

## 6. `tools/call` (client -> server)

```json
{"jsonrpc": "2.0", "id": 3, "method": "tools/call",
 "params": {"name": "lookup_ingredient", "arguments": {"name": "walnuts"}}}
```

- `params.name`: which discovered tool to invoke — must match a name `tools/list` returned.
- `params.arguments`: a JSON object satisfying that tool's `inputSchema` — structured, typed data, never a single opaque string.

## 7. `tools/call` response (server -> client)

```json
{"jsonrpc": "2.0", "id": 3,
 "result": {"content": [{"type": "text",
                          "text": "{\n  \"ingredient\": \"walnuts\",\n  \"allergens\": [\n    \"tree-nuts\"\n  ],\n  \"nutrition_per_100g\": {...}\n}"}],
            "isError": false}}
```

- `result.content`: a list of content blocks (here, one `text` block) — this SDK version serializes a Python `dict` return value as pretty-printed JSON **text**, not as structured content; the client (`app/agent/mcp_client.py`) re-parses that text with `json.loads` to get the dict back.
- `result.isError`: `false` — a **protocol-level, not transport-level** signal for tool failure. A tool that raises an exception still returns a normal JSON-RPC *result* (never a JSON-RPC *error*), just with `isError: true` and the exception text inside `content` — see `error_before_after.md` for that path.

## Where the model call happens, and where it doesn't

**The model call happens nowhere in this file, and nowhere inside either
MCP server process.** Both `recipe_server.py` and `ingredient_db_server.py`
are pure logic — retrieval, table lookups, string formatting — with zero
LLM calls anywhere in their code. The only two places an LLM is ever
invoked are in the **agent process** (`app/agent/agent.py`): once per loop
iteration to *decide* which tool to call next (`_llm_decide`, only when
`LLM_PROVIDER=anthropic`), and once at the end to *compose the final
answer* (`_compose_final_answer`). The MCP exchange above is strictly the
plumbing that gets a tool's raw result back to that agent process — the
server never sees the user's question, never reasons about anything, and
never decides what to do with what it returns.
