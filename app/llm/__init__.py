"""
LLM Provider abstraction — public API.

Usage:
    from app.llm import create_llm_client, LLMProvider

    client = create_llm_client("openai")
    response = await client.complete(messages=[{"role": "user", "content": "hi"}])
"""

from app.llm.base import (
    LLMClient,
    LLMProvider,
    LLMResponse,
    ProviderSpec,
    ToolCallRequest,
)
from app.llm.registry import (
    create_llm_client,
    get_spec,
    is_provider_available,
    list_providers,
    normalize_provider,
    register_provider,
    resolve_model,
)

# Import providers to trigger registration (side effect).
from app.llm import providers as _providers  # noqa: F401

__all__ = [
    "LLMClient",
    "LLMProvider",
    "LLMResponse",
    "ProviderSpec",
    "ToolCallRequest",
    "create_llm_client",
    "get_spec",
    "is_provider_available",
    "list_providers",
    "normalize_provider",
    "register_provider",
    "resolve_model",
]
