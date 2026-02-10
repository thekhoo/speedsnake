from unittest.mock import patch

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
    def test_raises_if_ssm_fails(self, monkeypatch):
        monkeypatch.setenv("UNIVERSE", "production")
        monkeypatch.setenv("SERVICE_NAME", "speedsnake")
        with patch("speedsnake.service.environment.ssm.get_parameter", side_effect=Exception("not found")):
            with pytest.raises(RuntimeError, match="Failed to get AWS role ARN from SSM"):
                environment.get_aws_role_arn()

    def test_returns_value_from_ssm(self, monkeypatch):
        monkeypatch.setenv("UNIVERSE", "production")
        monkeypatch.setenv("SERVICE_NAME", "speedsnake")
        with patch(
            "speedsnake.service.environment.ssm.get_parameter",
            return_value="arn:aws:iam::123456789012:role/MyRole",
        ):
            assert environment.get_aws_role_arn() == "arn:aws:iam::123456789012:role/MyRole"


class TestGetSsmPathPrefix:
    def test_raises_if_universe_missing(self, monkeypatch):
        monkeypatch.delenv("UNIVERSE", raising=False)
        with pytest.raises(KeyError):
            environment.get_ssm_path_prefix()

    def test_constructs_from_universe_and_service_name(self, monkeypatch):
        monkeypatch.setenv("UNIVERSE", "production")
        monkeypatch.setenv("SERVICE_NAME", "speedsnake")
        assert environment.get_ssm_path_prefix() == "/production/speedsnake/app"
