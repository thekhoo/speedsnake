import json
from unittest.mock import MagicMock, patch

import pytest

from speedsnake.service import speedtest
from speedsnake.service.speedtest import SpeedtestResponse, round_floats_to_ints
from tests.conftest import make_speedtest_response


@pytest.fixture
def sample_speedtest_response() -> SpeedtestResponse:
    return make_speedtest_response(
        download=125000000,
        upload=25000000,
        ping=15,
        timestamp="2025-01-15T10:30:00.000000Z",
        bytes_sent=32000000,
        bytes_received=156000000,
    )


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
        result = make_speedtest_response(timestamp="2024-12-31T23:59:59.999999Z")
        date_str = speedtest.get_date_str_from_result(result)
        assert date_str == "2024-12-31"

    def test_handles_timestamp_without_timezone(self):
        result = make_speedtest_response(timestamp="2025-06-15T08:00:00")
        date_str = speedtest.get_date_str_from_result(result)
        assert date_str == "2025-06-15"


class TestRoundFloatsToInts:
    def test_converts_float_to_int(self):
        assert round_floats_to_ints(1.5) == 2
        assert round_floats_to_ints(1.4) == 1
        assert round_floats_to_ints(10.5) == 10  # Python uses banker's rounding (round half to even)

    def test_preserves_non_float_primitives(self):
        assert round_floats_to_ints(42) == 42
        assert round_floats_to_ints("text") == "text"
        assert round_floats_to_ints(True) is True
        assert round_floats_to_ints(None) is None

    def test_converts_floats_in_dict(self):
        data = {"value": 1.3521, "score": 103.8198, "name": "Singapore", "id": 12345}
        result = round_floats_to_ints(data)
        assert result == {"value": 1, "score": 104, "name": "Singapore", "id": 12345}

    def test_converts_floats_in_nested_dict(self):
        data = {
            "server": {"value": 1.3521, "score": 103.8198, "latency": 10.5},
            "client": {"value": 1.3521, "score": 103.8198},
        }
        result = round_floats_to_ints(data)
        assert result == {
            "server": {"value": 1, "score": 104, "latency": 10},  # 10.5 rounds to 10 (banker's rounding)
            "client": {"value": 1, "score": 104},
        }

    def test_converts_floats_in_list(self):
        data = [1.5, 2.7, 3.2]
        result = round_floats_to_ints(data)
        assert result == [2, 3, 3]

    def test_converts_floats_in_mixed_structures(self):
        data = {"values": [1.5, 2.7], "nested": {"score": 98.6}}
        result = round_floats_to_ints(data)
        assert result == {"values": [2, 3], "nested": {"score": 99}}

    def test_excludes_specified_keys_from_conversion(self):
        data = {"lat": 1.3521, "lon": 103.8198, "d": 10.5, "latency": 5.2}
        result = round_floats_to_ints(data, exclude_keys={"lat", "lon", "d"})
        assert result == {"lat": 1.3521, "lon": 103.8198, "d": 10.5, "latency": 5}

    def test_excludes_keys_in_nested_structures(self):
        data = {
            "server": {"lat": 1.3521, "lon": 103.8198, "d": 10.5, "latency": 5.2},
            "client": {"lat": 1.3521, "lon": 103.8198},
        }
        result = round_floats_to_ints(data, exclude_keys={"lat", "lon", "d"})
        assert result == {
            "server": {"lat": 1.3521, "lon": 103.8198, "d": 10.5, "latency": 5},
            "client": {"lat": 1.3521, "lon": 103.8198},
        }

    def test_run_converts_floats_to_ints(self):
        """Verify that run() applies float-to-int conversion to speedtest output."""
        speedtest_response_with_floats = {
            "download": 68416346.56931093,
            "upload": 19265730.143106185,
            "ping": 9.348,
            "server": {
                "url": "http://speedtest.example.com",
                "lat": "51.5171",
                "lon": "-0.1062",
                "name": "London",
                "country": "United Kingdom",
                "cc": "GB",
                "sponsor": "Test ISP",
                "id": "12345",
                "host": "speedtest.example.com:8080",
                "d": 544.9533384101816,
                "latency": 9.348,
            },
            "timestamp": "2026-01-23T22:56:02.751950Z",
            "bytes_sent": 24313856,
            "bytes_received": 85717356,
            "share": None,
            "client": {
                "ip": "81.154.179.120",
                "lat": "55.7991",
                "lon": "-4.1357",
                "isp": "BT",
                "isprating": "3.7",
                "rating": "0",
                "ispdlavg": "0",
                "ispulavg": "0",
                "loggedin": "0",
                "country": "GB",
            },
        }

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(speedtest_response_with_floats)

        with patch("subprocess.run", return_value=mock_result):
            result = speedtest.run()

            # Verify floats were converted to ints
            assert result["download"] == 68416347  # Rounded from 68416346.56931093
            assert result["upload"] == 19265730  # Rounded from 19265730.143106185
            assert result["ping"] == 9  # Rounded from 9.348
            assert result["server"]["latency"] == 9  # Rounded from 9.348

            # Verify lat, lon, d are excluded from rounding (and are strings/floats)
            assert result["server"]["lat"] == "51.5171"  # String preserved
            assert result["server"]["lon"] == "-0.1062"  # String preserved
            assert result["server"]["d"] == 544.9533384101816  # Float preserved
            assert result["client"]["lat"] == "55.7991"  # String preserved
            assert result["client"]["lon"] == "-4.1357"  # String preserved

            # Verify other string fields are preserved
            assert result["server"]["id"] == "12345"
            assert result["client"]["rating"] == "0"
            assert result["client"]["ispdlavg"] == "0"
            assert result["client"]["ispulavg"] == "0"
            assert result["client"]["loggedin"] == "0"
