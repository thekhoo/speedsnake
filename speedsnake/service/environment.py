import os
from pathlib import Path

import speedsnake.aws.ssm as ssm


def get_sleep_seconds() -> int:
    # NOTE: this may be changed to get data from a config so it can be
    # updated during runtime without infiltrating this thread
    return int(os.getenv("SLEEP_SECONDS", "5"))


def get_universe() -> str:
    return os.environ["UNIVERSE"]


def get_service_name() -> str:
    return os.environ["SERVICE_NAME"]


def get_result_dir() -> Path:
    return Path("results")


def get_log_dir() -> Path:
    return Path("logs")


def get_upload_dir() -> Path:
    return Path("uploads")


def get_speedtest_location_uuid() -> str:
    return os.getenv("SPEEDTEST_LOCATION_UUID", "unknown-location")


def get_aws_region() -> str:
    return os.getenv("AWS_REGION", "eu-west-2")


def get_ssm_path_prefix() -> str:
    return f"/{get_universe()}/{get_service_name()}/app"


def get_s3_bucket_name() -> str:
    return f"{get_universe()}-{get_service_name()}"


def get_aws_role_arn() -> str:
    try:
        return ssm.get_parameter(f"{get_ssm_path_prefix()}/raspberry-pi-role-arn", region=get_aws_region())
    except Exception as e:
        raise RuntimeError("Failed to get AWS role ARN from SSM") from e
