import json
import logging
import subprocess
import typing

logger = logging.getLogger(__name__)


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
    latency: float


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


def run(flags: list[str] = None) -> SpeedtestResponse:
    if flags is None:
        flags = ["--secure", "--json", "--bytes"]

    logger.info(f'running speedtest with flags: {" ".join(flags)}')
    result = subprocess.run(["speedtest", *flags], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Speedtest failed with error: {result.stderr}")
        raise Exception("Speedtest failed")

    res_dict = json.loads(result.stdout)
    return res_dict


def get_date_str_from_result(result: SpeedtestResponse) -> str:
    return result["timestamp"].split("T")[0]  # type: ignore
