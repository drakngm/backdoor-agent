"""Tests for M5: four-level trace (system/data/decision/audit) + CoT + replay."""

import pytest

from app.trace.models import (
    CoTStep,
    Alternative,
    DataTraceEntry,
    stable_hash,
)
from app.trace.audit import AuditTrail
from app.trace.trace import FourLevelTrace
from app.trace.hooks import TraceRecorder
from app.hybrid.decisions import DetectionPlan, Decision
from app.hybrid.decision_engine import DecisionEngine
from app.hybrid.model_analyzer import ModelMetadata


# ── Content addressing ───────────────────────────────────────────────

def test_stable_hash_deterministic():
    assert stable_hash({"a": 1, "b": [2, 3]}) == stable_hash({"a": 1, "b": [2, 3]})
    assert stable_hash({"a": 1}) != stable_hash({"a": 2})


def test_cot_content_hash():
    cot = CoTStep(step_id="s0", observation="o", reasoning="r", decision="d")
    assert cot.content_hash() == stable_hash(cot.model_dump())


# ── L4 Audit Trail (hash-chained, immutable) ─────────────────────────

def test_audit_append_and_verify():
    trail = AuditTrail()
    trail.append("trc-1", "session_start")
    trail.append("trc-1", "tool_start", "strip_detect")
    assert len(trail.entries()) == 2
    assert trail.verify() is True


def test_audit_tamper_breaks_chain():
    trail = AuditTrail()
    trail.append("trc-1", "session_start")
    trail.append("trc-1", "tool_start")
    trail.entries()[0].message = "tampered"
    assert trail.verify() is False


# ── CoT step structure (matches forced system-prompt format) ─────────

def test_cot_step_structure():
    cot = CoTStep(
        step_id="neural_cleanse_0",
        step="select_tool",
        observation="STRIP 检测发现扰动熵降低 35%（阈值 5%）",
        reasoning="需要进一步缩小原因范围",
        decision="调用 Neural Cleanse 进行触发器逆向重建",
        alternatives_considered=[
            Alternative(tool="Activation Clustering", reason_rejected="缺乏标注数据"),
            Alternative(tool="直接报告", reason_rejected="证据不足"),
        ],
        tool_name="neural_cleanse",
    )
    assert cot.step == "select_tool"
    assert cot.tool_name == "neural_cleanse"
    assert len(cot.alternatives_considered) == 2


# ── FourLevelTrace (record / replay / compare / persist) ─────────────

def _make_trace(trace_id="trc-1") -> FourLevelTrace:
    return FourLevelTrace(trace_id=trace_id)


def test_four_level_trace_replay():
    ft = _make_trace()
    ft.record_audit("session_start")
    ft.record_cot(CoTStep(step_id="s0", tool_name="strip_detect"))
    ft.record_data(step_id="s0", tool_name="strip_detect",
                   input_data={"model_path": "m.h5"}, output_data={"success": True})

    replay = ft.replay()
    assert replay["trace_id"] == "trc-1"
    assert len(replay["decisions"]) == 1
    assert len(replay["data_flow"]) == 1
    assert replay["audit_verified"] is True
    # content hashes present for data flow
    assert replay["data_flow"][0]["input_hash"]
    assert replay["data_flow"][0]["output_hash"]


def test_four_level_trace_compare():
    a = _make_trace("trace-a")
    b = _make_trace("trace-b")
    a.record_cot(CoTStep(step_id="s0", tool_name="strip_detect"))
    a.record_cot(CoTStep(step_id="s1", tool_name="neural_cleanse"))
    b.record_cot(CoTStep(step_id="s0", tool_name="strip_detect"))
    b.record_cot(CoTStep(step_id="s1", tool_name="activation_clustering"))

    diff = a.compare(b)
    assert diff["same_sequence"] is False
    assert diff["tool_sequence_a"] == ["strip_detect", "neural_cleanse"]
    assert diff["differences"][0]["trace_a"] == "neural_cleanse"
    assert diff["differences"][0]["trace_b"] == "activation_clustering"


