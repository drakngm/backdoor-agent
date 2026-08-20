"""Agent Mode API endpoint."""

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from app.entry.dispatcher import Dispatcher
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class AgentRequest(BaseModel):
    message: str = Field(..., description="User message for the agent", min_length=1)
    trace_id: str | None = None


@router.post("/run_agent")
async def run_agent(req: AgentRequest):
    """Execute Agent Mode: LLM → Tool → Observation loop."""
    try:
        dispatcher = Dispatcher()
        result = await dispatcher.dispatch(
            mode="agent",
            input_data={"message": req.message},
            trace_id=req.trace_id,
        )
        return result
    except Exception as e:
        logger.error(f"/run_agent failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))