"""Tests for the real Activation Clustering detector and its Tool adapter."""

import pytest

from app.tools.schemas import Artifact
from app.tools.registry import ToolRegistry
from app.agents.tool_router import ToolRouter, ToolCallRequest


# ── Pure helper functions ──────────────────────────────────────────────

def test_euclidean():
    from app.security.activation_clustering import euclidean

    assert euclidean([0.0, 0.0], [3.0, 4.0]) == pytest.approx(5.0)


def test_kmeans_partitions_well_separated_points():
    from app.security.activation_clustering import kmeans

    points = [
        [0.0, 0.0], [0.1, 0.0], [0.0, 0.1],
        [10.0, 10.0], [10.1, 10.0], [10.0, 10.1],
    ]
    assignments, centroids = kmeans(points, k=2, seed=42)
    assert len(assignments) == len(points)
    assert len(centroids) == 2
    assert len(set(assignments)) == 2
    assert assignments[0] != assignments[3]


def test_silhouette_in_valid_range():
    from app.security.activation_clustering import kmeans, silhouette_score

    points = [[0.0, 0.0], [0.1, 0.0], [10.0, 10.0], [10.1, 10.0]]
    assignments, _ = kmeans(points, k=2, seed=42)
    score = silhouette_score(points, assignments)
    assert -1.0 <= score <= 1.0


def test_detect_anomalous_clusters_flags_small_cluster():
    from app.security.activation_clustering import detect_anomalous_clusters

    assignments = [0, 0, 0, 0, 0, 1, 1, 1, 1, 2]
    anomalous = detect_anomalous_clusters(assignments, n_clusters=3)
    assert anomalous == [2]


def test_detect_anomalous_clusters_clean_when_balanced():
    from app.security.activation_clustering import detect_anomalous_clusters

    assignments = [0, 0, 0, 1, 1, 1, 2, 2, 2]
    anomalous = detect_anomalous_clusters(assignments, n_clusters=3)
    assert anomalous == []


def test_detect_anomalous_strict_flags_tight_isolated_cluster():
    from app.security.activation_clustering import _detect_anomalous_strict

    points = (
        [[100.0, 100.0]]
        + [[0.0, 0.0], [0.1, 0.0], [0.0, 0.1], [0.1, 0.1], [0.0, 0.2]]
        + [[10.0, 0.0], [10.1, 0.0], [10.0, 0.1], [10.1, 0.1], [10.0, 0.2]]
    )
    assignments = [0] + [1] * 5 + [2] * 5
    centroids = [[100.0, 100.0], [0.04, 0.08], [10.04, 0.08]]
    assert _detect_anomalous_strict(points, assignments, centroids) == [0]


def test_detect_anomalous_strict_clean_when_balanced():
    from app.security.activation_clustering import _detect_anomalous_strict

    points = [[0, 0], [0.1, 0], [0, 0.1], [0.1, 0.1], [10, 10], [10.1, 10], [10, 10.1], [10.1, 10.1]]
    assignments = [0, 0, 0, 0, 1, 1, 1, 1]
    centroids = [[0.05, 0.05], [10.05, 10.05]]
    assert _detect_anomalous_strict(points, assignments, centroids) == []


# ── Detector ───────────────────────────────────────────────────────────

def test_ac_detector_requires_samples():
    from app.security.activation_clustering import ActivationClusteringDetector

    detector = ActivationClusteringDetector(lambda batch: [list(p) for p in batch])
    with pytest.raises(ValueError):
        detector.run(samples=[], n_clusters=3)


def test_ac_detector_is_deterministic():
    from app.security.activation_clustering import ActivationClusteringDetector

    samples = [[0.0, 0.0], [0.1, 0.0], [10.0, 10.0], [10.1, 10.0], [5.0, 5.0], [5.1, 5.0]]
    detector = ActivationClusteringDetector(lambda batch: [list(p) for p in batch])

    r1 = detector.run(samples=samples, n_clusters=2, seed=7)
    r2 = detector.run(samples=samples, n_clusters=2, seed=7)

    assert r1.silhouette_score == r2.silhouette_score
    assert r1.n_anomalous_clusters == r2.n_anomalous_clusters
    assert r1.is_backdoor == r2.is_backdoor


# ── Tool adapter ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ac_tool_routes_and_returns_standard_output():
    from app.tools.activation_clustering_tool import ActivationClusteringTool

    registry = ToolRegistry()
    registry.register(ActivationClusteringTool())
    router = ToolRouter(registry)

    out = await router.route(
        ToolCallRequest(
            tool_name="activation_clustering_real",
            input_data={
                "trace_id": "trc-ac",
                "model_path": "model.h5",
                "n_clusters": 3,
                "samples_per_class": 10,
            },
        )
    )

    assert out.success is True
    assert out.tool_name == "activation_clustering_real"
    assert 0.0 <= out.confidence_score <= 1.0
    assert out.risk_level in ("LOW", "MEDIUM", "HIGH")
    assert isinstance(out.artifact, list)
    assert all(isinstance(a, Artifact) for a in out.artifact)
    assert any(a.name == "activation_map" for a in out.artifact)


@pytest.mark.asyncio
async def test_ac_tool_respects_injected_activations():
    from app.tools.activation_clustering_tool import ActivationClusteringTool
    from app.security.activation_clustering import ActivationClusteringDetector

    samples = [[0.0, 0.0], [0.1, 0.0], [10.0, 10.0], [10.1, 10.0], [5.0, 5.0], [5.1, 5.0]]
    activate_fn = lambda batch: [list(p) for p in batch]  # noqa: E731

    registry = ToolRegistry()
    registry.register(ActivationClusteringTool(activate_fn=activate_fn, samples=samples))
    router = ToolRouter(registry)

    out = await router.route(
        ToolCallRequest(
            tool_name="activation_clustering_real",
            input_data={
                "trace_id": "trc-ac",
                "model_path": "m.h5",
                "n_clusters": 2,
            },
        )
    )

    expected = ActivationClusteringDetector(activate_fn).run(samples=samples, n_clusters=2)
    assert out.is_backdoor == expected.is_backdoor
    assert out.silhouette_score == pytest.approx(expected.silhouette_score)
