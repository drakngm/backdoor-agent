"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Return system health status."""
    from app.tools.registry import get_tool_registry
    from app.workflow.planner import Planner

    registry = get_tool_registry()
    planner = Planner()

    return {
        "status": "ok",
        "app": "backdoor-agent",
        "version": "0.1.0",
        "tools_registered": len(registry),
        "tools": registry.list_names(),
        "strategies": planner.list_strategies(),
    }