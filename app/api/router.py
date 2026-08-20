"""API router aggregator."""

from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.agent import router as agent_router
from app.api.workflow import router as workflow_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(agent_router, tags=["Agent"])
api_router.include_router(workflow_router, tags=["Workflow"])