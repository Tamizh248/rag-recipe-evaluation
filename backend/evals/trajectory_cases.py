"""The 10 trajectory-eval cases (Week 8, deliverable 1) against the real
agent (app/agent/agent.py) and its 3 real tools. Same shape as the sample
rag-poc project's evals/cases.py: `required_tools` is a SET the trajectory
must contain, not a rigid sequence, so a case with more than one legitimate
path (T05/T06 - the cascade fires whichever diet phrasing the request
used) isn't over-asserted into a brittle failure.

`expect` is the OUTCOME check (graded by evals/trajectory_metrics.py's
outcome_pass_rate - never looks at which tools ran); `required_tools` /
`forbidden_tools` / `optimal_tool_calls` are the TRAJECTORY check (never
looks at the answer text). Kept deliberately separate so the Gap
(outcome_pass_rate - trajectory_pass_rate) means something.
"""

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class TrajectoryCase:
    id: str
    question: str
    required_tools: frozenset[str]
    optimal_tool_calls: int
    expect: Callable[[str, str], bool]
    forbidden_tools: frozenset[str] = field(default_factory=frozenset)
    valid_tools: frozenset[str] | None = None
    expect_answered: bool = True
    notes: str = ""

    def tools_considered_valid(self) -> frozenset[str]:
        if self.valid_tools is not None:
            return self.valid_tools
        return self.required_tools | {"search_recipes"}


def _contains_all(answer: str, *phrases: str) -> bool:
    lowered = answer.lower()
    return all(p.lower() in lowered for p in phrases)


def _contains_any(answer: str, *phrases: str) -> bool:
    lowered = answer.lower()
    return any(p.lower() in lowered for p in phrases)


def _refused(answer: str, stop_reason: str) -> bool:
    return stop_reason in ("give_up", "insufficient_evidence", "max_iterations")


