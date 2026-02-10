from unittest.mock import MagicMock, patch

import pytest

from speedsnake.handlers import loop


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

        with patch("speedsnake.handlers.loop.sleep"):
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

        with patch("speedsnake.handlers.loop.sleep"):
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

        with patch("speedsnake.handlers.loop.sleep") as mock_sleep:
            with patch("speedsnake.service.environment.get_sleep_seconds", return_value=60):
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

        with patch("speedsnake.service.speedtest.run", side_effect=mock_speedtest_run):
            with patch("speedsnake.handlers.loop.sleep"):
                with patch("speedsnake.handlers.loop.check_and_convert_complete_days"):
                    with pytest.raises(KeyboardInterrupt):
                        loop.run()

        expected_file = tmp_path / "year=2025" / "month=01" / "day=20" / "speedtest_14-30-00.csv"
        assert expected_file.exists()


class TestMain:
    def test_main_handles_keyboard_interrupt(self):
        with patch("speedsnake.handlers.loop.run", side_effect=KeyboardInterrupt()):
            loop.main()

    def test_main_calls_run(self):
        with patch("speedsnake.handlers.loop.run", side_effect=KeyboardInterrupt()) as mock_run:
            loop.main()
            mock_run.assert_called_once()


class TestCheckAndConvertCompleteDays:
    def test_no_complete_days_returns_early(self, monkeypatch):
        monkeypatch.setenv("RESULT_DIR", "./results")
        with patch("speedsnake.data.parquet.get_complete_days", return_value=[]):
            with patch("speedsnake.data.parquet.convert_day_to_parquet") as mock_convert:
                loop.check_and_convert_complete_days()
                mock_convert.assert_not_called()

    def test_converts_single_complete_day(self, tmp_path, monkeypatch):
        monkeypatch.setenv("RESULT_DIR", str(tmp_path / "results"))
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
        monkeypatch.setenv("SPEEDTEST_LOCATION_UUID", "test-uuid")

        with patch("speedsnake.data.parquet.get_complete_days", return_value=["2026-01-20"]):
            with patch("speedsnake.data.parquet.convert_day_to_parquet") as mock_convert:
                mock_convert.return_value = tmp_path / "uploads" / "year=2026" / "month=01" / "day=20" / "test.parquet"
                loop.check_and_convert_complete_days()

                mock_convert.assert_called_once()
                call_args = mock_convert.call_args
                assert str(call_args[0][0]).endswith("year=2026/month=01/day=20")
                assert str(call_args[0][1]).endswith("location=test-uuid/year=2026/month=01/day=20")

    def test_converts_multiple_complete_days(self, tmp_path, monkeypatch):
        monkeypatch.setenv("RESULT_DIR", str(tmp_path / "results"))
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
        monkeypatch.setenv("SPEEDTEST_LOCATION_UUID", "test-uuid")

        with patch("speedsnake.data.parquet.get_complete_days", return_value=["2026-01-20", "2026-01-21"]):
            with patch("speedsnake.data.parquet.convert_day_to_parquet") as mock_convert:
                mock_convert.return_value = tmp_path / "uploads" / "test.parquet"
                loop.check_and_convert_complete_days()

                assert mock_convert.call_count == 2

    def test_continues_on_conversion_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("RESULT_DIR", str(tmp_path / "results"))
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))

        with patch("speedsnake.data.parquet.get_complete_days", return_value=["2026-01-20", "2026-01-21"]):
            with patch("speedsnake.data.parquet.convert_day_to_parquet") as mock_convert:
                # First call fails, second succeeds
                mock_convert.side_effect = [ValueError("Test error"), tmp_path / "test.parquet"]
                loop.check_and_convert_complete_days()

                # Should attempt both conversions despite first failure
                assert mock_convert.call_count == 2


