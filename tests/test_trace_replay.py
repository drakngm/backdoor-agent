"""Tests for trace persistence (TraceStore) and the /replay endpoint."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import create_app, register_tools
from app.tools.registry import reset_tool_registry
from app.trace.store import TraceStore


# ── TraceStore ─────────────────────────────────────────────────────────

def test_trace_store_roundtrip(tmp_path):
    store = TraceStore(storage_dir=tmp_path)
    payload = {"trace_id": "trc-1", "decisions": [], "data_flow": [], "audit": None}
    store.save(payload)

    assert store.exists("trc-1")
    assert store.load("trc-1") == payload


def test_trace_store_missing_returns_none(tmp_path):
    store = TraceStore(storage_dir=tmp_path)
    assert store.load("nope") is None
    assert store.exists("nope") is False


def test_trace_store_redacts_sensitive_fields(tmp_path):
    store = TraceStore(storage_dir=tmp_path)
    payload = {
        "trace_id": "trc-secret",
        "api_key": "sk-123",
        "nested": {"authorization": "Bearer xyz", "ok": 1},
        "access_token": "tok",
    }
    store.save(payload)
    loaded = store.load("trc-secret")

    assert loaded["api_key"] == "[REDACTED]"
    assert loaded["access_token"] == "[REDACTED]"
    assert loaded["nested"]["authorization"] == "[REDACTED]"
    assert loaded["nested"]["ok"] == 1


# ── /replay endpoint ───────────────────────────────────────────────────

@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKDOOR_TRACE_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr("configs.settings._settings", None)
    from app.core.config import reset_config

    reset_config()
    reset_tool_registry()
    register_tools()
    return create_app()


@pytest.mark.asyncio
async def test_replay_endpoint_returns_persisted_trace(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run = await client.post(
            "/run_hybrid",
            json={"message": "检测模型后门", "model_path": "m.h5"},
            timeout=30.0,
        )
        assert run.status_code == 200
        trace_id = run.json()["trace_id"]

        resp = await client.get(f"/replay/{trace_id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["trace_id"] == trace_id
    assert "decisions" in data
    assert "data_flow" in data
    assert "audit" in data


@pytest.mark.asyncio
async def test_replay_endpoint_unknown_id_returns_404(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/replay/does-not-exist")

    assert resp.status_code == 404
