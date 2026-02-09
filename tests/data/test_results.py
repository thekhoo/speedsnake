import csv

from speedsnake.data import results
from tests.conftest import make_speedtest_response


class TestFlattenDict:
    def test_flatten_simple_dict(self):
        data = {"a": 1, "b": 2}
        result = results.flatten_dict(data)
        assert result == {"a": 1, "b": 2}

    def test_flatten_nested_dict(self):
        data = {"outer": {"inner": "value"}}
        result = results.flatten_dict(data)
        assert result == {"outer_inner": "value"}

    def test_flatten_multiple_nested_levels(self):
        data = {"level1": {"level2": {"level3": "value"}}}
        result = results.flatten_dict(data)
        assert result == {"level1_level2_level3": "value"}

    def test_flatten_mixed_nested_dict(self):
        data = {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}
        result = results.flatten_dict(data)
        assert result == {"a": 1, "b_c": 2, "b_d": 3, "e": 4}

    def test_flatten_custom_separator(self):
        data = {"outer": {"inner": "value"}}
        result = results.flatten_dict(data, sep=".")
        assert result == {"outer.inner": "value"}

    def test_flatten_with_none_values(self):
        data = {"a": None, "b": {"c": None}}
        result = results.flatten_dict(data)
        assert result == {"a": None, "b_c": None}


class TestGetHivePartitionPath:
    def test_creates_partition_path_from_timestamp(self, tmp_path):
        timestamp = "2025-01-15T10:30:45.000000Z"
        result = results.get_hive_partition_path(tmp_path, timestamp)
        expected = tmp_path / "year=2025" / "month=01" / "day=15"
        assert result == expected

    def test_handles_different_dates(self, tmp_path):
        timestamp = "2024-12-31T23:59:59.000000Z"
        result = results.get_hive_partition_path(tmp_path, timestamp)
        expected = tmp_path / "year=2024" / "month=12" / "day=31"
        assert result == expected

    def test_pads_single_digit_month_and_day(self, tmp_path):
        timestamp = "2025-03-05T08:00:00.000000Z"
        result = results.get_hive_partition_path(tmp_path, timestamp)
        expected = tmp_path / "year=2025" / "month=03" / "day=05"
        assert result == expected


class TestGetCsvFilename:
    def test_creates_filename_from_timestamp(self):
        timestamp = "2025-01-15T10:30:45.000000Z"
        result = results.get_csv_filename(timestamp)
        assert result == "speedtest_10-30-45.csv"

    def test_pads_single_digit_time_components(self):
        timestamp = "2025-01-15T08:05:03.000000Z"
        result = results.get_csv_filename(timestamp)
        assert result == "speedtest_08-05-03.csv"

    def test_handles_midnight(self):
        timestamp = "2025-01-15T00:00:00.000000Z"
        result = results.get_csv_filename(timestamp)
        assert result == "speedtest_00-00-00.csv"


class TestWriteCsv:
    def test_creates_csv_file(self, tmp_path):
        filepath = tmp_path / "test.csv"
        sample_result = make_speedtest_response(
            download=125000000,
            upload=25000000,
            ping=15,
            timestamp="2025-01-15T10:30:00.000000Z",
            bytes_sent=0,
            bytes_received=0,
        )

        results.write_csv(filepath, sample_result)

        assert filepath.exists()

    def test_csv_has_header(self, tmp_path):
        filepath = tmp_path / "test.csv"
        sample_result = make_speedtest_response(
            download=100,
            upload=50,
        )

        results.write_csv(filepath, sample_result)

        with filepath.open("r") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert "download" in header
            assert "upload" in header
            assert "server_name" in header

    def test_csv_has_data_row(self, tmp_path):
        filepath = tmp_path / "test.csv"
        sample_result = make_speedtest_response(
            download=100,
            upload=50,
        )

        results.write_csv(filepath, sample_result)

        with filepath.open("r") as f:
            reader = csv.DictReader(f)
            row = next(reader)
            assert row["download"] == "100"
            assert row["upload"] == "50"

    def test_creates_parent_directories(self, tmp_path):
        filepath = tmp_path / "nested" / "path" / "test.csv"
        sample_result = make_speedtest_response()

        results.write_csv(filepath, sample_result)

        assert filepath.exists()
        assert filepath.parent.exists()

    def test_flattens_nested_fields(self, tmp_path):
        filepath = tmp_path / "test.csv"
        sample_result = make_speedtest_response()

        results.write_csv(filepath, sample_result)

        with filepath.open("r") as f:
            reader = csv.DictReader(f)
            row = next(reader)
            assert "server_name" in row
            assert "server_country" in row
            assert row["server_name"] == "Test Server"
            assert row["server_country"] == "US"
