import boto3
import pytest
from moto import mock_aws

from speedsnake.aws.ssm import get_parameter, get_parameters_by_path

PREFIX = "/production/service/app"
REGION = "eu-west-2"


@pytest.fixture(autouse=True)
def clear_ssm_cache():
    """Clear the lru_cache before each test to prevent cross-test bleedover."""
    get_parameter.cache_clear()
    get_parameters_by_path.cache_clear()
    yield
    get_parameter.cache_clear()
    get_parameters_by_path.cache_clear()


@pytest.fixture
def ssm_parameters():
    """Start a mocked AWS environment and seed SSM parameters under PREFIX."""
    with mock_aws():
        ssm = boto3.client("ssm", region_name=REGION)
        ssm.put_parameter(Name=f"{PREFIX}/a", Value="flat_value", Type="String")
        ssm.put_parameter(Name=f"{PREFIX}/b/c", Value="nested_value", Type="String")
        ssm.put_parameter(Name=f"{PREFIX}/b/d", Value="sibling_value", Type="String")
        ssm.put_parameter(Name=f"{PREFIX}/x/y/z", Value="deep_value", Type="String")
        ssm.put_parameter(Name=f"{PREFIX}/secret", Value="secret_value", Type="SecureString")
        yield


class TestGetParametersByPath:
    def test_flat_key_is_returned(self, ssm_parameters):
        result = get_parameters_by_path(PREFIX, region=REGION)
        assert result["a"] == "flat_value"

    def test_nested_key_is_returned(self, ssm_parameters):
        result = get_parameters_by_path(PREFIX, region=REGION)
        assert result["b"]["c"] == "nested_value"

    def test_sibling_keys_are_returned_under_same_parent(self, ssm_parameters):
        result = get_parameters_by_path(PREFIX, region=REGION)
        assert result["b"]["c"] == "nested_value"
        assert result["b"]["d"] == "sibling_value"

    def test_deeply_nested_key_is_returned(self, ssm_parameters):
        result = get_parameters_by_path(PREFIX, region=REGION)
        assert result["x"]["y"]["z"] == "deep_value"

    def test_returns_empty_dict_when_no_parameters(self):
        with mock_aws():
            result = get_parameters_by_path("/nonexistent/path", region=REGION)
            assert result == {}

    def test_trailing_slash_on_prefix_is_handled(self, ssm_parameters):
        result = get_parameters_by_path(PREFIX + "/", region=REGION)
        assert result["a"] == "flat_value"
        assert result["b"]["c"] == "nested_value"

    def test_secure_string_is_decrypted_and_returned(self, ssm_parameters):
        result = get_parameters_by_path(PREFIX, region=REGION)
        assert result["secret"] == "secret_value"

    def test_result_is_cached_and_aws_is_only_called_once(self, ssm_parameters):
        first = get_parameters_by_path(PREFIX, region=REGION)
        second = get_parameters_by_path(PREFIX, region=REGION)
        assert first is second
        info = get_parameters_by_path.cache_info()
        assert info.hits == 1
        assert info.misses == 1


class TestGetParameter:
    def test_returns_string_value(self, ssm_parameters):
        result = get_parameter(f"{PREFIX}/a", region=REGION)
        assert result == "flat_value"

    def test_returns_secure_string_decrypted(self, ssm_parameters):
        result = get_parameter(f"{PREFIX}/secret", region=REGION)
        assert result == "secret_value"

    def test_result_is_cached_and_aws_is_only_called_once(self, ssm_parameters):
        first = get_parameter(f"{PREFIX}/a", region=REGION)
        second = get_parameter(f"{PREFIX}/a", region=REGION)
        assert first is second
        info = get_parameter.cache_info()
        assert info.hits == 1
        assert info.misses == 1
