"""Draw a seeded random sample of N trace_ids from evaluation/week5/traces.jsonl
(Week 5, requirement 2). Prints and saves the seed plus the selected ids so
the sample is provable, not just claimed.

Usage:
    python scripts/sample_traces.py --seed 42 --n 20
"""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.tracing import TRACES_PATH, read_traces

OUTPUT_PATH = TRACES_PATH.parent / "sample.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n", type=int, default=20)
    args = parser.parse_args()

    traces = read_traces()
    if len(traces) < args.n:
        raise SystemExit(f"Only {len(traces)} traces exist; need at least {args.n}. Run generate_traces.py first.")

    trace_ids = [t["trace_id"] for t in traces]
    rng = random.Random(args.seed)
    sampled = rng.sample(trace_ids, args.n)

    result = {"seed": args.seed, "population_size": len(trace_ids), "n": args.n, "sampled_trace_ids": sampled}
    OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"Seed: {args.seed}")
    print(f"Population size (total traces): {len(trace_ids)}")
    print(f"Sampled {args.n} trace_ids:")
    for trace_id in sampled:
        print(f"  {trace_id}")
    print(f"\nWritten to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
