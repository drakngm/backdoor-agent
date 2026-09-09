"""BFF (Backend-for-Frontend) for the AI Backdoor Detection Command Center.

Serves dashboard/read models to the frontend and proxies execution runs to
the core FastAPI backend (../app in repo root), degrading to mock data when
the core backend is unavailable.

Run:  uvicorn app.main:app --port 8001  (from this directory)
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .routers import dashboard, detection, workflow, telemetry, execute

logger = logging.getLogger("bff")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="AI Backdoor Command Center · BFF",
    version="1.0.0",
    description="Backend-for-Frontend aggregating dashboard telemetry and proxying execution to the core agent system.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(detection.router)
app.include_router(workflow.router)
app.include_router(telemetry.router)
app.include_router(execute.router)


@app.get("/")
async def root():
    return {
        "service": "command-center-bff",
        "version": "1.0.0",
        "core_api": config.CORE_API_URL or "disabled",
        "mock_fallback": config.ALLOW_MOCK_FALLBACK,
        "endpoints": ["/dashboard/*", "/detection/*", "/workflow/*", "/memory/stats", "/traces", "/logs", "/threats", "/system/resources", "/execute/{mode}"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT)