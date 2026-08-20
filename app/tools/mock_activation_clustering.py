"""
Mock Activation Clustering Detector Tool.

Activation Clustering: Extracts intermediate layer activations for clean
and potentially backdoored samples, then applies dimensionality reduction
(PCA/t-SNE) + clustering (K-Means/DBSCAN) to detect anomalous activation
patterns that indicate a backdoor.
"""

import asyncio
import random
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.tools.base import BaseTool
from app.tools.contract import ToolContract
from app.tools.schemas import ToolInput, ToolOutput, RiskLevel, Artifact
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Contract-specific I/O schemas ──────────────────────────────────────

class ActivationClusteringInput(ToolInput):
    """Input for Activation Clustering detection."""
    model_path: str = Field(..., description="Path to the model file")
    layer_name: str = Field(default="dense_2", description="Target layer for activation extraction")
    n_clusters: int = Field(default=3, description="Number of clusters for K-Means")
    samples_per_class: int = Field(default=50, description="Samples extracted per class")


class ActivationClusteringOutput(ToolOutput):
    """Output from Activation Clustering detection."""
    silhouette_score: float = Field(..., description="Clustering quality metric (-1 to 1)")
    n_anomalous_clusters: int = Field(default=0, description="Number of anomalous clusters detected")
    is_backdoor: bool = Field(default=False, description="Whether backdoor was detected")


# ── Mock Tool ──────────────────────────────────────────────────────────

class MockActivationClusteringDetector(BaseTool):
    """
    Mock implementation of Activation Clustering backdoor detection.

    In production, this would:
      1. Feed clean + potentially poisoned samples through the model
      2. Extract activations from a target intermediate layer
      3. Apply PCA/t-SNE for dimensionality reduction
      4. Run K-Means or DBSCAN clustering
      5. Flag clusters with anomalous separation as backdoor evidence
    """

    contract = ToolContract(
        name="activation_clustering",
        description=(
            "Activation Clustering: extracts intermediate layer activations and "
            "applies clustering (K-Means/DBSCAN) to detect anomalous activation "
            "patterns. Clean vs. backdoored samples form distinct clusters."
        ),
        input_schema=ActivationClusteringInput,
        output_schema=ActivationClusteringOutput,
        timeout_ms=90000,
        requires_gpu=True,
        retry_count=1,
        tags=["detection", "gpu", "deep_scan", "forensic_scan"],
    )

    async def execute(self, input_data: ActivationClusteringInput) -> ActivationClusteringOutput:
        """
        Mock execution: simulate an Activation Clustering detection run.

        Args:
            input_data: ActivationClusteringInput with model_path, layer, cluster params.

        Returns:
            ActivationClusteringOutput with clustering metrics and standardized fields.
        """
        logger.info(
            f"[activation_clustering] Starting mock detection on {input_data.model_path} "
            f"(layer={input_data.layer_name}, clusters={input_data.n_clusters})",
            extra={"trace_id": input_data.trace_id},
        )

        # Simulate processing delay
        await asyncio.sleep(random.uniform(1.5, 3.0))

        # Mock detection logic
        silhouette = round(random.uniform(0.2, 0.85), 3)

        # Low silhouette + >1 cluster detected → potential backdoor
        n_anomalous = random.randint(0, 2) if silhouette < 0.5 else 0
        is_backdoor = n_anomalous > 0

        if is_backdoor:
            confidence = 1.0 - silhouette  # lower silhouette = higher backdoor confidence
        else:
            confidence = silhouette

        if n_anomalous >= 2:
            risk = RiskLevel.HIGH
        elif n_anomalous == 1:
            risk = RiskLevel.MEDIUM
        else:
            risk = RiskLevel.LOW

        output = ActivationClusteringOutput(
            trace_id=input_data.trace_id,
            tool_name="activation_clustering",
            success=True,
            data={
                "silhouette_score": silhouette,
                "n_anomalous_clusters": n_anomalous,
                "is_backdoor": is_backdoor,
                "layer_analyzed": input_data.layer_name,
                "total_clusters": input_data.n_clusters,
            },
            silhouette_score=silhouette,
            n_anomalous_clusters=n_anomalous,
            is_backdoor=is_backdoor,
            confidence_score=round(confidence, 3),
            risk_level=risk,
            artifact=[
                Artifact(
                    name="activation_map",
                    type="matrix",
                    path=f"/tmp/ac_activations_{input_data.trace_id}.npy",
                    format="npy",
                    metadata={"layer_shape": [128, 256]},
                ),
                Artifact(
                    name="pca_projection",
                    type="image",
                    path=f"/tmp/ac_pca_{input_data.trace_id}.png",
                    format="png",
                ),
                Artifact(
                    name="cluster_assignments",
                    type="json",
                    path=f"/tmp/ac_clusters_{input_data.trace_id}.json",
                    format="json",
                ),
            ],
            duration_ms=random.randint(2000, 6000),
        )

        logger.info(
            f"[activation_clustering] Complete: silhouette={silhouette}, "
            f"anomalous_clusters={n_anomalous}, risk={risk.value}",
            extra={"trace_id": input_data.trace_id},
        )

        return output