"""Decomposes a substitution request, delegates to the substitution worker
and the allergen worker, and synthesizes one answer (Week 10). Every
hand-off is logged (app/orchestrator/handoff.py) so the context re-send
multiplier and the largest-hand-off attribution are measured, not asserted.
"""

import time

from app.models.chat import Citation
from app.models.substitution import SubstitutionResponse
from app.orchestrator.handoff import HandoffLog
from app.orchestrator.workers import WorkerError, run_allergen_worker, run_substitution_worker


def _refusal_response(message: str) -> SubstitutionResponse:
    return SubstitutionResponse(
        answer=message,
        refused=True,
        substitute_ingredient=None,
        adapted_ingredients=[],
        adapted_method="",
        oven="",
        servings="",
        allergens="",
        citations=[],
    )


def run_orchestrator(
    case_id: str,
    recipe_id: str,
    ingredient: str,
    diet: str,
    log: HandoffLog,
    simulate_allergen_worker_failure: bool = False,
) -> tuple[SubstitutionResponse, dict]:
    start = time.perf_counter()

    sub_result = run_substitution_worker(case_id, recipe_id, ingredient, diet, log)
    if "error" in sub_result:
        response = _refusal_response(sub_result["error"])
        return response, {"worker_failure_behavior": None, "latency_s": time.perf_counter() - start}

    substitute = sub_result.get("substitute_ingredient")
    allergens_text = sub_result.get("allergens", "")
    worker_failure_behavior = "ok"

    try:
        run_allergen_worker(case_id, substitute, log, simulate_failure=simulate_allergen_worker_failure)
        caveat = ""
    except WorkerError as exc:
        # DEGRADE, never fabricate: the orchestrator does NOT invent an
        # independent allergen verdict when the worker that would have
        # produced one failed - it falls back to the substitution worker's
        # own (unverified-by-a-second-source) allergens field and says so.
        caveat = (
            f" NOTE: the independent allergen-verification worker failed ({exc}); "
            f"this allergen line is from the substitution worker only, not independently confirmed."
        )
        worker_failure_behavior = "degraded_with_caveat"

    log.record(
        case_id,
        "substitution_worker+allergen_worker",
        "synthesis",
        {"substitution": sub_result, "allergens_text": allergens_text},
        note="combine both workers' results into one answer",
    )

    answer = f"Use {substitute} instead of {ingredient}. {allergens_text}{caveat}".strip()
    response = SubstitutionResponse(
        answer=answer,
        refused=False,
        substitute_ingredient=substitute,
        adapted_ingredients=sub_result.get("adapted_ingredients", []),
        adapted_method=sub_result.get("adapted_method", ""),
        oven="",
        servings=sub_result.get("servings", ""),
        allergens=allergens_text,
        citations=[Citation(chunk_id=c) for c in sub_result.get("citations", [])],
    )
    return response, {"worker_failure_behavior": worker_failure_behavior, "latency_s": time.perf_counter() - start}
