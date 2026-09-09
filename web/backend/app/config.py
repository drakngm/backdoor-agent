"""BFF configuration."""

import os

HOST = os.getenv("BFF_HOST", "0.0.0.0")
PORT = int(os.getenv("BFF_PORT", "8001"))

# URL of the core FastAPI backend (app/main.py). Set empty to always use mock data.
CORE_API_URL = os.getenv("CORE_API_URL", "http://localhost:8000")

# When True, the BFF falls back to locally generated mock data if the core
# backend cannot be reached in time.
ALLOW_MOCK_FALLBACK = os.getenv("ALLOW_MOCK_FALLBACK", "true").lower() in ("1", "true", "yes")

CORE_TIMEOUT_SECONDS = float(os.getenv("CORE_TIMEOUT_SECONDS", "15"))