"""Integration tests against the real MCP servers (same rationale as
tests/test_agent.py - the orchestrator's workers call the real
mcp_client.py, a separate subprocess, which cannot be monkeypatched onto
this session's isolated fixtures)."""

from app.orchestrator.handoff import HandoffLog
from app.orchestrator.orchestrator import run_orchestrator
from app.orchestrator.single_agent import run_single_agent


def test_single_agent_and_orchestrator_agree_on_a_normal_case():
    single_response, _ = run_single_agent("brioche_sourdough_900g", "unsalted butter", "vegan")
    log = HandoffLog()
    orch_response, meta = run_orchestrator("t1", "brioche_sourdough_900g", "unsalted butter", "vegan", log)

    assert single_response.refused is False
    assert orch_response.refused is False
    assert single_response.substitute_ingredient == orch_response.substitute_ingredient
    assert meta["worker_failure_behavior"] == "ok"


def test_orchestrator_has_handoffs_single_agent_does_not():
    log = HandoffLog()
    run_orchestrator("t2", "sourdough_country_2kg", "bread flour", "gluten-free", log)
    assert len(log.entries) >= 3  # dispatch, result, synthesis at minimum
    assert log.total_tokens() > 0


def test_orchestrator_degrades_instead_of_fabricating_on_worker_failure():
    log = HandoffLog()
    response, meta = run_orchestrator(
        "t3", "brioche_sourdough_900g", "whole milk", "vegan", log, simulate_allergen_worker_failure=True
    )
    assert meta["worker_failure_behavior"] == "degraded_with_caveat"
    assert not response.refused
    # It must say the check failed, not silently present a confident, unverified claim as fact.
    assert "failed" in response.answer.lower() or "not independently confirmed" in response.answer.lower()


def test_orchestrator_refuses_the_same_way_single_agent_does():
    log = HandoffLog()
    orch_response, _ = run_orchestrator("t4", "brioche_sourdough_900g", "ground cinnamon", "vegan", log)
    single_response, _ = run_single_agent("brioche_sourdough_900g", "ground cinnamon", "vegan")
    assert orch_response.refused is True
    assert single_response.refused is True
