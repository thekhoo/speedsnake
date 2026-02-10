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


def get_aws_region() -> str:
    return os.getenv("AWS_REGION", "eu-west-2")


def get_aws_role_arn() -> str:
    role_arn = os.getenv("AWS_ROLE_ARN")
    if not role_arn:
        raise ValueError("AWS_ROLE_ARN environment variable is required")
    return role_arn


def get_ssm_path_prefix() -> str:
    prefix = os.getenv("SSM_PATH_PREFIX")
    if not prefix:
        raise ValueError("SSM_PATH_PREFIX environment variable is required")
    return prefix
