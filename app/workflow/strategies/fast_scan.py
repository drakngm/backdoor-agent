"""
FastScanStrategy: Quick CI/CD gate scan (~30s).

Uses only STRIP detector — fastest method.
Suitable for pre-commit hooks and CI pipeline gates.
"""

from typing import Any

from app.tools.registry import ToolRegistry
from app.workflow.task_graph import TaskGraph
from app.workflow.strategies.base import BaseScanStrategy


class FastScanStrategy(BaseScanStrategy):
    """Fast scan: single-detector, low latency."""

    name = "fast_scan"
    description = "Fast gate scan using STRIP detector only. ~30 seconds. Suitable for CI/CD pipelines."
    estimated_duration_seconds = 30

    def build_task_graph(self, tool_registry: ToolRegistry, **kwargs: Any) -> TaskGraph:
        model_path = kwargs.get("model_path", "model.h5")
        trace_id = kwargs.get("trace_id", "unknown")

        graph = TaskGraph()

        t_strip = graph.add_task(
            "strip_detect",
            params={"trace_id": trace_id, "model_path": model_path, "num_samples": 100},
        )

        return graph