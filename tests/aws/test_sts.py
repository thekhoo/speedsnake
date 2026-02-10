import boto3
import pytest
from moto import mock_aws

from speedsnake.aws.sts import assume_role

REGION = "eu-west-2"
ROLE_ARN = "arn:aws:iam::123456789012:role/TestRole"


@pytest.fixture
def iam_role():
    """Create a mocked IAM role that can be assumed."""
    with mock_aws():
        iam = boto3.client("iam", region_name=REGION)
        iam.create_role(
            RoleName="TestRole",
            AssumeRolePolicyDocument='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}',
        )
        yield


class TestAssumeRole:
    def test_returns_boto3_session(self, iam_role):
        session = assume_role(ROLE_ARN, region=REGION)
        assert isinstance(session, boto3.Session)

    def test_session_uses_temporary_credentials(self, iam_role):
        session = assume_role(ROLE_ARN, region=REGION)
        credentials = session.get_credentials().get_frozen_credentials()
        assert credentials.access_key is not None
        assert credentials.secret_key is not None
        assert credentials.token is not None

    def test_session_uses_specified_region(self, iam_role):
        session = assume_role(ROLE_ARN, region="us-east-1")
        assert session.region_name == "us-east-1"

    def test_default_region_is_eu_west_2(self, iam_role):
        session = assume_role(ROLE_ARN)
        assert session.region_name == "eu-west-2"

    def test_default_session_name_is_default(self, iam_role):
        # Verifies no error is raised with the default session name
        session = assume_role(ROLE_ARN)
        assert session is not None

    def test_custom_session_name_is_passed_to_sts(self, iam_role):
        # moto accepts any session name; verify it doesn't raise
        session = assume_role(ROLE_ARN, role_session_name="speedsnake-parquet-upload", region=REGION)
        assert isinstance(session, boto3.Session)

    def test_returned_session_can_create_service_clients(self, iam_role):
        session = assume_role(ROLE_ARN, region=REGION)
        s3_client = session.client("s3")
        assert s3_client.meta.service_model.service_name == "s3"
