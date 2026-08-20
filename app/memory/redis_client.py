"""
Redis client factory with graceful degradation.

Redis backs L1 (Episodic Memory). If `redis_url` is unset or the server is
unreachable, returns None so callers fall back to in-memory storage.
"""

from typing import Optional

from app.core.config import get_config
from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    import redis as _redis
except ImportError:  # pragma: no cover
    _redis = None

_client = None
_initialized = False


def get_redis_client() -> Optional["_redis.Redis"]:
    """
    Return a Redis client, or None if Redis is unavailable.

    Resolution: config.redis_url -> connect + ping. Any failure => None.
    """
    global _client, _initialized

    if _initialized:
        return _client
    _initialized = True

    if _redis is None:
        logger.warning("redis package not installed; Episodic Memory falls back to in-memory")
        return None

    url = get_config().redis_url
    if not url:
        return None

    try:
        client = _redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=1)
        client.ping()
        _client = client
        logger.info(f"Redis connected: {url}")
    except Exception as e:
        logger.warning(f"Redis unavailable ({e}); Episodic Memory falls back to in-memory")
        _client = None

    return _client


def reset_redis_client() -> None:
    """Reset the cached client (for testing)."""
    global _client, _initialized
    _client = None
    _initialized = False
