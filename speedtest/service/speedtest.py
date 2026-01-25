import json
import logging
import subprocess
import typing

logger = logging.getLogger(__name__)


def round_floats_to_ints(data: typing.Any, exclude_keys: set[str] | None = None) -> typing.Any:
    """Recursively round all float values to integers in a data structure.

    Args:
        data: Input data (dict, list, or primitive value)
        exclude_keys: Set of keys whose float values should not be rounded

    Returns:
        Data with all floats converted to integers via rounding (except excluded keys)
    """
    if exclude_keys is None:
        exclude_keys = set()

    if isinstance(data, dict):
        return {key: round_floats_to_ints(value, exclude_keys) if key not in exclude_keys else value for key, value in data.items()}
    elif isinstance(data, list):
        return [round_floats_to_ints(item, exclude_keys) for item in data]
    elif isinstance(data, float):
        return round(data)
    else:
        return data


class SpeedtestServerResponse(typing.TypedDict):
    url: str
    lat: float
    lon: float
    name: str
    country: str
    cc: str
    sponsor: str
    id: int
    host: str
    d: float
    latency: int


class SpeedtestClientResponse(typing.TypedDict):
    ip: str
    lat: float
    lon: float
    isp: str
    isprating: str
    rating: int
    ispdlavg: int
    ispulavg: int
    loggedin: bool
    country: str


class SpeedtestResponse(typing.TypedDict):
    download: int
    upload: int
    ping: int
    server: SpeedtestServerResponse
    timestamp: str
    bytes_sent: int
    bytes_received: int
    share: typing.Any
    client: SpeedtestClientResponse


def run(flags: typing.Optional[list[str]] = None) -> SpeedtestResponse:
    if flags is None:
        flags = ["--secure", "--json", "--bytes"]

    logger.info(f"running speedtest with flags: {' '.join(flags)}")
    result = subprocess.run(["speedtest", *flags], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Speedtest failed with error: {result.stderr}")
        raise Exception("Speedtest failed")

    res_dict = json.loads(result.stdout)
    return round_floats_to_ints(res_dict, exclude_keys={"lat", "lon", "d"})


def get_date_str_from_result(result: SpeedtestResponse) -> str:
    return result["timestamp"].split("T")[0]  # type: ignore
