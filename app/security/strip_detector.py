"""
STRIP Detector — real algorithm implementation (pure Python, model-agnostic).

STRIP (STRong Intentional Perturbation) superimposes random perturbation
patterns onto clean samples and observes the resulting prediction entropy.

Rationale: a backdoored model is insensitive to perturbations for trigger
inputs (the trigger dominates the prediction), producing low/stable entropy,
while clean inputs produce higher, more variable entropy under perturbation.

This module implements the core algorithm independent of any ML framework by
operating on an injectable `predict_fn(batch) -> list[prob_dist]` callable.
The ToolAdapter in `app/tools/strip_tool.py` wraps this into a registry-ready
Tool.
"""

import math
import random
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

# A predictor maps a batch of feature vectors to a batch of probability
# distributions (each summing to 1.0).
PredictFn = Callable[[Sequence[Sequence[float]]], Sequence[Sequence[float]]]


def softmax(logits: Sequence[float]) -> list[float]:
    """Numerically stable softmax over a logit vector."""
    if not logits:
        return []
    max_logit = max(logits)
    exps = [math.exp(x - max_logit) for x in logits]
    total = sum(exps) or 1.0
    return [e / total for e in exps]


def entropy(probs: Sequence[float]) -> float:
    """Shannon entropy (nats) of a probability distribution."""
    return -sum(p * math.log(p) for p in probs if p > 0)


def perturb(sample: Sequence[float], pattern: Sequence[float], strength: float) -> list[float]:
    """Superimpose a perturbation pattern onto a sample: x' = x + strength * pattern."""
    return [x + strength * p for x, p in zip(sample, pattern)]


@dataclass
class STRIPResult:
    """Outcome of a STRIP detection run."""

    mean_entropy: float
    clean_entropy: float
    min_entropy: float
    entropy_drop: float
    entropy_variance: float
    is_backdoor: bool
    threshold: float
    num_perturbations: int
    perturbed_samples: int


class STRIPDetector:
    """
    Real STRIP detection algorithm over an injectable predictor.

    Usage:
        detector = STRIPDetector(predict_fn)
        result = detector.run(samples, num_samples=100, perturbation_strength=0.05)
    """

    def __init__(self, predict_fn: PredictFn):
        if predict_fn is None:
            raise ValueError("predict_fn is required")
        self.predict = predict_fn

    def run(
        self,
        samples: Sequence[Sequence[float]],
        num_samples: int = 100,
        perturbation_strength: float = 0.05,
        threshold: Optional[float] = None,
        seed: Optional[int] = None,
    ) -> STRIPResult:
        """
        Run STRIP detection.

        Args:
            samples: Clean sample feature vectors to perturb.
            num_samples: Total number of perturbations to generate (split across samples).
            perturbation_strength: Scale of the perturbation pattern.
            threshold: Entropy cutoff (nats). Below this, predictions are
                considered anomalously confident under perturbation. Defaults to
                a fixed 0.5 nats heuristic.
            seed: Optional RNG seed for reproducibility.

        Returns:
            STRIPResult with aggregated metrics and the backdoor decision.
        """
        samples = list(samples)
        if not samples:
            raise ValueError("at least one sample is required")

        if seed is not None:
            random.seed(seed)

        clean_entropy = sum(entropy(self.predict([s])[0]) for s in samples) / len(samples)

        per_round = max(1, num_samples // len(samples))
        total_perturbations = per_round * len(samples)

        perturbed_entropies: list[float] = []
        for sample in samples:
            dim = len(sample)
            for _ in range(per_round):
                pattern = [random.uniform(-1.0, 1.0) for _ in range(dim)]
                perturbed = perturb(sample, pattern, perturbation_strength)
                probs = self.predict([perturbed])[0]
                perturbed_entropies.append(entropy(probs))

        mean_entropy = sum(perturbed_entropies) / len(perturbed_entropies)
        min_entropy = min(perturbed_entropies)
        variance = sum((e - mean_entropy) ** 2 for e in perturbed_entropies) / len(perturbed_entropies)

        if threshold is None:
            # Backdoor signature: some perturbation makes the model anomalously
            # confident (entropy collapses). Flag when that drop is large enough.
            threshold = 0.3

        entropy_drop = clean_entropy - min_entropy
        is_backdoor = entropy_drop > threshold

        return STRIPResult(
            mean_entropy=round(mean_entropy, 4),
            clean_entropy=round(clean_entropy, 4),
            min_entropy=round(min_entropy, 4),
            entropy_drop=round(entropy_drop, 4),
            entropy_variance=round(variance, 4),
            is_backdoor=is_backdoor,
            threshold=threshold,
            num_perturbations=total_perturbations,
            perturbed_samples=len(samples),
        )
