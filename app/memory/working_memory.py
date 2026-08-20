"""
L1: Working Memory — current reasoning window with tiered compaction.

Lifecycle: single Agent Loop iteration
Capacity: bounded by LLM context window (~8K tokens)
Storage: pure in-memory list[dict]

Context management (adapted from Claude Code s08_context_compact, but without
its LLM-based `compact_history` step):

    tool_result_budget   -> append_observation truncates oversized results,
                            keeping the full copy + a preview reference
    micro/snip compaction-> role-aware eviction preserves system messages and
                            the recent tail, archiving the middle to `_overflow`
    deterministic summary -> `compact()` replaces evicted history with a
                            rule-based summary (no LLM), then keeps a recent tail

The evicted messages are preserved in `_overflow` so nothing is silently lost;
they can be consolidated into SessionMemory / ProjectMemory by the caller.
"""

from typing import Any, Optional

from app.core.config import get_config
from app.memory.base import BaseMemory

DEFAULT_MAX_OBSERVATION_CHARS = 2000


def build_deterministic_summary(messages: list[dict[str, Any]]) -> str:
    """
    Build a rule-based (non-LLM) summary of evicted messages.

    Extracts structured facts from observation metadata: tool names called and
    their risk/confidence, so the LLM retains what matters without full history.
    """
    tool_calls: list[str] = []
    findings_by_tool: dict[str, str] = {}
    for message in messages:
        meta = message.get("metadata") or {}
        if meta.get("type") != "observation":
            continue
        tool = meta.get("tool")
        if tool and tool not in tool_calls:
            tool_calls.append(tool)
        risk = meta.get("risk_level")
        risk_str = getattr(risk, "value", risk)
        if tool and risk_str:
            # keep the latest finding per tool (avoids unbounded growth)
            findings_by_tool[tool] = f"{tool}: risk={risk_str}, conf={meta.get('confidence')}"

    parts = [f"{len(messages)} messages"]
    if tool_calls:
        parts.append(f"tools called: {', '.join(tool_calls)}")
    if findings_by_tool:
        parts.append("findings: " + "; ".join(findings_by_tool.values()))
    return " | ".join(parts)


