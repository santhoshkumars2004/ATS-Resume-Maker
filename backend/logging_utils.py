"""Logging helpers for readable backend traces."""
from __future__ import annotations

import logging
import time
import uuid


class IgnoreHealthcheckFilter(logging.Filter):
    """Hide noisy health-check access logs from uvicorn."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return "/api/health" not in message


def configure_logging() -> None:
    """Install log filters exactly once."""
    access_logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, IgnoreHealthcheckFilter) for f in access_logger.filters):
        access_logger.addFilter(IgnoreHealthcheckFilter())


def new_run_id() -> str:
    """Create a short request id for tracing a pipeline run."""
    return uuid.uuid4().hex[:8]


def log_event(run_id: str, component: str, message: str) -> None:
    """Emit a consistent log line with a request id and timestamp."""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{run_id}] {component} | {message}")
