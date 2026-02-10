import hashlib
import pathlib

import boto3

import speedsnake.service.environment as env


def assume_role() -> boto3.Session:
    """Assume the configured IAM role and return a boto3 Session with temporary credentials."""
    sts_client = boto3.client("sts", region_name=env.get_aws_region())
    response = sts_client.assume_role(
        RoleArn=env.get_aws_role_arn(),
        RoleSessionName="speedsnake-session",
    )
    credentials = response["Credentials"]
    return boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        region_name=env.get_aws_region(),
    )


def read_app_config(session: boto3.Session) -> dict[str, str]:
    """Read application configuration from SSM Parameter Store."""
    prefix = env.get_ssm_path_prefix()
    ssm_client = session.client("ssm", region_name=env.get_aws_region())
    response = ssm_client.get_parameters(
        Names=[
            f"{prefix}/s3_bucket_name",
            f"{prefix}/speedtest_location_uuid",
        ],
        WithDecryption=False,
    )
    return {param["Name"].split("/")[-1]: param["Value"] for param in response["Parameters"]}


def calculate_md5(file_path: pathlib.Path) -> str:
    """Calculate MD5 hex digest of a file, reading in chunks for memory efficiency."""
    md5 = hashlib.md5()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()


def construct_s3_key(parquet_path: pathlib.Path, uploads_dir: pathlib.Path) -> str:
    """Convert a local parquet path to an S3 key under the results/ prefix.

    Example:
        uploads/location=abc/year=2026/month=02/day=09/speedtest_001.parquet
        → results/location=abc/year=2026/month=02/day=09/speedtest_001.parquet
    """
    relative = parquet_path.relative_to(uploads_dir)
    return f"results/{relative}"


def upload_parquet_file(local_path: pathlib.Path, s3_key: str, bucket: str, session: boto3.Session) -> str:
    """Upload a parquet file to S3 and return the ETag from the response."""
    s3_client = session.client("s3", region_name=env.get_aws_region())
    with local_path.open("rb") as f:
        response = s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=f,
        )
    return response["ETag"]


def verify_upload_checksum(local_md5: str, s3_etag: str) -> bool:
    """Verify the local MD5 matches the S3 ETag (stripping surrounding quotes)."""
    return local_md5 == s3_etag.strip('"')
