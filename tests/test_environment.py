import pathlib

import pytest

from speedtest import environment


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
