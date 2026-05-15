"""
Structured logging configuration for the VMTips backend.

- Production (LOG_FORMAT=json): emits one JSON object per log line via
  python-json-logger.
- Development (default): human-readable console output.

Every log record automatically includes: timestamp, level, logger name,
and (when available) request_id.
"""
import logging
import os
import sys
import uuid
from contextvars import ContextVar

from pythonjsonlogger import json as json_formatter

# Context variable set per-request by the logging middleware.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class _RequestIdFilter(logging.Filter):
    """Inject the current request_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get("-")
        return True


def _human_formatter() -> logging.Formatter:
    fmt = "%(asctime)s [%(request_id)s] %(levelname)s %(name)s: %(message)s"
    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")
    return formatter


def _json_formatter() -> json_formatter.JsonFormatter:
    return json_formatter.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def setup_logging() -> None:
    """Configure the root logger according to the LOG_FORMAT env variable."""
    log_format = os.getenv("LOG_FORMAT", "human").lower()
    handler = logging.StreamHandler(sys.stdout)

    if log_format == "json":
        handler.setFormatter(_json_formatter())
    else:
        handler.setFormatter(_human_formatter())

    handler.addFilter(_RequestIdFilter())

    root = logging.getLogger()
    # Remove existing handlers to avoid duplicates on reload
    root.handlers.clear()
    root.addHandler(handler)

    level = os.getenv("LOG_LEVEL", "INFO").upper()
    root.setLevel(getattr(logging, level, logging.INFO))

    # Quiet down noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)