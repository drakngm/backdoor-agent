"""Detection-related read routes."""

from fastapi import APIRouter, Query

from .. import mock_data
from .. import core_client

router = APIRouter(prefix="/detection", tags=["Detection"])


def _core_tools_to_detectors(h: dict) -> list[dict]:
    return [
        {
            "name": t,
            "display": t,
            "description": "",
            "status": "active",
            "last_run_ms": 0,
            "detections": 0,
            "precision": 1.0,
        }
        for t in h.get("tools", [])
    ]


@router.get("/timeline")
async def timeline(points: int = Query(default=40, ge=2, le=200)):
    return core_client.mock(mock_data.timeline, points)


@router.get("/detectors")
async def detectors():
    return await core_client.resolve(
        "/health", mock_data.detectors, transform=_core_tools_to_detectors
    )
