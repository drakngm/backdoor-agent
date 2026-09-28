"""Tests for the BFF connecting to the core backend (prefer core, label source)."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app as bff_app
from app import config, core_client


def _client():
    return AsyncClient(transport=ASGITransport(app=bff_app), base_url="http://test")


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(config, "CORE_API_URL", "http://core")
    monkeypatch.setattr(config, "ALLOW_MOCK_FALLBACK", True)


@pytest.mark.asyncio
async def test_dashboard_health_prefers_core(monkeypatch):
    async def fake_get(path, timeout=None):
        return {
            "status": "ok",
            "app": "backdoor-agent",
            "version": "0.1.0",
            "tools_registered": 3,
            "tools": ["strip_detect_real", "neural_cleanse_real"],
            "strategies": ["fast_scan"],
        }

    monkeypatch.setattr(core_client, "get_json", fake_get)

    async with _client() as client:
        resp = await client.get("/dashboard/health")

    data = resp.json()
    assert resp.status_code == 200
    assert data["source"] == "core"
    assert data["backend_connected"] is True
    assert "strip_detect_real" in data["tools"]


@pytest.mark.asyncio
async def test_dashboard_health_falls_back_to_mock(monkeypatch):
    async def fake_get(path, timeout=None):
        return None

    monkeypatch.setattr(core_client, "get_json", fake_get)

    async with _client() as client:
        resp = await client.get("/dashboard/health")

    data = resp.json()
    assert resp.status_code == 200
    assert data["source"] == "mock"


@pytest.mark.asyncio
async def test_dashboard_health_503_when_fallback_disabled(monkeypatch):
    async def fake_get(path, timeout=None):
        return None

    monkeypatch.setattr(core_client, "get_json", fake_get)
    monkeypatch.setattr(config, "ALLOW_MOCK_FALLBACK", False)

    async with _client() as client:
        resp = await client.get("/dashboard/health")

    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_detectors_derived_from_core_tools(monkeypatch):
    async def fake_get(path, timeout=None):
        return {"tools": ["strip_detect_real", "neural_cleanse_real"]}

    monkeypatch.setattr(core_client, "get_json", fake_get)

    async with _client() as client:
        resp = await client.get("/detection/detectors")

    data = resp.json()
    assert isinstance(data, list)
    assert all(d["source"] == "core" for d in data)
    assert {d["name"] for d in data} == {"strip_detect_real", "neural_cleanse_real"}


@pytest.mark.asyncio
async def test_mock_only_endpoint_labels_source():
    async with _client() as client:
        resp = await client.get("/dashboard/overview")

    data = resp.json()
    assert resp.status_code == 200
    assert data["source"] == "mock"
