"""
OpenAI-compatible LLM client.

Implements LLMClient against the OpenAI chat completions API (or any
OpenAI-compatible endpoint). Uses raw httpx so no vendor SDK is required.

Tool calling uses OpenAI's native `tools` (function calling) format.
"""

import json
import os
from typing import Any, Optional

import httpx

from app.llm.base import LLMClient, LLMProvider, LLMResponse, ToolCallRequest
from app.llm.registry import PROVIDER_SPECS
from app.core.logging import get_logger
from app.core.exceptions import AgentLLMError

logger = get_logger(__name__)


class OpenAILLMClient(LLMClient):
    provider = LLMProvider.OPENAI

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ):
        spec = PROVIDER_SPECS[LLMProvider.OPENAI]
        self.model = model or spec.default_model
        self.api_key = api_key or os.getenv(spec.api_key_env_var)
        self.base_url = (base_url or spec.default_base_url).rstrip("/")
        self.temperature = temperature if temperature is not None else 0.1
        self.max_tokens = max_tokens or 4096
        self.timeout = timeout or 60.0

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        trace_id: str = "",
    ) -> LLMResponse:
        if not self.api_key:
            spec = PROVIDER_SPECS[LLMProvider.OPENAI]
            raise AgentLLMError(
                message=(
                    f"Missing API key for provider 'openai'. Set "
                    f"{spec.api_key_env_var} or BACKDOOR_LLM_API_KEY."
                )
            )

        payload = self._build_request(messages, tools)
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            logger.error(f"OpenAI request failed: {e}")
            raise AgentLLMError(message=f"OpenAI request failed: {e}")

        return self._parse_response(data, trace_id)

    # ── Request / response builders (pure, testable) ────────────────────

    def _build_request(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if tools:
            payload["tools"] = [self._tool_to_openai(t) for t in tools]
        return payload

    @staticmethod
    def _tool_to_openai(tool: dict[str, Any]) -> dict[str, Any]:
        function = {
            "name": tool.get("name"),
            "description": tool.get("description", ""),
        }
        # Prefer an explicit JSON-schema parameters block; otherwise a permissive default.
        function["parameters"] = tool.get("parameters") or {
            "type": "object",
            "properties": {},
        }
        return {"type": "function", "function": function}

    def _parse_response(self, data: dict[str, Any], trace_id: str) -> LLMResponse:
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})

        tool_calls = message.get("tool_calls")
        if tool_calls:
            call = tool_calls[0]
            function = call.get("function", {})
            name = function.get("name", "")
            try:
                args = json.loads(function.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            if not isinstance(args, dict):
                args = {}
            return LLMResponse(
                reasoning=message.get("content", ""),
                tool_call=ToolCallRequest(
                    tool_name=name,
                    input_data={**args, "trace_id": trace_id},
                ),
            )

        content = message.get("content") or ""
        return LLMResponse(is_final=True, reasoning="", final_answer=content)
