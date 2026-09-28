"""
Activation Clustering Detector — real algorithm implementation (pure Python, model-agnostic).

Activation Clustering extracts intermediate-layer activations for clean and
potentially backdoored samples, then clusters them. A backdoored model produces
a small, tight, well-separated cluster of poisoned activations — that small
cluster is the backdoor evidence.

Like STRIP and Neural Cleanse, this module operates on an injectable
`activate_fn(batch) -> list[vectors]` callable and requires no ML framework
(K-Means and silhouette are implemented in pure Python). The ToolAdapter in
`app/tools/activation_clustering_tool.py` wraps this into a registry-ready Tool.
"""

import math
import random
import statistics
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

# Maps a batch of feature vectors to a batch of intermediate activation vectors.
ActivateFn = Callable[[Sequence[Sequence[float]]], Sequence[Sequence[float]]]


def euclidean(a: Sequence[float], b: Sequence[float]) -> float:
    """Euclidean distance between two vectors."""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def kmeans(
    points: Sequence[Sequence[float]],
    k: int,
    seed: Optional[int] = None,
    max_iter: int = 100,
) -> tuple[list[int], list[list[float]]]:
    """
    Lloyd's K-Means clustering (pure Python, deterministic with a seed).

    Returns:
        (assignments, centroids) where assignments[i] is the cluster of points[i].
    """
    pts = [list(p) for p in points]
    if not pts:
        return [], []
    if k <= 0:
        raise ValueError("k must be positive")

    rng = random.Random(seed)
    n = len(pts)
    dim = len(pts[0])
    k = min(k, n)

    # Initialize centroids by sampling k distinct points at random.
    centroids = [list(p) for p in rng.sample(pts, k)]

    for _ in range(max_iter):
        # Assign each point to the nearest centroid.
        assignments: list[int] = []
        for p in pts:
            dists = [euclidean(p, c) for c in centroids]
            assignments.append(min(range(k), key=lambda i: dists[i]))

        # Recompute centroids as the mean of their assigned points.
        new_centroids: list[list[float]] = []
        for c in range(k):
            members = [pts[i] for i in range(n) if assignments[i] == c]
            if not members:
                new_centroids.append(centroids[c])
                continue
            mean = [sum(v[j] for v in members) / len(members) for j in range(dim)]
            new_centroids.append(mean)

        if new_centroids == centroids:
            break
        centroids = new_centroids

    # Final assignment with the converged centroids.
    assignments = []
    for p in pts:
        dists = [euclidean(p, c) for c in centroids]
        assignments.append(min(range(k), key=lambda i: dists[i]))

    return assignments, centroids


def silhouette_score(points: Sequence[Sequence[float]], assignments: Sequence[int]) -> float:
    """
    Mean silhouette coefficient over all points (range roughly -1 to 1).

    Points that are alone in their cluster (or when only one cluster exists)
    contribute 0.0.
    """
    pts = [list(p) for p in points]
    n = len(pts)
    if n == 0:
        return 0.0

    labels = list(assignments)
    clusters: dict[int, list[int]] = {}
    for i, label in enumerate(labels):
        clusters.setdefault(label, []).append(i)

    if len(clusters) <= 1:
        return 0.0

    def _mean_intra(i: int, label: int) -> float:
        members = clusters[label]
        if len(members) <= 1:
            return 0.0
        dists = [euclidean(pts[i], pts[j]) for j in members if j != i]
        return sum(dists) / len(dists)

    scores: list[float] = []
    for i in range(n):
        label = labels[i]
        a = _mean_intra(i, label)

        # Nearest other cluster distance b.
        b = float("inf")
        for other, members in clusters.items():
            if other == label:
                continue
            d = sum(euclidean(pts[i], pts[j]) for j in members) / len(members)
            b = min(b, d)

        if a == 0.0 and b == float("inf"):
            scores.append(0.0)
        else:
            scores.append((b - a) / max(a, b))

    return sum(scores) / len(scores)


