"""
Pytest configuration.

Ensures the test suite is hermetic: forces the mock LLM provider regardless of a
local `.env` (which may point to a real provider like openai/anthropic). OS env
vars take precedence over `.env` in pydantic-settings, so this overrides cleanly.
"""

import os

import pytest

os.environ["BACKDOOR_LLM_PROVIDER"] = "mock"


@pytest.fixture(scope="session", autouse=True)
def _reset_config():
    """Reset the cached config singleton so the forced env var takes effect."""
    from app.core.config import reset_config

    reset_config()
    yield
