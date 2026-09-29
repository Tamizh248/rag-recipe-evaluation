"""app.agent.tools calls app.api.deps.get_retriever()/get_substitution_service()
directly (same production-coupled style as the sample rag-poc project's own
app/agent/tools.py) - monkeypatched here to the session's ISOLATED test
store/retriever/substitution_service fixtures, so these tests never touch
the real backend/data/chroma directory.
"""

import pytest

from app.agent import tools as agent_tools
from app.agent.agent import run_agent_with_state
from app.agent.safety import MAX_STEPS
from app.agent.workflow import run_workflow


@pytest.fixture(autouse=True)
def _isolated_agent_tools(monkeypatch, retriever, substitution_service):
    monkeypatch.setattr(agent_tools, "get_retriever", lambda: retriever)
    monkeypatch.setattr(agent_tools, "get_substitution_service", lambda: substitution_service)


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