def test_four_level_trace_persist(tmp_path):
    ft = _make_trace("trc-1")
    ft.record_audit("session_start")
    ft.record_cot(CoTStep(step_id="s0"))
    fp = str(tmp_path / "trace.json")
    ft.save(fp)

    loaded = FourLevelTrace.load(fp)
    assert loaded.trace_id == "trc-1"
    assert len(loaded.cot_steps) == 1
    assert len(loaded.audit.entries()) == 1
    assert loaded.audit.verify() is True


# ── TraceRecorder hooks (combines trace with pre/post hooks) ─────────

class _FakeOutput:
    def model_dump(self):
        return {"tool_name": "strip_detect", "success": True, "data": {"is_backdoor": False}}


def test_trace_recorder_hooks():
    ft = _make_trace()
    recorder = TraceRecorder(ft)
    input_data = {"model_path": "m.h5"}

    assert recorder.pre_tool_hook("strip_detect", input_data) is None
    assert recorder.post_tool_hook("strip_detect", input_data, _FakeOutput()) is None

    assert len(ft.data_entries) == 1
    assert ft.data_entries[0].input_hash == stable_hash(input_data)
    assert len(ft.audit.entries()) == 2  # tool_start + tool_end
    assert ft.audit.verify() is True


# ── DecisionEngine produces structured CoT ───────────────────────────

def test_decision_engine_produces_cot():
    engine = DecisionEngine()
    meta = ModelMetadata(path="resnet18.h5", architecture="resnet", is_convolutional=True)
    plan = DetectionPlan(trace_id="t", model_metadata=meta)

    decision = engine.decide(meta, {}, plan)
    assert decision.cot is not None
    assert decision.cot.step == "select_tool"
    assert decision.cot.tool_name == "strip_detect"
    assert decision.cot.observation
    assert decision.cot.reasoning
    assert decision.cot.decision
    assert len(decision.cot.alternatives_considered) >= 1


# ── HybridAgent records four-level trace ─────────────────────────────

@pytest.mark.asyncio
async def test_hybrid_agent_records_four_level_trace(tmp_path):
    from app.tools.registry import ToolRegistry
    from app.tools.mock_strip import MockSTRIPDetector
    from app.tools.mock_neural_cleanse import MockNeuralCleanseDetector
    from app.tools.mock_activation_clustering import MockActivationClusteringDetector
    from app.workflow.executor import WorkflowExecutor
    from app.hybrid import HybridAgent
    from app.memory.hierarchical import HierarchicalMemory
    from app.memory.episodic_memory import EpisodicMemory
    from app.memory.semantic_memory import SemanticMemory
    from app.memory.procedural_memory import ProceduralMemory

    reg = ToolRegistry()
    reg.register(MockSTRIPDetector())
    reg.register(MockNeuralCleanseDetector())
    reg.register(MockActivationClusteringDetector())

    memory = HierarchicalMemory(
        episodic=EpisodicMemory(window_size=20),
        semantic=SemanticMemory(filepath=str(tmp_path / "sem.json")),
        procedural=ProceduralMemory(filepath=str(tmp_path / "proc.json")),
        use_redis=False,
    )
    agent = HybridAgent(executor=WorkflowExecutor(reg), memory=memory)
    result = await agent.run("检测 ResNet-18 是否存在后门", "resnet18.h5")

    tr = result.trace
    assert tr["trace_id"] == result.trace_id
    assert tr["audit_verified"] is True

    # L3 decision trace: structured CoT
    assert len(tr["decisions"]) >= 1
    for d in tr["decisions"]:
        assert "observation" in d
        assert "reasoning" in d
        assert "decision" in d
        assert "alternatives_considered" in d

    # L2 data trace: hashed input/output flow
    assert len(tr["data_flow"]) >= 1
    for entry in tr["data_flow"]:
        assert entry["input_hash"]
        assert entry["output_hash"]

    # L4 audit trail
    assert len(tr["audit"]) >= 2
