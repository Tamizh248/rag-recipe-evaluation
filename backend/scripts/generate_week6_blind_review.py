"""Generate the material for BLIND hand-labeling (Week 6, requirement 3) -
runs every substitution case for real and writes what a reviewer needs to
label PASS/FAIL, with NO judge verdict anywhere in this file. Run this
BEFORE ever running scripts/run_week6_judge.py, and label+commit
evaluation/week6/labels_25.json before that script runs too - the blind
protocol is graded on provable ordering (commit hashes/timestamps), not on
the numbers alone.

Usage:
    python scripts/generate_week6_blind_review.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.cases import CASES
from evals.harness import run_substitution_case

EVAL_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "week6"
BLIND_REVIEW_PATH = EVAL_DIR / "blind_review.json"
LABELS_TEMPLATE_PATH = EVAL_DIR / "labels_25.json"


def main() -> None:
    review_items = []
    labels_template = []

    for case in CASES:
        run = run_substitution_case(case)
        r = run.response
        item = {
            "id": case.id,
            "recipe_id": case.recipe_id,
            "ingredient": case.ingredient,
            "diet": case.diet,
            "refused": r.refused,
            "answer": r.answer,
            "substitute_ingredient": r.substitute_ingredient,
            "allergens": r.allergens,
        }
        review_items.append(item)
        labels_template.append({"id": case.id, "label_pass": None, "reviewer_note": ""})

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    BLIND_REVIEW_PATH.write_text(json.dumps(review_items, indent=2), encoding="utf-8")
    if not LABELS_TEMPLATE_PATH.exists():
        LABELS_TEMPLATE_PATH.write_text(json.dumps(labels_template, indent=2), encoding="utf-8")
        print(f"Wrote blank label template to {LABELS_TEMPLATE_PATH} - fill in label_pass (true/false) for each id,")
        print("by reading blind_review.json yourself, WITHOUT running run_week6_judge.py first. Commit it once done.")
    else:
        print(f"{LABELS_TEMPLATE_PATH} already exists - not overwriting your labels.")

    print(f"Wrote {len(review_items)} cases to review to {BLIND_REVIEW_PATH}")


if __name__ == "__main__":
    main()
