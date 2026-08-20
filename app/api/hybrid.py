"""Hybrid Mode API endpoint."""

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from app.entry.dispatcher import Dispatcher
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class HybridRequest(BaseModel):
    message: str = Field(..., description="Detection task description", min_length=1)
    model_path: str = Field(default="model.h5", description="Path to the model file")
    trace_id: str | None = None

    model_config = {"protected_namespaces": ()}


@router.post("/run_hybrid")
async def run_hybrid(req: HybridRequest):
    """Execute Hybrid Mode: Agent Loop decisions → DAG Workflow execution."""
    try:
        dispatcher = Dispatcher()
        result = await dispatcher.dispatch(
            mode="hybrid",
            input_data={"message": req.message, "model_path": req.model_path},
            trace_id=req.trace_id,
        )
        return result
    except Exception as e:
        logger.error(f"/run_hybrid failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
