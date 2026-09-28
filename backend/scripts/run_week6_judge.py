"""Run the LLM judge over all 26 substitution cases and compute agreement
against your OWN blind hand-labels (Week 6, requirements 3-4).

Refuses to run if evaluation/week6/labels_25.json still has any
label_pass == null, so it cannot be run before labeling is actually done -
but it CANNOT verify the labels predate this script's first run; that
proof is the labels file's commit hash/timestamp, which you control by
committing labels_25.json (and prediction.txt) before running this.

Usage:
    python scripts/run_week6_judge.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.cases import CASES_BY_ID
from evals.harness import run_substitution_case
from evals.judge import judge_case

EVAL_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "week6"
LABELS_PATH = EVAL_DIR / "labels_25.json"
OUTPUT_PATH = EVAL_DIR / "judge_v1_results.json"


def main() -> None:
    if not LABELS_PATH.exists():
        raise SystemExit(f"{LABELS_PATH} does not exist - run generate_week6_blind_review.py and label it first.")

    labels = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
    unlabeled = [entry["id"] for entry in labels if entry["label_pass"] is None]
    if unlabeled:
        raise SystemExit(f"{len(unlabeled)} case(s) still unlabeled in {LABELS_PATH}: {unlabeled}")

    results = []
    agreements = 0
    for entry in labels:
        case = CASES_BY_ID[entry["id"]]
        run = run_substitution_case(case)
        judge_pass, verdict = judge_case(case.recipe_id, case.ingredient, case.diet, run.response)
        agree = judge_pass == entry["label_pass"]
        agreements += agree
        results.append(
            {
                "id": case.id,
                "human_label_pass": entry["label_pass"],
                "judge_pass": judge_pass,
                "judge_verdict": verdict,
                "agree": agree,
            }
        )
        marker = "AGREE" if agree else "DISAGREE"
        print(f"[{case.id}] {marker}  human={entry['label_pass']}  judge={judge_pass}  ({verdict})")

    agreement_pct = agreements / len(labels)
    print(f"\nAgreement: {agreements}/{len(labels)} ({agreement_pct:.1%})")

    OUTPUT_PATH.write_text(
        json.dumps({"agreement": agreement_pct, "n": len(labels), "results": results}, indent=2), encoding="utf-8"
    )
    print(f"Written to {OUTPUT_PATH}")
    disagreements = [r for r in results if not r["agree"]]
    if disagreements:
        print(f"\n{len(disagreements)} disagreement(s) - read these for judge_v2.txt's few-shot examples:")
        for d in disagreements:
            print(f"  [{d['id']}] human={d['human_label_pass']} judge={d['judge_pass']}: {d['judge_verdict']}")


if __name__ == "__main__":
    main()
