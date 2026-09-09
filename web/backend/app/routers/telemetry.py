"""Aggregated read routes: memory, traces, logs, threats, resources."""

from fastapi import APIRouter

from .. import mock_data

router = APIRouter(tags=["Telemetry"])


@router.get("/memory/stats")
async def memory_stats():
    return mock_data.memory()


@router.get("/traces")
async def traces():
    return mock_data.traces()


@router.get("/logs")
async def logs():
    return mock_data.logs()


@router.get("/threats")
async def threats():
    return mock_data.threats()


@router.get("/system/resources")
async def resources():
    return mock_data.resources()