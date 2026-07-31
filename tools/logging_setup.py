"""Structured logging setup.

Every major workflow logs: timestamp, agent, workflow, execution duration,
status, error details (constitution Logging standard, plan.md §12, FR-020).
Secrets and transcript content must never be written to logs — log_event()
redacts any field whose name suggests it holds one, as a defensive backstop
on top of callers simply not passing that data in the first place.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

_REDACT_KEY_SUBSTRINGS = ("transcript", "token", "password", "secret", "api_key", "credential")


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "agent": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "fields"):
            payload.update(record.fields)  # type: ignore[attr-defined]
        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(logging.INFO)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")
    file_handler.setFormatter(_JsonFormatter())
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(_JsonFormatter())

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False
    return logger


def _redact(fields: dict) -> dict:
    redacted = {}
    for key, value in fields.items():
        if any(s in key.lower() for s in _REDACT_KEY_SUBSTRINGS):
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = value
    return redacted


def log_event(
    logger: logging.Logger,
    *,
    workflow: str,
    event: str,
    status: str,
    duration_ms: float | None = None,
    error: str | None = None,
    **extra,
) -> None:
    fields = _redact(
        {
            "workflow": workflow,
            "event": event,
            "status": status,
            "duration_ms": duration_ms,
            "error": error,
            **extra,
        }
    )
    level = logging.ERROR if status == "failed" else logging.INFO
    logger.log(level, event, extra={"fields": fields})


@contextmanager
def timed_event(logger: logging.Logger, *, workflow: str, event: str, **extra):
    """Usage: with timed_event(logger, workflow="meeting_workflow", event="process"): ..."""
    start = time.monotonic()
    try:
        yield
    except Exception as exc:  # noqa: BLE001 - re-raised after logging
        duration_ms = (time.monotonic() - start) * 1000
        log_event(
            logger,
            workflow=workflow,
            event=event,
            status="failed",
            duration_ms=duration_ms,
            error=str(exc),
            **extra,
        )
        raise
    else:
        duration_ms = (time.monotonic() - start) * 1000
        log_event(
            logger, workflow=workflow, event=event, status="success", duration_ms=duration_ms, **extra
        )
