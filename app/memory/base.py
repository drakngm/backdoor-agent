"""
BaseMemory: Abstract base class for all memory layers.

Defines the common interface that all four memory layers must implement:
  WorkingMemory, SessionMemory, ProjectMemory, KnowledgeMemory
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseMemory(ABC):
    """Abstract base for all memory layers."""

    @abstractmethod
    def store(self, key: str, value: Any) -> None:
        """Store a value in this memory layer."""
        ...

    @abstractmethod
    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve a value from this memory layer."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all data in this memory layer."""
        ...

    @abstractmethod
    def snapshot(self) -> dict[str, Any]:
        """Return a serializable snapshot of all contents."""
        ...