class TestCheckAndUploadParquets:
    def test_no_parquets_returns_early(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
        (tmp_path / "uploads").mkdir()

        with patch("speedsnake.service.s3.assume_role") as mock_assume:
            loop.check_and_upload_parquets()
            mock_assume.assert_not_called()

    def test_uploads_single_parquet_and_deletes_local(self, tmp_path, monkeypatch):
        upload_dir = tmp_path / "uploads"
        parquet_dir = upload_dir / "location=abc" / "year=2026" / "month=02" / "day=09"
        parquet_dir.mkdir(parents=True)
        parquet_file = parquet_dir / "speedtest_001.parquet"
        parquet_file.write_bytes(b"parquet data")

        monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))

        mock_session = MagicMock()
        mock_config = {"s3_bucket_name": "my-bucket", "speedtest_location_uuid": "abc"}

        with patch("speedsnake.service.s3.assume_role", return_value=mock_session):
            with patch("speedsnake.service.s3.read_app_config", return_value=mock_config):
                with patch("speedsnake.service.s3.upload_parquet_file", return_value='"abc123"') as mock_upload:
                    with patch("speedsnake.service.s3.calculate_md5", return_value="abc123"):
                        with patch("speedsnake.service.s3.verify_upload_checksum", return_value=True):
                            loop.check_and_upload_parquets()

        mock_upload.assert_called_once()
        assert not parquet_file.exists()

    def test_uploads_multiple_parquets(self, tmp_path, monkeypatch):
        upload_dir = tmp_path / "uploads"
        for i in range(3):
            parquet_dir = upload_dir / f"location=abc" / "year=2026" / "month=02" / f"day=0{i+1}"
            parquet_dir.mkdir(parents=True)
            (parquet_dir / "speedtest_001.parquet").write_bytes(b"data")

        monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))

        mock_session = MagicMock()
        mock_config = {"s3_bucket_name": "my-bucket", "speedtest_location_uuid": "abc"}

        with patch("speedsnake.service.s3.assume_role", return_value=mock_session):
            with patch("speedsnake.service.s3.read_app_config", return_value=mock_config):
                with patch("speedsnake.service.s3.upload_parquet_file", return_value='"abc123"') as mock_upload:
                    with patch("speedsnake.service.s3.calculate_md5", return_value="abc123"):
                        with patch("speedsnake.service.s3.verify_upload_checksum", return_value=True):
                            loop.check_and_upload_parquets()

        assert mock_upload.call_count == 3

    def test_preserves_file_on_checksum_mismatch(self, tmp_path, monkeypatch):
        upload_dir = tmp_path / "uploads"
        parquet_dir = upload_dir / "location=abc" / "year=2026" / "month=02" / "day=09"
        parquet_dir.mkdir(parents=True)
        parquet_file = parquet_dir / "speedtest_001.parquet"
        parquet_file.write_bytes(b"parquet data")

        monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))

        mock_session = MagicMock()
        mock_config = {"s3_bucket_name": "my-bucket", "speedtest_location_uuid": "abc"}

        with patch("speedsnake.service.s3.assume_role", return_value=mock_session):
            with patch("speedsnake.service.s3.read_app_config", return_value=mock_config):
                with patch("speedsnake.service.s3.upload_parquet_file", return_value='"wronghash"'):
                    with patch("speedsnake.service.s3.calculate_md5", return_value="abc123"):
                        with patch("speedsnake.service.s3.verify_upload_checksum", return_value=False):
                            loop.check_and_upload_parquets()

        assert parquet_file.exists()

    def test_preserves_file_on_upload_exception(self, tmp_path, monkeypatch):
        upload_dir = tmp_path / "uploads"
        parquet_dir = upload_dir / "location=abc" / "year=2026" / "month=02" / "day=09"
        parquet_dir.mkdir(parents=True)
        parquet_file = parquet_dir / "speedtest_001.parquet"
        parquet_file.write_bytes(b"parquet data")

        monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))

        mock_session = MagicMock()
        mock_config = {"s3_bucket_name": "my-bucket", "speedtest_location_uuid": "abc"}

        with patch("speedsnake.service.s3.assume_role", return_value=mock_session):
            with patch("speedsnake.service.s3.read_app_config", return_value=mock_config):
                with patch("speedsnake.service.s3.upload_parquet_file", side_effect=Exception("Network error")):
                    with patch("speedsnake.service.s3.calculate_md5", return_value="abc123"):
                        loop.check_and_upload_parquets()

        assert parquet_file.exists()

    def test_continues_after_single_failure(self, tmp_path, monkeypatch):
        upload_dir = tmp_path / "uploads"
        for i in range(2):
            parquet_dir = upload_dir / "location=abc" / "year=2026" / "month=02" / f"day=0{i+1}"
            parquet_dir.mkdir(parents=True)
            (parquet_dir / "speedtest_001.parquet").write_bytes(b"data")

        monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))

        mock_session = MagicMock()
        mock_config = {"s3_bucket_name": "my-bucket", "speedtest_location_uuid": "abc"}

        with patch("speedsnake.service.s3.assume_role", return_value=mock_session):
            with patch("speedsnake.service.s3.read_app_config", return_value=mock_config):
                with patch(
                    "speedsnake.service.s3.upload_parquet_file",
                    side_effect=[Exception("fail"), '"abc123"'],
                ) as mock_upload:
                    with patch("speedsnake.service.s3.calculate_md5", return_value="abc123"):
                        with patch("speedsnake.service.s3.verify_upload_checksum", return_value=True):
                            loop.check_and_upload_parquets()

        assert mock_upload.call_count == 2

    def test_reads_config_from_ssm_once(self, tmp_path, monkeypatch):
        upload_dir = tmp_path / "uploads"
        for i in range(3):
            parquet_dir = upload_dir / "location=abc" / "year=2026" / "month=02" / f"day=0{i+1}"
            parquet_dir.mkdir(parents=True)
            (parquet_dir / "speedtest_001.parquet").write_bytes(b"data")

        monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))

        mock_session = MagicMock()
        mock_config = {"s3_bucket_name": "my-bucket", "speedtest_location_uuid": "abc"}

        with patch("speedsnake.service.s3.assume_role", return_value=mock_session) as mock_assume:
            with patch("speedsnake.service.s3.read_app_config", return_value=mock_config) as mock_read_config:
                with patch("speedsnake.service.s3.upload_parquet_file", return_value='"abc123"'):
                    with patch("speedsnake.service.s3.calculate_md5", return_value="abc123"):
                        with patch("speedsnake.service.s3.verify_upload_checksum", return_value=True):
                            loop.check_and_upload_parquets()

        mock_assume.assert_called_once()
        mock_read_config.assert_called_once()


class TestLoopDecoratorWithParquetConversion:
    def test_loop_calls_parquet_conversion_in_finally(self):
        call_count = 0

        @loop.loop
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise KeyboardInterrupt()

        with patch("speedsnake.handlers.loop.sleep"):
            with patch("speedsnake.handlers.loop.check_and_convert_complete_days") as mock_convert:
                with pytest.raises(KeyboardInterrupt):
                    test_func()

                # Should be called once per loop iteration
                assert mock_convert.call_count == 2

    def test_loop_continues_on_parquet_conversion_error(self):
        call_count = 0

        @loop.loop
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                raise KeyboardInterrupt()

        with patch("speedsnake.handlers.loop.sleep"):
            with patch(
                "speedsnake.handlers.loop.check_and_convert_complete_days", side_effect=ValueError("Test error")
            ):
                with pytest.raises(KeyboardInterrupt):
                    test_func()

                # Loop should continue despite parquet conversion errors
                assert call_count == 3
