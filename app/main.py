"""
FastAPI application entry point.

On startup:
  - Registers all available tools into ToolRegistry
  - Initializes configuration

Endpoints:
  GET  /health        → System health + tool list
  POST /run_agent     → Agent Mode (LLM → Tool → Loop)
  POST /run_workflow  → Workflow Mode (Planner → DAG → Execute)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.tools.registry import get_tool_registry
from app.tools.mock_strip import MockSTRIPDetector
from app.tools.mock_neural_cleanse import MockNeuralCleanseDetector
from app.tools.mock_activation_clustering import MockActivationClusteringDetector
from app.tools.strip_tool import STRIPTool
from app.core.config import get_config
from app.core.logging import get_logger

logger = get_logger(__name__)


def register_tools() -> None:
    """Register all available tools into the global ToolRegistry."""
    registry = get_tool_registry()
    registry.register(MockSTRIPDetector())
    registry.register(MockNeuralCleanseDetector())
    registry.register(MockActivationClusteringDetector())
    registry.register(STRIPTool())
    logger.info(f"Tools registered: {registry.list_names()}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup + shutdown."""
    # Startup
    config = get_config()
    logger.info(f"Starting {config.app_name} v{config.app_version}")
    register_tools()
    logger.info("Application startup complete")
    yield
    # Shutdown
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    config = get_config()

    app = FastAPI(
        title=config.app_name,
        version=config.app_version,
        description="AI Backdoor Detection & Defense Agent System",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(api_router)

    return app


# ── WSGI/ASGI entry point ──────────────────────────────────────────

app = create_app()

if __name__ == "__main__":
    import uvicorn
    config = get_config()
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
    )