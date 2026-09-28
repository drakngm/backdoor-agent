"""Tests for report generation including CoT decision chain + audit evidence."""

import pytest

from app.report.generator import ReportGenerator
from app.tools.schemas import ToolOutput, RiskLevel
from app.trace.trace import FourLevelTrace
from app.trace.models import CoTStep


def _outputs():
    return [
        ToolOutput(
            trace_id="t",
            tool_name="strip_detect",
            success=True,
            data={"is_backdoor": True},
            confidence_score=0.9,
            risk_level=RiskLevel.HIGH,
        )
    ]


def _make_trace():
    t = FourLevelTrace(trace_id="t")
    t.record_cot(CoTStep(step_id="s1", reasoning="reason", decision="run_nc"))
    t.record_data("s1", "strip_detect", {"a": 1}, {"b": 2})
    t.record_audit("decision", "msg")
    return t


# ── ReportGenerator ────────────────────────────────────────────────────

def test_report_without_trace_marks_evidence_incomplete():
    report = ReportGenerator().generate("t", _outputs())
    assert report["verdict"] == "backdoor_detected"
    assert report["evidence_incomplete"] is True
    assert report["decision_chain"] is None
    assert report["audit"] is None
    assert report["data_flow_summary"] is None


def test_report_with_trace_includes_cot_and_audit():
    report = ReportGenerator().generate("t", _outputs(), trace=_make_trace())
    assert report["evidence_incomplete"] is False
    assert report["decision_chain"][0]["decision"] == "run_nc"
    assert report["audit"]["verified"] is True
    assert "entries" in report["audit"]
    assert report["data_flow_summary"][0]["tool_name"] == "strip_detect"


def test_report_accepts_replay_dict():
    replay = _make_trace().replay()
    report = ReportGenerator().generate("t", _outputs(), trace=replay)
    assert report["decision_chain"][0]["decision"] == "run_nc"
    assert report["audit"]["verified"] is True


# ── Hybrid report integration ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_hybrid_report_includes_cot_and_audit(tmp_path):
    from app.tools.registry import ToolRegistry
    from app.tools.mock_strip import MockSTRIPDetector
    from app.workflow.executor import WorkflowExecutor
    from app.hybrid import HybridAgent, DetectionStep, Decision
    from app.memory.hierarchical import HierarchicalMemory
    from app.memory.episodic_memory import EpisodicMemory
    from app.memory.semantic_memory import SemanticMemory
    from app.memory.procedural_memory import ProceduralMemory

    class _ScriptedEngine:
        def __init__(self, steps, final):
            self.steps = steps
            self.final = final
            self.max_steps = 10

        def decide(self, metadata, results, plan):
            if len(plan.steps) < len(self.steps):
                return Decision(step=self.steps[len(plan.steps)])
            return self.final

    registry = ToolRegistry()
    registry.register(MockSTRIPDetector())

    steps = [
        DetectionStep(
            step_id="strip_0",
            tool_name="strip_detect",
            params={"model_path": "resnet18.h5", "num_samples": 50},
            reasoning="run strip",
        )
    ]
    final = Decision(is_final=True, verdict="clean", confidence=0.9, final_answer="无后门")
    engine = _ScriptedEngine(steps, final)

    memory = HierarchicalMemory(
        episodic=EpisodicMemory(window_size=20),
        semantic=SemanticMemory(filepath=str(tmp_path / "sem.json")),
        procedural=ProceduralMemory(filepath=str(tmp_path / "proc.json")),
        use_redis=False,
    )

    agent = HybridAgent(engine=engine, executor=WorkflowExecutor(registry), memory=memory)
    result = await agent.run("detect backdoor", "resnet18.h5")

    assert "decision_chain" in result.report
    assert "audit" in result.report
    assert result.report["audit"]["verified"] is True
    assert "data_flow_summary" in result.report
