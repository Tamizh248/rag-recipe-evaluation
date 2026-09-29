"""Shared hand-off log: every message that crosses an agent/worker boundary
in the orchestrator (Week 10, requirement 3) gets one entry here, with its
real token count (app.core.tokens.count_tokens on the actual JSON payload -
never estimated). The single agent (single_agent.py) never writes to this
log at all - it has no hand-offs, by construction, which is exactly the
comparison this week is measuring.
"""

import json
from dataclasses import dataclass, field

from app.core.tokens import count_tokens


@dataclass
class HandoffEntry:
    case_id: str
    from_: str
    to: str
    payload_tokens: int
    note: str = ""


@dataclass
class HandoffLog:
    entries: list[HandoffEntry] = field(default_factory=list)

    def record(self, case_id: str, from_: str, to: str, payload: object, note: str = "") -> int:
        tokens = count_tokens(json.dumps(payload, default=str))
        self.entries.append(HandoffEntry(case_id=case_id, from_=from_, to=to, payload_tokens=tokens, note=note))
        return tokens

    def total_tokens(self) -> int:
        return sum(e.payload_tokens for e in self.entries)

    def tokens_for_case(self, case_id: str) -> int:
        return sum(e.payload_tokens for e in self.entries if e.case_id == case_id)

    def totals_by_name(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for entry in self.entries:
            key = f"{entry.from_} -> {entry.to}"
            totals[key] = totals.get(key, 0) + entry.payload_tokens
        return totals

    def to_lines(self) -> list[str]:
        return [
            f"[{e.case_id}] {e.from_} -> {e.to}: {e.payload_tokens} tokens" + (f"  ({e.note})" if e.note else "")
            for e in self.entries
        ]
