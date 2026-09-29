"""MCP server exposing this app's OWN 3 recipe tools - "server one" in the
Week 9 task. Run standalone (python mcp_servers/recipe_server.py, cwd=
backend/) or spawned by app/agent/mcp_client.py per backend/mcp_config.json.

Reuses the exact same underlying implementations app/agent/tools.py already
had (search/substitute/allergen) - this file only adds the MCP transport
and typed parameters on top; it does not reimplement any retrieval or
substitution logic.
"""

import contextlib
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# MUST happen before importing any app.* module: MCP's stdio transport uses
# stdout exclusively for the JSON-RPC stream, byte for byte - a single
# stray log line on stdout corrupts it. app.core.logging.configure_logging()
# attaches a stdout StreamHandler on first call (triggered transitively by
# importing app.agent.tools below); pre-empting the root logger with a
# stderr handler here makes that later call a no-op (it checks
# `if root.handlers: return`), so every log line - ours and the mcp
# library's own - goes to stderr instead.
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

from mcp.server.fastmcp import FastMCP

from app.agent.tools import _get_allergen_profile, _search_recipes, _substitute_ingredient

mcp = FastMCP("recipe_server")


@contextlib.contextmanager
def _stdout_redirected_to_stderr():
    """Belt-and-suspenders on top of the logging fix above: the
    sentence-transformers/huggingface_hub stack (loaded on the FIRST real
    search_recipes call, downloading/loading the embedding model) writes
    tqdm progress bars and warnings straight to the OS stdout file
    descriptor, bypassing Python's logging module entirely - the logging
    fix above cannot catch that. Redirects fd 1 (stdout) to fd 2 (stderr)
    for the duration of one tool call, at the OS level, so nothing any
    library writes can land on the JSON-RPC stream; restored immediately
    after, before the mcp library writes this call's own response."""
    stdout_fd = 1
    saved_fd = os.dup(stdout_fd)
    try:
        os.dup2(2, stdout_fd)
        yield
    finally:
        os.dup2(saved_fd, stdout_fd)
        os.close(saved_fd)


@mcp.tool()
def search_recipes(query: str) -> dict:
    """Search the recipe corpus for passages relevant to a free-text query.
    Runs hybrid BM25 + dense retrieval. Argument: the search query."""
    with _stdout_redirected_to_stderr():
        return _search_recipes(query)


@mcp.tool()
def substitute_ingredient(recipe_id: str, ingredient: str, diet: str) -> dict:
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
    with _stdout_redirected_to_stderr():
        return _substitute_ingredient(f"{recipe_id}, {ingredient}, {diet}")


@mcp.tool()
def get_allergen_profile(ingredient: str) -> dict:
    """Look up known allergens for exactly one ingredient - nothing else,
    and independent of any specific recipe. Returns allergens from:
    gluten, dairy, eggs, tree-nuts."""
    with _stdout_redirected_to_stderr():
        return _get_allergen_profile(ingredient)


if __name__ == "__main__":
    mcp.run()
