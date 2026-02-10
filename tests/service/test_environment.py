import pytest

from speedsnake.service import environment


class TestGetAwsRegion:
    def test_default_value(self, monkeypatch):
        monkeypatch.delenv("AWS_REGION", raising=False)
        assert environment.get_aws_region() == "eu-west-2"

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        assert environment.get_aws_region() == "us-east-1"


class TestGetAwsRoleArn:
    def test_raises_if_missing(self, monkeypatch):
        monkeypatch.delenv("AWS_ROLE_ARN", raising=False)
        with pytest.raises(ValueError, match="AWS_ROLE_ARN environment variable is required"):
            environment.get_aws_role_arn()

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("AWS_ROLE_ARN", "arn:aws:iam::123456789012:role/MyRole")
        assert environment.get_aws_role_arn() == "arn:aws:iam::123456789012:role/MyRole"


class TestGetSsmPathPrefix:
    def test_raises_if_missing(self, monkeypatch):
        monkeypatch.delenv("SSM_PATH_PREFIX", raising=False)
        with pytest.raises(ValueError, match="SSM_PATH_PREFIX environment variable is required"):
            environment.get_ssm_path_prefix()

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("SSM_PATH_PREFIX", "/production/speedsnake/app")
        assert environment.get_ssm_path_prefix() == "/production/speedsnake/app"
