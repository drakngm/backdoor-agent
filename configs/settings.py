"""
Global application settings using pydantic-settings.
Supports env vars, .env file, and hardcoded defaults (priority: env > .env > default).
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """Unified configuration for the Backdoor Agent system."""

    # ---- Application ----
    app_name: str = "backdoor-agent"
    app_version: str = "0.1.0"
    debug: bool = False

    # ---- Server ----
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # ---- LLM API ----
    llm_provider: str = "mock"  # mock | openai | anthropic
    llm_api_base_url: Optional[str] = None  # None → provider default
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None  # None → provider default model
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.1
    llm_timeout_seconds: float = 60.0

    # ---- Agent Runtime ----
    agent_max_iterations: int = 15
    agent_loop_timeout_seconds: int = 300
    working_memory_max_tokens: int = 8000

    # ---- Tool System ----
    tool_default_timeout_ms: int = 30000
    tool_max_retries: int = 2

    # ---- Execution Trace ----
    trace_enabled: bool = True
    trace_storage_dir: str = "./data/traces"

    # ---- Memory / Persistence ----
    data_dir: str = "./data"
    project_memory_path: str = "./data/project_memory.json"

    # ---- Redis (optional) ----
    redis_url: Optional[str] = None
    redis_task_queue: str = "backdoor:tasks"

    # ---- Security scan defaults ----
    default_scan_strategy: str = "fast_scan"

    model_config = {
        "env_prefix": "BACKDOOR_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


# Global singleton
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Return the global Settings instance (lazy init)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings