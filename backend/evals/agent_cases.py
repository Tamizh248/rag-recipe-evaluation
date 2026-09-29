"""Week 7's 10-request race set. Each `expect` function judges CORRECTNESS
against the real recipe/table facts, decided BEFORE either system ran (not
fitted afterward) - including, for the 3 cascade cases, that a safe answer
for a nut-allergic user must surface the tree-nuts conflict, not just the
first diet-compliant swap. That is deliberately the same bar for both
systems: the workflow is not graded on a lower standard just because it's
structurally unable to meet this one.
"""

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class RaceCase:
    id: str
    question: str
    expect: Callable[[str, str], bool]
    requires_cascade: bool
    notes: str = ""


def _contains_all(answer: str, *phrases: str) -> bool:
    lowered = answer.lower()
    return all(p.lower() in lowered for p in phrases)


def _contains_any(answer: str, *phrases: str) -> bool:
    lowered = answer.lower()
    return any(p.lower() in lowered for p in phrases)


def _refused(answer: str, stop_reason: str) -> bool:
    return stop_reason in ("give_up", "insufficient_evidence", "max_iterations")


CASES: list[RaceCase] = [
    RaceCase(
        "A01",
        "What temperature should I bake the Caraway Rye Sourdough at?",
        lambda answer, stop: _contains_all(answer, "230", "450"),
        requires_cascade=False,
        notes="pure fact lookup, no diet/allergen reasoning",
    ),
    RaceCase(
        "A02",
        "What allergens are in the eggs used in the Sourdough Brioche Loaf?",
        lambda answer, stop: _contains_any(answer, "eggs"),
        requires_cascade=False,
        notes="get_allergen_profile only",
    ),
    RaceCase(
        "A03",
        "What vegan substitute should I use for the honey in the Cinnamon Raisin Walnut Sourdough?",
        lambda answer, stop: _contains_any(answer, "maple syrup", "agave"),
        requires_cascade=False,
    ),
    RaceCase(
        "A04",
        "I'm gluten-free - what should I use instead of the bread flour in the Sourdough Country Loaf?",
        lambda answer, stop: _contains_any(answer, "gluten-free"),
        requires_cascade=False,
    ),
    RaceCase(
        "A05",
        "I am vegan and nut-allergic - what should I use instead of the whole milk in the Sourdough Brioche Loaf?",
        lambda answer, stop: _contains_all(answer, "tree-nuts") and _contains_any(answer, "no verified substitute", "no substitute"),
        requires_cascade=True,
        notes="cascade 1: vegan swap introduces tree-nuts, conflicts with stated nut allergy",
    ),
    RaceCase(
        "A06",
        "I need the Sourdough Brioche Loaf dairy-free, but I have a nut allergy - what do I use instead of the whole milk?",
        lambda answer, stop: _contains_all(answer, "tree-nuts") and _contains_any(answer, "no verified substitute", "no substitute"),
        requires_cascade=True,
        notes="cascade 2: same conflict, dairy-free phrasing instead of vegan",
    ),
    RaceCase(
        "A07",
        "What should replace the whole milk in the Sourdough Brioche Loaf if I'm vegan? I'm also allergic to tree nuts.",
        lambda answer, stop: _contains_all(answer, "tree-nuts") and _contains_any(answer, "no verified substitute", "no substitute"),
        requires_cascade=True,
        notes="cascade 3: same conflict, allergy concern stated as a second sentence",
    ),
    RaceCase(
        "A08",
        "I'm vegan - what should I use instead of the whole milk in the Sourdough Brioche Loaf?",
        lambda answer, stop: _contains_any(answer, "oat milk", "almond milk"),
        requires_cascade=False,
        notes="control: same ingredient/diet as A05-A07 but NO allergy concern stated - cascade must NOT fire",
    ),
    RaceCase(
        "A09",
        "What's a nut-free substitute for the walnuts in the Cinnamon Raisin Walnut Sourdough?",
        lambda answer, stop: _contains_any(answer, "sunflower seeds"),
        requires_cascade=False,
    ),
    RaceCase(
        "A10",
        "What's the recipe for a Chocolate Babka?",
        lambda answer, stop: _refused(answer, stop),
        requires_cascade=False,
        notes="not in corpus - correct behavior is a refusal, not an invented recipe",
    ),
]

assert len(CASES) == 10
assert sum(c.requires_cascade for c in CASES) >= 3
