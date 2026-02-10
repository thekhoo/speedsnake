from unittest.mock import MagicMock, patch

import pytest

from speedsnake.handlers import loop


class TestSleep:
    @patch("time.sleep")
    def test_sleep_calls_time_sleep(self, mock_sleep):
        loop.sleep(10)
        mock_sleep.assert_called_once_with(10)

    @patch("time.sleep")
    def test_sleep_with_zero_seconds(self, mock_sleep):
        loop.sleep(0)
        mock_sleep.assert_called_once_with(0)


class TestLoopDecorator:
    @patch("speedsnake.handlers.loop.sleep")
    def test_loop_calls_function_repeatedly(self, mock_sleep):
        call_count = 0

        @loop.loop
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                raise KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            test_func()

        assert call_count == 3

    @patch("speedsnake.handlers.loop.sleep")
    def test_loop_continues_on_exception(self, mock_sleep):
        call_count = 0

        @loop.loop
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Test error")
            raise KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            test_func()

        assert call_count == 3

    @patch("speedsnake.service.environment.get_sleep_seconds", return_value=60)
    @patch("speedsnake.handlers.loop.sleep")
    def test_loop_sleeps_between_calls(self, mock_sleep, mock_get_sleep):
        call_count = 0

        @loop.loop
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise KeyboardInterrupt()

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

    @pytest.fixture
    def loop_infra(self, tmp_path):
        patchers = [
            patch("speedsnake.handlers.loop.sleep"),
            patch("speedsnake.handlers.loop.check_and_convert_complete_days"),
            patch("speedsnake.handlers.loop.check_and_upload_parquets"),
            patch("speedsnake.handlers.loop.env.get_result_dir", return_value=tmp_path),
        ]
        for p in patchers:
            p.start()
        yield tmp_path
        for p in patchers:
            p.stop()

    @patch("speedsnake.service.speedtest.run")
    def test_run_executes_speedtest_and_saves_result(self, mock_run, mock_speedtest_response, loop_infra, monkeypatch):
        monkeypatch.setenv("SLEEP_SECONDS", "1")
        call_count = 0

        def mock_speedtest_fn():
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise KeyboardInterrupt()
            return mock_speedtest_response

        mock_run.side_effect = mock_speedtest_fn

        with pytest.raises(KeyboardInterrupt):
            loop.run()

        expected_file = loop_infra / "year=2025" / "month=01" / "day=20" / "speedtest_14-30-00.csv"
        assert expected_file.exists()


class TestMain:
    @patch("speedsnake.handlers.loop.run", side_effect=KeyboardInterrupt())
    def test_main_handles_keyboard_interrupt(self, mock_run):
        loop.main()

    @patch("speedsnake.handlers.loop.run", side_effect=KeyboardInterrupt())
    def test_main_calls_run(self, mock_run):
        loop.main()
        mock_run.assert_called_once()


class TestCheckAndConvertCompleteDays:
    @patch("speedsnake.data.parquet.convert_day_to_parquet")
    @patch("speedsnake.data.parquet.get_complete_days", return_value=[])
    def test_no_complete_days_returns_early(self, mock_get_days, mock_convert):
        loop.check_and_convert_complete_days()
        mock_convert.assert_not_called()

    @patch("speedsnake.data.parquet.convert_day_to_parquet")
    @patch("speedsnake.data.parquet.get_complete_days", return_value=["2026-01-20"])
    def test_converts_single_complete_day(self, mock_get_days, mock_convert, tmp_path, monkeypatch):
        monkeypatch.setenv("SPEEDTEST_LOCATION_UUID", "test-uuid")
        mock_convert.return_value = tmp_path / "uploads" / "year=2026" / "month=01" / "day=20" / "test.parquet"

        loop.check_and_convert_complete_days()

        mock_convert.assert_called_once()
        call_args = mock_convert.call_args
        assert str(call_args[0][0]).endswith("year=2026/month=01/day=20")
        assert str(call_args[0][1]).endswith("location=test-uuid/year=2026/month=01/day=20")

    @patch("speedsnake.data.parquet.convert_day_to_parquet")
    @patch("speedsnake.data.parquet.get_complete_days", return_value=["2026-01-20", "2026-01-21"])
    def test_converts_multiple_complete_days(self, mock_get_days, mock_convert, tmp_path):
        mock_convert.return_value = tmp_path / "uploads" / "test.parquet"
        loop.check_and_convert_complete_days()
        assert mock_convert.call_count == 2

    @patch("speedsnake.data.parquet.convert_day_to_parquet")
    @patch("speedsnake.data.parquet.get_complete_days", return_value=["2026-01-20", "2026-01-21"])
    def test_continues_on_conversion_error(self, mock_get_days, mock_convert, tmp_path):
        mock_convert.side_effect = [ValueError("Test error"), tmp_path / "test.parquet"]
        loop.check_and_convert_complete_days()
        assert mock_convert.call_count == 2


