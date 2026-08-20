"""
Tests for ToolRegistry and mock tools.
"""

import pytest

from app.tools.registry import ToolRegistry
from app.tools.mock_strip import MockSTRIPDetector
from app.tools.mock_neural_cleanse import MockNeuralCleanseDetector
from app.tools.mock_activation_clustering import MockActivationClusteringDetector
from app.tools.schemas import ToolInput


@pytest.fixture
def registry():
    reg = ToolRegistry()
    reg.register(MockSTRIPDetector())
    reg.register(MockNeuralCleanseDetector())
    reg.register(MockActivationClusteringDetector())
    return reg


def test_registry_has_all_tools(registry):
    assert len(registry) == 3
    assert "strip_detect" in registry
    assert "neural_cleanse" in registry
    assert "activation_clustering" in registry


def test_registry_get(registry):
    tool = registry.get("strip_detect")
    assert tool.contract.name == "strip_detect"
    assert tool.contract.requires_gpu is True


def test_registry_list_by_tag(registry):
    detection_tools = registry.list_by_tag("detection")
    assert len(detection_tools) == 3


def test_registry_list_by_gpu(registry):
    gpu_tools = registry.list_by_gpu(requires_gpu=True)
    assert len(gpu_tools) == 3


@pytest.mark.asyncio
async def test_mock_strip_execute(registry):
    tool = registry.get("strip_detect")
    input_data = {"trace_id": "test-001", "model_path": "test.h5", "num_samples": 10}
    tool.validate_input(input_data)
    typed_input = tool.contract.input_schema(**input_data)
    output = await tool.execute(typed_input)
    assert output.success is True
    assert output.tool_name == "strip_detect"
    assert 0.0 <= output.confidence_score <= 1.0
    assert output.risk_level in ("LOW", "MEDIUM", "HIGH")


@pytest.mark.asyncio
async def test_mock_neural_cleanse_execute(registry):
    tool = registry.get("neural_cleanse")
    input_data = {"trace_id": "test-002", "model_path": "test.h5", "num_classes": 10}
    typed_input = tool.contract.input_schema(**input_data)
    output = await tool.execute(typed_input)
    assert output.success is True


@pytest.mark.asyncio
async def test_mock_activation_clustering_execute(registry):
    tool = registry.get("activation_clustering")
    input_data = {"trace_id": "test-003", "model_path": "test.h5", "layer_name": "dense_2", "n_clusters": 3}
    typed_input = tool.contract.input_schema(**input_data)
    output = await tool.execute(typed_input)
    assert output.success is True