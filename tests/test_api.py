"""Tests for FastAPI endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import create_app, register_tools
from app.tools.registry import reset_tool_registry


@pytest.fixture
def app():
    reset_tool_registry()
    register_tools()  # Manually register tools (lifespan doesn't fire in ASGITransport)
    return create_app()


@pytest.mark.asyncio
async def test_health_check(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "tools_registered" in data
    assert "strategies" in data


@pytest.mark.asyncio
async def test_run_agent(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/run_agent",
            json={"message": "Detect backdoors in model.h5"},
            timeout=30.0,
        )
    assert response.status_code == 200
    data = response.json()
    assert "trace_id" in data
    assert "spans" in data
    assert "mermaid" in data


@pytest.mark.asyncio
async def test_run_workflow_fast_scan(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/run_workflow",
            json={"strategy": "fast_scan", "model_path": "model.h5"},
            timeout=30.0,
        )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "workflow"
    assert data["strategy"] == "fast_scan"