"""Dashboard read-model routes (BFF)."""

from fastapi import APIRouter

from .. import mock_data
from .. import core_client

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _core_health(h: dict) -> dict:
    return {
        "status": "operational" if h.get("status") == "ok" else "down",
        "app": h.get("app", "backdoor-agent"),
        "version": h.get("version", ""),
        "uptime_seconds": 0,
        "tools": h.get("tools", []),
        "backend_connected": True,
    }


@router.get("/health")
async def health():
    return await core_client.resolve("/health", mock_data.health, transform=_core_health)


@router.get("/overview")
async def overview():
    return core_client.mock(mock_data.overview)


@router.get("/overview/metrics")
async def metrics():
    return core_client.mock(mock_data.metrics)
