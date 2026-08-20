"""
LLM Provider abstraction — core types and interfaces.

Reference design (adapted from craft-agents-oss backend abstraction):
  - LLMProvider: provider identifier union (mock / openai / anthropic / ...)
  - LLMClient:   uniform interface every provider implements (AgentBackend analog)
  - ProviderSpec: declarative per-provider metadata (defaults + capabilities)
  - LLMResponse:  structured result returned to the Agent Loop (tool_call or final)
  - ToolCallRequest: the tool invocation the LLM asks the runtime to perform

The Agent Loop depends only on LLMClient, so switching providers never touches
the reasoning/orchestration logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Provider identifiers (mirrors craft's AgentProvider union)."""

    MOCK = "mock"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class ToolCallRequest(BaseModel):
    """A tool invocation requested by the LLM.

    Owned by the LLM layer (the LLM emits it); the ToolRouter consumes it.
    """

    tool_name: str
    input_data: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Structured LLM result returned to the Agent Loop.

    Either `tool_call` (agent should execute a tool) or `is_final` + `final_answer`
    (agent should stop). `reasoning` carries the model's CoT-style rationale.
    """

    is_final: bool = False
    reasoning: str = ""
    tool_call: Optional[ToolCallRequest] = None
    final_answer: Optional[str] = None


@dataclass(frozen=True)
class ProviderSpec:
    """Declarative metadata + capabilities for a provider.

    Analog of craft's BACKEND_CAPABILITIES + per-provider defaults. Keeps
    provider-specific branching (defaults, env vars, capabilities) out of the
    Agent Loop and factory.
    """

    provider: LLMProvider
    default_model: str
    default_base_url: str
    api_key_env_var: str
    supports_tool_calling: bool = True
    supports_streaming: bool = True
    supports_vision: bool = False
    description: str = ""


class LLMClient(ABC):
    """
    Uniform interface every LLM provider implements (AgentBackend analog).

    Subclasses:
      - set `provider: LLMProvider` (class attribute)
      - implement `async def complete(messages, tools=None, trace_id="") -> LLMResponse`
      - optionally override `reset()` for per-instance state
    """

    #: Provider identifier; used by the registry to route and by specs lookup.
    provider: LLMProvider

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        trace_id: str = "",
    ) -> LLMResponse:
        """
        Send messages to the model and return a structured LLMResponse.

        Args:
            messages: Chat messages in OpenAI-style shape [{role, content}, ...].
            tools: Optional tool descriptors for function/tool calling.
            trace_id: Correlation ID propagated through logs/errors.

        Returns:
            LLMResponse carrying either a ToolCallRequest or a final answer.
        """
        ...

    def reset(self) -> None:
        """Reset per-instance state (e.g. a scripted step counter)."""
        ...
