"""Workflow / DAG read routes."""

from fastapi import APIRouter

from .. import mock_data
from .. import core_client

router = APIRouter(prefix="/workflow", tags=["Workflow"])


@router.get("/dag/live")
async def live_dag():
    return core_client.mock(mock_data.dag)
