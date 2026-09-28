"""
TraceStore: local JSON persistence for execution traces.

Traces are stored content-addressed by `trace_id` under the configured
`trace_storage_dir`, written atomically (temp file + rename). Sensitive fields
(API keys, tokens, credentials) are redacted before writing so the on-disk audit
trail never records secrets (NFR-5).
"""

import json
import os
from pathlib import Path
from typing import Any, Optional

from configs.settings import get_settings

_SENSITIVE_MARKERS = (
    "token",
    "secret",
    "password",
    "credential",
    "api_key",
    "apikey",
    "api-key",
    "authorization",
)


def _is_sensitive(key: str) -> bool:
    k = key.lower()
    return any(m in k for m in _SENSITIVE_MARKERS)


def redact(value: Any) -> Any:
    """Recursively replace sensitive values with a placeholder."""
    if isinstance(value, dict):
        return {
            k: ("[REDACTED]" if _is_sensitive(str(k)) else redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


class TraceStore:
    """Local JSON trace persistence keyed by trace_id."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(
            storage_dir if storage_dir is not None else get_settings().trace_storage_dir
        )

    def _path(self, trace_id: str) -> Path:
        return self.storage_dir / f"{trace_id}.json"

    def save(self, payload: dict[str, Any]) -> None:
        """Persist a trace payload atomically, redacting sensitive fields."""
        trace_id = payload["trace_id"]
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        target = self._path(trace_id)
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(redact(payload), ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        os.replace(tmp, target)

    def load(self, trace_id: str) -> Optional[dict[str, Any]]:
        """Return the persisted trace, or None if not found."""
        target = self._path(trace_id)
        if not target.exists():
            return None
        return json.loads(target.read_text(encoding="utf-8"))

    def exists(self, trace_id: str) -> bool:
        return self._path(trace_id).exists()
