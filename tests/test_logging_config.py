"""Tests for the logging configuration."""

from __future__ import annotations

import json
import logging

from backend.logging_config import JsonFormatter, setup_logging


class TestJsonFormatter:
    def test_json_formatter_output(self):
        fmt = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=42,
            msg="hello %s",
            args=("world",),
            exc_info=None,
        )
        output = fmt.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test_logger"
        assert parsed["message"] == "hello world"

    def test_json_formatter_includes_timestamp(self):
        fmt = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="", lineno=0,
            msg="test", args=(), exc_info=None,
        )
        output = fmt.format(record)
        parsed = json.loads(output)
        assert "timestamp" in parsed


class TestSetupLogging:
    def test_setup_logging_console_format(self, monkeypatch):
        monkeypatch.setenv("LOG_FORMAT", "console")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        setup_logging()
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_setup_logging_json_format(self, monkeypatch):
        monkeypatch.setenv("LOG_FORMAT", "json")
        monkeypatch.setenv("LOG_LEVEL", "INFO")
        setup_logging()
        root = logging.getLogger()
        assert root.level == logging.INFO
        handler = root.handlers[0]
        assert isinstance(handler.formatter, JsonFormatter)
