"""
Neural Cleanse Detector — real algorithm implementation (pure Python, model-agnostic).

Neural Cleanse reverse-engineers potential backdoor triggers: for each class it
optimizes a small perturbation ("trigger") that flips predictions toward that
class, then applies MAD (Median Absolute Deviation) outlier detection on the L1
norms of the recovered triggers. A backdoored class is characterized by an
anomalously *small* trigger — the attacker's injected patch needs little
perturbation to hijack the model.

Like STRIP, this module operates on an injectable `predict_fn(batch) -> list[prob_dist]`
callable and requires no ML framework. The ToolAdapter in
`app/tools/neural_cleanse_tool.py` wraps this into a registry-ready Tool.
"""

import statistics
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

# A predictor maps a batch of feature vectors to a batch of probability
# distributions (each summing to 1.0). Reused from the STRIP module.
PredictFn = Callable[[Sequence[Sequence[float]]], Sequence[Sequence[float]]]


def l1_norm(vector: Sequence[float]) -> float:
    """Sum of absolute values (L1 norm) of a vector."""
    return sum(abs(x) for x in vector)


def modified_z_scores(values: Sequence[float]) -> list[float]:
    """
    Robust modified z-scores (MAD-based) for outlier detection.

    Falls back to the standard-deviation scale when MAD is degenerate (e.g. more
    than half the values are identical), so the statistic stays well-defined.
    """
    vals = list(values)
    if not vals:
        return []

    median = statistics.median(vals)
    mad = statistics.median([abs(v - median) for v in vals])

    if mad > 0.0:
        scale = mad / 0.6745
        return [0.6745 * (v - median) / mad for v in vals]

    # Degenerate MAD: fall back to standard deviation as the dispersion scale.
    mean = sum(vals) / len(vals)
    variance = sum((v - mean) ** 2 for v in vals) / len(vals)
    std = variance ** 0.5
    if std == 0.0:
        return [0.0] * len(vals)
    return [(v - mean) / std for v in vals]


def detect_anomalies(
    norms: Sequence[float], threshold: float = 2.0
) -> tuple[float, list[int], bool]:
    """
    Flag classes whose trigger norm is anomalously small (backdoor candidates).

    Args:
        norms: L1 norms of recovered triggers, one per class.
        threshold: Modified z-score cutoff for an outlier.

    Returns:
        (anomaly_index, suspicious_classes, is_backdoor) where anomaly_index is
        the maximum absolute modified z-score across classes.
    """
    zs = modified_z_scores(norms)
    suspicious = [i for i, z in enumerate(zs) if z < -threshold]
    anomaly_index = max((abs(z) for z in zs), default=0.0)
    return anomaly_index, suspicious, bool(suspicious)


@dataclass
class NeuralCleanseResult:
    """Outcome of a Neural Cleanse detection run."""

    trigger_norms: list[float]
    anomaly_index: float
    anomaly_threshold: float
    suspicious_classes: list[int] = field(default_factory=list)
    is_backdoor: bool = False
    num_classes: int = 0
    optimization_steps: int = 0


class NeuralCleanseDetector:
    """
    Real Neural Cleanse detection algorithm over an injectable predictor.

    Usage:
        detector = NeuralCleanseDetector(predict_fn)
        result = detector.run(samples, num_classes=10, optimization_steps=100)
    """

    def __init__(self, predict_fn: PredictFn):
        if predict_fn is None:
            raise ValueError("predict_fn is required")
        self.predict = predict_fn

    def _mean_class_prob(
        self,
        samples: Sequence[Sequence[float]],
        target_class: int,
        delta: Sequence[float],
    ) -> float:
        """Mean predicted probability of `target_class` under perturbation `delta`."""
        total = 0.0
        count = 0
        for sample in samples:
            perturbed = [x + d for x, d in zip(sample, delta)]
            probs = self.predict([perturbed])[0]
            total += probs[target_class]
            count += 1
        return total / count if count else 0.0

    def recover_trigger(
        self,
        samples: Sequence[Sequence[float]],
        target_class: int,
        steps: int = 100,
        lr: float = 0.05,
    ) -> list[float]:
        """
        Reverse-engineer the *minimal* L1 perturbation that flips predictions
        toward `target_class`.

        Black-box approach (no gradients): estimate a steepest-ascent direction
        with finite differences, then binary-search the smallest scale along that
        direction that drives the target-class probability above 0.9. A backdoored
        class admits a much smaller trigger than a clean class, which is the MAD
        signature Neural Cleanse detects.
        """
        dim = len(samples[0])
        eps = max(lr, 1e-3)

        grad = [0.0] * dim
        for j in range(dim):
            up = [0.0] * dim
            down = [0.0] * dim
            up[j] = eps
            down[j] = -eps
            grad[j] = (
                self._mean_class_prob(samples, target_class, up)
                - self._mean_class_prob(samples, target_class, down)
            ) / (2 * eps)

        l1 = sum(abs(g) for g in grad) or 1.0
        direction = [g / l1 for g in grad]

        lo, hi = 0.0, 100.0
        for _ in range(max(10, steps)):
            mid = (lo + hi) / 2.0
            delta = [mid * d for d in direction]
            if self._mean_class_prob(samples, target_class, delta) >= 0.9:
                hi = mid
            else:
                lo = mid

        return [hi * d for d in direction]

    def run(
        self,
        samples: Sequence[Sequence[float]],
        num_classes: int = 10,
        optimization_steps: int = 100,
        lr: float = 0.05,
        threshold: float = 2.0,
        seed: Optional[int] = None,
    ) -> NeuralCleanseResult:
        """
        Run Neural Cleanse detection.

        Args:
            samples: Clean sample feature vectors used for trigger recovery.
            num_classes: Number of output classes to reverse-engineer.
            optimization_steps: Coordinate-ascent iterations per class.
            lr: Trigger perturbation step size.
            threshold: Modified z-score cutoff for flagging a class as backdoored.
            seed: Accepted for API parity with STRIP (recovery is deterministic).

        Returns:
            NeuralCleanseResult with per-class trigger norms and the decision.
        """
        samples = list(samples)
        if not samples:
            raise ValueError("at least one sample is required")

        trigger_norms: list[float] = []
        for cls in range(num_classes):
            trigger = self.recover_trigger(
                samples, cls, steps=optimization_steps, lr=lr
            )
            trigger_norms.append(round(l1_norm(trigger), 4))

        anomaly_index, suspicious, is_backdoor = detect_anomalies(trigger_norms, threshold)

        return NeuralCleanseResult(
            trigger_norms=trigger_norms,
            anomaly_index=round(anomaly_index, 4),
            anomaly_threshold=threshold,
            suspicious_classes=suspicious,
            is_backdoor=is_backdoor,
            num_classes=num_classes,
            optimization_steps=optimization_steps,
        )
