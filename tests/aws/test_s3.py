import boto3
import pytest
from moto import mock_aws

from speedsnake.aws.s3 import S3ObjectLocation, S3PrefixLocation, get_s3_client, upload_object

REGION = "eu-west-2"
BUCKET = "test-bucket"


@pytest.fixture
def s3_bucket():
    """Create a mocked S3 bucket."""
    with mock_aws():
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(
            Bucket=BUCKET,
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )
        yield s3


class TestS3ObjectLocation:
    def test_stores_bucket_and_key(self):
        loc = S3ObjectLocation(bucket="my-bucket", key="path/to/file.parquet")
        assert loc.bucket == "my-bucket"
        assert loc.key == "path/to/file.parquet"

    def test_is_immutable(self):
        loc = S3ObjectLocation(bucket="b", key="k")
        with pytest.raises(AttributeError):
            loc.bucket = "other"  # type: ignore[misc]


class TestS3PrefixLocation:
    def test_stores_bucket_and_prefix(self):
        loc = S3PrefixLocation(bucket="my-bucket", prefix="results/year=2026/")
        assert loc.bucket == "my-bucket"
        assert loc.prefix == "results/year=2026/"


class TestGetS3Client:
    def test_returns_s3_client(self):
        with mock_aws():
            client = get_s3_client(region=REGION)
            assert client.meta.service_model.service_name == "s3"

    def test_uses_default_region(self):
        with mock_aws():
            client = get_s3_client()
            assert client.meta.region_name == "eu-west-2"

    def test_uses_custom_region(self):
        with mock_aws():
            client = get_s3_client(region="us-east-1")
            assert client.meta.region_name == "us-east-1"


class TestUploadObject:
    def test_uploads_file_to_s3(self, tmp_path, s3_bucket):
        test_file = tmp_path / "speedtest_001.parquet"
        test_file.write_bytes(b"parquet data")

        location = S3ObjectLocation(bucket=BUCKET, key="results/speedtest_001.parquet")
        upload_object(test_file, location, region=REGION)

        response = s3_bucket.get_object(Bucket=BUCKET, Key="results/speedtest_001.parquet")
        assert response["Body"].read() == b"parquet data"

    def test_returns_response_with_etag(self, tmp_path, s3_bucket):
        test_file = tmp_path / "speedtest_001.parquet"
        test_file.write_bytes(b"parquet data")

        location = S3ObjectLocation(bucket=BUCKET, key="results/speedtest_001.parquet")
        response = upload_object(test_file, location, region=REGION)

        assert "ETag" in response

    def test_uploads_to_hive_partitioned_key(self, tmp_path, s3_bucket):
        test_file = tmp_path / "speedtest_001.parquet"
        test_file.write_bytes(b"data")

        key = "results/location=abc/year=2026/month=02/day=09/speedtest_001.parquet"
        location = S3ObjectLocation(bucket=BUCKET, key=key)
        upload_object(test_file, location, region=REGION)

        response = s3_bucket.get_object(Bucket=BUCKET, Key=key)
        assert response["Body"].read() == b"data"

    def test_uses_session_when_provided(self, tmp_path, s3_bucket):
        test_file = tmp_path / "speedtest_001.parquet"
        test_file.write_bytes(b"session data")

        session = boto3.Session(
            aws_access_key_id="test",
            aws_secret_access_key="test",
            aws_session_token="test",
            region_name=REGION,
        )

        location = S3ObjectLocation(bucket=BUCKET, key="results/speedtest_001.parquet")
        upload_object(test_file, location, region=REGION, session=session)

        response = s3_bucket.get_object(Bucket=BUCKET, Key="results/speedtest_001.parquet")
        assert response["Body"].read() == b"session data"

    def test_uses_direct_client_when_no_session(self, tmp_path, s3_bucket):
        test_file = tmp_path / "speedtest_001.parquet"
        test_file.write_bytes(b"direct client data")

        location = S3ObjectLocation(bucket=BUCKET, key="results/speedtest_001.parquet")
        upload_object(test_file, location, region=REGION, session=None)

        response = s3_bucket.get_object(Bucket=BUCKET, Key="results/speedtest_001.parquet")
        assert response["Body"].read() == b"direct client data"
