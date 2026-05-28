"""Application logging configuration.

Provides ``setup_logging()`` which configures JSON-formatted or
console-formatted logs depending on the ``LOG_FORMAT`` env var.
"""

from __future__ import annotations

import json
import logging
import logging.config
import os


class JsonFormatter(logging.Formatter):
    """Output log records as newline-delimited JSON."""

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            },
            default=str,
        )


def setup_logging() -> None:
    """Configure root logger based on environment variables."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "console").lower()

    config: dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "level": log_level,
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
    }

    if log_format == "json":
        config["handlers"]["console"]["formatter"] = "json"
        config["formatters"] = {
            "json": {
                "()": JsonFormatter,
            },
        }
    else:
        config["handlers"]["console"]["formatter"] = "default"
        config["formatters"] = {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%H:%M:%S",
            },
        }

    logging.config.dictConfig(config)
    logging.getLogger(__name__).debug("Logging configured (format=%s, level=%s)", log_format, log_level)
