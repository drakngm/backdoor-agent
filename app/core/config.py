"""
Global configuration singleton.
Wraps configs/settings.py to provide a centralized access point.
"""

from typing import Optional
from configs.settings import Settings, get_settings as _get_settings

_config_instance: Optional[Settings] = None


def get_config() -> Settings:
    """Return the global configuration singleton."""
    global _config_instance
    if _config_instance is None:
        _config_instance = _get_settings()
    return _config_instance


def reset_config() -> None:
    """Reset the config singleton (useful for tests)."""
    global _config_instance
    _config_instance = None