import hashlib
import pathlib
from unittest.mock import MagicMock, patch

import pytest

from speedsnake.service import s3


class TestCalculateMd5:
    def test_calculates_correct_hash_for_known_content(self, tmp_path):
        test_file = tmp_path / "test.parquet"
        content = b"hello world"
        test_file.write_bytes(content)

        expected = hashlib.md5(content).hexdigest()
        assert s3.calculate_md5(test_file) == expected

    def test_handles_empty_file(self, tmp_path):
        test_file = tmp_path / "empty.parquet"
        test_file.write_bytes(b"")

        expected = hashlib.md5(b"").hexdigest()
        assert s3.calculate_md5(test_file) == expected


class TestConstructS3Key:
    def test_strips_uploads_prefix_and_adds_results(self, tmp_path):
        uploads_dir = tmp_path / "uploads"
        parquet_path = uploads_dir / "location=abc" / "year=2026" / "speedtest_001.parquet"

        key = s3.construct_s3_key(parquet_path, uploads_dir)
        assert key == "results/location=abc/year=2026/speedtest_001.parquet"

    def test_preserves_hive_partitions(self, tmp_path):
        uploads_dir = tmp_path / "uploads"
        parquet_path = (
            uploads_dir / "location=abc" / "year=2026" / "month=02" / "day=09" / "speedtest_001.parquet"
        )

        key = s3.construct_s3_key(parquet_path, uploads_dir)
        assert key == "results/location=abc/year=2026/month=02/day=09/speedtest_001.parquet"


class TestVerifyUploadChecksum:
    def test_matching_returns_true(self):
        assert s3.verify_upload_checksum("abc123", "abc123") is True

    def test_strips_etag_quotes(self):
        assert s3.verify_upload_checksum("abc123", '"abc123"') is True

    def test_mismatch_returns_false(self):
        assert s3.verify_upload_checksum("abc123", '"differenthash"') is False


class TestAssumeRole:
    def test_calls_sts_with_role_arn(self, monkeypatch):
        monkeypatch.setenv("AWS_ROLE_ARN", "arn:aws:iam::123456789012:role/TestRole")
        monkeypatch.setenv("AWS_REGION", "eu-west-2")

        mock_sts = MagicMock()
        mock_sts.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": "ASIA...",
                "SecretAccessKey": "secret",
                "SessionToken": "token",
            }
        }

        with patch("boto3.client", return_value=mock_sts):
            with patch("boto3.Session") as mock_session:
                s3.assume_role()

                mock_sts.assume_role.assert_called_once_with(
                    RoleArn="arn:aws:iam::123456789012:role/TestRole",
                    RoleSessionName="speedsnake-session",
                )

    def test_returns_session_with_credentials(self, monkeypatch):
        monkeypatch.setenv("AWS_ROLE_ARN", "arn:aws:iam::123456789012:role/TestRole")
        monkeypatch.setenv("AWS_REGION", "eu-west-2")

        mock_sts = MagicMock()
        mock_sts.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": "ASIA_KEY",
                "SecretAccessKey": "my_secret",
                "SessionToken": "my_token",
            }
        }

        with patch("boto3.client", return_value=mock_sts):
            with patch("boto3.Session") as mock_session:
                s3.assume_role()

                mock_session.assert_called_once_with(
                    aws_access_key_id="ASIA_KEY",
                    aws_secret_access_key="my_secret",
                    aws_session_token="my_token",
                    region_name="eu-west-2",
                )


class TestReadAppConfig:
    def test_reads_bucket_and_location_uuid_from_ssm(self, monkeypatch):
        monkeypatch.setenv("SSM_PATH_PREFIX", "/production/speedsnake/app")
        monkeypatch.setenv("AWS_REGION", "eu-west-2")

        mock_ssm = MagicMock()
        mock_ssm.get_parameters.return_value = {
            "Parameters": [
                {"Name": "/production/speedsnake/app/s3_bucket_name", "Value": "my-bucket"},
                {"Name": "/production/speedsnake/app/speedtest_location_uuid", "Value": "some-uuid"},
            ]
        }

        mock_session = MagicMock()
        mock_session.client.return_value = mock_ssm

        result = s3.read_app_config(mock_session)

        assert result["s3_bucket_name"] == "my-bucket"
        assert result["speedtest_location_uuid"] == "some-uuid"

    def test_uses_ssm_path_prefix(self, monkeypatch):
        monkeypatch.setenv("SSM_PATH_PREFIX", "/staging/speedsnake/app")
        monkeypatch.setenv("AWS_REGION", "eu-west-2")

        mock_ssm = MagicMock()
        mock_ssm.get_parameters.return_value = {"Parameters": []}

        mock_session = MagicMock()
        mock_session.client.return_value = mock_ssm

        s3.read_app_config(mock_session)

        mock_ssm.get_parameters.assert_called_once_with(
            Names=[
                "/staging/speedsnake/app/s3_bucket_name",
                "/staging/speedsnake/app/speedtest_location_uuid",
            ],
            WithDecryption=False,
        )


class TestUploadParquetFile:
    def test_calls_put_object_with_correct_params(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AWS_REGION", "eu-west-2")

        test_file = tmp_path / "speedtest_001.parquet"
        test_file.write_bytes(b"parquet data")

        mock_s3 = MagicMock()
        mock_s3.put_object.return_value = {"ETag": '"abc123"'}

        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3

        s3.upload_parquet_file(test_file, "results/test/speedtest_001.parquet", "my-bucket", mock_session)

        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "my-bucket"
        assert call_kwargs["Key"] == "results/test/speedtest_001.parquet"

    def test_returns_etag_from_response(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AWS_REGION", "eu-west-2")

        test_file = tmp_path / "speedtest_001.parquet"
        test_file.write_bytes(b"parquet data")

        mock_s3 = MagicMock()
        mock_s3.put_object.return_value = {"ETag": '"abc123"'}

        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3

        etag = s3.upload_parquet_file(test_file, "results/test/speedtest_001.parquet", "my-bucket", mock_session)

        assert etag == '"abc123"'
