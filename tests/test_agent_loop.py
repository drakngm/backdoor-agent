"""Tests for Agent Loop with Mock LLM."""

import pytest
from app.agents.agent_loop import AgentLoop, MockLLM
from app.tools.registry import ToolRegistry
from app.tools.mock_strip import MockSTRIPDetector
from app.tools.mock_neural_cleanse import MockNeuralCleanseDetector
from app.tools.mock_activation_clustering import MockActivationClusteringDetector


@pytest.fixture
def registry():
    reg = ToolRegistry()
    reg.register(MockSTRIPDetector())
    reg.register(MockNeuralCleanseDetector())
    reg.register(MockActivationClusteringDetector())
    return reg


@pytest.mark.asyncio
async def test_agent_loop_runs_without_error(registry):
    agent = AgentLoop()
    trace = await agent.run("Detect backdoors in model.h5")
    assert trace.trace_id.startswith("trc-")
    assert len(trace.spans) > 0
    assert trace.status.value in ("success", "partial_failure")


@pytest.mark.asyncio
async def test_mock_llm_returns_sequence():
    llm = MockLLM()
    r1 = await llm.complete([], trace_id="test")
    assert r1.tool_call is not None
    assert r1.tool_call.tool_name == "strip_detect"

    r2 = await llm.complete([], trace_id="test")
    assert r2.tool_call.tool_name == "neural_cleanse"

    r3 = await llm.complete([], trace_id="test")
    assert r3.tool_call.tool_name == "activation_clustering"

    r4 = await llm.complete([], trace_id="test")
    assert r4.is_final is True
    assert r4.final_answer is not None


@pytest.mark.asyncio
async def test_agent_trace_has_spans(registry):
    agent = AgentLoop()
    trace = await agent.run("scan model.h5")
    chain = trace.get_linear_chain()
    tool_spans = [s for s in chain if s.span_type.value == "tool_call"]
    assert len(tool_spans) >= 3


@pytest.mark.asyncio
async def test_agent_trace_has_mermaid(registry):
    agent = AgentLoop()
    trace = await agent.run("scan")
    mermaid = trace.to_mermaid()
    assert "flowchart" in mermaid
    assert "-->" in mermaid