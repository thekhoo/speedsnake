import json
import logging

import pytest

from speedtest.logging import JSONFormatter, setup_logging


class TestJSONFormatter:
    @pytest.fixture
    def formatter(self):
        return JSONFormatter()

    @pytest.fixture
    def log_record(self):
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        return record

    def test_format_returns_valid_json(self, formatter, log_record):
        result = formatter.format(log_record)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_format_includes_required_fields(self, formatter, log_record):
        result = formatter.format(log_record)
        parsed = json.loads(result)

        assert "timestamp" in parsed
        assert "level" in parsed
        assert "logger" in parsed
        assert "message" in parsed
        assert "module" in parsed
        assert "function" in parsed
        assert "line" in parsed

    def test_format_level_name(self, formatter, log_record):
        result = formatter.format(log_record)
        parsed = json.loads(result)
        assert parsed["level"] == "INFO"

    def test_format_message(self, formatter, log_record):
        result = formatter.format(log_record)
        parsed = json.loads(result)
        assert parsed["message"] == "Test message"

    def test_format_logger_name(self, formatter, log_record):
        result = formatter.format(log_record)
        parsed = json.loads(result)
        assert parsed["logger"] == "test.logger"

    def test_format_line_number(self, formatter, log_record):
        result = formatter.format(log_record)
        parsed = json.loads(result)
        assert parsed["line"] == 42

    def test_format_with_exception(self, formatter):
        import sys

        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="/path/to/file.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=exc_info,
            )

            result = formatter.format(record)
            parsed = json.loads(result)
            assert "exception" in parsed
            assert "ValueError" in parsed["exception"]


class TestSetupLogging:
    def test_setup_logging_creates_log_directory(self, tmp_path, monkeypatch):
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("LOG_DIR", str(log_dir))

        setup_logging()

        assert log_dir.exists()

    def test_setup_logging_configures_root_logger(self, tmp_path, monkeypatch):
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("LOG_DIR", str(log_dir))

        setup_logging(level=logging.DEBUG)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_setup_logging_adds_file_handler(self, tmp_path, monkeypatch):
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("LOG_DIR", str(log_dir))

        setup_logging()

        root_logger = logging.getLogger()
        handler_types = [type(h).__name__ for h in root_logger.handlers]
        assert "RotatingFileHandler" in handler_types

    def test_setup_logging_adds_console_handler(self, tmp_path, monkeypatch):
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("LOG_DIR", str(log_dir))

        setup_logging()

        root_logger = logging.getLogger()
        handler_types = [type(h).__name__ for h in root_logger.handlers]
        assert "StreamHandler" in handler_types

    def test_setup_logging_writes_json_to_file(self, tmp_path, monkeypatch):
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("LOG_DIR", str(log_dir))

        setup_logging()

        test_logger = logging.getLogger("test")
        test_logger.info("Test log message")

        log_file = log_dir / "speedtest.log"
        assert log_file.exists()

        content = log_file.read_text()
        parsed = json.loads(content.strip())
        assert parsed["message"] == "Test log message"
