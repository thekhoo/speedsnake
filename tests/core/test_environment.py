import pathlib

import pytest

from speedtest.service import environment


class TestGetSleepSeconds:
    def test_default_value(self, monkeypatch):
        monkeypatch.delenv("SLEEP_SECONDS", raising=False)
        assert environment.get_sleep_seconds() == 5

    def test_custom_value(self, monkeypatch):
        monkeypatch.setenv("SLEEP_SECONDS", "600")
        assert environment.get_sleep_seconds() == 600

    def test_converts_string_to_int(self, monkeypatch):
        monkeypatch.setenv("SLEEP_SECONDS", "120")
        result = environment.get_sleep_seconds()
        assert isinstance(result, int)
        assert result == 120

    def test_invalid_value_raises_error(self, monkeypatch):
        monkeypatch.setenv("SLEEP_SECONDS", "invalid")
        with pytest.raises(ValueError):
            environment.get_sleep_seconds()


class TestGetResultDir:
    def test_default_value(self, monkeypatch):
        monkeypatch.delenv("RESULT_DIR", raising=False)
        assert environment.get_result_dir() == pathlib.Path("./results")

    def test_custom_value(self, monkeypatch):
        monkeypatch.setenv("RESULT_DIR", "/custom/path")
        assert environment.get_result_dir() == pathlib.Path("/custom/path")

    def test_returns_pathlib_path(self, monkeypatch):
        monkeypatch.setenv("RESULT_DIR", "/some/dir")
        result = environment.get_result_dir()
        assert isinstance(result, pathlib.Path)


class TestGetLogDir:
    def test_default_value(self, monkeypatch):
        monkeypatch.delenv("LOG_DIR", raising=False)
        assert environment.get_log_dir() == pathlib.Path("./logs")

    def test_custom_value(self, monkeypatch):
        monkeypatch.setenv("LOG_DIR", "/var/log/speedtest")
        assert environment.get_log_dir() == pathlib.Path("/var/log/speedtest")

    def test_returns_pathlib_path(self, monkeypatch):
        monkeypatch.setenv("LOG_DIR", "/some/log/dir")
        result = environment.get_log_dir()
        assert isinstance(result, pathlib.Path)


class TestGetUploadDir:
    def test_default_value(self, monkeypatch):
        monkeypatch.delenv("UPLOAD_DIR", raising=False)
        assert environment.get_upload_dir() == pathlib.Path("./uploads")

    def test_custom_value(self, monkeypatch):
        monkeypatch.setenv("UPLOAD_DIR", "/app/uploads")
        assert environment.get_upload_dir() == pathlib.Path("/app/uploads")

    def test_returns_pathlib_path(self, monkeypatch):
        monkeypatch.setenv("UPLOAD_DIR", "/custom/uploads")
        result = environment.get_upload_dir()
        assert isinstance(result, pathlib.Path)


class TestGetSpeedtestLocationUuid:
    def test_default_value(self, monkeypatch):
        monkeypatch.delenv("SPEEDTEST_LOCATION_UUID", raising=False)
        assert environment.get_speedtest_location_uuid() == "unknown-location"

    def test_custom_value(self, monkeypatch):
        monkeypatch.setenv("SPEEDTEST_LOCATION_UUID", "550e8400-e29b-41d4-a716-446655440000")
        assert environment.get_speedtest_location_uuid() == "550e8400-e29b-41d4-a716-446655440000"

    def test_returns_string(self, monkeypatch):
        monkeypatch.setenv("SPEEDTEST_LOCATION_UUID", "test-uuid")
        result = environment.get_speedtest_location_uuid()
        assert isinstance(result, str)
