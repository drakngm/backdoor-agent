"""Aggregated read routes: memory, traces, logs, threats, resources."""

from fastapi import APIRouter

from .. import mock_data
from .. import core_client

router = APIRouter(tags=["Telemetry"])


@router.get("/memory/stats")
async def memory_stats():
    return core_client.mock(mock_data.memory)


@router.get("/traces")
async def traces():
    return core_client.mock(mock_data.traces)


@router.get("/logs")
async def logs():
    return core_client.mock(mock_data.logs)


@router.get("/threats")
async def threats():
    return core_client.mock(mock_data.threats)


@router.get("/system/resources")
async def resources():
    return core_client.mock(mock_data.resources)
