import json
from unittest.mock import MagicMock, patch

import pytest

from speedtest.service import speedtest


@pytest.fixture
def sample_speedtest_response():
    return {
        "download": 125000000,
        "upload": 25000000,
        "ping": 15,
        "server": {
            "url": "http://speedtest.example.com",
            "lat": 1.3521,
            "lon": 103.8198,
            "name": "Singapore",
            "country": "Singapore",
            "cc": "SG",
            "sponsor": "Test ISP",
            "id": 12345,
            "host": "speedtest.example.com:8080",
            "d": 10.5,
            "latency": 5.2,
        },
        "timestamp": "2025-01-15T10:30:00.000000Z",
        "bytes_sent": 32000000,
        "bytes_received": 156000000,
        "share": None,
        "client": {
            "ip": "192.168.1.1",
            "lat": 1.3521,
            "lon": 103.8198,
            "isp": "Test ISP",
            "isprating": "3.5",
            "rating": 0,
            "ispdlavg": 0,
            "ispulavg": 0,
            "loggedin": False,
            "country": "SG",
        },
    }


class TestRun:
    def test_run_with_default_flags(self, sample_speedtest_response):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(sample_speedtest_response)

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = speedtest.run()

            mock_run.assert_called_once_with(
                ["speedtest", "--secure", "--json", "--bytes"],
                capture_output=True,
                text=True,
            )
            assert result == sample_speedtest_response

    def test_run_with_custom_flags(self, sample_speedtest_response):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(sample_speedtest_response)

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = speedtest.run(flags=["--json"])

            mock_run.assert_called_once_with(
                ["speedtest", "--json"],
                capture_output=True,
                text=True,
            )
            assert result == sample_speedtest_response

    def test_run_raises_exception_on_failure(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Connection failed"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(Exception, match="Speedtest failed"):
                speedtest.run()

    def test_run_parses_json_output(self, sample_speedtest_response):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(sample_speedtest_response)

        with patch("subprocess.run", return_value=mock_result):
            result = speedtest.run()

            assert result["download"] == 125000000
            assert result["upload"] == 25000000
            assert result["ping"] == 15


class TestGetDateStrFromResult:
    def test_extracts_date_from_timestamp(self, sample_speedtest_response):
        date_str = speedtest.get_date_str_from_result(sample_speedtest_response)
        assert date_str == "2025-01-15"

    def test_handles_different_date_formats(self):
        result = {"timestamp": "2024-12-31T23:59:59.999999Z"}
        date_str = speedtest.get_date_str_from_result(result)
        assert date_str == "2024-12-31"

    def test_handles_timestamp_without_timezone(self):
        result = {"timestamp": "2025-06-15T08:00:00"}
        date_str = speedtest.get_date_str_from_result(result)
        assert date_str == "2025-06-15"
