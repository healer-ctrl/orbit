import os
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .tracer import get_current_trace_id, get_current_span_id, get_current_traceparent


class StructuredJsonFormatter(logging.Formatter):
    """
    Enterprise Structured JSON Formatter.
    Formats logs into JSON objects enriched with OpenTelemetry distributed trace context:
    - trace_id
    - span_id
    - traceparent (W3C standard)
    - service name & version
    - environment
    - timestamp in ISO 8601 UTC
    """

    def __init__(
        self,
        service_name: str = "mailmind-backend",
        environment: str = "production",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "environment": self.environment,
            "trace_id": getattr(record, "trace_id", None) or get_current_trace_id(),
            "span_id": getattr(record, "span_id", None) or get_current_span_id(),
            "traceparent": getattr(record, "traceparent", None) or get_current_traceparent(),
        }

        # Source code location
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_entry["stack_info"] = self.formatStack(record.stack_info)

        # Include custom extra attributes passed via logging calls
        standard_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "trace_id", "span_id", "traceparent",
        }
        extra_fields = {
            k: v for k, v in record.__dict__.items() if k not in standard_attrs and not k.startswith("_")
        }
        if extra_fields:
            log_entry["context"] = extra_fields

        return json.dumps(log_entry, default=str)


def setup_logging(
    level: str = "INFO",
    service_name: str = "mailmind-backend",
    environment: Optional[str] = None,
) -> None:
    """
    Configures standard library and Uvicorn loggers to use structured JSON logging.
    """
    env = environment or os.getenv("ENVIRONMENT", "production")
    log_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicate output
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJsonFormatter(service_name=service_name, environment=env))
    root_logger.addHandler(handler)

    # Intercept common loggers
    for logger_name in ["mailmind", "uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]:
        log = logging.getLogger(logger_name)
        log.handlers = []
        log.propagate = True
