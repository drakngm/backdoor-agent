"""
Trace models for the four-level trace system (L1 system / L2 data / L3 decision /
L4 audit) with content-addressed storage.

Every record can be identified by a stable content hash (sha256), enabling
tamper-evident storage (like git objects).
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


def stable_hash(obj: Any) -> str:
    """Deterministic sha256 hash of a JSON-serializable object."""
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Alternative(BaseModel):
    """A considered-but-rejected alternative in a decision."""

    tool: str
    reason_rejected: str = ""


class CoTStep(BaseModel):
    """
    L3 Decision Trace: structured chain-of-thought for one agent decision.

    Matches the forced system-prompt format:
        {step, observation, reasoning, decision, alternatives_considered}
    """

    step_id: str
    step: str = "select_tool"          # select_tool | finalize | ...
    observation: str = ""
    reasoning: str = ""
    decision: str = ""
    alternatives_considered: list[Alternative] = Field(default_factory=list)
    tool_name: Optional[str] = None
    confidence: float = 0.0
    timestamp: str = Field(default_factory=_now)

    def content_hash(self) -> str:
        return stable_hash(self.model_dump())


class DataTraceEntry(BaseModel):
    """L2 Data Trace: data flow (input -> output) with content hashes."""

    entry_id: str
    trace_id: str
    step_id: str
    tool_name: str
    input_hash: str
    output_hash: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=_now)

    def content_hash(self) -> str:
        return stable_hash(self.model_dump())


class AuditEntry(BaseModel):
    """L4 Audit Trail: append-only, hash-chained (immutable) record."""

    entry_id: str
    trace_id: str
    event_type: str
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=_now)
    prev_hash: str = ""   # "" for the genesis entry
    hash: str = ""        # content hash that includes prev_hash

    def compute_hash(self) -> str:
        payload = {
            "entry_id": self.entry_id,
            "trace_id": self.trace_id,
            "event_type": self.event_type,
            "message": self.message,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
        }
        return stable_hash(payload)
