"""Tests for the real Neural Cleanse detector and its Tool adapter."""

import pytest

from app.tools.schemas import Artifact
from app.tools.registry import ToolRegistry
from app.agents.tool_router import ToolRouter, ToolCallRequest


# ── Pure helper functions ──────────────────────────────────────────────

def test_l1_norm():
    from app.security.neural_cleanse import l1_norm

    assert l1_norm([3.0, -4.0, 0.0]) == pytest.approx(7.0)
    assert l1_norm([]) == 0.0


def test_modified_z_scores_are_centered():
    from app.security.neural_cleanse import modified_z_scores

    zs = modified_z_scores([10.0, 10.0, 10.0, 11.0, 11.0, 11.0])
    assert all(abs(z) < 2.0 for z in zs)


def test_detect_anomalies_flags_small_norm():
    from app.security.neural_cleanse import detect_anomalies

    # A backdoored class needs a much smaller trigger (norm) than clean classes.
    norms = [10.0] * 7 + [1.0]
    anomaly_index, suspicious, is_backdoor = detect_anomalies(norms, threshold=2.0)

    assert is_backdoor is True
    assert suspicious == [7]
    assert anomaly_index > 2.0


def test_detect_anomalies_clean_when_no_outlier():
    from app.security.neural_cleanse import detect_anomalies

    norms = [10.0, 10.0, 10.0, 11.0, 11.0, 11.0, 10.0, 10.0]
    anomaly_index, suspicious, is_backdoor = detect_anomalies(norms, threshold=2.0)

    assert is_backdoor is False
    assert suspicious == []


# ── Detector ───────────────────────────────────────────────────────────

def test_nc_detector_requires_samples():
    from app.security.neural_cleanse import NeuralCleanseDetector

    detector = NeuralCleanseDetector(lambda batch: [[1.0, 0.0] for _ in batch])
    with pytest.raises(ValueError):
        detector.run(samples=[], num_classes=2, optimization_steps=10)


def test_nc_detector_is_deterministic():
    from app.security.neural_cleanse import NeuralCleanseDetector

    def predict(batch):
        return [[0.2, 0.8] for _ in batch]

    samples = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
    detector = NeuralCleanseDetector(predict)

    r1 = detector.run(samples=samples, num_classes=2, optimization_steps=20)
    r2 = detector.run(samples=samples, num_classes=2, optimization_steps=20)

    assert r1.trigger_norms == r2.trigger_norms
    assert r1.is_backdoor == r2.is_backdoor
    assert len(r1.trigger_norms) == 2


def test_recover_trigger_flips_with_minimal_perturbation():
    import math

    from app.security.neural_cleanse import NeuralCleanseDetector, l1_norm

    def logistic(batch):
        out = []
        for s in batch:
            p0 = 1.0 / (1.0 + math.exp(-10.0 * s[0]))
            out.append([p0, 1.0 - p0])
        return out

    detector = NeuralCleanseDetector(logistic)
    samples = [[-1.0, 0.0]]  # currently class 1 (x0 < 0)

    trigger = detector.recover_trigger(samples, 0, steps=40, lr=0.1)

    assert detector._mean_class_prob(samples, 0, trigger) >= 0.9
    assert 0.0 < l1_norm(trigger) < 10.0


# ── Tool adapter ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_nc_tool_routes_and_returns_standard_output():
    from app.tools.neural_cleanse_tool import NeuralCleanseTool

    registry = ToolRegistry()
    registry.register(NeuralCleanseTool())
    router = ToolRouter(registry)

    out = await router.route(
        ToolCallRequest(
            tool_name="neural_cleanse_real",
            input_data={
                "trace_id": "trc-nc",
                "model_path": "model.h5",
                "num_classes": 4,
                "optimization_steps": 20,
            },
        )
    )

    assert out.success is True
    assert out.tool_name == "neural_cleanse_real"
    assert 0.0 <= out.confidence_score <= 1.0
    assert out.risk_level in ("LOW", "MEDIUM", "HIGH")
    assert isinstance(out.artifact, list)
    assert all(isinstance(a, Artifact) for a in out.artifact)
    assert any(a.name == "trigger_patterns" for a in out.artifact)


@pytest.mark.asyncio
async def test_nc_tool_respects_injected_predictor():
    from app.tools.neural_cleanse_tool import NeuralCleanseTool
    from app.security.neural_cleanse import NeuralCleanseDetector

    def predict(batch):
        return [[0.1, 0.9] for _ in batch]

    samples = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
    registry = ToolRegistry()
    registry.register(NeuralCleanseTool(predict_fn=predict, samples=samples))
    router = ToolRouter(registry)

    out = await router.route(
        ToolCallRequest(
            tool_name="neural_cleanse_real",
            input_data={
                "trace_id": "trc-nc",
                "model_path": "m.h5",
                "num_classes": 2,
                "optimization_steps": 20,
            },
        )
    )

    expected = NeuralCleanseDetector(predict).run(
        samples=samples, num_classes=2, optimization_steps=20
    )
    assert out.is_backdoor == expected.is_backdoor
    assert out.anomaly_index == pytest.approx(expected.anomaly_index)
