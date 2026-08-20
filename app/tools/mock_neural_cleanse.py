"""
Mock Neural Cleanse Detector Tool.

Neural Cleanse: Reverses potential backdoor triggers by optimizing
a universal perturbation pattern, then detects anomalies via outlier
detection on the L1 norm of the recovered triggers.
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

class NeuralCleanseInput(ToolInput):
    """Input for Neural Cleanse detection."""
    model_path: str = Field(..., description="Path to the model file")
    num_classes: int = Field(default=10, description="Number of output classes")
    optimization_steps: int = Field(default=1000, description="Gradient descent iterations")


class NeuralCleanseOutput(ToolOutput):
    """Output from Neural Cleanse detection."""
    anomaly_index: float = Field(..., description="Median Absolute Deviation anomaly score")
    is_backdoor: bool = Field(..., description="Whether a backdoor was detected")
    recovered_triggers: int = 0


# ── Mock Tool ──────────────────────────────────────────────────────────

class MockNeuralCleanseDetector(BaseTool):
    """
    Mock implementation of Neural Cleanse backdoor detection.

    In production, this would:
      1. For each class, optimize a trigger pattern that flips predictions
      2. Compute L1 norm of each recovered trigger
      3. Apply MAD (Median Absolute Deviation) outlier detection
      4. Flag classes with abnormally small triggers as backdoor candidates
    """

    contract = ToolContract(
        name="neural_cleanse",
        description=(
            "Neural Cleanse: reverse-engineers potential backdoor triggers via "
            "gradient-based optimization. Uses MAD outlier detection on recovered "
            "trigger norms to identify anomalous (backdoored) classes."
        ),
        input_schema=NeuralCleanseInput,
        output_schema=NeuralCleanseOutput,
        timeout_ms=120000,
        requires_gpu=True,
        retry_count=1,
        tags=["detection", "gpu", "deep_scan", "forensic_scan"],
    )

    async def execute(self, input_data: NeuralCleanseInput) -> NeuralCleanseOutput:
        """
        Mock execution: simulate a Neural Cleanse detection run.

        Args:
            input_data: NeuralCleanseInput with model_path, num_classes, optimization_steps.

        Returns:
            NeuralCleanseOutput with anomaly_index, is_backdoor, and standardized fields.
        """
        logger.info(
            f"[neural_cleanse] Starting mock detection on {input_data.model_path} "
            f"(classes={input_data.num_classes}, steps={input_data.optimization_steps})",
            extra={"trace_id": input_data.trace_id},
        )

        # Simulate longer processing (Neural Cleanse is more expensive)
        await asyncio.sleep(random.uniform(2.0, 4.0))

        # Mock detection logic
        anomaly_index = round(random.uniform(0.5, 3.0), 3)

        # MAD threshold: typically 2.0 is the cutoff
        is_backdoor = anomaly_index > 2.0
        confidence = min(1.0, anomaly_index / 3.0) if is_backdoor else max(0.01, 1.0 - anomaly_index / 3.0)

        if anomaly_index > 2.5:
            risk = RiskLevel.HIGH
        elif anomaly_index > 2.0:
            risk = RiskLevel.MEDIUM
        else:
            risk = RiskLevel.LOW

        recovered = random.randint(1, 3) if is_backdoor else 0

        output = NeuralCleanseOutput(
            trace_id=input_data.trace_id,
            tool_name="neural_cleanse",
            success=True,
            data={
                "anomaly_index": anomaly_index,
                "is_backdoor": is_backdoor,
                "recovered_triggers": recovered,
                "classes_tested": input_data.num_classes,
            },
            anomaly_index=anomaly_index,
            is_backdoor=is_backdoor,
            recovered_triggers=recovered,
            confidence_score=round(confidence, 3),
            risk_level=risk,
            artifact=[
                Artifact(
                    name="trigger_patterns",
                    type="matrix",
                    path=f"/tmp/nc_triggers_{input_data.trace_id}.npy",
                    format="npy",
                    metadata={
                        "anomaly_scores_per_class": {
                            i: round(random.uniform(0.5, 3.0), 3)
                            for i in range(input_data.num_classes)
                        },
                        "mad_threshold": 2.0,
                    },
                ),
            ],
            duration_ms=random.randint(3000, 8000),
        )

        logger.info(
            f"[neural_cleanse] Complete: anomaly={anomaly_index}, backdoor={is_backdoor}, risk={risk.value}",
            extra={"trace_id": input_data.trace_id},
        )

        return output