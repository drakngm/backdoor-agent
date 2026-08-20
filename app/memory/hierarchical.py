"""
HierarchicalMemory: three-layer memory facade.

    L1 Episodic (Redis) -> L2 Semantic (vector) -> L3 Procedural (rules)

Provides:
  - start_session / remember (write to L1)
  - search (degradation: L1 keyword -> L2 semantic -> L3 rules/cases)
  - consolidate (L1 -> L2 -> L3 memory consolidation)
"""

from typing import Any, Optional

from app.memory.episodic_memory import EpisodicMemory
from app.memory.semantic_memory import SemanticMemory
from app.memory.procedural_memory import ProceduralMemory
from app.memory.consolidation import MemoryConsolidation
from app.memory.redis_client import get_redis_client


class HierarchicalMemory:
    """
    Unified three-layer memory.

    Usage:
        memory = HierarchicalMemory()
        memory.start_session("ses-1")
        memory.remember({"type": "observation", "tool": "strip_detect", ...})
        memory.search("STRIP 结果")           # L1 keyword
        memory.search("similar backdoor pattern")  # L2 semantic
        memory.consolidate()                  # L1 -> L2 -> L3
    """

    def __init__(
        self,
        episodic: Optional[EpisodicMemory] = None,
        semantic: Optional[SemanticMemory] = None,
        procedural: Optional[ProceduralMemory] = None,
        window_size: int = 20,
        use_redis: bool = True,
    ):
        redis_client = get_redis_client() if use_redis else None
        self.episodic = episodic or EpisodicMemory(window_size=window_size, redis_client=redis_client)
        self.semantic = semantic or SemanticMemory()
        self.procedural = procedural or ProceduralMemory()
        self.consolidation = MemoryConsolidation(self.semantic, self.procedural)

    # ── L1 session ────────────────────────────────────────────────

    def start_session(self, session_id: str) -> None:
        self.episodic.start_session(session_id)

    def remember(self, entry: dict[str, Any]) -> None:
        self.episodic.add(entry)

    # ── Retrieval (degradation L1 -> L2 -> L3) ────────────────────

    def search(self, query: str, top_k: int = 5) -> dict[str, Any]:
        """Hierarchical search: L1 keyword -> L2 semantic -> L3 rules/cases."""
        episodic_hits = self.episodic.search(query, top_k)
        if episodic_hits:
            return {"layer": "episodic", "results": episodic_hits}

        semantic_hits = self.semantic.search(query, top_k)
        if semantic_hits:
            return {"layer": "semantic", "results": semantic_hits}

        cases = self.procedural.search_cases(query, top_k)
        return {"layer": "procedural", "results": cases}

    def match_strategy(self, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """Match L3 rules by model architecture/task (accelerates decisions)."""
        return self.procedural.match_strategy(metadata)

    # ── Consolidation ─────────────────────────────────────────────

    def consolidate(self) -> dict[str, int]:
        """Run memory consolidation: L1 -> L2, then L2 -> L3."""
        l1_l2 = self.consolidation.consolidate_session(self.episodic)
        l2_l3 = self.consolidation.promote_verified()
        return {"l1_to_l2": len(l1_l2), "l2_to_l3": len(l2_l3)}

    # ── Misc ──────────────────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        return {
            "episodic": self.episodic.snapshot(),
            "semantic": self.semantic.snapshot(),
            "procedural": self.procedural.snapshot(),
        }
