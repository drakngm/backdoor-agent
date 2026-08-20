"""Tests for the LLM Provider abstraction (M2)."""

import pytest

from app.llm.base import (
    LLMClient,
    LLMProvider,
    LLMResponse,
    ToolCallRequest,
)
from app.llm import (
    create_llm_client,
    get_spec,
    is_provider_available,
    list_providers,
    normalize_provider,
    resolve_model,
)
from app.llm.registry import PROVIDER_SPECS
from app.llm.providers.mock import MockLLMClient
from app.llm.providers.openai import OpenAILLMClient
from app.llm.providers.anthropic import AnthropicLLMClient
from app.core.exceptions import ConfigurationError, AgentLLMError


# ── Provider registry / factory ────────────────────────────────────────

def test_all_providers_registered():
    registered = set(list_providers())
    assert {"mock", "openai", "anthropic"} <= registered


def test_is_provider_available():
    assert is_provider_available("openai") is True
    assert is_provider_available("does_not_exist") is False


def test_normalize_provider():
    assert normalize_provider("OPENAI") is LLMProvider.OPENAI
    assert normalize_provider(LLMProvider.MOCK) is LLMProvider.MOCK


def test_normalize_provider_unknown_raises():
    with pytest.raises(ConfigurationError):
        normalize_provider("nope")


def test_get_spec_defaults():
    assert get_spec("openai").default_model == "gpt-4o"
    assert get_spec("anthropic").default_base_url == "https://api.anthropic.com"
    assert get_spec("mock").supports_streaming is False


def test_resolve_model():
    assert resolve_model("openai") == "gpt-4o"
    assert resolve_model("openai", "gpt-4o-mini") == "gpt-4o-mini"
    assert resolve_model("anthropic") == get_spec("anthropic").default_model


def test_create_llm_client_default_is_mock():
    client = create_llm_client()
    assert isinstance(client, MockLLMClient)


def test_create_llm_client_openai():
    client = create_llm_client("openai", model="gpt-4o-mini", api_key="sk-test")
    assert isinstance(client, OpenAILLMClient)
    assert client.model == "gpt-4o-mini"


def test_create_llm_client_anthropic():
    client = create_llm_client(LLMProvider.ANTHROPIC)
    assert isinstance(client, AnthropicLLMClient)


def test_create_llm_client_unknown_raises():
    with pytest.raises(ConfigurationError):
        create_llm_client("unknown")


# ── Mock client ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mock_client_is_llm_client():
    assert isinstance(MockLLMClient(), LLMClient)


@pytest.mark.asyncio
async def test_mock_client_injects_trace_id():
    llm = MockLLMClient()
    resp = await llm.complete([], trace_id="trc-abc")
    assert resp.tool_call.input_data["trace_id"] == "trc-abc"


@pytest.mark.asyncio
async def test_mock_client_reset():
    llm = MockLLMClient()
    await llm.complete([])
    await llm.complete([])
    llm.reset()
    resp = await llm.complete([])
    assert resp.tool_call.tool_name == "strip_detect"


# ── OpenAI client (request/response builders) ──────────────────────────

def _openai_client() -> OpenAILLMClient:
    return OpenAILLMClient(model="gpt-4o", api_key="sk-test")


def test_openai_build_request_with_tools():
    client = _openai_client()
    payload = client._build_request(
        [{"role": "user", "content": "hi"}],
        tools=[{"name": "strip_detect", "description": "d", "parameters": {"type": "object"}}],
    )
    assert payload["model"] == "gpt-4o"
    tool = payload["tools"][0]
    assert tool["type"] == "function"
    assert tool["function"]["name"] == "strip_detect"
    assert tool["function"]["parameters"] == {"type": "object"}


def test_openai_parse_tool_call():
    client = _openai_client()
    data = {
        "choices": [{
            "message": {
                "content": "running detection",
                "tool_calls": [{
                    "function": {"name": "strip_detect", "arguments": '{"model_path": "m.h5"}'}
                }],
            }
        }]
    }
    resp = client._parse_response(data, "trc-1")
    assert resp.tool_call.tool_name == "strip_detect"
    assert resp.tool_call.input_data["model_path"] == "m.h5"
    assert resp.tool_call.input_data["trace_id"] == "trc-1"


def test_openai_parse_final_text():
    client = _openai_client()
    data = {"choices": [{"message": {"content": "all done"}}]}
    resp = client._parse_response(data, "trc-1")
    assert resp.is_final is True
    assert resp.final_answer == "all done"


@pytest.mark.asyncio
async def test_openai_missing_key_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = OpenAILLMClient(model="gpt-4o", api_key=None)
    with pytest.raises(AgentLLMError):
        await client.complete([{"role": "user", "content": "hi"}])


# ── Anthropic client (request/response builders) ───────────────────────

def _anthropic_client() -> AnthropicLLMClient:
    return AnthropicLLMClient(model="claude-test", api_key="sk-test")


def test_anthropic_build_request_splits_system():
    client = _anthropic_client()
    payload = client._build_request([
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ])
    assert payload["system"] == "be brief"
    assert payload["messages"] == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]


def test_anthropic_build_request_tools():
    client = _anthropic_client()
    payload = client._build_request([], tools=[{"name": "t", "description": "d"}])
    assert payload["tools"][0]["name"] == "t"
    assert payload["tools"][0]["input_schema"] == {"type": "object", "properties": {}}


def test_anthropic_parse_tool_use():
    client = _anthropic_client()
    data = {"content": [
        {"type": "text", "text": "thinking"},
        {"type": "tool_use", "name": "neural_cleanse", "input": {"num_classes": 10}},
    ]}
    resp = client._parse_response(data, "trc-2")
    assert resp.tool_call.tool_name == "neural_cleanse"
    assert resp.tool_call.input_data["num_classes"] == 10
    assert resp.tool_call.input_data["trace_id"] == "trc-2"


def test_anthropic_parse_final_text():
    client = _anthropic_client()
    data = {"content": [{"type": "text", "text": "finished"}]}
    resp = client._parse_response(data, "trc-2")
    assert resp.is_final is True
    assert resp.final_answer == "finished"


@pytest.mark.asyncio
async def test_anthropic_missing_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = AnthropicLLMClient(model="claude-test", api_key=None)
    with pytest.raises(AgentLLMError):
        await client.complete([{"role": "user", "content": "hi"}])


# ── Backward-compat: ToolCallRequest still importable from tool_router ──

def test_tool_call_request_import_from_tool_router():
    from app.agents.tool_router import ToolCallRequest as TR
    assert TR is ToolCallRequest
