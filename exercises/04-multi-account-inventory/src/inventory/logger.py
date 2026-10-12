"""Structured logging. Given to you complete - it is the pattern, not the exercise.

Same shape as E01: one JSON object per line, on stdout, with the log message as
the event name. stdout rather than stderr or a file because in a container or a
CI runner, stdout is the only stream anything reliably collects.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    """One JSON object per line. The log message is the event name."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname.lower(),
            "event": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        return json.dumps(payload, default=str)


def get_logger(name: str = "inventory", level: int = logging.INFO) -> logging.Logger:
    """Configure and return the package logger. Idempotent - safe to call twice."""
    logger = logging.getLogger(name)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False
    return logger


__all__ = ["JsonFormatter", "get_logger"]
