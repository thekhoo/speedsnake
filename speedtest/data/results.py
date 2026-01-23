import csv
import logging
import pathlib
from datetime import datetime
from typing import Any

from speedtest.speedtest import SpeedtestResponse

logger = logging.getLogger(__name__)


def flatten_dict(data: dict[str, Any], parent_key: str = "", sep: str = "_") -> dict[str, Any]:
    """Flatten nested dictionary by joining keys with separator.

    Args:
        data: Dictionary to flatten
        parent_key: Parent key for nested fields
        sep: Separator between parent and child keys

    Returns:
        Flattened dictionary
    """
    items = []
    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, sep=sep).items())
        else:
            items.append((new_key, value))
    return dict(items)


def get_hive_partition_path(base_dir: pathlib.Path, timestamp: str) -> pathlib.Path:
    """Get Hive partition path from timestamp.

    Args:
        base_dir: Base results directory
        timestamp: ISO 8601 timestamp string

    Returns:
        Path with Hive partitioning (year=YYYY/month=MM/day=DD)
    """
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return base_dir / f"year={dt.year}" / f"month={dt.month:02d}" / f"day={dt.day:02d}"


def get_csv_filename(timestamp: str) -> str:
    """Get CSV filename from timestamp.

    Args:
        timestamp: ISO 8601 timestamp string

    Returns:
        Filename in format speedtest_HH-MM-SS.csv
    """
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return f"speedtest_{dt.hour:02d}-{dt.minute:02d}-{dt.second:02d}.csv"


def write_csv(filepath: pathlib.Path, result: SpeedtestResponse) -> None:
    """Write speedtest result to CSV file.

    Args:
        filepath: Path to CSV file
        result: Speedtest result
    """
    flattened = flatten_dict(dict(result))

    filepath.parent.mkdir(parents=True, exist_ok=True)

    with filepath.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=sorted(flattened.keys()))
        writer.writeheader()
        writer.writerow(flattened)

    logger.info(f"Speedtest result saved to {filepath}")
