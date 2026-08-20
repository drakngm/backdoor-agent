"""
BaseScanStrategy: Abstract base for all scan strategies.

Each strategy defines which tools to use, in what order,
and how they depend on each other (resulting in a TaskGraph DAG).
"""

from abc import ABC, abstractmethod
from typing import Any

from app.tools.registry import ToolRegistry
from app.workflow.task_graph import TaskGraph


class BaseScanStrategy(ABC):
    """Abstract base for scan strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique strategy identifier."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        ...

    @property
    @abstractmethod
    def estimated_duration_seconds(self) -> int:
        """Estimated runtime for planning/scheduling."""
        ...

    @abstractmethod
    def build_task_graph(self, tool_registry: ToolRegistry, **kwargs: Any) -> TaskGraph:
        """
        Build the TaskGraph DAG for this strategy.

        Args:
            tool_registry: Shared ToolRegistry (for validation/availability checks).
            **kwargs: Strategy-specific parameters (e.g., model_path).

        Returns:
            A TaskGraph ready for execution.
        """
        ...