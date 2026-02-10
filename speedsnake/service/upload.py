import hashlib
import pathlib

import speedsnake.aws.s3 as s3
import speedsnake.aws.sts as sts
import speedsnake.service.environment as env


def calculate_md5(file_path: pathlib.Path) -> str:
    """Calculate MD5 hex digest of a file, reading in chunks for memory efficiency."""
    md5 = hashlib.md5()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()


def upload_parquet_file(local_path: pathlib.Path) -> str:
    """Upload a parquet file to S3 and return the ETag from the response."""
    upload_iam_role = env.get_aws_role_arn()
    session = sts.assume_role(upload_iam_role, role_session_name="speedsnake-parquet-upload")
    res = s3.upload_object(
        filepath=local_path,
        s3_location=s3.S3ObjectLocation(bucket=env.get_s3_bucket_name(), key=str(local_path)),
        session=session,
    )
    return res["ETag"]


def verify_upload_checksum(local_md5: str, s3_etag: str) -> bool:
    """Verify the local MD5 matches the S3 ETag (stripping surrounding quotes)."""
    return local_md5 == s3_etag.strip('"')
