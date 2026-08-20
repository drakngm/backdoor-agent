"""
L3: Project Memory — cross-session persistent storage.

Lifecycle: cross-session, persistent
Capacity: project-level (multiple detection tasks)
Storage: JSON file (MVP) → SQLite/Redis later

Stores historical detection reports, model fingerprints, and
discovered threats for future reference.
"""

import json
import os
from hashlib import sha256
from typing import Any, Optional

from app.memory.base import BaseMemory
from app.core.config import get_config
from app.core.logging import get_logger

logger = get_logger(__name__)


class ProjectMemory(BaseMemory):
    """
    Persistent memory shared across sessions.

    Stores:
      - reports: report_id → structured report dict
      - models: model_hash → model fingerprint metadata
      - findings: list of threat findings across all scans

    On init, loads from JSON file. On each save, writes back to disk.
    """

    def __init__(self, filepath: Optional[str] = None):
        self._filepath = filepath or get_config().project_memory_path
        self._storage: dict[str, Any] = {}
        self.reports: dict[str, dict[str, Any]] = {}
        self.models: dict[str, dict[str, Any]] = {}
        self.findings: list[dict[str, Any]] = []
        self._load()

    # ── BaseMemory interface ────────────────────────────────────────

    def store(self, key: str, value: Any) -> None:
        self._storage[key] = value

    def retrieve(self, key: str) -> Optional[Any]:
        return self._storage.get(key)

    def clear(self) -> None:
        self.reports.clear()
        self.models.clear()
        self.findings.clear()
        self._storage.clear()

    def snapshot(self) -> dict[str, Any]:
        return {
            "reports_count": len(self.reports),
            "models_count": len(self.models),
            "findings_count": len(self.findings),
            "filepath": self._filepath,
        }

    # ── Report management ───────────────────────────────────────────

    def save_report(self, report_id: str, report: dict[str, Any]) -> None:
        """Persist a detection report."""
        self.reports[report_id] = report
        self._persist()
        logger.info(f"Report saved: {report_id}")

    def get_report(self, report_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a report by ID."""
        return self.reports.get(report_id)

    def list_reports(self) -> list[str]:
        """List all report IDs."""
        return list(self.reports.keys())

    # ── Model fingerprinting ────────────────────────────────────────

    def register_model(self, model_path: str, metadata: dict[str, Any]) -> str:
        """
        Register a model with its fingerprint.

        Returns: model_hash (sha256 of path)
        """
        model_hash = sha256(model_path.encode()).hexdigest()[:16]
        self.models[model_hash] = {
            "path": model_path,
            "first_seen": metadata.get("first_seen", ""),
            "metadata": metadata,
        }
        self._persist()
        return model_hash

    def get_model_history(self, model_hash: str) -> Optional[dict[str, Any]]:
        """Get historical data for a model."""
        return self.models.get(model_hash)

    # ── Findings ────────────────────────────────────────────────────

    def add_finding(self, finding: dict[str, Any]) -> None:
        """Log a threat finding."""
        self.findings.append(finding)
        self._persist()

    def query_findings_by_type(self, threat_type: str) -> list[dict[str, Any]]:
        """Filter findings by threat type."""
        return [f for f in self.findings if f.get("type") == threat_type]

    def query_findings_by_risk(self, risk_level: str) -> list[dict[str, Any]]:
        """Filter findings by risk level."""
        return [f for f in self.findings if f.get("risk_level") == risk_level]

    # ── Persistence ─────────────────────────────────────────────────

    def _persist(self) -> None:
        """Write current state to JSON file."""
        try:
            os.makedirs(os.path.dirname(self._filepath), exist_ok=True)
            data = {
                "reports": self.reports,
                "models": self.models,
                "findings": self.findings,
            }
            with open(self._filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to persist project memory: {e}")

    def _load(self) -> None:
        """Load state from JSON file (if exists)."""
        if not os.path.exists(self._filepath):
            logger.info(f"No existing project memory at {self._filepath}, starting fresh")
            return

        try:
            with open(self._filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.reports = data.get("reports", {})
            self.models = data.get("models", {})
            self.findings = data.get("findings", [])
            logger.info(
                f"Loaded project memory: {len(self.reports)} reports, "
                f"{len(self.models)} models, {len(self.findings)} findings"
            )
        except Exception as e:
            logger.error(f"Failed to load project memory: {e}")
            self.reports = {}
            self.models = {}
            self.findings = []