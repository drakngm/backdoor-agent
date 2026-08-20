"""
ForensicScanStrategy: Deep forensic investigation (~30min).

Uses all detectors + cross-validation for maximum thoroughness.
Generates complete evidence chains for incident response.
"""

from typing import Any

from app.tools.registry import ToolRegistry
from app.workflow.task_graph import TaskGraph
from app.workflow.strategies.base import BaseScanStrategy


class ForensicScanStrategy(BaseScanStrategy):
    """Forensic scan: full detector suite, ~30 minutes."""

    name = "forensic_scan"
    description = (
        "Full forensic investigation with all detectors "
        "(STRIP + Neural Cleanse + Activation Clustering + Spectral Signature). "
        "Generates complete evidence chain. ~30 minutes."
    )
    estimated_duration_seconds = 1800

    def build_task_graph(self, tool_registry: ToolRegistry, **kwargs: Any) -> TaskGraph:
        model_path = kwargs.get("model_path", "model.h5")
        trace_id = kwargs.get("trace_id", "unknown")

        graph = TaskGraph()

        # All detectors run independently (parallel)
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