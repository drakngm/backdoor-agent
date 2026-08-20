"""
ToolRegistry: Centralized tool management.

Features:
  - Register/unregister tools
  - Query by name, tag, GPU requirement
  - Generate LLM-compatible tool descriptions
  - Singleton access via get_tool_registry()
"""

from typing import Any, Optional

from app.tools.base import BaseTool
from app.tools.contract import ToolContract
from app.core.logging import get_logger
from app.core.exceptions import ToolNotFoundError

logger = get_logger(__name__)


class ToolRegistry:
    """
    Global registry for all tools.

    Supports:
      - register(tool)       → add a tool
      - get(name)            → retrieve by contract.name
      - list_all()           → list all registered tools
      - list_by_tag(tag)     → filter by tag
      - list_by_gpu(gpu)     → filter by GPU requirement
      - get_contracts_for_llm() → export contract dicts for LLM prompt building
      - reset()              → clear all (for testing)
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    # ── Registration ────────────────────────────────────────────────────

    def register(self, tool: BaseTool) -> None:
        """Register a tool. Keyed by contract.name."""
        name = tool.contract.name
        if name in self._tools:
            logger.warning(f"Tool '{name}' is being overwritten in registry")
        self._tools[name] = tool
        logger.info(f"Tool registered: {name} (tags={tool.contract.tags})")

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry."""
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Tool unregistered: {name}")

    def reset(self) -> None:
        """Clear all registered tools (useful for testing)."""
        self._tools.clear()
        logger.info("ToolRegistry reset")

    # ── Query ───────────────────────────────────────────────────────────

    def get(self, name: str) -> BaseTool:
        """Retrieve a tool by name. Raises ToolNotFoundError if missing."""
        if name not in self._tools:
            available = list(self._tools.keys())
            raise ToolNotFoundError(
                message=f"Tool '{name}' not found. Available: {available}",
                details={"requested": name, "available": available},
            )
        return self._tools[name]

    def has(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def list_all(self) -> list[BaseTool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def list_names(self) -> list[str]:
        """Return all registered tool names."""
        return list(self._tools.keys())

    def list_by_tag(self, tag: str) -> list[BaseTool]:
        """Filter tools by a single tag."""
        return [t for t in self._tools.values() if tag in t.contract.tags]

    def list_by_gpu(self, requires_gpu: bool = True) -> list[BaseTool]:
        """Filter tools by GPU requirement."""
        return [t for t in self._tools.values() if t.contract.requires_gpu == requires_gpu]

    def list_by_tags(self, tags: list[str], match_all: bool = False) -> list[BaseTool]:
        """
        Filter tools by multiple tags.

        Args:
            tags: List of tags to filter by.
            match_all: If True, tool must have ALL tags. If False, ANY tag matches.
        """
        tag_set = set(tags)
        results = []
        for tool in self._tools.values():
            tool_tags = set(tool.contract.tags)
            if match_all:
                if tag_set.issubset(tool_tags):
                    results.append(tool)
            else:
                if tag_set & tool_tags:
                    results.append(tool)
        return results

    # ── LLM Integration ─────────────────────────────────────────────────

    def get_contracts_for_llm(self) -> list[dict[str, Any]]:
        """
        Generate a list of tool descriptions suitable for LLM prompt injection.
        Each entry includes name, description, timeout, and tags.
        """
        return [
            {
                "name": t.contract.name,
                "description": t.contract.description,
                "timeout_ms": t.contract.timeout_ms,
                "requires_gpu": t.contract.requires_gpu,
                "tags": t.contract.tags,
            }
            for t in self._tools.values()
        ]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# ── Singleton ───────────────────────────────────────────────────────────

_registry_instance: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Return the global ToolRegistry singleton."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry()
    return _registry_instance


def reset_tool_registry() -> None:
    """Reset the global ToolRegistry (for testing)."""
    global _registry_instance
    if _registry_instance is not None:
        _registry_instance.reset()
    _registry_instance = None