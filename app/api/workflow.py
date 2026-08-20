"""Workflow Mode API endpoint."""

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from app.entry.dispatcher import Dispatcher
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class WorkflowRequest(BaseModel):
    strategy: str = Field(default="fast_scan", description="Scan strategy: fast_scan, deep_scan, forensic_scan")
    model_path: str = Field(default="model.h5", description="Path to the model file")
    trace_id: str | None = None


@router.post("/run_workflow")
async def run_workflow(req: WorkflowRequest):
    """Execute Workflow Mode: Planner → DAG → Tool execution."""
    try:
        dispatcher = Dispatcher()
        result = await dispatcher.dispatch(
            mode="workflow",
            input_data={"strategy": req.strategy, "model_path": req.model_path},
            trace_id=req.trace_id,
        )
        return result
    except Exception as e:
        logger.error(f"/run_workflow failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))