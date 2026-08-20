"""
ContextManager: 4-layer memory orchestration with degrade strategy.

Search sequence (when Agent needs information):
  1. Working Memory  → found? return
  2. Session Memory  → found? promote to WM → return
  3. Project Memory  → found? compress → promote to SM → return
  4. Knowledge Memory (RAG) → search → inject into WM → return
  5. Not found → return None (Agent handles via tool call)

This manager is the SINGLE entry point for memory operations
used by both Agent Mode and Workflow Mode.
"""

from typing import Any, Optional

from app.memory.base import BaseMemory
from app.memory.working_memory import WorkingMemory
from app.memory.session_memory import SessionMemory
from app.memory.project_memory import ProjectMemory
from app.memory.knowledge_memory import KnowledgeMemory
from app.core.logging import get_logger

logger = get_logger(__name__)


class ContextManager:
    """
    Orchestrates the 4-layer memory hierarchy.

    Usage:
        ctx = ContextManager()
        ctx.init_session(trace_id="trc-abc")
        ctx.working.append("user", "detect model.h5")
        # ... agent loop ...
        result = ctx.search("model_hash")
    """

    def __init__(
        self,
        working: Optional[WorkingMemory] = None,
        session: Optional[SessionMemory] = None,
        project: Optional[ProjectMemory] = None,
        knowledge: Optional[KnowledgeMemory] = None,
    ):
        self.working = working or WorkingMemory()
        self.session = session or SessionMemory()
        self.project = project or ProjectMemory()
        self.knowledge = knowledge or KnowledgeMemory()

    # ── Session lifecycle ──────────────────────────────────────────

    def init_session(self, trace_id: str) -> None:
        """Initialize a new session (clears WM + SM, keeps PM + KM)."""
        self.working.clear()
        self.session = SessionMemory(trace_id=trace_id)
        logger.info(f"Session initialized: trace_id={trace_id}")

    def end_session(self) -> None:
        """End current session: compress SM, optionally persist."""
        summary = self.session.compress_to_summary()
        self.project.store(f"session_{self.session.session_id}_summary", summary)
        self.working.clear()
        logger.info(f"Session ended: {self.session.session_id}")

    # ── Hierarchical Search / Retrieve ─────────────────────────────

    def search(self, key: str) -> Optional[Any]:
        """
        4-layer search with degrade strategy.

        Priority: WM → SM → PM → KM
        """
        # L1: Working Memory
        result = self.working.retrieve(key)
        if result is not None:
            logger.debug(f"[memory] L1 hit: {key}")
            return result

        # L2: Session Memory
        result = self.session.retrieve(key)
        if result is not None:
            logger.debug(f"[memory] L2 hit: {key} → promoting to WM")
            self.working.store(key, result)
            return result

        # L3: Project Memory
        result = self.project.retrieve(key)
        if result is not None:
            logger.debug(f"[memory] L3 hit: {key} → promoting to SM + WM")
            self.session.store(key, result)
            self.working.store(key, result)
            return result

        # L4: Knowledge Memory (RAG)
        docs = self.knowledge.search(key, top_k=3)
        if docs:
            logger.debug(f"[memory] L4 hit: {key} → {len(docs)} docs found")
            self.working.store(f"rag:{key}", docs)
            return docs

        logger.debug(f"[memory] MISS: {key} (all layers)")
        return None

    def retrieve_from_layer(self, layer_name: str, key: str) -> Optional[Any]:
        """Retrieve directly from a specific layer."""
        layers: dict[str, BaseMemory] = {
            "working": self.working,
            "session": self.session,
            "project": self.project,
            "knowledge": self.knowledge,
        }
        layer = layers.get(layer_name)
        if layer is None:
            return None
        return layer.retrieve(key)

    # ── Message / Tool result helpers ──────────────────────────────

    def add_user_message(self, content: str) -> None:
        """Append a user message to both WM and SM."""
        self.working.append("user", content)
        self.session.append_message("user", content)

    def add_assistant_message(self, content: str) -> None:
        """Append an assistant (LLM) message to both WM and SM."""
        self.working.append("assistant", content)
        self.session.append_message("assistant", content)

    def add_tool_result(self, tool_name: str, output: dict[str, Any]) -> None:
        """Store a tool result in both SM and WM."""
        self.session.store_tool_result(tool_name, output)
        self.working.append_observation(output)

    # ── Context building for LLM ───────────────────────────────────

    def build_context(self) -> dict[str, Any]:
        """
        Build a complete context dict for LLM prompt construction.

        Returns:
            {
                "messages": [...],           # WM messages for LLM
                "recent_tools": [...],       # Recent tool calls
                "knowledge_hints": [...],    # Relevant knowledge snippets
                "session_summary": ...,      # SM summary (if exists)
            }
        """
        return {
            "messages": self.working.get_context_for_llm(),
            "recent_tools": list(self.session.tool_results.keys()),
            "knowledge_hints": self.knowledge.search("backdoor detection best practices", top_k=2),
            "session_summary": self.session.summary,
        }

    # ── Snapshot ───────────────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        """Return a full snapshot of all 4 layers."""
        return {
            "working": self.working.snapshot(),
            "session": self.session.snapshot(),
            "project": self.project.snapshot(),
            "knowledge": self.knowledge.snapshot(),
        }