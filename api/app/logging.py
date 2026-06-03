"""Structured logging configuration."""

import logging
import sys
from typing import Any

from pythonjsonlogger.json import JsonFormatter

from app.config import Settings


class _ContextFilter(logging.Filter):
    """Inject static application context into every log record."""

    def __init__(self, app_name: str, environment: str) -> None:
        super().__init__()
        self._app_name = app_name
        self._environment = environment

    def filter(self, record: logging.LogRecord) -> bool:
        record.app_name = self._app_name  # type: ignore[attr-defined]
        record.environment = self._environment  # type: ignore[attr-defined]
        return True


def configure_logging(settings: Settings) -> None:
    """Configure root logger once at application startup."""
    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_ContextFilter(settings.app_name, settings.environment))

    if settings.log_json:
        formatter = JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
            static_fields={"service": "api"},
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(settings.log_level)

    # Quiet noisy third-party loggers in production
    for logger_name in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(logger_name).setLevel(
            logging.WARNING if settings.is_production else logging.INFO
        )


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger."""
    return logging.getLogger(name)


def log_extra(**kwargs: Any) -> dict[str, Any]:
    """Helper for attaching structured fields to a log call."""
    return kwargs
