"""
L2 — Semantic Memory (中期记忆): vectorized, cross-session.

Storage:
  - JSON file (persistent) + in-memory vector index for cosine search
  - vectors produced by the (pluggable) Embedder

Retrieval: semantic similarity search + cross-reference against current findings.

Lifecycle: persists across sessions; accumulates findings.
"""

import json
import os
import uuid
from typing import Any, Optional

from app.core.config import get_config
from app.core.logging import get_logger
from app.memory.embedder import EmbedderLike, HashingEmbedder

logger = get_logger(__name__)


class SemanticMemory:
    """L2: vectorized findings shared across detection sessions."""

    def __init__(
        self,
        embedder: Optional[EmbedderLike] = None,
        filepath: Optional[str] = None,
    ):
        self.embedder = embedder or HashingEmbedder()
        self.filepath = filepath or get_config().semantic_memory_path
        self._entries: list[dict[str, Any]] = []
        self._load()

    # ── Write ─────────────────────────────────────────────────────

    def add_finding(
        self,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
        entry_id: Optional[str] = None,
    ) -> str:
        """Store a finding with its vector."""
        entry = {
            "id": entry_id or f"finding-{uuid.uuid4().hex[:8]}",
            "content": content,
            "metadata": metadata or {},
            "vector": self.embedder.embed(content),
        }
        self._entries.append(entry)
        self._persist()
        return entry["id"]

    # ── Read ──────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Semantic similarity search over stored findings."""
        qv = self.embedder.embed(query)
        scored = sorted(
            ((self.embedder.similarity(qv, e["vector"]), e) for e in self._entries),
            key=lambda x: x[0],
            reverse=True,
        )
        return [
            {
                "id": e["id"],
                "content": e["content"],
                "metadata": e["metadata"],
                "score": round(s, 4),
            }
            for s, e in scored[:top_k]
        ]

    def cross_reference(self, content: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Alias: semantic search for cross-referencing a current finding."""
        return self.search(content, top_k)

    def list_findings(self) -> list[dict[str, Any]]:
        """Return all stored findings (for consolidation)."""
        return list(self._entries)

    # ── Persistence ───────────────────────────────────────────────

    def _persist(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to persist semantic memory: {e}")

    def _load(self) -> None:
        if not os.path.exists(self.filepath):
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                self._entries = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load semantic memory: {e}")
            self._entries = []

    def snapshot(self) -> dict[str, Any]:
        return {
            "filepath": self.filepath,
            "findings_count": len(self._entries),
        }
