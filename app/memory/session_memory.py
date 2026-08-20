"""
L2: Session Memory — full task context.

Lifecycle: single /run_agent or /run_workflow call
Capacity: all messages + tool results from the current session
Storage: in-memory dict with optional summary compression

Relationship to L1 (WorkingMemory):
  WorkingMemory is a sliding window into SessionMemory.
  SessionMemory holds the complete history.
"""

from typing import Any, Optional

from app.memory.base import BaseMemory
from app.core.trace import generate_session_id


class SessionMemory(BaseMemory):
    """
    Holds all messages and tool results for the current session.

    When the message list grows too large, a summary is generated
    (via LLM call in production; stub here) to compress history.

    Attributes:
        session_id: Unique session identifier.
        trace_id: Associated trace ID.
        messages: Complete message history.
        tool_results: tool_name → latest output dict.
        summary: Compressed summary of older messages (if any).
    """

    def __init__(self, trace_id: str = ""):
        self._storage: dict[str, Any] = {}
        self.session_id: str = generate_session_id()
        self.trace_id: str = trace_id
        self.messages: list[dict[str, Any]] = []
        self.tool_results: dict[str, dict[str, Any]] = {}
        self.summary: Optional[str] = None

    # ── BaseMemory interface ────────────────────────────────────────

    def store(self, key: str, value: Any) -> None:
        self._storage[key] = value

    def retrieve(self, key: str) -> Optional[Any]:
        return self._storage.get(key)

    def clear(self) -> None:
        self.messages.clear()
        self.tool_results.clear()
        self._storage.clear()
        self.summary = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "messages": list(self.messages),
            "tool_results": dict(self.tool_results),
            "summary": self.summary,
            "storage": dict(self._storage),
        }

    # ── Message management ──────────────────────────────────────────

    def append_message(self, role: str, content: str, metadata: Optional[dict] = None) -> None:
        """Append a message to the full session history."""
        msg = {"role": role, "content": content}
        if metadata:
            msg["metadata"] = metadata
        self.messages.append(msg)

    def store_tool_result(self, tool_name: str, result: dict[str, Any]) -> None:
        """Store the latest result for a given tool."""
        self.tool_results[tool_name] = result

    def get_tool_result(self, tool_name: str) -> Optional[dict[str, Any]]:
        """Retrieve the latest result for a tool."""
        return self.tool_results.get(tool_name)

    def get_recent_messages(self, n: int = 20) -> list[dict[str, Any]]:
        """Return the most recent n messages."""
        return self.messages[-n:] if len(self.messages) > n else list(self.messages)

    # ── Compression ─────────────────────────────────────────────────

    def compress_to_summary(self) -> str:
        """
        Generate a summary of the current session history.

        Rule-based (no LLM): aggregates message count, tools called, and
        per-tool findings (risk/confidence) for consolidation into Project
        Memory and for compacting the working window.
        """
        tool_names = list(self.tool_results.keys())
        findings = []
        for tool in tool_names:
            result = self.tool_results[tool] or {}
            risk = result.get("risk_level")
            risk_str = getattr(risk, "value", risk)
            if risk_str:
                findings.append(f"{tool}: risk={risk_str}")

        self.summary = (
            f"Session {self.session_id}: {len(self.messages)} messages, "
            f"tools called: {tool_names}"
        )
        if findings:
            self.summary += " | findings: " + "; ".join(findings)
        return self.summary