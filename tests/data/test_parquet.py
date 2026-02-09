import duckdb
import pytest

from speedsnake.data import parquet


class TestGetNextParquetNumber:
    def test_empty_directory_returns_one(self, tmp_path):
        partition_dir = tmp_path / "partition"
        partition_dir.mkdir()
        assert parquet.get_next_parquet_number(partition_dir) == 1

    def test_nonexistent_directory_returns_one(self, tmp_path):
        partition_dir = tmp_path / "nonexistent"
        assert parquet.get_next_parquet_number(partition_dir) == 1

    def test_single_file_increments(self, tmp_path):
        partition_dir = tmp_path / "partition"
        partition_dir.mkdir()
        (partition_dir / "speedtest_001.parquet").touch()
        assert parquet.get_next_parquet_number(partition_dir) == 2

    def test_multiple_files_returns_max_plus_one(self, tmp_path):
        partition_dir = tmp_path / "partition"
        partition_dir.mkdir()
        (partition_dir / "speedtest_001.parquet").touch()
        (partition_dir / "speedtest_003.parquet").touch()
        (partition_dir / "speedtest_002.parquet").touch()
        assert parquet.get_next_parquet_number(partition_dir) == 4

    def test_ignores_non_matching_files(self, tmp_path):
        partition_dir = tmp_path / "partition"
        partition_dir.mkdir()
        (partition_dir / "speedtest_001.parquet").touch()
        (partition_dir / "other_file.parquet").touch()
        (partition_dir / "speedtest.parquet").touch()
        assert parquet.get_next_parquet_number(partition_dir) == 2

    def test_handles_gaps_in_numbering(self, tmp_path):
        partition_dir = tmp_path / "partition"
        partition_dir.mkdir()
        (partition_dir / "speedtest_001.parquet").touch()
        (partition_dir / "speedtest_005.parquet").touch()
        assert parquet.get_next_parquet_number(partition_dir) == 6


class TestGetParquetFilename:
    def test_single_digit_pads_with_zeros(self):
        assert parquet.get_parquet_filename(1) == "speedtest_001.parquet"

    def test_double_digit_pads_with_zeros(self):
        assert parquet.get_parquet_filename(42) == "speedtest_042.parquet"

    def test_triple_digit_no_padding(self):
        assert parquet.get_parquet_filename(999) == "speedtest_999.parquet"

    def test_four_digit_extends_width(self):
        assert parquet.get_parquet_filename(1234) == "speedtest_1234.parquet"


class TestGetCompleteDays:
    def test_empty_directory_returns_empty_list(self, tmp_path):
        result = parquet.get_complete_days(tmp_path, "2026-01-23")
        assert result == []

    def test_nonexistent_directory_returns_empty_list(self, tmp_path):
        result = parquet.get_complete_days(tmp_path / "nonexistent", "2026-01-23")
        assert result == []

    def test_finds_single_complete_day(self, tmp_path):
        # Create partition with CSV file
        day_dir = tmp_path / "year=2026" / "month=01" / "day=20"
        day_dir.mkdir(parents=True)
        (day_dir / "speedtest_10-00-00.csv").touch()

        result = parquet.get_complete_days(tmp_path, "2026-01-23")
        assert result == ["2026-01-20"]

    def test_finds_multiple_complete_days_sorted(self, tmp_path):
        # Create multiple partitions
        for day in [20, 21, 22]:
            day_dir = tmp_path / "year=2026" / "month=01" / f"day={day:02d}"
            day_dir.mkdir(parents=True)
            (day_dir / "speedtest_10-00-00.csv").touch()

        result = parquet.get_complete_days(tmp_path, "2026-01-23")
        assert result == ["2026-01-20", "2026-01-21", "2026-01-22"]

    def test_excludes_today_and_future_days(self, tmp_path):
        # Create partitions for past, today, and future
        for day in [20, 23, 25]:
            day_dir = tmp_path / "year=2026" / "month=01" / f"day={day:02d}"
            day_dir.mkdir(parents=True)
            (day_dir / "speedtest_10-00-00.csv").touch()

        result = parquet.get_complete_days(tmp_path, "2026-01-23")
        assert result == ["2026-01-20"]

    def test_ignores_partitions_without_csv_files(self, tmp_path):
        # Create partition without CSV files
        day_dir = tmp_path / "year=2026" / "month=01" / "day=20"
        day_dir.mkdir(parents=True)
        (day_dir / "other_file.txt").touch()

        result = parquet.get_complete_days(tmp_path, "2026-01-23")
        assert result == []

    def test_handles_invalid_date_format(self, tmp_path):
        result = parquet.get_complete_days(tmp_path, "invalid-date")
        assert result == []

    def test_handles_multiple_months_and_years(self, tmp_path):
        # Create partitions across different months and years
        partitions = [
            ("2025", "12", "31"),
            ("2026", "01", "15"),
            ("2026", "02", "10"),
        ]
        for year, month, day in partitions:
            day_dir = tmp_path / f"year={year}" / f"month={month}" / f"day={day}"
            day_dir.mkdir(parents=True)
            (day_dir / "speedtest_10-00-00.csv").touch()

        result = parquet.get_complete_days(tmp_path, "2026-01-23")
        assert result == ["2025-12-31", "2026-01-15"]


