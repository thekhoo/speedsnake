import pathlib
from unittest.mock import MagicMock, call, patch

import pytest

from speedtest.handlers import loop


class TestSleep:
    def test_sleep_calls_time_sleep(self):
        with patch("time.sleep") as mock_sleep:
            loop.sleep(10)
            mock_sleep.assert_called_once_with(10)

    def test_sleep_with_zero_seconds(self):
        with patch("time.sleep") as mock_sleep:
            loop.sleep(0)
            mock_sleep.assert_called_once_with(0)


class TestLoopDecorator:
    def test_loop_calls_function_repeatedly(self):
        call_count = 0

        @loop.loop
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                raise KeyboardInterrupt()

        with patch("speedtest.handlers.loop.sleep"):
            with pytest.raises(KeyboardInterrupt):
                test_func()

        assert call_count == 3

    def test_loop_continues_on_exception(self):
        call_count = 0

        @loop.loop
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Test error")
            raise KeyboardInterrupt()

        with patch("speedtest.handlers.loop.sleep"):
            with pytest.raises(KeyboardInterrupt):
                test_func()

        assert call_count == 3

    def test_loop_sleeps_between_calls(self):
        call_count = 0

        @loop.loop
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise KeyboardInterrupt()

        with patch("speedtest.handlers.loop.sleep") as mock_sleep:
            with patch("speedtest.environment.get_sleep_seconds", return_value=60):
                with pytest.raises(KeyboardInterrupt):
                    test_func()

        assert mock_sleep.call_count == 2

    def test_loop_preserves_function_name(self):
        @loop.loop
        def my_function():
            pass

        assert my_function.__name__ == "my_function"


class TestRun:
    @pytest.fixture
    def mock_speedtest_response(self):
        return {
            "download": 100000000,
            "upload": 20000000,
            "ping": 10,
            "timestamp": "2025-01-20T14:30:00.000000Z",
            "server": {},
            "client": {},
            "bytes_sent": 0,
            "bytes_received": 0,
            "share": None,
        }

    def test_run_executes_speedtest_and_saves_result(self, mock_speedtest_response, tmp_path, monkeypatch):
        monkeypatch.setenv("RESULT_DIR", str(tmp_path))
        monkeypatch.setenv("SLEEP_SECONDS", "1")

        call_count = 0

        def mock_speedtest_run():
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise KeyboardInterrupt()
            return mock_speedtest_response

        with patch("speedtest.speedtest.run", side_effect=mock_speedtest_run):
            with patch("speedtest.handlers.loop.sleep"):
                with pytest.raises(KeyboardInterrupt):
                    loop.run()

        expected_file = tmp_path / "2025-01-20_speedtest.json"
        assert expected_file.exists()


class TestMain:
    def test_main_handles_keyboard_interrupt(self):
        with patch("speedtest.handlers.loop.run", side_effect=KeyboardInterrupt()):
            loop.main()

    def test_main_calls_run(self):
        with patch("speedtest.handlers.loop.run", side_effect=KeyboardInterrupt()) as mock_run:
            loop.main()
            mock_run.assert_called_once()
