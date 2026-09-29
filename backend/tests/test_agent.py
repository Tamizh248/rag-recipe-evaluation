"""As of Week 9, the agent talks to its tools over the real MCP protocol
(app/agent/mcp_client.py spawns backend/mcp_servers/recipe_server.py as a
real subprocess - see backend/mcp_config.json). That subprocess is a
separate Python process with its own memory, so it cannot be monkeypatched
onto this test session's isolated store/retriever fixtures the way
in-process calls could before Week 9.

These are therefore integration tests against the REAL backend/data/chroma
directory (already ingested with the same 6 known recipes - see
backend/scripts/ingest_recipes.py) - same philosophy as the sample rag-poc
project's own tests/test_e2e.py ("real chunking, real embeddings, ... no
mocks") for exactly this kind of process-boundary-crossing integration
point.
"""

from app.agent.agent import run_agent_with_state
from app.agent.safety import MAX_STEPS
from app.agent.workflow import run_workflow


def test_agent_answers_pure_fact_lookup_with_search_only():
    result, state = run_agent_with_state("What temperature should I bake the Caraway Rye Sourdough at?")
    assert result["stop_reason"] == "goal_completed"
    assert "230" in result["answer"] and "450" in result["answer"]
    assert [s.tool for s in state.steps] == ["search_recipes"]


def test_agent_cascades_when_substitute_conflicts_with_stated_allergy():
    question = "I am vegan and nut-allergic - what should I use instead of the whole milk in the Sourdough Brioche Loaf?"
    result, state = run_agent_with_state(question)
    tool_sequence = [s.tool for s in state.steps]

    assert tool_sequence.count("substitute_ingredient") == 2, "must attempt a second swap after finding the conflict"
    assert "get_allergen_profile" in tool_sequence
    assert "tree-nuts" in result["answer"].lower()
    assert result["stop_reason"] == "goal_completed"


def test_workflow_does_not_cascade_on_the_same_request():
    question = "I am vegan and nut-allergic - what should I use instead of the whole milk in the Sourdough Brioche Loaf?"
    result = run_workflow(question)
    # The fixed workflow only ever runs ONE substitution step - it has no
    # way to notice the tree-nuts conflict this specific request creates.
    assert "tree-nuts" not in result["answer"].lower() or "no verified substitute" not in result["answer"].lower()
    assert result["tool_calls"] <= 2


def test_agent_refuses_when_ingredient_not_in_the_recipe_it_found():
    result, state = run_agent_with_state("What's the recipe for a Chocolate Babka?")
    assert result["stop_reason"] in ("give_up", "insufficient_evidence")


def test_agent_budget_terminates_cleanly_instead_of_spinning():
    question = (
        "I need this vegan, dairy-free, egg-free, nut-free, and gluten-free - "
        "what should I use instead of the whole milk in the Sourdough Brioche Loaf?"
    )
    result, state = run_agent_with_state(question)
    assert result["stop_reason"] == "max_iterations"
    assert len(state.steps) == MAX_STEPS
