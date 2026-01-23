import os
import pathlib


def get_sleep_seconds() -> int:
    # NOTE: this may be changed to get data from a config so it can be
    # updated during runtime without infiltrating this thread
    return int(os.getenv("SLEEP_SECONDS", "5"))


def get_result_dir() -> pathlib.Path:
    return pathlib.Path(os.getenv("RESULT_DIR", "./results"))


def get_log_dir() -> pathlib.Path:
    return pathlib.Path(os.getenv("LOG_DIR", "./logs"))


def get_upload_dir() -> pathlib.Path:
    return pathlib.Path(os.getenv("UPLOAD_DIR", "./uploads"))


def get_speedtest_location_uuid() -> str:
    return os.getenv("SPEEDTEST_LOCATION_UUID", "unknown-location")
