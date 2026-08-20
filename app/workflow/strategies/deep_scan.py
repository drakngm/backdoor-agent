"""
DeepScanStrategy: Comprehensive pre-release scan (~5min).

Uses three detectors (STRIP, Neural Cleanse, Activation Clustering)
in parallel, then aggregates results.
"""

from typing import Any

from app.tools.registry import ToolRegistry
from app.workflow.task_graph import TaskGraph
from app.workflow.strategies.base import BaseScanStrategy


class DeepScanStrategy(BaseScanStrategy):
    """Deep scan: 3 detectors in parallel, ~5 minutes."""

    name = "deep_scan"
    description = "Comprehensive scan with 3 parallel detectors (STRIP + Neural Cleanse + Activation Clustering). ~5 minutes."
    estimated_duration_seconds = 300

    def build_task_graph(self, tool_registry: ToolRegistry, **kwargs: Any) -> TaskGraph:
        model_path = kwargs.get("model_path", "model.h5")
        trace_id = kwargs.get("trace_id", "unknown")

        graph = TaskGraph()

        # All three detectors run independently (no deps between them)
        t_strip = graph.add_task(
            "strip_detect",
            params={"trace_id": trace_id, "model_path": model_path, "num_samples": 100},
        )
        t_nc = graph.add_task(
            "neural_cleanse",
            params={"trace_id": trace_id, "model_path": model_path, "num_classes": 10},
        )
        t_ac = graph.add_task(
            "activation_clustering",
            params={"trace_id": trace_id, "model_path": model_path, "layer_name": "dense_2", "n_clusters": 3},
        )

        return graph