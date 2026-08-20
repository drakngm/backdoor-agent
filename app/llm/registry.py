"""
LLM provider registry + factory.

Adapted from craft-agents-oss `agent/backend/factory.ts`:
  - DRIVER_REGISTRY          -> _CLIENT_REGISTRY (provider -> client class)
  - getAvailableProviders    -> list_providers()
  - isProviderAvailable      -> is_provider_available()
  - createBackend/createAgent-> create_llm_client()
  - resolveModelForProvider  -> resolve_model()

Provider-specific branching (defaults, env vars, capabilities) lives in
ProviderSpec so the factory stays declarative.
"""

from typing import Any, Optional, Union

from app.llm.base import LLMClient, LLMProvider, ProviderSpec
from app.core.config import get_config
from app.core.logging import get_logger
from app.core.exceptions import ConfigurationError

logger = get_logger(__name__)


# ── Declarative provider specs (capabilities + defaults) ──────────────────

PROVIDER_SPECS: dict[LLMProvider, ProviderSpec] = {
    LLMProvider.MOCK: ProviderSpec(
        provider=LLMProvider.MOCK,
        default_model="mock-scripted",
        default_base_url="",
        api_key_env_var="",
        supports_tool_calling=True,
        supports_streaming=False,
        supports_vision=False,
        description="Scripted in-process LLM for development/testing (no API key required).",
    ),
    LLMProvider.OPENAI: ProviderSpec(
        provider=LLMProvider.OPENAI,
        default_model="gpt-4o",
        default_base_url="https://api.openai.com/v1",
        api_key_env_var="OPENAI_API_KEY",
        supports_tool_calling=True,
        supports_streaming=True,
        supports_vision=True,
        description="OpenAI chat completions API (also OpenAI-compatible endpoints).",
    ),
    LLMProvider.ANTHROPIC: ProviderSpec(
        provider=LLMProvider.ANTHROPIC,
        default_model="claude-sonnet-4-5-20250929",
        default_base_url="https://api.anthropic.com",
        api_key_env_var="ANTHROPIC_API_KEY",
        supports_tool_calling=True,
        supports_streaming=True,
        supports_vision=True,
        description="Anthropic Messages API.",
    ),
}


# ── Client registry (provider -> client class) ────────────────────────────

_CLIENT_REGISTRY: dict[LLMProvider, type[LLMClient]] = {}


def register_provider(client_cls: type[LLMClient]) -> type[LLMClient]:
    """Register a provider client class (keyed by `client_cls.provider`)."""
    provider = client_cls.provider
    _CLIENT_REGISTRY[provider] = client_cls
    logger.info(f"LLM provider registered: {provider.value}")
    return client_cls


# ── Query helpers ─────────────────────────────────────────────────────────

def list_providers() -> list[str]:
    """Return identifiers of currently available (registered) providers."""
    return [p.value for p in _CLIENT_REGISTRY]


def is_provider_available(provider: Union[str, LLMProvider]) -> bool:
    """Check whether a provider has a working implementation registered."""
    try:
        return normalize_provider(provider) in _CLIENT_REGISTRY
    except ConfigurationError:
        return False


def get_spec(provider: Union[str, LLMProvider]) -> ProviderSpec:
    """Return the declarative spec for a provider."""
    normalized = normalize_provider(provider)
    return PROVIDER_SPECS[normalized]


def normalize_provider(provider: Union[str, LLMProvider]) -> LLMProvider:
    """Coerce a provider name/str to an LLMProvider, raising on unknown values."""
    if isinstance(provider, LLMProvider):
        return provider
    try:
        return LLMProvider(str(provider).strip().lower())
    except ValueError:
        raise ConfigurationError(
            message=f"Unknown LLM provider: '{provider}'. Available: {list(PROVIDER_SPECS)}",
            details={"requested": provider, "available": list(PROVIDER_SPECS)},
        )


def resolve_model(
    provider: Union[str, LLMProvider],
    model: Optional[str] = None,
) -> str:
    """
    Resolve the model ID for a provider.

    Priority: explicit `model` argument -> provider spec default.
    (The factory injects the configured model before calling this, mirroring
    craft's resolveModelForProvider.)
    """
    normalized = normalize_provider(provider)
    spec = PROVIDER_SPECS[normalized]
    return model or spec.default_model


# ── Factory ───────────────────────────────────────────────────────────────

def create_llm_client(
    provider: Optional[Union[str, LLMProvider]] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs: Any,
) -> LLMClient:
    """
    Create an LLM client for the requested provider.

    Resolution order (mirrors craft's connection/provider resolution):
      provider  -> explicit arg, else config.llm_provider
      model     -> explicit arg, else config.llm_model, else provider default
      api_key   -> explicit arg, else config.llm_api_key (client falls back to env)
      base_url  -> explicit arg, else config.llm_api_base_url, else provider default

    Raises:
        ConfigurationError: unknown or unregistered provider.
    """
    cfg = get_config()
    resolved_provider = normalize_provider(provider or cfg.llm_provider)

    client_cls = _CLIENT_REGISTRY.get(resolved_provider)
    if client_cls is None:
        raise ConfigurationError(
            message=f"Provider '{resolved_provider.value}' is not registered. "
                    f"Available: {list_providers()}",
            details={"requested": resolved_provider.value, "available": list_providers()},
        )

    spec = PROVIDER_SPECS[resolved_provider]
    resolved_model = resolve_model(resolved_provider, model or cfg.llm_model)
    resolved_api_key = api_key or cfg.llm_api_key
    resolved_base_url = base_url or cfg.llm_api_base_url or spec.default_base_url

    logger.info(
        f"Creating LLM client: provider={resolved_provider.value}, model={resolved_model}"
    )
    return client_cls(
        model=resolved_model,
        api_key=resolved_api_key,
        base_url=resolved_base_url,
        **kwargs,
    )
