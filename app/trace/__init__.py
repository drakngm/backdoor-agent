"""
Four-level Trace system: L1 system / L2 data / L3 decision (CoT) / L4 audit.

Content-addressed records (sha256), hash-chained audit trail, replay, and
cross-trace comparison for interpretability & auditability.
"""

from app.trace.models import (
    Alternative,
    CoTStep,
    DataTraceEntry,
    AuditEntry,
    stable_hash,
)
from app.trace.audit import AuditTrail
from app.trace.trace import FourLevelTrace
from app.trace.hooks import TraceRecorder

__all__ = [
    "Alternative",
    "CoTStep",
    "DataTraceEntry",
    "AuditEntry",
    "stable_hash",
    "AuditTrail",
    "FourLevelTrace",
    "TraceRecorder",
]
