"""
Planner: Strategy-based task planning for Workflow Mode.

Receives a strategy name → delegates to the correct strategy → returns a TaskGraph.
"""

from typing import Any, Optional

from app.workflow.task_graph import TaskGraph
from app.workflow.strategies.base import BaseScanStrategy
from app.workflow.strategies.fast_scan import FastScanStrategy
from app.workflow.strategies.deep_scan import DeepScanStrategy
from app.workflow.strategies.forensic_scan import ForensicScanStrategy
from app.tools.registry import ToolRegistry
from app.core.logging import get_logger
from app.core.exceptions import WorkflowStrategyError

logger = get_logger(__name__)


class Planner:
    """
    Plans the detection workflow by selecting the correct strategy.

    Usage:
        planner = Planner()
        graph = planner.plan("deep_scan", tool_registry, model_path="model.h5")
    """

    def __init__(self):
        self._strategies: dict[str, BaseScanStrategy] = {
            "fast_scan": FastScanStrategy(),
            "deep_scan": DeepScanStrategy(),
            "forensic_scan": ForensicScanStrategy(),
        }

    def plan(
        self,
        strategy_name: str,
        tool_registry: ToolRegistry,
        **kwargs: Any,
    ) -> TaskGraph:
        """
        Build a TaskGraph from a named strategy.

        Args:
            strategy_name: One of "fast_scan", "deep_scan", "forensic_scan".
            tool_registry: Shared ToolRegistry.
            **kwargs: Forwarded to strategy.build_task_graph().

        Returns:
            A TaskGraph ready for execution.

        Raises:
            WorkflowStrategyError: If strategy_name is unknown.
        """
        strategy = self._strategies.get(strategy_name)
        if strategy is None:
            available = list(self._strategies.keys())
            raise WorkflowStrategyError(
                message=f"Unknown strategy: '{strategy_name}'. Available: {available}",
                details={"requested": strategy_name, "available": available},
            )

        logger.info(f"Planning workflow with strategy: {strategy.name} ({strategy.description})")
        return strategy.build_task_graph(tool_registry, **kwargs)

    def list_strategies(self) -> list[dict[str, Any]]:
        """Return metadata for all registered strategies."""
        return [
            {
                "name": s.name,
                "description": s.description,
                "estimated_duration_seconds": s.estimated_duration_seconds,
            }
            for s in self._strategies.values()
        ]

    def register_strategy(self, strategy: BaseScanStrategy) -> None:
        """Register a custom strategy at runtime."""
        self._strategies[strategy.name] = strategy
        logger.info(f"Strategy registered: {strategy.name}")