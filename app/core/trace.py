"""
Trace-ID generation and management.

Every request (Agent or Workflow) gets a unique trace_id
that is propagated through all tool calls, logs, and spans.
"""

import uuid
from datetime import datetime
from typing import Optional


def generate_trace_id(prefix: str = "trc") -> str:
    """
    Generate a unique trace ID.

    Format: {prefix}-{short_uuid}
    Example: trc-a1b2c3d4e5f6
    """
    short_id = uuid.uuid4().hex[:12]
    return f"{prefix}-{short_id}"


def generate_span_id() -> str:
    """Generate a unique span ID (used within a trace)."""
    return uuid.uuid4().hex[:12]


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return f"ses-{uuid.uuid4().hex[:8]}"