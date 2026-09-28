"""API router aggregator."""

from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.agent import router as agent_router
from app.api.workflow import router as workflow_router
from app.api.hybrid import router as hybrid_router
from app.api.replay import router as replay_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(agent_router, tags=["Agent"])
api_router.include_router(workflow_router, tags=["Workflow"])
api_router.include_router(hybrid_router, tags=["Hybrid"])
api_router.include_router(replay_router, tags=["Trace"])