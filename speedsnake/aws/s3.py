from pathlib import Path
from typing import NamedTuple, Optional

import boto3


class S3ObjectLocation(NamedTuple):
    bucket: str
    key: str


class S3PrefixLocation(NamedTuple):
    bucket: str
    prefix: str


def get_s3_client(region: str = "eu-west-2"):
    return boto3.client("s3", region_name=region)


def upload_object(
    filepath: Path, s3_location: S3ObjectLocation, region: str = "eu-west-2", session: Optional[boto3.Session] = None
):
    s3_client = session.client("s3") if session else get_s3_client(region)
    with filepath.open("rb") as f:
        res = s3_client.put_object(Bucket=s3_location.bucket, Key=s3_location.key, Body=f)
    return res
