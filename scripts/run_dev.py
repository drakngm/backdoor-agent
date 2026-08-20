#!/usr/bin/env python
"""
Development server launcher.

Usage:
    python scripts/run_dev.py
    uvicorn app.main:app --reload
"""

import sys
import os

# Ensure the project root (parent of scripts/) is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import uvicorn
from app.core.config import get_config

if __name__ == "__main__":
    config = get_config()
    print(f"Starting {config.app_name} v{config.app_version}")
    print(f"API docs: http://{config.host}:{config.port}/docs")
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=True,
        log_level="info",
    )