"""Execution proxy: forwards agent/workflow/hybrid runs to the core backend,
with a mock-data fallback when the core backend is unreachable."""

import asyncio
import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import config
from .. import mock_data

logger = logging.getLogger("bff.execute")
router = APIRouter(prefix="/execute", tags=["Execute"])


class ExecuteRequest(BaseModel):
    message: str | None = None
    strategy: str | None = None
    model_path: str | None = None
    trace_id: str | None = None

    model_config = {"protected_namespaces": ()}


_CORE_ENDPOINTS = {
    "agent": "/run_agent",
    "workflow": "/run_workflow",
    "hybrid": "/run_hybrid",
}


async def _call_core(mode: str, req: ExecuteRequest) -> dict | None:
    if not config.CORE_API_URL:
        return None
    url = f"{config.CORE_API_URL}{_CORE_ENDPOINTS[mode]}"
    payload: dict[str, str] = {}
    for key in ("message", "strategy", "model_path"):
        value = getattr(req, key)
        if value:
            payload[key] = value
    if req.trace_id:
        payload["trace_id"] = req.trace_id

    try:
        async with asyncio.timeout(config.CORE_TIMEOUT_SECONDS):
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                data["source"] = "backend"
                return data
    except Exception as exc:  # noqa: BLE001
        logger.warning("Core backend unreachable (%s), falling back to mock: %s", mode, exc)
        return None


@router.post("/{mode}")
async def execute(mode: str, req: ExecuteRequest):
    if mode not in _CORE_ENDPOINTS:
        raise HTTPException(status_code=404, detail=f"unknown mode: {mode}")

    core = await _call_core(mode, req)
    if core is not None:
        return core
    if not config.ALLOW_MOCK_FALLBACK:
        raise HTTPException(status_code=503, detail="core backend unavailable and mock fallback disabled")
    return mock_data.execute(mode)


@router.get("/health")
async def execute_health():
    alive = False
    if config.CORE_API_URL:
        try:
            async with asyncio.timeout(3):
                async with httpx.AsyncClient() as client:
                    r = await client.get(f"{config.CORE_API_URL}/health")
                alive = r.is_success
        except Exception:  # noqa: BLE001
            alive = False
    return {"core_backend_connected": alive, "mock_fallback_enabled": config.ALLOW_MOCK_FALLBACK}