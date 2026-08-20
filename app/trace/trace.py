"""
FourLevelTrace: aggregates the four trace levels and supports replay + compare.

    L1 System   -> ExecutionTrace span tree (existing)
    L2 Data     -> DataTraceEntry list (input/output + hashes)
    L3 Decision -> CoTStep list (structured chain-of-thought)
    L4 Audit    -> AuditTrail (append-only, hash-chained)

Replay reconstructs the full detection flow from recorded intermediate states.
Compare diff two traces' decision chains (e.g. same model -> different choices).
"""

import os
import json
from typing import Any, Optional

from app.core.execution_trace import ExecutionTrace
from app.trace.models import CoTStep, DataTraceEntry, AuditEntry, stable_hash
from app.trace.audit import AuditTrail


class FourLevelTrace:
    """Four-level trace for one detection run."""

    def __init__(self, trace_id: str, system: Optional[ExecutionTrace] = None):
        self.trace_id = trace_id
        self.system = system or ExecutionTrace(trace_id=trace_id)  # L1
        self.data_entries: list[DataTraceEntry] = []  # L2
        self.cot_steps: list[CoTStep] = []            # L3
        self.audit = AuditTrail()                     # L4

    # ── Record ─────────────────────────────────────────────────────

    def record_cot(self, cot: CoTStep) -> CoTStep:
        self.cot_steps.append(cot)
        return cot

    def record_data(
        self,
        step_id: str,
        tool_name: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
    ) -> DataTraceEntry:
        """Record a data-flow entry with input/output content hashes."""
        entry = DataTraceEntry(
            entry_id=stable_hash(
                {"trace_id": self.trace_id, "step_id": step_id, "tool_name": tool_name}
            )[:16],
            trace_id=self.trace_id,
            step_id=step_id,
            tool_name=tool_name,
            input_hash=stable_hash(input_data),
            output_hash=stable_hash(output_data),
            input=input_data,
            output=output_data,
        )
        self.data_entries.append(entry)
        return entry

    def record_audit(
        self,
        event_type: str,
        message: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuditEntry:
        return self.audit.append(self.trace_id, event_type, message, metadata)

    # ── Replay ─────────────────────────────────────────────────────

    def replay(self) -> dict[str, Any]:
        """Reconstruct the full detection flow from recorded intermediate states."""
        return {
            "trace_id": self.trace_id,
            "status": self.system.status.value,
            "decisions": [c.model_dump() for c in self.cot_steps],
            "data_flow": [d.model_dump() for d in self.data_entries],
            "audit": self.audit.snapshot(),
            "audit_verified": self.audit.verify(),
            "system_spans": [s.model_dump() for s in self.system.spans],
        }

    # ── Compare ────────────────────────────────────────────────────

    def compare(self, other: "FourLevelTrace") -> dict[str, Any]:
        """Diff two traces' decision chains to surface strategy differences."""
        self_tools = [c.tool_name for c in self.cot_steps]
        other_tools = [c.tool_name for c in other.cot_steps]

        differences = []
        for i in range(max(len(self_tools), len(other_tools))):
            a = self_tools[i] if i < len(self_tools) else None
            b = other_tools[i] if i < len(other_tools) else None
            if a != b:
                differences.append({"index": i, "trace_a": a, "trace_b": b})

        return {
            "trace_a": self.trace_id,
            "trace_b": other.trace_id,
            "tool_sequence_a": self_tools,
            "tool_sequence_b": other_tools,
            "same_sequence": self_tools == other_tools,
            "differences": differences,
        }

    # ── Persistence ────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "cot_steps": [c.model_dump() for c in self.cot_steps],
            "data_entries": [d.model_dump() for d in self.data_entries],
            "audit": self.audit.snapshot(),
        }

    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: str) -> "FourLevelTrace":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        trace = cls(trace_id=data["trace_id"])
        trace.cot_steps = [CoTStep(**c) for c in data.get("cot_steps", [])]
        trace.data_entries = [DataTraceEntry(**d) for d in data.get("data_entries", [])]
        for a in data.get("audit", []):
            entry = AuditEntry(**a)
            trace.audit._entries.append(entry)
            trace.audit._last_hash = entry.hash
        return trace
