"""
Anthropic LLM client.

Implements LLMClient against the Anthropic Messages API. Uses raw httpx so no
vendor SDK is required.

Tool calling uses Anthropic's native `tools` (tool_use content blocks) format.
"""

import os
from typing import Any, Optional

import httpx

from app.llm.base import LLMClient, LLMProvider, LLMResponse, ToolCallRequest
from app.llm.registry import PROVIDER_SPECS
from app.core.logging import get_logger
from app.core.exceptions import AgentLLMError

logger = get_logger(__name__)


class AnthropicLLMClient(LLMClient):
    provider = LLMProvider.ANTHROPIC

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
        spec = PROVIDER_SPECS[LLMProvider.ANTHROPIC]
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
            spec = PROVIDER_SPECS[LLMProvider.ANTHROPIC]
            raise AgentLLMError(
                message=(
                    f"Missing API key for provider 'anthropic'. Set "
                    f"{spec.api_key_env_var} or BACKDOOR_LLM_API_KEY."
                )
            )

        payload = self._build_request(messages, tools)
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/messages",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            logger.error(f"Anthropic request failed: {e}")
            raise AgentLLMError(message=f"Anthropic request failed: {e}")

        return self._parse_response(data, trace_id)

    # ── Request / response builders (pure, testable) ────────────────────

    def _build_request(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        # Anthropic requires `system` as a top-level field, not a message role.
        system_parts = [m.get("content", "") for m in messages if m.get("role") == "system"]
        converted = [
            {"role": self._map_role(m.get("role", "user")), "content": m.get("content", "")}
            for m in messages
            if m.get("role") != "system"
        ]

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": converted,
            "temperature": self.temperature,
        }
        if system_parts:
            payload["system"] = "\n".join(system_parts)
        if tools:
            payload["tools"] = [self._tool_to_anthropic(t) for t in tools]
        return payload

    @staticmethod
    def _map_role(role: str) -> str:
        # Anthropic roles are limited to 'user' and 'assistant'.
        return {"user": "user", "assistant": "assistant", "tool": "user"}.get(role, "user")

    @staticmethod
    def _tool_to_anthropic(tool: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": tool.get("name"),
            "description": tool.get("description", ""),
            "input_schema": tool.get("parameters") or {"type": "object", "properties": {}},
        }

    def _parse_response(self, data: dict[str, Any], trace_id: str) -> LLMResponse:
        content = data.get("content", [])
        text_parts: list[str] = []

        for block in content:
            if block.get("type") == "tool_use":
                args = block.get("input", {}) or {}
                return LLMResponse(
                    reasoning="\n".join(text_parts),
                    tool_call=ToolCallRequest(
                        tool_name=block.get("name", ""),
                        input_data={**args, "trace_id": trace_id},
                    ),
                )
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))

        return LLMResponse(is_final=True, reasoning="", final_answer="\n".join(text_parts))
