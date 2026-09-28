"""
NeuralCleanseTool: real Neural Cleanse detection exposed as a Tool via ToolAdapter.

Wraps the standalone NeuralCleanseDetector algorithm (app/security/neural_cleanse.py)
into a registry-ready Tool, mirroring the STRIPTool adapter. The predictor and
clean samples are injectable so the algorithm can be tested deterministically;
without injection a synthetic deterministic predictor is used as the MVP fallback.
"""

import hashlib
import math
from typing import Callable, Optional, Sequence

from pydantic import BaseModel, Field

from app.tools.adapter import ToolAdapter
from app.tools.contract import ToolContract
from app.tools.schemas import ToolInput, ToolOutput, RiskLevel, Artifact
from app.security.neural_cleanse import NeuralCleanseDetector, PredictFn
from app.security.strip_detector import softmax
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Contract-specific I/O schemas ──────────────────────────────────────

class NeuralCleanseInput(ToolInput):
    """Input for Neural Cleanse detection."""
    model_path: str = Field(..., description="Path to the model file")
    num_classes: int = Field(default=10, description="Number of output classes")
    optimization_steps: int = Field(default=100, description="Trigger recovery iterations")

    model_config = {"protected_namespaces": ()}


class NeuralCleanseOutput(ToolOutput):
    """Output from Neural Cleanse detection."""
    anomaly_index: float = Field(..., description="Maximum absolute modified z-score")
    is_backdoor: bool = Field(..., description="Whether a backdoor was detected")
    suspicious_classes: list[int] = Field(default_factory=list)


# ── Synthetic MVP fallback (replace with real model loader in production) ──

def synthetic_predict_fn(model_path: str, num_classes: int) -> PredictFn:
    """Build a deterministic pseudo-model predictor from `model_path`."""
    seed = int(hashlib.sha256(model_path.encode("utf-8")).hexdigest()[:8], 16)

    def predict(batch: Sequence[Sequence[float]]) -> list[list[float]]:
        outputs: list[list[float]] = []
        for sample in batch:
            logits = []
            for c in range(num_classes):
                acc = 0.0
                for i, x in enumerate(sample):
                    acc += math.sin((seed + c * 29 + i * 13) % 997) * x
                logits.append(acc)
            outputs.append(softmax(logits))
        return outputs

    return predict


# ── Tool ──────────────────────────────────────────────────────────────

class NeuralCleanseTool(ToolAdapter):
    """Real Neural Cleanse detector wrapped as a Tool."""

    manifest = ToolContract(
        name="neural_cleanse_real",
        description=(
            "Real Neural Cleanse detection: reverse-engineers backdoor triggers "
            "for each class and applies MAD outlier detection on trigger L1 norms. "
            "An anomalously small trigger indicates a backdoored class. Wraps the "
            "NeuralCleanseDetector algorithm via ToolAdapter."
        ),
        input_schema=NeuralCleanseInput,
        output_schema=NeuralCleanseOutput,
        timeout_ms=120000,
        requires_gpu=False,
        retry_count=1,
        tags=["detection", "deep_scan", "forensic_scan"],
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
        from app.tools.strip_tool import synthetic_samples

        return synthetic_samples(count=10, dim=8)

    async def run(self, input_data: NeuralCleanseInput) -> NeuralCleanseOutput:
        predict = self._get_predict_fn(input_data.model_path)
        samples = self._get_samples()

        detector = NeuralCleanseDetector(predict)
        result = detector.run(
            samples=samples,
            num_classes=input_data.num_classes,
            optimization_steps=input_data.optimization_steps,
        )

        if result.is_backdoor:
            confidence = min(1.0, result.anomaly_index / 3.0)
            risk = (
                RiskLevel.HIGH if result.anomaly_index > 2.5 else RiskLevel.MEDIUM
            )
        else:
            confidence = max(0.01, 1.0 - result.anomaly_index / 3.0)
            risk = RiskLevel.LOW

        logger.info(
            f"[neural_cleanse_real] anomaly_index={result.anomaly_index}, "
            f"backdoor={result.is_backdoor}, risk={risk.value}",
            extra={"trace_id": input_data.trace_id},
        )

        return NeuralCleanseOutput(
            trace_id=input_data.trace_id,
            tool_name="neural_cleanse_real",
            success=True,
            data={
                "anomaly_index": result.anomaly_index,
                "is_backdoor": result.is_backdoor,
                "suspicious_classes": result.suspicious_classes,
                "trigger_norms": result.trigger_norms,
                "threshold": result.anomaly_threshold,
                "classes_tested": result.num_classes,
            },
            anomaly_index=result.anomaly_index,
            is_backdoor=result.is_backdoor,
            suspicious_classes=result.suspicious_classes,
            confidence_score=round(confidence, 3),
            risk_level=risk,
            artifact=[
                Artifact(
                    name="trigger_patterns",
                    type="matrix",
                    format="json",
                    metadata={
                        "trigger_norms": result.trigger_norms,
                        "anomaly_threshold": result.anomaly_threshold,
                    },
                ),
                Artifact(
                    name="mad_stats",
                    type="stats",
                    format="json",
                    metadata={
                        "anomaly_index": result.anomaly_index,
                        "suspicious_classes": result.suspicious_classes,
                    },
                ),
            ],
        )
