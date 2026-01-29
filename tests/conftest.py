"""Shared test fixtures and utilities."""

import typing

from speedtest.service.speedtest import (
    SpeedtestClientResponse,
    SpeedtestResponse,
    SpeedtestServerResponse,
)


def make_speedtest_response(**overrides: typing.Any) -> SpeedtestResponse:
    """Create a minimal valid SpeedtestResponse for testing.

    Args:
        **overrides: Fields to override in the default response

    Returns:
        A complete SpeedtestResponse with defaults that can be overridden
    """
    default_server: SpeedtestServerResponse = {
        "url": "http://test.example.com",
        "lat": "0.0",
        "lon": "0.0",
        "name": "Test Server",
        "country": "US",
        "cc": "US",
        "sponsor": "Test Sponsor",
        "id": "12345",
        "host": "test.example.com:8080",
        "d": 0.0,
        "latency": 10,
    }

    default_client: SpeedtestClientResponse = {
        "ip": "192.168.1.1",
        "lat": "0.0",
        "lon": "0.0",
        "isp": "Test ISP",
        "isprating": "3.7",
        "rating": "0",
        "ispdlavg": "0",
        "ispulavg": "0",
        "loggedin": "0",
        "country": "US",
    }

    default_response: SpeedtestResponse = {
        "download": 100000000,
        "upload": 50000000,
        "ping": 15,
        "server": default_server,
        "timestamp": "2025-01-15T10:30:00.000000Z",
        "bytes_sent": 1000000,
        "bytes_received": 5000000,
        "share": None,
        "client": default_client,
    }

    # Apply overrides
    result = default_response.copy()
    for key, value in overrides.items():
        if key in result:
            result[key] = value  # type: ignore

    return result
