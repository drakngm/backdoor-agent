"""
Structured Execution Trace: Span Tree for Agent & Workflow observability.

Every request generates an ExecutionTrace containing TraceSpans.
Supports both linear chains (Agent Mode) and nested trees (Workflow Mode).

Output formats:
- JSON serialization (for API responses)
- Mermaid flowchart (for visualization)
- Flamegraph data (for performance analysis)
- Critical path (longest duration chain)
"""

import asyncio
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────── Enums ────────────────────────────────

class SpanType(str, Enum):
    """Type of execution span."""
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    WORKFLOW_STEP = "workflow_step"
    AGGREGATION = "aggregation"
    HOOK = "hook"


class SpanStatus(str, Enum):
    """Status of a span during its lifecycle."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class TraceStatus(str, Enum):
    """Overall trace status (derived from span statuses)."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"


class EventType(str, Enum):
    """Milestone events within a trace (lightweight markers)."""
    ENTRY_START = "entry_start"
    ENTRY_END = "entry_end"
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    HOOK_FIRED = "hook_fired"
    ERROR = "error"


# ──────────────────────────────── Models ────────────────────────────────

class TraceEvent(BaseModel):
    """Lightweight timestamped event attached to a trace or span."""
    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceSpan(BaseModel):
    """A single unit of execution within a trace."""

    span_id: str
    parent_span_id: Optional[str] = None
    trace_id: str
    span_type: SpanType
    name: str
    step_index: int = 0
    input: dict[str, Any] = Field(default_factory=dict)
    output: Optional[dict[str, Any]] = None
    status: SpanStatus = SpanStatus.PENDING
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    children: list["TraceSpan"] = Field(default_factory=list)

    def start(self) -> "TraceSpan":
        """Mark the span as running with a start timestamp."""
        self.status = SpanStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)
        return self

    def finish(
        self,
        output: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> "TraceSpan":
        """Mark the span as finished, compute duration."""
        self.finished_at = datetime.now(timezone.utc)
        if self.started_at:
            self.duration_ms = (self.finished_at - self.started_at).total_seconds() * 1000

        if error:
            self.status = SpanStatus.FAILED
            self.error = error
        else:
            self.status = SpanStatus.SUCCESS

        self.output = output
        return self

    def fail(self, error: str) -> "TraceSpan":
        """Convenience method to immediately fail a span."""
        self.status = SpanStatus.FAILED
        self.error = error
        self.finished_at = datetime.now(timezone.utc)
        if self.started_at:
            self.duration_ms = (self.finished_at - self.started_at).total_seconds() * 1000
        return self


# ──────────────────────────────── Main Trace ────────────────────────────────

class ExecutionTrace(BaseModel):
    """
    Complete execution trace for one request.

    Builder Methods (called by Agent Loop / Workflow Executor):
        trace.create_span(...)
        span.start()
        span.finish(output=...)

    Query Methods (for observability / debugging):
        trace.get_linear_chain()
        trace.get_span_tree()
        trace.get_critical_path()
        trace.to_mermaid()
        trace.to_flamegraph_data()
    """

    trace_id: str
    spans: list[TraceSpan] = Field(default_factory=list)
    events: list[TraceEvent] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    total_duration_ms: Optional[float] = None
    status: TraceStatus = TraceStatus.PENDING
    metadata: dict[str, Any] = Field(default_factory=dict)

    _step_counter: int = 0

    # ── Builder API ─────────────────────────────────────────────────────

    def create_span(
        self,
        name: str,
        span_type: SpanType,
        parent_span_id: Optional[str] = None,
        input_data: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> TraceSpan:
        """
        Create and register a new span. Returns the span so the caller can
        call .start() / .finish() on it.
        """
        from app.core.trace import generate_span_id  # local import to avoid circular

        self._step_counter += 1

        span = TraceSpan(
            span_id=generate_span_id(),
            parent_span_id=parent_span_id,
            trace_id=self.trace_id,
            span_type=span_type,
            name=name,
            step_index=self._step_counter,
            input=input_data or {},
            metadata=metadata or {},
        )

        # Attach to tree: if has parent, nest under parent.children
        if parent_span_id:
            parent = self._find_span(parent_span_id)
            if parent:
                parent.children.append(span)

        self.spans.append(span)

        if self.status == TraceStatus.PENDING:
            self.status = TraceStatus.RUNNING

        return span

    def add_event(
        self,
        event_type: EventType,
        message: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> TraceEvent:
        """Attach a lightweight event to the trace timeline."""
        event = TraceEvent(
            event_type=event_type,
            message=message,
            metadata=metadata or {},
        )
        self.events.append(event)
        return event

    def finalize(self) -> "ExecutionTrace":
        """Mark trace as finished and compute total duration & overall status."""
        self.end_time = datetime.now(timezone.utc)
        self.total_duration_ms = (
            self.end_time - self.start_time
        ).total_seconds() * 1000

        # Derive overall status from spans
        statuses = [s.status for s in self.spans]
        if not statuses:
            self.status = TraceStatus.SUCCESS
        elif all(s == SpanStatus.SUCCESS for s in statuses):
            self.status = TraceStatus.SUCCESS
        elif any(s == SpanStatus.FAILED for s in statuses) and any(
            s == SpanStatus.SUCCESS for s in statuses
        ):
            self.status = TraceStatus.PARTIAL_FAILURE
        elif all(s == SpanStatus.FAILED for s in statuses):
            self.status = TraceStatus.FAILED
        else:
            self.status = TraceStatus.PARTIAL_FAILURE

        return self

    # ── Query API ───────────────────────────────────────────────────────

    def get_linear_chain(self) -> list[TraceSpan]:
        """Return spans sorted by step_index (Agent Mode linear view)."""
        return sorted(self.spans, key=lambda s: s.step_index)

    def get_span_tree(self) -> list[dict[str, Any]]:
        """Return root-level spans as nested dicts (Workflow Mode tree view)."""
        roots = [s for s in self.spans if s.parent_span_id is None]
        return [self._span_to_tree(s) for s in roots]

    def get_critical_path(self) -> list[dict[str, Any]]:
        """
        Find the longest-duration chain of spans.
        Uses a greedy DFS approach: for each leaf, walk up to root summing durations.
        """
        if not self.spans:
            return []

        span_map = {s.span_id: s for s in self.spans}

        # Start from leaf spans (spans with no children in self.spans)
        leaf_ids = {s.span_id for s in self.spans} - {
            s.parent_span_id for s in self.spans if s.parent_span_id
        }

        best_path: list[TraceSpan] = []
        best_duration = 0.0

        for leaf_id in leaf_ids:
            path = []
            current_id = leaf_id
            total = 0.0
            visited = set()

            while current_id and current_id not in visited:
                span = span_map.get(current_id)
                if not span:
                    break
                visited.add(current_id)
                path.append(span)
                total += span.duration_ms or 0
                current_id = span.parent_span_id

            if total > best_duration:
                best_duration = total
                best_path = list(reversed(path))

        return [
            {
                "span_id": s.span_id,
                "name": s.name,
                "span_type": s.span_type.value,
                "duration_ms": s.duration_ms,
                "status": s.status.value,
            }
            for s in best_path
        ]

    def to_mermaid(self, direction: str = "LR") -> str:
        """
        Export the span tree as a Mermaid flowchart string.

        Args:
            direction: "LR" (left-right) or "TD" (top-down)
        """
        lines = [f"flowchart {direction}"]
        span_ids = {s.span_id for s in self.spans}

        for span in self.spans:
            label = f"{span.name}<br/>{span.duration_ms:.0f}ms"
            status_char = {"success": "✅", "failed": "❌", "running": "⏳", "pending": "⬜", "timeout": "⏰"}.get(
                span.status.value, "⬜"
            )
            lines.append(f'    {span.span_id}["{status_char} {label}"]')

            if span.parent_span_id and span.parent_span_id in span_ids:
                lines.append(f"    {span.parent_span_id} --> {span.span_id}")

        return "\n".join(lines)

    def to_flamegraph_data(self) -> list[dict[str, Any]]:
        """Export data suitable for flamegraph visualization."""
        return [
            {
                "name": s.name,
                "value": int(s.duration_ms or 0),
                "children": self._flamegraph_children(s),
            }
            for s in self.spans
            if s.parent_span_id is None
        ]

    # ── Helpers ─────────────────────────────────────────────────────────

    def _find_span(self, span_id: str) -> Optional[TraceSpan]:
        """Find a span by ID (linear scan — OK for typical trace sizes < 100 spans)."""
        for s in self.spans:
            if s.span_id == span_id:
                return s
        return None

    def _span_to_tree(self, span: TraceSpan) -> dict[str, Any]:
        """Recursively build a nested dict for tree visualization."""
        return {
            "span_id": span.span_id,
            "name": span.name,
            "span_type": span.span_type.value,
            "step_index": span.step_index,
            "status": span.status.value,
            "duration_ms": span.duration_ms,
            "error": span.error,
            "children": [self._span_to_tree(c) for c in span.children],
        }

    def _flamegraph_children(self, span: TraceSpan) -> list[dict[str, Any]]:
        """Recursively build flamegraph child nodes."""
        return [
            {
                "name": c.name,
                "value": int(c.duration_ms or 0),
                "children": self._flamegraph_children(c),
            }
            for c in span.children
        ]

    # ── Serialization helpers ────────────────────────────────────────────

    def model_dump_json_trace(self, **kwargs) -> str:
        """JSON dump with sensible defaults for API responses."""
        return self.model_dump_json(indent=2, exclude_none=True, **kwargs)


# ──────────────────────────────── Async Context Manager ──────────────────

class TraceSpanContext:
    """
    Async context manager for a single span within a trace.

    Usage:
        async with TraceSpanContext(trace, "strip_detect", SpanType.TOOL_CALL) as span:
            result = await do_detection()
            span.output = result
    """

    def __init__(
        self,
        trace: ExecutionTrace,
        name: str,
        span_type: SpanType,
        parent_span_id: Optional[str] = None,
        input_data: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        self.trace = trace
        self.name = name
        self.span_type = span_type
        self.parent_span_id = parent_span_id
        self.input_data = input_data
        self.metadata = metadata
        self.span: Optional[TraceSpan] = None

    async def __aenter__(self) -> TraceSpan:
        self.span = self.trace.create_span(
            name=self.name,
            span_type=self.span_type,
            parent_span_id=self.parent_span_id,
            input_data=self.input_data,
            metadata=self.metadata,
        )
        self.span.start()
        return self.span

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self.span is None:
            return False

        if exc_type is not None:
            self.span.fail(error=str(exc_val))
        else:
            # Caller should have set span.output; if not, finish with empty
            if self.span.status == SpanStatus.RUNNING:
                self.span.finish(output=self.span.output or {})

        return False  # Don't suppress exceptions