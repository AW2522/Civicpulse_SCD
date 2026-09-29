import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class JSONFormatter(logging.Formatter):
    """
    Custom JSON Log Formatter that formats log records into structured JSON
    including timestamp, log level, request_id context variable, logger name, and message.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_record: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "request_id": request_id_ctx.get() or "N/A",
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Include extra fields passed to logger if present
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_record.update(record.extra_fields)

        return json.dumps(log_record)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configures root logger with stdout JSON handler."""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Silence verbose third-party loggers
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = True

    return root_logger


logger = logging.getLogger("civicpulse")
