"""
Provider implementations registration.

Importing this package registers all concrete providers into the registry.
"""

from app.llm.registry import register_provider
from app.llm.providers.mock import MockLLMClient
from app.llm.providers.openai import OpenAILLMClient
from app.llm.providers.anthropic import AnthropicLLMClient

register_provider(MockLLMClient)
register_provider(OpenAILLMClient)
register_provider(AnthropicLLMClient)

__all__ = ["MockLLMClient", "OpenAILLMClient", "AnthropicLLMClient"]
