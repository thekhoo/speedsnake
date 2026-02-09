import logging
import pathlib
import re
from datetime import datetime

import duckdb

logger = logging.getLogger(__name__)


def get_next_parquet_number(partition_dir: pathlib.Path) -> int:
    """Find highest speedtest_NNN.parquet number in partition, return next number.

    Args:
        partition_dir: Partition directory to search (e.g., uploads/year=2025/month=01/day=23/)

    Returns:
        Next available number (1-indexed)
    """
    if not partition_dir.exists():
        return 1

    existing = list(partition_dir.glob("speedtest_*.parquet"))
    if not existing:
        return 1

    numbers = []
    for file in existing:
        match = re.match(r"speedtest_(\d+)\.parquet", file.name)
        if match:
            numbers.append(int(match.group(1)))

    return max(numbers) + 1 if numbers else 1


def get_parquet_filename(number: int) -> str:
    """Format parquet filename with zero-padded number.

    Args:
        number: File number (1-indexed)

    Returns:
        Filename in format speedtest_NNN.parquet
    """
    return f"speedtest_{number:03d}.parquet"


def get_complete_days(base_dir: pathlib.Path, before_date: str) -> list[str]:
    """Find all complete days (before today) that contain CSV files.

    Args:
        base_dir: Base results directory (e.g., ./results)
        before_date: Date string in YYYY-MM-DD format (e.g., "2026-01-23")

    Returns:
        List of date strings in YYYY-MM-DD format for days with CSVs
    """
    complete_days = []

    if not base_dir.exists():
        return complete_days

    # Parse before_date
    try:
        before_dt = datetime.strptime(before_date, "%Y-%m-%d")
    except ValueError:
        logger.error(f"Invalid date format: {before_date}")
        return complete_days

    # Scan Hive partitions
    for year_dir in base_dir.glob("year=*"):
        year = year_dir.name.split("=")[1]
        for month_dir in year_dir.glob("month=*"):
            month = month_dir.name.split("=")[1]
            for day_dir in month_dir.glob("day=*"):
                day = day_dir.name.split("=")[1]

                # Construct date string and check if before today
                date_str = f"{year}-{month}-{day}"
                try:
                    partition_dt = datetime.strptime(date_str, "%Y-%m-%d")
                    if partition_dt < before_dt:
                        # Check if directory has CSV files
                        csv_files = list(day_dir.glob("speedtest_*.csv"))
                        if csv_files:
                            complete_days.append(date_str)
                except ValueError:
                    logger.warning(f"Invalid partition date: {date_str}")
                    continue

    return sorted(complete_days)


def verify_parquet_integrity(parquet_path: pathlib.Path, expected_rows: int) -> bool:
    """Verify parquet file integrity before deleting source CSVs.

    Args:
        parquet_path: Path to parquet file to verify
        expected_rows: Expected number of rows

    Returns:
        True if verification passes, False otherwise

    Raises:
        ValueError: If verification fails
    """
    if not parquet_path.exists():
        raise ValueError(f"Parquet file does not exist: {parquet_path}")

    # Verify row count
    count_result = duckdb.query(f"SELECT COUNT(*) as count FROM '{parquet_path}'").fetchone()
    actual_rows = count_result[0] if count_result else 0

    if actual_rows != expected_rows:
        raise ValueError(f"Row count mismatch: expected {expected_rows}, got {actual_rows}")

    logger.info(f"Parquet integrity verified: {parquet_path} ({actual_rows} rows)")
    return True


def delete_csv_files(csv_dir: pathlib.Path) -> None:
    """Delete all CSV files in partition directory.

    Args:
        csv_dir: Partition directory containing CSV files

    Raises:
        OSError: If deletion fails
    """
    if not csv_dir.exists():
        logger.warning(f"CSV directory does not exist: {csv_dir}")
        return

    csv_files = list(csv_dir.glob("speedtest_*.csv"))
    if not csv_files:
        logger.warning(f"No CSV files found in {csv_dir}")
        return

    deleted_count = 0
    for csv_file in csv_files:
        try:
            csv_file.unlink()
            deleted_count += 1
        except OSError as e:
            logger.error(f"Failed to delete {csv_file}: {e}")
            raise

    logger.info(f"Deleted {deleted_count} CSV files from {csv_dir}")


def convert_day_to_parquet(csv_dir: pathlib.Path, parquet_dir: pathlib.Path) -> pathlib.Path:
    """Convert all CSV files for a day into a single numbered Parquet file.

    Args:
        csv_dir: Source partition directory with CSV files
        parquet_dir: Destination partition directory for parquet file (includes location in path)

    Returns:
        Path to created parquet file

    Raises:
        ValueError: If no CSV files found or conversion fails
        OSError: If file operations fail
    """
    if not csv_dir.exists():
        raise ValueError(f"CSV directory does not exist: {csv_dir}")

    # Find all CSV files
    csv_files = list(csv_dir.glob("speedtest_*.csv"))
    if not csv_files:
        raise ValueError(f"No CSV files found in {csv_dir}")

    logger.info(f"Converting {len(csv_files)} CSV files from {csv_dir}")

    # Get next parquet number
    parquet_dir.mkdir(parents=True, exist_ok=True)
    next_number = get_next_parquet_number(parquet_dir)
    parquet_filename = get_parquet_filename(next_number)
    parquet_path = parquet_dir / parquet_filename

    # Use DuckDB to read CSVs and write parquet
    csv_pattern = str(csv_dir / "speedtest_*.csv")

    try:
        # Read all CSVs and write to parquet
        query = f"""
            COPY (
                SELECT *
                FROM read_csv('{csv_pattern}', auto_detect=true, union_by_name=true)
            ) TO '{parquet_path}' (FORMAT PARQUET);
        """
        duckdb.query(query)

        logger.info(f"Created parquet file: {parquet_path}")

        # Verify integrity before deleting CSVs
        verify_parquet_integrity(parquet_path, len(csv_files))

        # Delete source CSV files
        delete_csv_files(csv_dir)

        return parquet_path

    except Exception as e:
        logger.error(f"Failed to convert CSV to parquet: {e}")
        # Clean up partial parquet file if it exists
        if parquet_path.exists():
            try:
                parquet_path.unlink()
                logger.info(f"Cleaned up partial parquet file: {parquet_path}")
            except OSError:
                pass
        raise
