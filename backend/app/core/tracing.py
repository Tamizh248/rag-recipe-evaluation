"""Trace logging for every /api/chat call (Week 5 - error analysis input).

Each trace is one self-contained JSON line, appended to
evaluation/week5/traces.jsonl: enough by itself (prompt version, retrieved
chunk ids/scores/text, model+params, the exact prompt sent, the raw output)
to replay the request's grounding/citation/refusal decision without touching
the vector store or embedding model again - see backend/scripts/replay_trace.py.
"""

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import BACKEND_DIR

TRACES_PATH = BACKEND_DIR.parent / "evaluation" / "week5" / "traces.jsonl"


@dataclass
class RetrievedChunkTrace:
    chunk_id: str
    score: float
    recipe_id: str
    section: str
    text: str


@dataclass
class TraceRecord:
    trace_id: str
    timestamp: str
    prompt_version: str
    question: str
    strategy: str
    dietary_tag_filters: list[str]
    retrieved: list[RetrievedChunkTrace]
    model_provider: str
    model_name: str
    refused_pre_llm: bool
    llm_called: bool = False
    prompt: str | None = None
    raw_llm_output: str | None = None
    parse_retried: bool = False
    answerable: bool | None = None
    answer: str | None = None
    citations: list[str] = field(default_factory=list)
    final_refused: bool | None = None

    def to_json_line(self) -> str:
        return json.dumps(asdict(self))


def new_trace_id() -> str:
    return uuid.uuid4().hex


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TraceLogger:
    """Append-only JSONL writer, one process-wide lock: uvicorn serves chat
    requests from a threadpool, and interleaved partial writes would corrupt
    the file that sampling/replay later read back."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()

    def log(self, record: TraceRecord) -> None:
        line = record.to_json_line()
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")


_default_logger: TraceLogger | None = None


def get_trace_logger() -> TraceLogger:
    global _default_logger
    if _default_logger is None:
        _default_logger = TraceLogger(TRACES_PATH)
    return _default_logger


def read_traces(path: Path = TRACES_PATH) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
