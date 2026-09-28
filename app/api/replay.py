"""Replay endpoint: retrieve a persisted execution trace by trace_id."""

from fastapi import APIRouter, HTTPException

from app.trace.store import TraceStore

router = APIRouter()


@router.get("/replay/{trace_id}")
async def replay(trace_id: str):
    """Return the full audit chain for a previously executed detection run."""
    payload = TraceStore().load(trace_id)
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "trace not found", "trace_id": trace_id},
        )
    return payload
