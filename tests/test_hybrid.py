"""Tests for M3: Hybrid Agent (Agent Loop decisions + DAG execution)."""

import pytest

from app.tools.registry import ToolRegistry
from app.tools.mock_strip import MockSTRIPDetector
from app.tools.mock_neural_cleanse import MockNeuralCleanseDetector
from app.tools.mock_activation_clustering import MockActivationClusteringDetector

from app.workflow.executor import WorkflowExecutor
from app.hybrid import (
    ModelAnalyzer,
    DecisionEngine,
    DecisionCompiler,
    HybridAgent,
    DetectionPlan,
    DetectionStep,
    Decision,
)
from app.hybrid.model_analyzer import ModelMetadata


@pytest.fixture
def registry():
    reg = ToolRegistry()
    reg.register(MockSTRIPDetector())
    reg.register(MockNeuralCleanseDetector())
    reg.register(MockActivationClusteringDetector())
    return reg


def _meta(path="resnet18.h5", arch="resnet", conv=True) -> ModelMetadata:
    return ModelMetadata(path=path, architecture=arch, is_convolutional=conv)


# ── ModelAnalyzer ─────────────────────────────────────────────────────

def test_analyzer_resnet():
    m = ModelAnalyzer().analyze("resnet18.h5")
    assert m.architecture == "resnet"
    assert m.is_convolutional is True


def test_analyzer_mlp():
    m = ModelAnalyzer().analyze("mlp_model.h5")
    assert m.architecture == "mlp"
    assert m.is_convolutional is False


# ── DecisionEngine (deterministic reasoning) ──────────────────────────

def test_engine_decides_strip_first():
    engine = DecisionEngine()
    meta = _meta()
    plan = DetectionPlan(trace_id="t", model_metadata=meta)
    d = engine.decide(meta, {}, plan)
    assert d.is_final is False
    assert d.step.tool_name == "strip_detect"


def test_engine_decides_nc_after_backdoor_strip():
    engine = DecisionEngine()
    meta = _meta()
    plan = DetectionPlan(trace_id="t", model_metadata=meta)
    plan.add_step(DetectionStep(step_id="strip_0", tool_name="strip_detect", params={}))
    results = {
        "strip_0": {"tool_name": "strip_detect", "data": {"is_backdoor": True},
                    "confidence_score": 0.9}
    }
    d = engine.decide(meta, results, plan)
    assert d.step.tool_name == "neural_cleanse"
    assert d.step.depends_on == ["strip_0"]


def test_engine_finalizes_clean_after_strip():
    engine = DecisionEngine()
    meta = _meta()
    plan = DetectionPlan(trace_id="t", model_metadata=meta)
    plan.add_step(DetectionStep(step_id="strip_0", tool_name="strip_detect", params={}))
    results = {
        "strip_0": {"tool_name": "strip_detect", "data": {"is_backdoor": False},
                    "confidence_score": 0.9}
    }
    d = engine.decide(meta, results, plan)
    assert d.is_final is True
    assert d.verdict == "clean"


def test_engine_finalizes_backdoor_after_all():
    engine = DecisionEngine()
    meta = _meta()
    plan = DetectionPlan(trace_id="t", model_metadata=meta)
    for sid, tool in [("strip_0", "strip_detect"), ("neural_cleanse_0", "neural_cleanse"),
                      ("activation_clustering_0", "activation_clustering")]:
        plan.add_step(DetectionStep(step_id=sid, tool_name=tool, params={}))
    results = {
        "strip_0": {"tool_name": "strip_detect", "data": {"is_backdoor": True},
                    "confidence_score": 0.8},
        "neural_cleanse_0": {"tool_name": "neural_cleanse", "data": {"is_backdoor": True},
                             "confidence_score": 0.85},
        "activation_clustering_0": {"tool_name": "activation_clustering",
                                    "data": {"is_backdoor": True, "n_anomalous_clusters": 1},
                                    "confidence_score": 0.7},
    }
    d = engine.decide(meta, results, plan)
    assert d.is_final is True
    assert d.verdict == "backdoor_suspected"
    assert d.confidence == 0.85


# ── DecisionCompiler ──────────────────────────────────────────────────

def test_compiler_builds_dag_with_deps():
    meta = _meta()
    plan = DetectionPlan(trace_id="t", model_metadata=meta)
    plan.add_step(DetectionStep(step_id="strip_0", tool_name="strip_detect", params={"num_samples": 100}))
    plan.add_step(DetectionStep(step_id="nc_0", tool_name="neural_cleanse", params={}, depends_on=["strip_0"]))
    plan.add_step(DetectionStep(step_id="ac_0", tool_name="activation_clustering", params={}, depends_on=["nc_0"]))

    graph = DecisionCompiler().compile(plan)
    assert len(graph) == 3
    assert not graph.has_cycle()
    assert graph.topological_tiers() == [["strip_0"], ["nc_0"], ["ac_0"]]


# ── HybridAgent (end-to-end) ──────────────────────────────────────────

class _ScriptedEngine:
    """Deterministic engine: returns steps in order, then a final decision."""

    def __init__(self, steps, final):
        self.steps = steps
        self.final = final
        self.max_steps = 10

    def decide(self, metadata, results, plan):
        executed = len(plan.steps)
        if executed < len(self.steps):
            return Decision(step=self.steps[executed])
        return self.final


@pytest.mark.asyncio
async def test_hybrid_agent_runs_and_builds_dag(registry):
    steps = [
        DetectionStep(step_id="strip_0", tool_name="strip_detect",
                      params={"model_path": "resnet18.h5", "num_samples": 100},
                      reasoning="run strip"),
        DetectionStep(step_id="nc_0", tool_name="neural_cleanse",
                      params={"model_path": "resnet18.h5", "num_classes": 10},
                      depends_on=["strip_0"], reasoning="run nc"),
        DetectionStep(step_id="ac_0", tool_name="activation_clustering",
                      params={"model_path": "resnet18.h5", "layer_name": "dense_2", "n_clusters": 3},
                      depends_on=["nc_0"], reasoning="run ac"),
    ]
    final = Decision(is_final=True, verdict="backdoor_suspected",
                     confidence=0.85, final_answer="疑似后门")
    engine = _ScriptedEngine(steps, final)

    agent = HybridAgent(engine=engine, executor=WorkflowExecutor(registry))
    result = await agent.run("检测 ResNet-18 是否存在后门", "resnet18.h5")

    assert result.verdict == "backdoor_suspected"
    assert result.confidence == 0.85
    assert len(result.decisions) == 3
    assert len(result.tool_results) == 3
    # dependency edges preserved in the decision chain
    assert result.decisions[1]["depends_on"] == ["strip_0"]
    assert result.decisions[2]["depends_on"] == ["nc_0"]
    assert result.report["architecture"] == "resnet"
    assert result.report["steps_executed"] == 3
    assert "task:" in result.mermaid


@pytest.mark.asyncio
async def test_hybrid_agent_default_engine_runs(registry):
    agent = HybridAgent(executor=WorkflowExecutor(registry))
    result = await agent.run("detect backdoor", "resnet18.h5")
    assert result.trace_id.startswith("trc-")
    assert result.report["architecture"] == "resnet"
    assert result.verdict in ("clean", "backdoor_suspected", "inconclusive")
