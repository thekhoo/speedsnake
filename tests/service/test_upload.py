import hashlib
from unittest.mock import MagicMock, patch

import pytest

from speedsnake.service import upload


class TestCalculateMd5:
    def test_calculates_correct_hash_for_known_content(self, tmp_path):
        test_file = tmp_path / "test.parquet"
        content = b"hello world"
        test_file.write_bytes(content)

        expected = hashlib.md5(content).hexdigest()
        assert upload.calculate_md5(test_file) == expected

    def test_handles_empty_file(self, tmp_path):
        test_file = tmp_path / "empty.parquet"
        test_file.write_bytes(b"")

        expected = hashlib.md5(b"").hexdigest()
        assert upload.calculate_md5(test_file) == expected


class TestVerifyUploadChecksum:
    def test_matching_returns_true(self):
        assert upload.verify_upload_checksum("abc123", "abc123") is True

    def test_strips_etag_quotes(self):
        assert upload.verify_upload_checksum("abc123", '"abc123"') is True

    def test_mismatch_returns_false(self):
        assert upload.verify_upload_checksum("abc123", '"differenthash"') is False


class TestUploadParquetFile:
    @pytest.fixture
    def aws_mocks(self):
        mock_session = MagicMock()
        patchers = [
            patch("speedsnake.service.upload.env.get_aws_role_arn", return_value="arn:aws:iam::123:role/Role"),
            patch("speedsnake.service.upload.env.get_s3_bucket_name", return_value="my-bucket"),
            patch("speedsnake.service.upload.sts.assume_role", return_value=mock_session),
            patch("speedsnake.service.upload.s3.upload_object", return_value={"ETag": '"abc123"'}),
        ]
        mocks = [p.start() for p in patchers]
        yield {"session": mock_session, "upload_object": mocks[3]}
        for p in patchers:
            p.stop()

    def test_calls_upload_object_with_correct_params(self, tmp_path, aws_mocks):
        test_file = tmp_path / "speedtest_001.parquet"
        test_file.write_bytes(b"parquet data")

        upload.upload_parquet_file(test_file)

        aws_mocks["upload_object"].assert_called_once()
        call_kwargs = aws_mocks["upload_object"].call_args.kwargs
        assert call_kwargs["s3_location"].bucket == "my-bucket"
        assert call_kwargs["session"] == aws_mocks["session"]

    def test_returns_etag_from_response(self, tmp_path, aws_mocks):
        test_file = tmp_path / "speedtest_001.parquet"
        test_file.write_bytes(b"parquet data")

        etag = upload.upload_parquet_file(test_file)

        assert etag == '"abc123"'
