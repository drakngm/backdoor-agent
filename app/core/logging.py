"""
Structured logging with trace-ID injection.

All logs carry the trace_id automatically via a context variable.
Usage:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("tool called", extra={"trace_id": trace_id})
"""

import logging
import sys
from typing import Optional


class TraceAwareFormatter(logging.Formatter):
    """Custom formatter that includes trace_id when present."""

    def format(self, record: logging.LogRecord) -> str:
        trace_id = getattr(record, "trace_id", "-")
        record.trace_id = trace_id
        fmt = f"[%(asctime)s] [%(levelname)s] [trace=%(trace_id)s] [%(name)s] %(message)s"
        self._style = logging.PercentStyle(fmt)
        self._fmt = fmt
        return super().format(record)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a trace-aware logger instance."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(TraceAwareFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    logger.setLevel(level)
    return logger


def inject_trace_id(logger: logging.Logger, trace_id: str) -> logging.Logger:
    """
    Return a LoggerAdapter that injects trace_id into every log record.
    Usage:
        logger = inject_trace_id(get_logger(__name__), "trc-abc123")
        logger.info("hello")  # trace_id automatically appended
    """
    return logging.LoggerAdapter(logger, {"trace_id": trace_id})  # type: ignore