def detect_anomalous_clusters(
    assignments: Sequence[int], n_clusters: int, min_ratio: float = 0.5
) -> list[int]:
    """
    Flag clusters whose size is well below the mean cluster size.

    A backdoored model yields a small, tight cluster of poisoned activations, so
    an undersized cluster is treated as backdoor evidence.
    """
    if n_clusters <= 0:
        return []
    counts = [0] * n_clusters
    for a in assignments:
        if 0 <= a < n_clusters:
            counts[a] += 1

    if not counts or sum(counts) == 0:
        return []

    mean = sum(counts) / n_clusters
    return [c for c in range(n_clusters) if counts[c] < min_ratio * mean]


def _detect_anomalous_strict(
    points: Sequence[Sequence[float]],
    assignments: Sequence[int],
    centroids: Sequence[Sequence[float]],
) -> list[int]:
    """Flag clusters that are small, tight, and well-separated (backdoor signature)."""
    n = len(assignments)
    k = len(centroids)
    if n == 0 or k <= 1:
        return []

    counts = [0] * k
    intra_sum = [0.0] * k
    for i, c in enumerate(assignments):
        if 0 <= c < k:
            counts[c] += 1
            intra_sum[c] += euclidean(points[i], centroids[c])

    intra = [intra_sum[c] / counts[c] if counts[c] else 0.0 for c in range(k)]
    mean_size = n / k

    nonempty_intra = [v for v in intra if v > 0]
    med_intra = statistics.median(nonempty_intra) if nonempty_intra else 0.0
    if med_intra <= 0.0:
        med_intra = 1.0

    seps = [
        min((euclidean(centroids[c], centroids[o]) for o in range(k) if o != c), default=0.0)
        for c in range(k)
    ]
    nonzero_seps = [s for s in seps if s > 0]
    med_sep = statistics.median(nonzero_seps) if nonzero_seps else 0.0

    anomalous = []
    for c in range(k):
        if counts[c] == 0:
            continue
        small = counts[c] < 0.6 * mean_size
        tight = intra[c] < 0.8 * med_intra
        separated = seps[c] > 1.2 * med_sep if med_sep > 0 else True
        if small and tight and separated:
            anomalous.append(c)
    return anomalous


@dataclass
class ActivationClusteringResult:
    """Outcome of an Activation Clustering detection run."""

    silhouette_score: float
    n_anomalous_clusters: int
    anomalous_clusters: list[int] = field(default_factory=list)
    is_backdoor: bool = False
    n_clusters: int = 0


class ActivationClusteringDetector:
    """
    Real Activation Clustering detection algorithm over an injectable activation
    extractor.

    Usage:
        detector = ActivationClusteringDetector(activate_fn)
        result = detector.run(samples, n_clusters=3)
    """

    def __init__(self, activate_fn: ActivateFn):
        if activate_fn is None:
            raise ValueError("activate_fn is required")
        self.activate = activate_fn

    def run(
        self,
        samples: Sequence[Sequence[float]],
        n_clusters: int = 3,
        seed: Optional[int] = None,
    ) -> ActivationClusteringResult:
        """
        Run Activation Clustering detection.

        Args:
            samples: Clean + potentially poisoned sample feature vectors.
            n_clusters: Number of clusters for K-Means.
            seed: Optional RNG seed for deterministic clustering.

        Returns:
            ActivationClusteringResult with silhouette, anomalous clusters, and
            the backdoor decision.
        """
        samples = list(samples)
        if not samples:
            raise ValueError("at least one sample is required")

        # Deterministic default seed for reproducibility (NFR-2).
        if seed is None:
            seed = 0

        activations = [list(v) for v in self.activate(samples)]
        assignments, centroids = kmeans(activations, k=n_clusters, seed=seed)
        silhouette = silhouette_score(activations, assignments)
        anomalous = _detect_anomalous_strict(activations, assignments, centroids)

        return ActivationClusteringResult(
            silhouette_score=round(silhouette, 4),
            n_anomalous_clusters=len(anomalous),
            anomalous_clusters=anomalous,
            is_backdoor=len(anomalous) > 0,
            n_clusters=n_clusters,
        )
