"""Workflow / DAG read routes."""

from fastapi import APIRouter

from .. import mock_data

router = APIRouter(prefix="/workflow", tags=["Workflow"])


@router.get("/dag/live")
async def live_dag():
    return mock_data.dag()