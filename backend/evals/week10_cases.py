"""The SAME 10 Week-6 eval cases, reused verbatim for Week 10's race - no
new cases written, per the task's explicit requirement ("do not write new
cases - a changed eval set voids the comparison").

Week 6 (evals/cases.py) has 26 substitution cases + 2 regression cases,
not literally 10 - this template's generic "same 10 Week-6 cases" phrasing
assumes a 10-case Week 6, which this project's didn't have. These 10 IDs
are a fixed, DISCLOSED subset of the real Week 6 set (not new cases),
chosen to cover: multiple successful substitutions including one where the
substitute introduces a NEW allergen (S03 - the case the failure injection
targets, since that's exactly where an allergen-worker failure matters)
and one where an allergen is correctly dropped (S08), plus a spread of
refusal reasons (ingredient not in recipe, no substitute on file, invalid
diet, recipe not found).
"""

from evals.cases import CASES_BY_ID, SubstitutionCase

WEEK10_CASE_IDS = ["S01", "S03", "S07", "S08", "S09", "S13", "S15", "S21", "S25", "S26"]
WEEK10_CASES: list[SubstitutionCase] = [CASES_BY_ID[cid] for cid in WEEK10_CASE_IDS]

assert len(WEEK10_CASES) == 10

# The case the injected worker failure (Week 10, requirement 4) targets -
# S03 is the one case in this set where the allergen worker's finding
# (oat/almond milk introduces tree-nuts) actually changes what a correct
# answer must say, so a failed allergen worker here is the meaningful test
# of whether the orchestrator degrades honestly or fabricates a claim.
FAILURE_INJECTION_CASE_ID = "S03"
