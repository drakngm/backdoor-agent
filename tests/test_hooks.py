"""Tests for the Pre/Post Hook validation system (M2)."""

import pytest

from app.agents.hooks import (
    HookManager,
    HookResult,
    HookDecision,
    validate_input_hook,
    path_safety_hook,
    verify_output_hook,
    result_consistency_hook,
    register_default_hooks,
)
from app.tools.schemas import ToolOutput, RiskLevel, Artifact


def _output(**overrides) -> ToolOutput:
    base = dict(
        trace_id="trc-1",
        tool_name="strip_detect",
        success=True,
        confidence_score=0.8,
        risk_level=RiskLevel.MEDIUM,
        data={"is_backdoor": True},
    )
    base.update(overrides)
    return ToolOutput(**base)


# ── PreToolUse: validate_input_hook (输入校验) ──────────────────────

def test_validate_input_denies_missing_trace_id():
    result = validate_input_hook("strip_detect", {"model_path": "model.h5"})
    assert result.decision == HookDecision.DENY
    assert "trace_id" in result.reason


def test_validate_input_denies_missing_model_path():
    result = validate_input_hook("strip_detect", {"trace_id": "trc-1"})
    assert result.decision == HookDecision.DENY
    assert "model_path" in result.reason


def test_validate_input_denies_bad_num_samples():
    result = validate_input_hook(
        "strip_detect", {"trace_id": "t", "model_path": "m.h5", "num_samples": -5}
    )
    assert result.decision == HookDecision.DENY


def test_validate_input_denies_strength_out_of_range():
    result = validate_input_hook(
        "strip_detect",
        {"trace_id": "t", "model_path": "m.h5", "perturbation_strength": 2.0},
    )
    assert result.decision == HookDecision.DENY


def test_validate_input_allows_valid():
    result = validate_input_hook(
        "strip_detect",
        {"trace_id": "t", "model_path": "m.h5", "num_samples": 100, "perturbation_strength": 0.05},
    )
    assert result is None


# ── PreToolUse: path_safety_hook ────────────────────────────────────

def test_path_safety_denies_traversal():
    result = path_safety_hook("strip_detect", {"model_path": "../../etc/passwd"})
    assert result.decision == HookDecision.DENY


def test_path_safety_denies_absolute():
    result = path_safety_hook("strip_detect", {"model_path": "/etc/passwd"})
    assert result.decision == HookDecision.DENY


def test_path_safety_allows_relative():
    result = path_safety_hook("strip_detect", {"model_path": "models/model.h5"})
    assert result is None


# ── PostToolUse: verify_output_hook (结果验证) ──────────────────────

def test_verify_output_denies_failure_without_error():
    out = _output(success=False, error=None)
    result = verify_output_hook("strip_detect", {}, out)
    assert result.decision == HookDecision.DENY


def test_verify_output_denies_bad_artifact_hash():
    out = _output(artifact=[Artifact(name="a", type="x", hash="not-a-hash")])
    result = verify_output_hook("strip_detect", {}, out)
    assert result.decision == HookDecision.DENY


def test_verify_output_allows_valid():
    out = _output()
    result = verify_output_hook("strip_detect", {}, out)
    assert result is None


# ── PostToolUse: result_consistency_hook (soft, adds context) ───────

def test_consistency_flags_backdoor_with_low_risk():
    out = _output(data={"is_backdoor": True}, risk_level=RiskLevel.LOW)
    result = result_consistency_hook("strip_detect", {}, out)
    assert result.decision == HookDecision.ALLOW
    assert result.additional_context is not None


def test_consistency_silent_when_consistent():
    out = _output(data={"is_backdoor": True}, risk_level=RiskLevel.HIGH)
    result = result_consistency_hook("strip_detect", {}, out)
    assert result is None


# ── HookManager aggregation ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_manager_deny_wins():
    hm = HookManager()
    hm.on_before_tool(lambda name, data: HookResult.deny("blocked"))
    hm.on_before_tool(lambda name, data: None)
    result = await hm.fire_before_tool("strip_detect", {"trace_id": "t", "model_path": "m.h5"})
    assert result.decision == HookDecision.DENY
    assert result.reason == "blocked"


@pytest.mark.asyncio
async def test_manager_merges_updated_input():
    hm = HookManager()
    hm.on_before_tool(lambda name, data: HookResult(updated_input={**data, "num_samples": 5}))
    hm.on_before_tool(lambda name, data: HookResult(updated_input={**data, "num_samples": 10}))
    result = await hm.fire_before_tool("strip_detect", {"trace_id": "t", "model_path": "m.h5"})
    assert result.decision == HookDecision.ALLOW
    assert result.updated_input["num_samples"] == 10  # last non-None wins


@pytest.mark.asyncio
async def test_manager_concats_additional_context():
    hm = HookManager()
    hm.on_after_tool(lambda n, d, o: HookResult(additional_context="ctx-a"))
    hm.on_after_tool(lambda n, d, o: HookResult(additional_context="ctx-b"))
    out = _output()
    result = await hm.fire_after_tool("strip_detect", {}, out)
    assert result.additional_context == "ctx-a\nctx-b"


@pytest.mark.asyncio
async def test_manager_disabled_returns_allow():
    hm = HookManager()
    hm.disable()
    hm.on_before_tool(lambda name, data: HookResult.deny("blocked"))
    result = await hm.fire_before_tool("strip_detect", {"trace_id": "t", "model_path": "m.h5"})
    assert result.decision == HookDecision.ALLOW


# ── Default registration ────────────────────────────────────────────

def test_register_default_hooks_populates_manager():
    hm = HookManager()
    register_default_hooks(hm)
    assert len(hm._before_tool_hooks) == 3
    assert len(hm._after_tool_hooks) == 3
    assert len(hm._error_hooks) == 1