class WorkingMemory(BaseMemory):
    """
    Working memory holds the messages for the current agent reasoning step.

    Attributes:
        messages: The message list fed to the LLM prompt.
        current_observation: The most recent tool observation.
        max_tokens: Hard limit on estimated token count.
        _overflow: Evicted messages preserved for consolidation/audit.
    """

    def __init__(
        self,
        max_tokens: Optional[int] = None,
        max_observation_chars: Optional[int] = None,
    ):
        self._storage: dict[str, Any] = {}
        self.messages: list[dict[str, Any]] = []
        self.current_observation: Optional[dict[str, Any]] = None
        self.max_tokens = max_tokens or get_config().working_memory_max_tokens
        self.max_observation_chars = max_observation_chars or DEFAULT_MAX_OBSERVATION_CHARS
        self._estimated_tokens: int = 0
        self._overflow: list[dict[str, Any]] = []

    # ── BaseMemory interface ────────────────────────────────────────

    def store(self, key: str, value: Any) -> None:
        self._storage[key] = value

    def retrieve(self, key: str) -> Optional[Any]:
        return self._storage.get(key)

    def clear(self) -> None:
        self.messages.clear()
        self._storage.clear()
        self.current_observation = None
        self._estimated_tokens = 0
        self._overflow.clear()

    def snapshot(self) -> dict[str, Any]:
        return {
            "messages": list(self.messages),
            "current_observation": self.current_observation,
            "estimated_tokens": self._estimated_tokens,
            "max_tokens": self.max_tokens,
            "overflow_count": len(self._overflow),
            "storage": dict(self._storage),
        }

    # ── Message management ──────────────────────────────────────────

    def append(self, role: str, content: str, metadata: Optional[dict] = None) -> None:
        """
        Add a message to the working memory.

        Args:
            role: 'user', 'assistant', 'tool', or 'system'
            content: The message text
            metadata: Optional metadata dict
        """
        msg = {"role": role, "content": content}
        if metadata:
            msg["metadata"] = metadata

        self.messages.append(msg)
        self._estimated_tokens += self._estimate_tokens(content)

    def append_observation(self, observation: dict[str, Any]) -> None:
        """Store the latest tool observation, applying a size budget."""
        self.current_observation = observation

        serialized = str(observation)
        if len(serialized) > self.max_observation_chars:
            # tool_result_budget: keep full copy + preview reference
            key = f"overflow:obs:{len(self._overflow)}"
            self._storage[key] = observation
            serialized = (
                serialized[: self.max_observation_chars]
                + f"... [truncated, full observation at {key}]"
            )

        metadata = {
            "type": "observation",
            "tool": observation.get("tool_name") or observation.get("tool"),
            "success": observation.get("success"),
            "risk_level": observation.get("risk_level"),
            "confidence": observation.get("confidence_score"),
        }
        self.append("tool", serialized, metadata=metadata)

    def prune(self) -> None:
        """Force-prune to max_tokens by evicting oldest non-essential messages."""
        self._prune_if_needed()

    def _prune_if_needed(self) -> None:
        while self._estimated_tokens > self.max_tokens and len(self.messages) > 1:
            if self._evict_one() is None:
                break

    def _evict_one(self) -> Optional[dict[str, Any]]:
        """Evict one message, preferring tool/assistant over user/system."""
        for priority_role in ("tool", "assistant"):
            for i, msg in enumerate(self.messages):
                if msg.get("role") == priority_role:
                    return self._pop(i)
        # fallback: oldest non-system message
        for i, msg in enumerate(self.messages):
            if msg.get("role") != "system":
                return self._pop(i)
        return None

    def _pop(self, index: int) -> dict[str, Any]:
        removed = self.messages.pop(index)
        self._estimated_tokens -= self._estimate_tokens(removed.get("content", ""))
        self._overflow.append(removed)
        return removed

    def compact(self, keep_recent: int = 4) -> Optional[str]:
        """
        Tiered consolidation when over budget (no LLM).

        Preserves system messages + the recent tail, archives the middle into
        `_overflow`, and prepends a deterministic summary message so the LLM
        still sees the essential state. Returns the summary string, or None if
        no compaction was needed.
        """
        if self._estimated_tokens <= self.max_tokens:
            return None

        # summary messages are transient; rebuild from scratch
        non_summary = [
            m for m in self.messages
            if (m.get("metadata") or {}).get("type") != "summary"
        ]

        keep_start = max(0, len(non_summary) - keep_recent)
        head = [m for m in non_summary[:keep_start] if m.get("role") == "system"]
        tail = non_summary[keep_start:]

        evicted = [m for m in non_summary[:keep_start] if m.get("role") != "system"]
        if not evicted:
            return None

        summary = build_deterministic_summary(evicted)
        self._overflow.extend(evicted)

        summary_msg = {
            "role": "system",
            "content": f"[Conversation summary] {summary}",
            "metadata": {"type": "summary"},
        }
        self.messages = [summary_msg, *head, *tail]
        self._estimated_tokens = sum(
            self._estimate_tokens(m.get("content", "")) for m in self.messages
        )
        return summary

    def get_context_for_llm(self) -> list[dict[str, Any]]:
        """Return the current message list suitable for LLM API call."""
        return list(self.messages)

    def get_latest_observation(self) -> Optional[dict[str, Any]]:
        """Return the most recent tool observation."""
        return self.current_observation

    def get_overflow(self) -> list[dict[str, Any]]:
        """Return evicted messages (for consolidation into upper memory layers)."""
        return list(self._overflow)

    # ── Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Approximate token count: CJK ≈ 1 token/char, ASCII ≈ 4 chars/token."""
        if not text:
            return 0
        cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
        other = len(text) - cjk
        return max(1, cjk + (other // 4))
