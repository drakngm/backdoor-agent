"""Shared httpx client for talking to the core backend (prefer-core pattern).

`get_json` returns the parsed core response or `None` on any failure. `resolve`
wraps the prefer-core/fallback-to-mock/503 logic, and `mock` labels a mock-only
response with `source="mock"`. Every response carries a `source` field so the
frontend can show whether data is real or simulated.
"""

import asyncio
import logging
from typing import Any, Callable, Optional

import httpx
from fastapi import HTTPException

from . import config

logger = logging.getLogger("bff.core_client")


def _make_client() -> httpx.AsyncClient:
    """Test seam: patch this to inject a custom transport."""
    return httpx.AsyncClient()


async def get_json(path: str, timeout: Optional[float] = None) -> Any:
    """GET JSON from the core backend; return the parsed body or None on failure."""
    if not config.CORE_API_URL:
        return None
    try:
        async with asyncio.timeout(timeout or config.CORE_TIMEOUT_SECONDS):
            async with _make_client() as client:
                resp = await client.get(f"{config.CORE_API_URL}{path}")
                resp.raise_for_status()
                return resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("core GET %s failed: %s", path, exc)
        return None


def _with_source(data: Any, source: str) -> Any:
    """Attach a `source` label to dicts and lists-of-dicts (backward compatible)."""
    if isinstance(data, dict):
        return {**data, "source": source}
    if isinstance(data, list):
        return [{**item, "source": source} for item in data if isinstance(item, dict)]
    return data


def mock(mock_fn: Callable[..., Any], *args: Any) -> Any:
    """Label a mock-only response with `source="mock"`."""
    return _with_source(mock_fn(*args), "mock")


async def resolve(
    core_path: str,
    mock_fn: Callable[..., Any],
    *mock_args: Any,
    transform: Optional[Callable[[Any], Any]] = None,
) -> Any:
    """Prefer core data; fall back to mock; raise 503 when fallback is disabled."""
    data = await get_json(core_path)
    if data is not None:
        if transform is not None:
            data = transform(data)
        return _with_source(data, "core")
    if not config.ALLOW_MOCK_FALLBACK:
        raise HTTPException(
            status_code=503,
            detail="core backend unavailable and mock fallback disabled",
        )
    return _with_source(mock_fn(*mock_args), "mock")
