"""Replay ONE trace purely from its own stored fields (Week 5, requirement 1) -
no vector store or embedding model call, only what's already in the trace
record: prompt_version, retrieved chunk_ids/scores/text, model+params, and
the exact prompt that was sent.

Replay logic:
  - Recompute the pre-LLM lexical-support refusal check from the trace's
    OWN stored retrieved chunk text (never re-retrieved).
  - If the LLM was called, re-invoke the SAME provider+model with the
    trace's OWN stored prompt, then re-run the same post-LLM
    parse/citation-validation/refusal-policy logic the live app uses.
  - Print original vs replayed side by side.

Usage:
    python scripts/replay_trace.py --trace-id <trace_id>
    python scripts/replay_trace.py --random --seed 42   # replay trace #1 of the seeded sample
"""
import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.core.tracing import TRACES_PATH, read_traces
from app.generation.grounding import enforce_refusal_policy, has_lexical_support, parse_llm_response
from app.generation.llm import get_llm_provider


@dataclass
class _ReplayChunk:
    """The minimal shape has_lexical_support() needs (.text), built only
    from what the trace itself stored - not re-fetched from the vector store."""
    text: str


def find_trace(trace_id: str) -> dict:
    for trace in read_traces():
        if trace["trace_id"] == trace_id:
            return trace
    raise SystemExit(f"No trace found with trace_id={trace_id!r} in {TRACES_PATH}")


def replay(trace: dict) -> dict:
    settings = get_settings()
    replay_chunks = [_ReplayChunk(text=r["text"]) for r in trace["retrieved"]]
    retrieved_ids = {r["chunk_id"] for r in trace["retrieved"]}

    replayed_refused_pre_llm = not has_lexical_support(trace["question"], replay_chunks)

    if trace["refused_pre_llm"]:
        return {
            "refused_pre_llm_matches": replayed_refused_pre_llm == trace["refused_pre_llm"],
            "replayed_refused_pre_llm": replayed_refused_pre_llm,
            "replayed_answer": "I cannot answer this from the provided recipes.",
            "replayed_raw_output": None,
            "llm_replayed": False,
        }

    if not trace["llm_called"] or not trace["prompt"]:
        return {"error": "Trace has no stored prompt to replay from - nothing further to reconstruct."}

    provider = get_llm_provider(trace["model_provider"], settings.llm_api_key, trace["model_name"])
    replayed_raw_output = provider.generate(trace["prompt"])
    parsed = parse_llm_response(replayed_raw_output)

    if parsed is None:
        return {
            "replayed_refused_pre_llm": False,
            "replayed_raw_output": replayed_raw_output,
            "replayed_answer": "I cannot answer this from the provided recipes. (unparseable LLM output)",
            "llm_replayed": True,
        }

    final_answer = enforce_refusal_policy(parsed, retrieved_ids)
    return {
        "replayed_refused_pre_llm": False,
        "replayed_raw_output": replayed_raw_output,
        "replayed_answer": final_answer.answer,
        "replayed_answerable": final_answer.answerable,
        "replayed_citations": [c.chunk_id for c in final_answer.citations],
        "llm_replayed": True,
        "raw_output_matches_original": replayed_raw_output == trace["raw_llm_output"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-id", type=str, default=None)
    parser.add_argument("--random", action="store_true", help="pick the first trace_id from the seeded Week-5 sample")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.trace_id:
        trace_id = args.trace_id
    elif args.random:
        sample_path = TRACES_PATH.parent / "sample.json"
        sample = json.loads(sample_path.read_text(encoding="utf-8"))
        if sample["seed"] != args.seed:
            raise SystemExit(f"sample.json was generated with seed={sample['seed']}, not {args.seed}")
        trace_id = sample["sampled_trace_ids"][0]
    else:
        raise SystemExit("Pass --trace-id <id> or --random")

    trace = find_trace(trace_id)
    result = replay(trace)

    print(f"trace_id: {trace_id}")
    print(f"question: {trace['question']}")
    print(f"model: {trace['model_provider']}/{trace['model_name']}  prompt_version: {trace['prompt_version']}")
    print()
    print("=== ORIGINAL ===")
    print(f"refused_pre_llm: {trace['refused_pre_llm']}")
    print(f"answer: {trace['answer']}")
    print(f"citations: {trace['citations']}")
    print(f"raw_llm_output: {trace['raw_llm_output']}")
    print()
    print("=== REPLAYED (from the trace's own stored fields only) ===")
    for key, value in result.items():
        print(f"{key}: {value}")

    output_path = TRACES_PATH.parent / f"replay_{trace_id}.json"
    output_path.write_text(
        json.dumps({"trace_id": trace_id, "original": trace, "replayed": result}, indent=2),
        encoding="utf-8",
    )
    print(f"\nWritten to {output_path}")


if __name__ == "__main__":
    main()
