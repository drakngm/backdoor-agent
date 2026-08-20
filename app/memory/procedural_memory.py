"""
L3 — Procedural Memory (长期记忆/知识库): verified strategies + known signatures.

Storage:
  - structured rules (strategy templates / detection procedures)
  - vectorized case base (verified patterns, semantically searchable)

Retrieval:
  - strategy matching by model architecture / task type ("ResNet 系列优先 STRIP + NC")
  - semantic search over the case base

Lifecycle: permanent; accumulates over time.
"""

import json
import os
import uuid
from typing import Any, Optional

from app.core.config import get_config
from app.core.logging import get_logger
from app.memory.embedder import EmbedderLike, HashingEmbedder

logger = get_logger(__name__)


class ProceduralMemory:
    """L3: long-term verified knowledge (rules + case base)."""

    def __init__(
        self,
        embedder: Optional[EmbedderLike] = None,
        filepath: Optional[str] = None,
    ):
        self.embedder = embedder or HashingEmbedder()
        self.filepath = filepath or get_config().procedural_memory_path
        self.rules: list[dict[str, Any]] = []
        self.cases: list[dict[str, Any]] = []
        self._load()

    # ── Rules ─────────────────────────────────────────────────────

    def add_rule(self, rule: dict[str, Any]) -> str:
        """
        Store a structured strategy rule.

        Rule shape:
            {"id", "architecture", "task", "strategy": [...], "description"}
        """
        rule = dict(rule)
        rule.setdefault("id", f"rule-{uuid.uuid4().hex[:8]}")
        self.rules.append(rule)
        self._persist()
        return rule["id"]

    def match_strategy(self, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """Match rules by architecture/task type (accelerates detection decisions)."""
        arch = metadata.get("architecture")
        task = metadata.get("task", "detection")
        matched = []
        for rule in self.rules:
            if rule.get("architecture") in (None, "any", arch) and rule.get("task") in (None, "any", task):
                matched.append(rule)
        return matched

    # ── Case base (vectorized) ────────────────────────────────────

    def add_case(self, content: str, metadata: Optional[dict[str, Any]] = None) -> str:
        """Store a verified pattern/case with its vector."""
        case = {
            "id": f"case-{uuid.uuid4().hex[:8]}",
            "content": content,
            "metadata": metadata or {},
            "vector": self.embedder.embed(content),
        }
        self.cases.append(case)
        self._persist()
        return case["id"]

    def search_cases(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Semantic search over the case base."""
        qv = self.embedder.embed(query)
        scored = sorted(
            ((self.embedder.similarity(qv, c["vector"]), c) for c in self.cases),
            key=lambda x: x[0],
            reverse=True,
        )
        return [
            {"id": c["id"], "content": c["content"], "metadata": c["metadata"], "score": round(s, 4)}
            for s, c in scored[:top_k]
        ]

    # ── Persistence ───────────────────────────────────────────────

    def _persist(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            data = {"rules": self.rules, "cases": self.cases}
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to persist procedural memory: {e}")

    def _load(self) -> None:
        if not os.path.exists(self.filepath):
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.rules = data.get("rules", [])
            self.cases = data.get("cases", [])
        except Exception as e:
            logger.error(f"Failed to load procedural memory: {e}")
            self.rules = []
            self.cases = []

    def snapshot(self) -> dict[str, Any]:
        return {
            "filepath": self.filepath,
            "rules_count": len(self.rules),
            "cases_count": len(self.cases),
        }
