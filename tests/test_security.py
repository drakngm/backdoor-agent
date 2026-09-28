"""Tests for API auth + rate limiting (configurable, default off)."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.core.security import FixedWindowRateLimiter, check_api_key


# ── Pure primitives ────────────────────────────────────────────────────

def test_check_api_key():
    assert check_api_key("secret", "secret") is True
    assert check_api_key("wrong", "secret") is False
    assert check_api_key(None, "secret") is False
    assert check_api_key("x", None) is False


def test_rate_limiter_disabled_always_allows():
    limiter = FixedWindowRateLimiter(enabled=False, limit=1)
    assert limiter.allow("k") is True
    assert limiter.allow("k") is True


def test_rate_limiter_enforced_with_fake_clock():
    clock = [0.0]
    limiter = FixedWindowRateLimiter(
        enabled=True, limit=2, window_seconds=60.0, clock=lambda: clock[0]
    )
    assert limiter.allow("k") is True
    assert limiter.allow("k") is True
    assert limiter.allow("k") is False
    clock[0] = 61.0  # window rolls over
    assert limiter.allow("k") is True


# ── Middleware (via app) ──────────────────────────────────────────────

def _make_app(monkeypatch, **env):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr("configs.settings._settings", None)
    from app.core.config import reset_config

    reset_config()
    from app.main import create_app, register_tools
    from app.tools.registry import reset_tool_registry

    reset_tool_registry()
    register_tools()
    return create_app()


@pytest.mark.asyncio
async def test_auth_disabled_by_default(monkeypatch):
    app = _make_app(monkeypatch)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_auth_required_when_enabled(monkeypatch):
    app = _make_app(
        monkeypatch,
        BACKDOOR_API_AUTH_ENABLED="true",
        BACKDOOR_API_AUTH_KEY="secret",
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        assert health.status_code == 200  # /health stays open for liveness

        denied = await client.get("/replay/nope")
        assert denied.status_code == 401

        ok = await client.get("/replay/nope", headers={"X-API-Key": "secret"})
        assert ok.status_code == 404  # auth passed; 404 is the trace lookup


@pytest.mark.asyncio
async def test_rate_limit_returns_429_when_enabled(monkeypatch):
    app = _make_app(
        monkeypatch,
        BACKDOOR_RATE_LIMIT_ENABLED="true",
        BACKDOOR_RATE_LIMIT_PER_MINUTE="1",
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/health")
        second = await client.get("/health")
    assert first.status_code == 200
    assert second.status_code == 429