class TestVerifyParquetIntegrity:
    def test_nonexistent_file_raises_error(self, tmp_path):
        parquet_path = tmp_path / "nonexistent.parquet"
        with pytest.raises(ValueError, match="does not exist"):
            parquet.verify_parquet_integrity(parquet_path, 10)

    def test_row_count_mismatch_raises_error(self, tmp_path):
        # Create parquet with 2 rows
        parquet_path = tmp_path / "test.parquet"
        duckdb.query(f"COPY (SELECT 1 as a UNION ALL SELECT 2) TO '{parquet_path}' (FORMAT PARQUET)")

        with pytest.raises(ValueError, match="Row count mismatch"):
            parquet.verify_parquet_integrity(parquet_path, 5)

    def test_valid_parquet_returns_true(self, tmp_path):
        # Create valid parquet
        parquet_path = tmp_path / "test.parquet"
        duckdb.query(f"COPY (SELECT 1 as download, 2 as upload) TO '{parquet_path}' (FORMAT PARQUET)")

        assert parquet.verify_parquet_integrity(parquet_path, 1) is True


class TestDeleteCsvFiles:
    def test_nonexistent_directory_logs_warning(self, tmp_path, caplog):
        csv_dir = tmp_path / "nonexistent"
        parquet.delete_csv_files(csv_dir)
        assert "does not exist" in caplog.text

    def test_empty_directory_logs_warning(self, tmp_path, caplog):
        csv_dir = tmp_path / "empty"
        csv_dir.mkdir()
        parquet.delete_csv_files(csv_dir)
        assert "No CSV files found" in caplog.text

    def test_deletes_csv_files(self, tmp_path):
        csv_dir = tmp_path / "csv"
        csv_dir.mkdir()
        csv1 = csv_dir / "speedtest_10-00-00.csv"
        csv2 = csv_dir / "speedtest_10-10-00.csv"
        csv1.write_text("data1")
        csv2.write_text("data2")

        parquet.delete_csv_files(csv_dir)

        assert not csv1.exists()
        assert not csv2.exists()

    def test_ignores_non_csv_files(self, tmp_path):
        csv_dir = tmp_path / "csv"
        csv_dir.mkdir()
        csv_file = csv_dir / "speedtest_10-00-00.csv"
        other_file = csv_dir / "other.txt"
        csv_file.write_text("data")
        other_file.write_text("keep")

        parquet.delete_csv_files(csv_dir)

        assert not csv_file.exists()
        assert other_file.exists()


class TestConvertDayToParquet:
    def test_nonexistent_csv_dir_raises_error(self, tmp_path):
        csv_dir = tmp_path / "nonexistent"
        parquet_dir = tmp_path / "parquet"

        with pytest.raises(ValueError, match="does not exist"):
            parquet.convert_day_to_parquet(csv_dir, parquet_dir)

    def test_no_csv_files_raises_error(self, tmp_path):
        csv_dir = tmp_path / "csv"
        csv_dir.mkdir()
        parquet_dir = tmp_path / "parquet"

        with pytest.raises(ValueError, match="No CSV files found"):
            parquet.convert_day_to_parquet(csv_dir, parquet_dir)

    def test_converts_single_csv_to_parquet(self, tmp_path):
        # Create CSV file
        csv_dir = tmp_path / "csv"
        csv_dir.mkdir()
        csv_file = csv_dir / "speedtest_10-00-00.csv"
        csv_file.write_text("download,upload,ping\n100,50,10\n")

        parquet_dir = tmp_path / "parquet"

        result_path = parquet.convert_day_to_parquet(csv_dir, parquet_dir)

        # Verify parquet created
        assert result_path.exists()
        assert result_path.name == "speedtest_001.parquet"

        # Verify data
        data = duckdb.query(f"SELECT * FROM '{result_path}'").fetchall()
        assert len(data) == 1

        # Verify CSV deleted
        assert not csv_file.exists()

    def test_converts_multiple_csvs_to_parquet(self, tmp_path):
        # Create multiple CSV files
        csv_dir = tmp_path / "csv"
        csv_dir.mkdir()
        for i in range(3):
            csv_file = csv_dir / f"speedtest_10-{i:02d}-00.csv"
            csv_file.write_text(f"download,upload,ping\n{100 + i},{50 + i},{10 + i}\n")

        parquet_dir = tmp_path / "parquet"

        result_path = parquet.convert_day_to_parquet(csv_dir, parquet_dir)

        # Verify parquet created with all rows
        data = duckdb.query(f"SELECT * FROM '{result_path}'").fetchall()
        assert len(data) == 3

        # Verify all CSVs deleted
        assert len(list(csv_dir.glob("speedtest_*.csv"))) == 0

    def test_increments_parquet_number(self, tmp_path):
        # Create existing parquet file
        parquet_dir = tmp_path / "parquet"
        parquet_dir.mkdir()
        (parquet_dir / "speedtest_001.parquet").touch()

        # Create CSV files
        csv_dir = tmp_path / "csv"
        csv_dir.mkdir()
        csv_file = csv_dir / "speedtest_10-00-00.csv"
        csv_file.write_text("download,upload,ping\n100,50,10\n")

        result_path = parquet.convert_day_to_parquet(csv_dir, parquet_dir)

        # Verify new file is numbered 002
        assert result_path.name == "speedtest_002.parquet"

    def test_cleans_up_on_failure(self, tmp_path):
        # Create CSV file
        csv_dir = tmp_path / "csv"
        csv_dir.mkdir()
        csv_file = csv_dir / "speedtest_10-00-00.csv"
        csv_file.write_text("download,upload,ping\n100,50,10\n")

        # Create read-only parquet directory to trigger write failure
        parquet_dir = tmp_path / "parquet"
        parquet_dir.mkdir()
        parquet_dir.chmod(0o444)  # Read-only

        try:
            with pytest.raises(Exception):
                parquet.convert_day_to_parquet(csv_dir, parquet_dir)

            # Verify CSV still exists (not deleted on failure)
            assert csv_file.exists()
        finally:
            # Restore permissions for cleanup
            parquet_dir.chmod(0o755)