class TestCheckAndUploadParquets:
    @pytest.fixture
    def upload_dir(self, tmp_path):
        d = tmp_path / "uploads"
        d.mkdir()
        with patch("speedsnake.handlers.loop.env.get_upload_dir", return_value=d):
            yield d

    @pytest.fixture
    def single_parquet_file(self, upload_dir):
        parquet_dir = upload_dir / "location=abc" / "year=2026" / "month=02" / "day=09"
        parquet_dir.mkdir(parents=True)
        parquet_file = parquet_dir / "speedtest_001.parquet"
        parquet_file.write_bytes(b"parquet data")
        return parquet_file

    @pytest.fixture
    def upload_mocks(self):
        patchers = [
            patch("speedsnake.service.upload.calculate_md5", return_value="abc123"),
            patch("speedsnake.service.upload.upload_parquet_file", return_value='"abc123"'),
            patch("speedsnake.service.upload.verify_upload_checksum", return_value=True),
        ]
        mocks = [p.start() for p in patchers]
        yield {"md5": mocks[0], "upload": mocks[1], "verify": mocks[2]}
        for p in patchers:
            p.stop()

    def test_no_parquets_returns_early(self, upload_dir, upload_mocks):
        loop.check_and_upload_parquets()
        upload_mocks["upload"].assert_not_called()

    def test_uploads_single_parquet_and_deletes_local(self, single_parquet_file, upload_mocks):
        loop.check_and_upload_parquets()
        upload_mocks["upload"].assert_called_once()
        assert not single_parquet_file.exists()

    def test_uploads_multiple_parquets(self, upload_dir, upload_mocks):
        for i in range(3):
            parquet_dir = upload_dir / "location=abc" / "year=2026" / "month=02" / f"day=0{i + 1}"
            parquet_dir.mkdir(parents=True)
            (parquet_dir / "speedtest_001.parquet").write_bytes(b"data")

        loop.check_and_upload_parquets()

        assert upload_mocks["upload"].call_count == 3

    def test_preserves_file_on_checksum_mismatch(self, single_parquet_file, upload_mocks):
        upload_mocks["upload"].return_value = '"wronghash"'
        upload_mocks["verify"].return_value = False

        loop.check_and_upload_parquets()

        assert single_parquet_file.exists()

    def test_preserves_file_on_upload_exception(self, single_parquet_file, upload_mocks):
        upload_mocks["upload"].side_effect = Exception("Network error")

        loop.check_and_upload_parquets()

        assert single_parquet_file.exists()

    def test_continues_after_single_failure(self, upload_dir, upload_mocks):
        for i in range(2):
            parquet_dir = upload_dir / "location=abc" / "year=2026" / "month=02" / f"day=0{i + 1}"
            parquet_dir.mkdir(parents=True)
            (parquet_dir / "speedtest_001.parquet").write_bytes(b"data")

        upload_mocks["upload"].side_effect = [Exception("fail"), '"abc123"']

        loop.check_and_upload_parquets()

        assert upload_mocks["upload"].call_count == 2

    def test_upload_called_once_per_parquet_file(self, upload_dir, upload_mocks):
        for i in range(3):
            parquet_dir = upload_dir / "location=abc" / "year=2026" / "month=02" / f"day=0{i + 1}"
            parquet_dir.mkdir(parents=True)
            (parquet_dir / "speedtest_001.parquet").write_bytes(b"data")

        loop.check_and_upload_parquets()

        assert upload_mocks["upload"].call_count == 3


class TestLoopDecoratorWithParquetConversion:
    @patch("speedsnake.handlers.loop.check_and_convert_complete_days")
    @patch("speedsnake.handlers.loop.sleep")
    def test_loop_calls_parquet_conversion_in_finally(self, mock_sleep, mock_convert):
        call_count = 0

        @loop.loop
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            test_func()

        assert mock_convert.call_count == 2

    @patch("speedsnake.handlers.loop.check_and_convert_complete_days", side_effect=ValueError("Test error"))
    @patch("speedsnake.handlers.loop.sleep")
    def test_loop_continues_on_parquet_conversion_error(self, mock_sleep, mock_convert):
        call_count = 0

        @loop.loop
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                raise KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            test_func()

        assert call_count == 3
