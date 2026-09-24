import logging
import sys
from datetime import datetime, UTC
import json

class LoggerFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
        }

        extra = getattr(record, "fields")
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload)

def get_logger(name: str = "healthchecker", level = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)

    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(LoggerFormatter())
    logger.addHandler(handler)
    logger.propagate = False

    return logger

__all__ = ["get_logger"]