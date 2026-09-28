"""
STRIPTool: real STRIP detection exposed as a Tool via ToolAdapter.

Demonstrates the Adapter pattern: the standalone STRIPDetector algorithm
(app/security/strip_detector.py) is wrapped into a registry-ready Tool with
only a `manifest` declaration and a thin `run()` implementation.

The model predictor and clean samples are injectable (constructor) so the
algorithm can be tested deterministically. Without injection, a synthetic
deterministic predictor and sample set are used as an MVP fallback; a real
model loader is the documented production path.
"""

import hashlib
import math
import random
from typing import Callable, Optional, Sequence

from pydantic import BaseModel, Field

from app.tools.adapter import ToolAdapter
from app.tools.contract import ToolContract
from app.tools.schemas import ToolInput, ToolOutput, RiskLevel, Artifact
from app.security.strip_detector import STRIPDetector, PredictFn, softmax
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Contract-specific I/O schemas ──────────────────────────────────────

class STRIPInput(ToolInput):
    """Input for STRIP detection."""
    model_path: str = Field(..., description="Path to the model file")
    num_samples: int = Field(default=100, description="Number of perturbation samples")
    perturbation_strength: float = Field(default=0.05, ge=0.0, le=1.0)

    model_config = {"protected_namespaces": ()}


class STRIPOutput(ToolOutput):
    """Output from STRIP detection."""
    entropy_score: float = Field(..., description="Average entropy score across perturbations")
    is_backdoor: bool = Field(..., description="Whether a backdoor is detected")
    perturbed_samples: int = 0


# ── Synthetic MVP fallbacks (replace with real model loader in production) ──

def synthetic_predict_fn(model_path: str, num_classes: int) -> PredictFn:
    """
    Build a deterministic pseudo-model predictor from `model_path`.

    Production path: load a real model (e.g. via PyTorch) and return a predictor.
    """
    seed = int(hashlib.sha256(model_path.encode("utf-8")).hexdigest()[:8], 16)

    def predict(batch: Sequence[Sequence[float]]) -> list[list[float]]:
        outputs: list[list[float]] = []
        for sample in batch:
            logits = []
            for c in range(num_classes):
                acc = 0.0
                for i, x in enumerate(sample):
                    acc += math.sin((seed + c * 31 + i * 17) % 1009) * x
                logits.append(acc)
            outputs.append(softmax(logits))
        return outputs

    return predict


def synthetic_samples(count: int, dim: int, seed: int = 1234) -> list[list[float]]:
    """Generate deterministic clean sample vectors."""
    rng = random.Random(seed)
    return [[rng.uniform(0.0, 1.0) for _ in range(dim)] for _ in range(count)]


# ── Tool ──────────────────────────────────────────────────────────────

class STRIPTool(ToolAdapter):
    """
    Real STRIP detector wrapped as a Tool.

    The algorithm (`STRIPDetector`) is model-agnostic; the tool supplies a
    predictor (injected or synthetic) and clean samples.
    """

    manifest = ToolContract(
        name="strip_detect_real",
        description=(
            "Real STRIP detection: perturbs input samples and measures prediction "
            "entropy. Anomalously low/stable entropy under perturbation indicates a "
            "backdoor trigger. Wraps the STRIPDetector algorithm via ToolAdapter."
        ),
        input_schema=STRIPInput,
        output_schema=STRIPOutput,
        timeout_ms=60000,
        requires_gpu=False,
        retry_count=2,
        tags=["detection", "fast_scan", "deep_scan", "forensic_scan"],
    )

    def __init__(
        self,
        predict_fn: Optional[PredictFn] = None,
        samples: Optional[Sequence[Sequence[float]]] = None,
        num_classes: int = 10,
    ):
        self._predict_fn = predict_fn
        self._samples = samples
        self._num_classes = num_classes

    def _get_predict_fn(self, model_path: str) -> PredictFn:
        if self._predict_fn is not None:
            return self._predict_fn
        return synthetic_predict_fn(model_path, self._num_classes)

    def _get_samples(self) -> list[list[float]]:
        if self._samples is not None:
            return [list(s) for s in self._samples]
        return synthetic_samples(count=10, dim=8)

    async def run(self, input_data: STRIPInput) -> STRIPOutput:
        predict = self._get_predict_fn(input_data.model_path)
        samples = self._get_samples()

        detector = STRIPDetector(predict)
        result = detector.run(
            samples=samples,
            num_samples=input_data.num_samples,
            perturbation_strength=input_data.perturbation_strength,
        )

        drop = result.entropy_drop
        if result.is_backdoor:
            confidence = min(1.0, drop)
            risk = RiskLevel.HIGH if drop > 2 * result.threshold else RiskLevel.MEDIUM
        else:
            confidence = max(0.0, 1.0 - drop)
            risk = RiskLevel.LOW

        logger.info(
            f"[strip_detect_real] entropy_drop={result.entropy_drop}, "
            f"backdoor={result.is_backdoor}, risk={risk.value}",
            extra={"trace_id": input_data.trace_id},
        )

        return STRIPOutput(
            trace_id=input_data.trace_id,
            tool_name="strip_detect_real",
            success=True,
            data={
                "mean_entropy": result.mean_entropy,
                "clean_entropy": result.clean_entropy,
                "min_entropy": result.min_entropy,
                "entropy_drop": result.entropy_drop,
                "entropy_variance": result.entropy_variance,
                "is_backdoor": result.is_backdoor,
                "threshold": result.threshold,
                "perturbation_strength": input_data.perturbation_strength,
            },
            entropy_score=result.mean_entropy,
            is_backdoor=result.is_backdoor,
            perturbed_samples=result.perturbed_samples,
            confidence_score=round(confidence, 3),
            risk_level=risk,
            artifact=[
                Artifact(
                    name="entropy_distribution",
                    type="distribution",
                    format="json",
                    metadata={
                        "mean_entropy": result.mean_entropy,
                        "entropy_variance": result.entropy_variance,
                        "threshold": result.threshold,
                    },
                ),
                Artifact(
                    name="perturbation_stats",
                    type="stats",
                    format="json",
                    metadata={
                        "num_perturbations": result.num_perturbations,
                        "perturbed_samples": result.perturbed_samples,
                    },
                ),
            ],
        )
