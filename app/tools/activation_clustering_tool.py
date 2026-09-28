"""
ActivationClusteringTool: real Activation Clustering exposed as a Tool via ToolAdapter.

Wraps the standalone ActivationClusteringDetector algorithm
(app/security/activation_clustering.py) into a registry-ready Tool, mirroring the
STRIPTool adapter. The activation extractor and clean samples are injectable so
the algorithm can be tested deterministically; without injection a synthetic
deterministic extractor is used as the MVP fallback.
"""

import hashlib
import math
from typing import Callable, Optional, Sequence

from pydantic import BaseModel, Field

from app.tools.adapter import ToolAdapter
from app.tools.contract import ToolContract
from app.tools.schemas import ToolInput, ToolOutput, RiskLevel, Artifact
from app.security.activation_clustering import ActivationClusteringDetector, ActivateFn
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Contract-specific I/O schemas ──────────────────────────────────────

class ActivationClusteringInput(ToolInput):
    """Input for Activation Clustering detection."""
    model_path: str = Field(..., description="Path to the model file")
    layer_name: str = Field(default="dense_2", description="Target layer for activation extraction")
    n_clusters: int = Field(default=3, description="Number of clusters for K-Means")
    samples_per_class: int = Field(default=50, description="Samples extracted per class")

    model_config = {"protected_namespaces": ()}


class ActivationClusteringOutput(ToolOutput):
    """Output from Activation Clustering detection."""
    silhouette_score: float = Field(..., description="Clustering quality metric (-1 to 1)")
    n_anomalous_clusters: int = Field(default=0, description="Number of anomalous clusters detected")
    is_backdoor: bool = Field(default=False, description="Whether backdoor was detected")


# ── Synthetic MVP fallback (replace with real activation extractor) ──────

def synthetic_activate_fn(model_path: str, dim: int = 8) -> ActivateFn:
    """Build a deterministic pseudo-activation extractor from `model_path`."""
    seed = int(hashlib.sha256(model_path.encode("utf-8")).hexdigest()[:8], 16)

    def activate(batch: Sequence[Sequence[float]]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for sample in batch:
            vectors.append([
                math.sin((seed + j * 17) % 997) * x
                for j, x in enumerate(sample)
            ])
        return vectors

    return activate


# ── Tool ──────────────────────────────────────────────────────────────

class ActivationClusteringTool(ToolAdapter):
    """Real Activation Clustering detector wrapped as a Tool."""

    manifest = ToolContract(
        name="activation_clustering_real",
        description=(
            "Real Activation Clustering detection: extracts intermediate-layer "
            "activations, clusters them with K-Means, and flags undersized (tight) "
            "clusters as backdoor evidence. Wraps the ActivationClusteringDetector "
            "algorithm via ToolAdapter."
        ),
        input_schema=ActivationClusteringInput,
        output_schema=ActivationClusteringOutput,
        timeout_ms=90000,
        requires_gpu=False,
        retry_count=1,
        tags=["detection", "deep_scan", "forensic_scan"],
    )

    def __init__(
        self,
        activate_fn: Optional[ActivateFn] = None,
        samples: Optional[Sequence[Sequence[float]]] = None,
    ):
        self._activate_fn = activate_fn
        self._samples = samples

    def _get_activate_fn(self, model_path: str) -> ActivateFn:
        if self._activate_fn is not None:
            return self._activate_fn
        return synthetic_activate_fn(model_path)

    def _get_samples(self) -> list[list[float]]:
        if self._samples is not None:
            return [list(s) for s in self._samples]
        from app.tools.strip_tool import synthetic_samples

        return synthetic_samples(count=12, dim=8)

    async def run(self, input_data: ActivationClusteringInput) -> ActivationClusteringOutput:
        activate = self._get_activate_fn(input_data.model_path)
        samples = self._get_samples()

        detector = ActivationClusteringDetector(activate)
        result = detector.run(samples=samples, n_clusters=input_data.n_clusters)

        if result.is_backdoor:
            confidence = min(1.0, 1.0 - result.silhouette_score)
            risk = (
                RiskLevel.HIGH if result.n_anomalous_clusters >= 2 else RiskLevel.MEDIUM
            )
        else:
            confidence = max(0.01, result.silhouette_score)
            risk = RiskLevel.LOW

        logger.info(
            f"[activation_clustering_real] silhouette={result.silhouette_score}, "
            f"anomalous_clusters={result.n_anomalous_clusters}, risk={risk.value}",
            extra={"trace_id": input_data.trace_id},
        )

        return ActivationClusteringOutput(
            trace_id=input_data.trace_id,
            tool_name="activation_clustering_real",
            success=True,
            data={
                "silhouette_score": result.silhouette_score,
                "n_anomalous_clusters": result.n_anomalous_clusters,
                "anomalous_clusters": result.anomalous_clusters,
                "is_backdoor": result.is_backdoor,
                "layer_analyzed": input_data.layer_name,
                "total_clusters": result.n_clusters,
            },
            silhouette_score=result.silhouette_score,
            n_anomalous_clusters=result.n_anomalous_clusters,
            is_backdoor=result.is_backdoor,
            confidence_score=round(confidence, 3),
            risk_level=risk,
            artifact=[
                Artifact(
                    name="activation_map",
                    type="matrix",
                    format="json",
                    metadata={"n_clusters": result.n_clusters},
                ),
                Artifact(
                    name="cluster_assignments",
                    type="json",
                    format="json",
                    metadata={"anomalous_clusters": result.anomalous_clusters},
                ),
            ],
        )
