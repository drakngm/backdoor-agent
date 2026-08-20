"""
L1 — Episodic Memory (短期记忆): sliding-window, session-scoped.

Storage:
  - Redis (list per session, `rpush` + `ltrim` to keep the last N entries)
  - In-memory fallback when Redis is unavailable

Retrieval:
  - chronological (time order)
  - simple keyword matching for immediate follow-ups ("刚才 STRIP 结果是多少?")

Lifecycle: cleared when the session ends.
"""

import json
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


class EpisodicMemory:
    """L1: recent N interactions of a detection session."""

    def __init__(self, window_size: int = 20, redis_client: Optional[Any] = None):
        self.window_size = window_size
        self.redis = redis_client
        self._inmem: dict[str, list[dict[str, Any]]] = {}
        self._session_id: Optional[str] = None

    # ── Session lifecycle ─────────────────────────────────────────

    def start_session(self, session_id: str) -> None:
        self._session_id = session_id
        if self.redis is not None:
            self.redis.delete(self._key(session_id))
        else:
            self._inmem[session_id] = []

    def clear(self) -> None:
        if self._session_id is None:
            return
        if self.redis is not None:
            self.redis.delete(self._key(self._session_id))
        else:
            self._inmem.pop(self._session_id, None)
        self._session_id = None

    # ── Write ─────────────────────────────────────────────────────

    def add(self, entry: dict[str, Any]) -> None:
        """Append an entry (tool call / observation / reasoning)."""
        if self._session_id is None:
            raise RuntimeError("start_session() must be called before add()")

        entry = dict(entry)
        entry.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

        if self.redis is not None:
            key = self._key(self._session_id)
            pipe = self.redis.pipeline()
            pipe.rpush(key, json.dumps(entry, default=str))
            pipe.ltrim(key, -self.window_size, -1)  # keep last N
            pipe.execute()
        else:
            entries = self._inmem.setdefault(self._session_id, [])
            entries.append(entry)
            if len(entries) > self.window_size:
                del entries[: len(entries) - self.window_size]

    # ── Read ──────────────────────────────────────────────────────

    def recent(self, n: Optional[int] = None) -> list[dict[str, Any]]:
        """Return the last N entries in chronological order (oldest -> newest)."""
        n = n or self.window_size
        if self._session_id is None:
            return []

        if self.redis is not None:
            raw = self.redis.lrange(self._key(self._session_id), -n, -1)
            return [json.loads(r) for r in raw]

        entries = self._inmem.get(self._session_id, [])
        return list(entries[-n:])

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Simple keyword match over the window (chronological order preserved)."""
        terms = [t.lower() for t in query.split() if t]
        scored: list[tuple[int, dict[str, Any]]] = []
        for entry in self.recent():
            text = json.dumps(entry, ensure_ascii=False).lower()
            score = sum(1 for t in terms if t in text)
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_k]]

    # ── Misc ──────────────────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        return {
            "session_id": self._session_id,
            "window_size": self.window_size,
            "entries": self.recent(),
        }

    @staticmethod
    def _key(session_id: str) -> str:
        return f"episodic:{session_id}"
