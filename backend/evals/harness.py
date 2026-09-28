"""Runs the Week 6 eval set against the REAL SubstitutionService /
ChatService - shared by run_eval.py (requirement 1, no judge) and
run_judge.py (requirements 3-5, judge validation). One place that runs a
case, so both scripts agree on what "ran" means.
"""

from dataclasses import dataclass, field

from app.api.deps import get_chat_service, get_substitution_service
from evals import assertions
from evals.cases import CASES, REGRESSION_CASES, RegressionCase, SubstitutionCase


@dataclass
class CaseRun:
    case: SubstitutionCase
    response: object  # SubstitutionResponse
    assertion_results: list[tuple[str, bool, str]] = field(default_factory=list)
    outcome_correct: bool = False
    judge_pass: bool | None = None
    judge_verdict: str | None = None

    @property
    def passed(self) -> bool:
        if not self.outcome_correct:
            return False
        return all(ok for _, ok, _ in self.assertion_results)


@dataclass
class RegressionRun:
    case: RegressionCase
    answer: str
    citations: list[str]
    passed: bool
    detail: str


def run_substitution_case(case: SubstitutionCase) -> CaseRun:
    service = get_substitution_service()
    response = service.substitute(case.recipe_id, case.ingredient, case.diet)

    outcome_correct = response.refused != case.expect_answerable
    results: list[tuple[str, bool, str]] = []

    if case.expect_answerable and not response.refused:
        for fn in assertions.ASSERTIONS:
            ok, detail = fn(response)
            results.append((fn.__name__, ok, detail))
        ok, detail = assertions.allergen_warning_present_when_needed(response, set(case.expected_allergens))
        results.append(("allergen_warning_present_when_needed", ok, detail))
        if case.expected_servings:
            ok, detail = assertions.servings_are_echoed(response, case.expected_servings)
            results.append(("servings_are_echoed", ok, detail))

    return CaseRun(case=case, response=response, assertion_results=results, outcome_correct=outcome_correct)


def run_all_substitution_cases() -> list[CaseRun]:
    return [run_substitution_case(case) for case in CASES]


def _check_regression(case: RegressionCase, answer: str, citations: list[str]) -> tuple[bool, str]:
    if case.id == "R01":
        ok = answer.strip() != "Method:" and len(answer.strip()) > 20
        return ok, f"answer={answer!r}"
    if case.id == "R02":
        ok = any(cid.startswith("rosemary_olive_focaccia") for cid in citations)
        return ok, f"citations={citations!r}"
    raise ValueError(f"No regression check defined for {case.id!r}")


def run_regression_case(case: RegressionCase) -> RegressionRun:
    chat_service = get_chat_service()
    response = chat_service.answer(case.question, strategy="structure-aware")
    passed, detail = _check_regression(case, response.answer, response.citations and [c.chunk_id for c in response.citations])
    return RegressionRun(case=case, answer=response.answer, citations=[c.chunk_id for c in response.citations], passed=passed, detail=detail)


def run_all_regression_cases() -> list[RegressionRun]:
    return [run_regression_case(case) for case in REGRESSION_CASES]


def pass_rate_by_mode(runs: list[CaseRun], regression_runs: list[RegressionRun]) -> dict[str, dict]:
    by_mode: dict[str, list[bool]] = {}
    for run in runs:
        by_mode.setdefault(run.case.mode, []).append(run.passed)
    for run in regression_runs:
        by_mode.setdefault(run.case.mode, []).append(run.passed)

    return {
        mode: {"pass": sum(results), "total": len(results), "pass_rate": sum(results) / len(results)}
        for mode, results in sorted(by_mode.items())
    }
