"""Tests for M1: Artifact model, ToolAdapter, and real STRIP tool."""

import math

import pytest
from pydantic import BaseModel, Field

from app.tools.schemas import Artifact, ToolInput, ToolOutput, RiskLevel
from app.tools.contract import ToolContract, ToolManifest
from app.tools.adapter import ToolAdapter
from app.tools.base import BaseTool
from app.tools.registry import ToolRegistry
from app.agents.tool_router import ToolRouter, ToolCallRequest
from app.security.strip_detector import (
    STRIPDetector,
    softmax,
    entropy,
    perturb,
)
from app.tools.strip_tool import STRIPTool


# ── Artifact model ────────────────────────────────────────────────────

def test_artifact_model_fields():
    artifact = Artifact(
        name="entropy_distribution",
        type="distribution",
        path="/tmp/e.npy",
        hash="sha256:abc",
        size_bytes=2048,
        format="npy",
        metadata={"threshold": 0.5},
    )
    assert artifact.name == "entropy_distribution"
    assert artifact.type == "distribution"
    assert artifact.format == "npy"


def test_artifact_optional_fields_default():
    artifact = Artifact(name="stats", type="stats")
    assert artifact.path is None
    assert artifact.hash is None
    assert artifact.size_bytes is None
    assert artifact.metadata == {}


def test_tool_output_accepts_artifact_list():
    out = ToolOutput(
        trace_id="trc-1",
        tool_name="t",
        success=True,
        artifact=[Artifact(name="a", type="x")],
    )
    assert isinstance(out.artifact, list)
    assert out.artifact[0].name == "a"


def test_tool_output_rejects_dict_artifact():
    with pytest.raises(Exception):
        ToolOutput(trace_id="trc-1", tool_name="t", success=True, artifact={"a": 1})


# ── ToolManifest alias ────────────────────────────────────────────────

def test_tool_manifest_is_contract_alias():
    assert ToolManifest is ToolContract


# ── ToolAdapter ───────────────────────────────────────────────────────

class _AdderInput(ToolInput):
    a: int
    b: int


class _AdderOutput(ToolOutput):
    result: int


class _AdderTool(ToolAdapter):
    manifest = ToolContract(
        name="adder",
        description="adds two ints",
        input_schema=_AdderInput,
        output_schema=_AdderOutput,
    )

    async def run(self, input_data: _AdderInput) -> _AdderOutput:
        return _AdderOutput(
            trace_id=input_data.trace_id,
            tool_name="adder",
            success=True,
            result=input_data.a + input_data.b,
        )


class _BrokenTool(ToolAdapter):
    manifest = ToolContract(
        name="broken",
        description="always fails",
        input_schema=_AdderInput,
        output_schema=_AdderOutput,
    )

    async def run(self, input_data: _AdderInput) -> _AdderOutput:
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_adapter_is_a_base_tool():
    assert isinstance(_AdderTool(), BaseTool)


@pytest.mark.asyncio
async def test_adapter_execute_sets_duration():
    tool = _AdderTool()
    out = await tool.execute(_AdderInput(trace_id="t", a=1, b=2))
    assert out.result == 3
    assert out.duration_ms >= 0.0


@pytest.mark.asyncio
async def test_adapter_normalizes_errors():
    from app.core.exceptions import ToolExecutionError

    tool = _BrokenTool()
    with pytest.raises(ToolExecutionError):
        await tool.execute(_AdderInput(trace_id="t", a=1, b=2))


@pytest.mark.asyncio
async def test_adapter_registers_and_routes():
    registry = ToolRegistry()
    registry.register(_AdderTool())
    router = ToolRouter(registry)
    out = await router.route(ToolCallRequest(tool_name="adder", input_data={"trace_id": "t", "a": 3, "b": 4}))
    assert out.result == 7


# ── STRIP algorithm ───────────────────────────────────────────────────

def test_softmax_sums_to_one():
    probs = softmax([1.0, 2.0, 3.0])
    assert abs(sum(probs) - 1.0) < 1e-6


def test_entropy_single_class_is_zero():
    assert entropy([1.0]) == 0.0


def test_entropy_uniform_two_classes():
    assert abs(entropy([0.5, 0.5]) - math.log(2)) < 1e-6


def test_perturb_adds_scaled_pattern():
    assert perturb([1.0, 2.0], [0.5, 0.5], 0.1) == [1.05, 2.05]


def _constant_predictor(dist):
    def predict(batch):
        return [list(dist) for _ in batch]
    return predict


def test_strip_detects_confident_backdoor():
    # Predictor always returns a confident (low entropy) distribution.
    detector = STRIPDetector(_constant_predictor([1.0, 0.0]))
    result = detector.run(samples=[[0.1, 0.2]], num_samples=20, seed=42)
    assert result.mean_entropy < 0.5
    assert result.is_backdoor is True


def test_strip_clean_for_uncertain_predictor():
    # Predictor always returns a uniform (high entropy) distribution.
    detector = STRIPDetector(_constant_predictor([0.5, 0.5]))
    result = detector.run(samples=[[0.1, 0.2]], num_samples=20, seed=42)
    assert result.mean_entropy > 0.5
    assert result.is_backdoor is False


def test_strip_deterministic_with_seed():
    detector = STRIPDetector(_constant_predictor([0.3, 0.7]))
    r1 = detector.run(samples=[[0.1, 0.2]], num_samples=20, seed=7)
    r2 = detector.run(samples=[[0.1, 0.2]], num_samples=20, seed=7)
    assert r1.mean_entropy == r2.mean_entropy
    assert r1.is_backdoor == r2.is_backdoor


# ── STRIPTool (Adapter wrapping real algorithm) ───────────────────────

@pytest.mark.asyncio
async def test_strip_tool_routes_successfully():
    registry = ToolRegistry()
    registry.register(STRIPTool())
    router = ToolRouter(registry)

    out = await router.route(
        ToolCallRequest(
            tool_name="strip_detect_real",
            input_data={"trace_id": "trc-1", "model_path": "model.h5", "num_samples": 40},
        )
    )
    assert out.success is True
    assert out.tool_name == "strip_detect_real"
    assert 0.0 <= out.confidence_score <= 1.0
    assert out.risk_level in ("LOW", "MEDIUM", "HIGH")
    assert isinstance(out.artifact, list)
    assert all(isinstance(a, Artifact) for a in out.artifact)
    assert any(a.name == "entropy_distribution" for a in out.artifact)


@pytest.mark.asyncio
async def test_strip_tool_respects_injected_predictor():
    registry = ToolRegistry()
    registry.register(STRIPTool(predict_fn=_constant_predictor([1.0, 0.0]), samples=[[0.1, 0.2]]))
    router = ToolRouter(registry)

    out = await router.route(
        ToolCallRequest(
            tool_name="strip_detect_real",
            input_data={"trace_id": "trc-2", "model_path": "m.h5", "num_samples": 20},
        )
    )
    assert out.is_backdoor is True
