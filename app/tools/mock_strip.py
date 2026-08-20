"""
Mock STRIP Detector Tool.

STRIP (STRong Intentional Perturbation):
Perturbs input samples systematically and observes output entropy changes.
High entropy perturbation = likely backdoor trigger present.
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

class STRIPInput(ToolInput):
    """Input for STRIP detection."""
    model_path: str = Field(..., description="Path to the model file")
    num_samples: int = Field(default=100, description="Number of perturbation samples")
    perturbation_strength: float = Field(default=0.05, ge=0.0, le=1.0)


class STRIPOutput(ToolOutput):
    """Output from STRIP detection."""
    entropy_score: float = Field(..., description="Average entropy score across perturbations")
    is_backdoor: bool = Field(..., description="Whether a backdoor is detected")
    perturbed_samples: int = 0


# ── Mock Tool ──────────────────────────────────────────────────────────

class MockSTRIPDetector(BaseTool):
    """
    Mock implementation of STRIP backdoor detection.

    In production, this would:
      1. Load the model
      2. Generate N perturbed inputs
      3. Measure output entropy distribution
      4. Compare against clean baseline
    """

    contract = ToolContract(
        name="strip_detect",
        description=(
            "STRIP detection: systematically perturbs input samples and measures "
            "output entropy. High entropy variance indicates a potential backdoor trigger. "
            "Suitable for fast CI/CD pipeline scans."
        ),
        input_schema=STRIPInput,
        output_schema=STRIPOutput,
        timeout_ms=60000,
        requires_gpu=True,
        retry_count=2,
        tags=["detection", "gpu", "fast_scan", "deep_scan", "forensic_scan"],
    )

    async def execute(self, input_data: STRIPInput) -> STRIPOutput:
        """
        Mock execution: simulate a detection run with randomized results.

        Args:
            input_data: STRIPInput with model_path and perturbation params.

        Returns:
            STRIPOutput with entropy_score, is_backdoor, and standardized fields.
        """
        logger.info(
            f"[strip_detect] Starting mock detection on {input_data.model_path}",
            extra={"trace_id": input_data.trace_id},
        )

        # Simulate processing delay
        await asyncio.sleep(random.uniform(0.5, 1.5))

        # Mock detection logic
        entropy_score = round(random.uniform(0.01, 0.95), 3)
        is_backdoor = entropy_score > 0.5
        confidence = entropy_score if is_backdoor else (1.0 - entropy_score)

        if is_backdoor:
            risk = RiskLevel.HIGH if entropy_score > 0.8 else RiskLevel.MEDIUM
        else:
            risk = RiskLevel.LOW

        output = STRIPOutput(
            trace_id=input_data.trace_id,
            tool_name="strip_detect",
            success=True,
            data={
                "entropy_score": entropy_score,
                "is_backdoor": is_backdoor,
                "perturbed_samples": input_data.num_samples,
                "perturbation_strength": input_data.perturbation_strength,
            },
            entropy_score=entropy_score,
            is_backdoor=is_backdoor,
            perturbed_samples=input_data.num_samples,
            confidence_score=round(confidence, 3),
            risk_level=risk,
            artifact=[
                Artifact(
                    name="entropy_distribution",
                    type="distribution",
                    path=f"/tmp/strip_entropy_{input_data.trace_id}.npy",
                    format="npy",
                    metadata={"threshold_used": 0.5},
                ),
            ],
            duration_ms=random.randint(800, 3000),
        )

        logger.info(
            f"[strip_detect] Complete: entropy={entropy_score}, backdoor={is_backdoor}, risk={risk.value}",
            extra={"trace_id": input_data.trace_id},
        )

        return output