CASES: list[TrajectoryCase] = [
    TrajectoryCase(
        id="T01",
        question="What temperature should I bake the Caraway Rye Sourdough at?",
        required_tools=frozenset({"search_recipes"}),
        forbidden_tools=frozenset({"substitute_ingredient", "get_allergen_profile"}),
        optimal_tool_calls=1,
        expect=lambda answer, stop: _contains_all(answer, "230", "450"),
        notes="pure fact lookup - no diet/allergen reasoning needed.",
    ),
    TrajectoryCase(
        id="T02",
        question="What allergens are in the eggs used in the Sourdough Brioche Loaf?",
        required_tools=frozenset({"search_recipes", "get_allergen_profile"}),
        forbidden_tools=frozenset({"substitute_ingredient"}),
        optimal_tool_calls=2,
        expect=lambda answer, stop: _contains_any(answer, "eggs"),
    ),
    TrajectoryCase(
        id="T03",
        question="What vegan substitute should I use for the honey in the Cinnamon Raisin Walnut Sourdough?",
        required_tools=frozenset({"search_recipes", "substitute_ingredient"}),
        valid_tools=frozenset({"search_recipes", "substitute_ingredient", "get_allergen_profile"}),
        optimal_tool_calls=2,
        expect=lambda answer, stop: _contains_any(answer, "maple syrup", "agave"),
        notes="the agent also runs a post-substitution allergen check (see T08/T09) - allowed as a valid extra tool, but it costs a step beyond optimal.",
    ),
    TrajectoryCase(
        id="T04",
        question="I'm gluten-free - what should I use instead of the bread flour in the Sourdough Country Loaf?",
        required_tools=frozenset({"search_recipes", "substitute_ingredient"}),
        valid_tools=frozenset({"search_recipes", "substitute_ingredient", "get_allergen_profile"}),
        optimal_tool_calls=2,
        expect=lambda answer, stop: _contains_any(answer, "gluten-free"),
    ),
    TrajectoryCase(
        id="T05",
        question="I am vegan and nut-allergic - what should I use instead of the whole milk in the Sourdough Brioche Loaf?",
        required_tools=frozenset({"search_recipes", "substitute_ingredient", "get_allergen_profile"}),
        optimal_tool_calls=4,
        expect=lambda answer, stop: _contains_all(answer, "tree-nuts") and _contains_any(answer, "no verified substitute", "no substitute"),
        notes=(
            "ALTERNATE PATH ACCEPTED: required_tools is a set, not a sequence - the request can "
            "legitimately resolve 'vegan' before or after checking the allergen profile depending "
            "on phrasing (see T06), and the specific diet value used for each substitute_ingredient "
            "call varies (vegan then nut-free) without that making the trajectory wrong."
        ),
    ),
    TrajectoryCase(
        id="T06",
        question="I need the Sourdough Brioche Loaf dairy-free, but I have a nut allergy - what do I use instead of the whole milk?",
        required_tools=frozenset({"search_recipes", "substitute_ingredient", "get_allergen_profile"}),
        optimal_tool_calls=4,
        expect=lambda answer, stop: _contains_all(answer, "tree-nuts") and _contains_any(answer, "no verified substitute", "no substitute"),
        notes="same cascade as T05, dairy-free phrasing instead of vegan - the other legitimate path.",
    ),
    TrajectoryCase(
        id="T07",
        question="I'm vegan - what should I use instead of the granulated sugar in the Sourdough Brioche Loaf?",
        required_tools=frozenset({"search_recipes", "substitute_ingredient"}),
        optimal_tool_calls=2,
        expect=lambda answer, stop: _contains_any(answer, "granulated sugar"),
        notes=(
            "THE right-answer-wrong-path case (deliverable 3): 'granulated sugar' has no entry in "
            "app/agent/intent.py's fixed ingredient-alias table, so detect_target_ingredient() "
            "returns None and the agent skips substitute_ingredient entirely, falling back to "
            "raw retrieved chunk text - which happens to already contain the words 'granulated "
            "sugar', passing this lenient outcome check while never having actually attempted "
            "(let alone verified) a substitution. A stricter outcome check would have caught it; "
            "this one doesn't, which is exactly Week 8's point about trusting outcome evals alone."
        ),
    ),
    TrajectoryCase(
        id="T08",
        question="I'm vegan - what should I use instead of the whole milk in the Sourdough Brioche Loaf?",
        required_tools=frozenset({"search_recipes", "substitute_ingredient"}),
        valid_tools=frozenset({"search_recipes", "substitute_ingredient", "get_allergen_profile"}),
        optimal_tool_calls=2,
        expect=lambda answer, stop: _contains_any(answer, "oat milk", "almond milk"),
        notes="control: no allergy concern stated, so the post-substitution allergen check (get_allergen_profile) is UNNECESSARY here - step_efficiency should flag it.",
    ),
    TrajectoryCase(
        id="T09",
        question="What's a nut-free substitute for the walnuts in the Cinnamon Raisin Walnut Sourdough?",
        required_tools=frozenset({"search_recipes", "substitute_ingredient"}),
        valid_tools=frozenset({"search_recipes", "substitute_ingredient", "get_allergen_profile"}),
        optimal_tool_calls=2,
        expect=lambda answer, stop: _contains_any(answer, "sunflower seeds"),
    ),
    TrajectoryCase(
        id="T10",
        question="What's the recipe for a Chocolate Babka?",
        required_tools=frozenset({"search_recipes"}),
        forbidden_tools=frozenset({"substitute_ingredient", "get_allergen_profile"}),
        optimal_tool_calls=1,
        expect_answered=False,
        expect=lambda answer, stop: _refused(answer, stop),
        notes="not in corpus - correct trajectory outcome is a refusal, never goal_completed.",
    ),
]

CASES_BY_ID = {case.id: case for case in CASES}
assert len(CASES) == 10, f"expected exactly 10 trajectory cases, got {len(CASES)}"
