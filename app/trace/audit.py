"""
L4 — Audit Trail: append-only, immutable, hash-chained log.

Each entry's hash depends on the previous entry's hash, so any tampering (edit,
delete, reorder) breaks the chain and is detectable via `verify()`.
"""

from typing import Any, Optional

from app.trace.models import AuditEntry


class AuditTrail:
    """Append-only immutable audit log with hash chaining."""

    def __init__(self):
        self._entries: list[AuditEntry] = []
        self._last_hash: str = ""  # genesis
        self._counter: int = 0

    def append(
        self,
        trace_id: str,
        event_type: str,
        message: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuditEntry:
        """Append an audit record and return it."""
        self._counter += 1
        entry = AuditEntry(
            entry_id=f"audit-{trace_id}-{self._counter:04d}",
            trace_id=trace_id,
            event_type=event_type,
            message=message,
            metadata=metadata or {},
            prev_hash=self._last_hash,
        )
        entry.hash = entry.compute_hash()
        self._entries.append(entry)
        self._last_hash = entry.hash
        return entry

    def entries(self) -> list[AuditEntry]:
        return list(self._entries)

    def verify(self) -> bool:
        """Verify hash-chain integrity (no tampering / reordering / deletion)."""
        prev = ""
        for entry in self._entries:
            if entry.prev_hash != prev:
                return False
            if entry.compute_hash() != entry.hash:
                return False
            prev = entry.hash
        return True

    def snapshot(self) -> list[dict[str, Any]]:
        return [e.model_dump() for e in self._entries]
