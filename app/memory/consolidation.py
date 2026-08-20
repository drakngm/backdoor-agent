"""
Memory Consolidation: the memory-consolidation (巩固) mechanism.

Simulates the brain's short -> long term memory consolidation:

    L1 (Episodic)  --consolidate-->  L2 (Semantic)  --promote-->  L3 (Procedural)

- consolidate(): extract *important* findings from a finished L1 session into L2
  (key patterns / anomalies, with tool + risk metadata).
- promote(): move *verified* patterns from L2 into L3 (rules / case base).
"""

from typing import Any, Optional

from app.core.logging import get_logger
from app.memory.episodic_memory import EpisodicMemory
from app.memory.semantic_memory import SemanticMemory
from app.memory.procedural_memory import ProceduralMemory

logger = get_logger(__name__)

_IMPORTANT_RISK = {"MEDIUM", "HIGH"}


def _as_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return getattr(value, "value", value)


def _is_important(entry: dict[str, Any]) -> bool:
    """Heuristic: an entry is important if it carries risk or a backdoor signal."""
    meta = entry.get("metadata") or {}
    risk = _as_str(meta.get("risk_level") or entry.get("risk_level"))
    if risk in _IMPORTANT_RISK:
        return True
    data = entry.get("data") or {}
    if data.get("is_backdoor"):
        return True
    return False


class MemoryConsolidation:
    """Moves important findings L1 -> L2 and verified patterns L2 -> L3."""

    def __init__(self, semantic: SemanticMemory, procedural: ProceduralMemory):
        self.semantic = semantic
        self.procedural = procedural

    def consolidate_session(
        self,
        episodic: EpisodicMemory,
        session_id: Optional[str] = None,
    ) -> list[str]:
        """
        Extract important findings from the current L1 session into L2.

        Returns the list of promoted finding contents.
        """
        promoted: list[str] = []
        for entry in episodic.recent():
            if not _is_important(entry):
                continue
            tool = entry.get("tool") or entry.get("tool_name") or "unknown"
            risk = _as_str(entry.get("risk_level"))
            content = self._summarize(entry)
            self.semantic.add_finding(
                content,
                metadata={
                    "source": "episodic",
                    "session_id": session_id or episodic.snapshot().get("session_id"),
                    "tool": tool,
                    "risk_level": risk,
                },
            )
            promoted.append(content)
        logger.info(f"Consolidation L1->L2: promoted {len(promoted)} findings")
        return promoted

    def promote_verified(self, verified_flag: str = "verified") -> list[str]:
        """
        Move verified L2 findings into L3 (as cases).

        A finding is "verified" when its metadata carries the verified flag.
        Returns the list of promoted case contents.
        """
        promoted: list[str] = []
        for entry in self.semantic.list_findings():
            meta = entry.get("metadata") or {}
            if meta.get(verified_flag) is True:
                self.procedural.add_case(entry["content"], metadata={**meta, "source": "semantic"})
                promoted.append(entry["content"])
        logger.info(f"Consolidation L2->L3: promoted {len(promoted)} cases")
        return promoted

    @staticmethod
    def _summarize(entry: dict[str, Any]) -> str:
        tool = entry.get("tool") or entry.get("tool_name") or "unknown"
        risk = _as_str(entry.get("risk_level")) or "?"
        data = entry.get("data") or {}
        is_backdoor = data.get("is_backdoor", "?")
        return f"{tool}: risk={risk}, is_backdoor={is_backdoor}"
