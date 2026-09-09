"""Detection-related read routes."""

from fastapi import APIRouter, Query

from .. import mock_data

router = APIRouter(prefix="/detection", tags=["Detection"])


@router.get("/timeline")
async def timeline(points: int = Query(default=40, ge=2, le=200)):
    return mock_data.timeline(points)


@router.get("/detectors")
async def detectors():
    return mock_data.detectors()