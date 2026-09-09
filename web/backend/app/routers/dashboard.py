"""Dashboard read-model routes (BFF)."""

from fastapi import APIRouter

from .. import mock_data

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/health")
async def health():
    return mock_data.health()


@router.get("/overview")
async def overview():
    return mock_data.overview()


@router.get("/overview/metrics")
async def metrics():
    return mock_data.metrics()