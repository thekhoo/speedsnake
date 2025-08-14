import datetime
import json
import logging
import os
import pathlib
import sys
import time
import typing
from uuid import uuid4

import speedtest


class SpeedtestResultsDict(typing.TypedDict):
    download: int
    upload: int
    ping: int
    server: dict
    timestamp: str
    bytes_sent: int
    bytes_received: int
    share: typing.Any
    client: dict


logger = logging.getLogger(__name__)

MINUTE = 60  # seconds
MEGABYTES = 1 / 1024 / 1024


def get_output_directory() -> pathlib.Path:
    return pathlib.Path("cache")


def get_sleep_interval_minutes() -> int:
    return int(os.environ.get("SLEEP_INTERVAL_MINUTES", "5"))


def sleep(seconds: int):
    logger.info(f"sleeping for {seconds} seconds")
    time.sleep(seconds)


def run_speed_check() -> SpeedtestResultsDict:
    logger.info("starting speed check")
    client = speedtest.Speedtest(secure=True)
    client.get_best_server()
    client.download()
    client.upload()

    res = client.results
    download_speed_mbps = res.download * MEGABYTES
    upload_speed_mbps = res.upload * MEGABYTES

    logger.info(f"download speed of {download_speed_mbps:.2f} Mbps")
    logger.info(f"upload speed of {upload_speed_mbps:.2f} Mbps")

    return SpeedtestResultsDict(**res.dict())


def cache_data_local(res: SpeedtestResultsDict) -> pathlib.Path:
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    file_path = get_output_directory() / "speedtest" / f"{today_str}_results.json"
    logger.info(f"writing file to {file_path}")

    def read_json(path: pathlib.Path):
        with open(path, "r") as f:
            return json.load(f)

    def write_json(path: pathlib.Path, data):
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    # always make sure we have the directories
    file_path.parent.mkdir(parents=True, exist_ok=True)

    current_data_raw = read_json(file_path) if file_path.exists() else {}
    updated_data = current_data_raw.get("results", [])
    updated_data.append(res)

    write_json(file_path, {"results": updated_data})

    return file_path


def run_loop():
    seconds_to_sleep = get_sleep_interval_minutes() * MINUTE

    while True:
        try:
            data = run_speed_check()

            # store this data + upload it to S3?
            cache_path = cache_data_local(data)

            sleep(seconds_to_sleep)
        except KeyboardInterrupt as _:
            logger.warning("bail out requested, bailing.")
            break
        except Exception as e:
            logger.exception(e)

    logger.info("program terminated.")
    sys.exit(0)


if __name__ == "__main__":
    # configure logging
    local_request_id = f"local-{uuid4()}"

    # get a basic configuration out there for all logging
    logging.basicConfig(
        format=f"%(asctime)s.%(msecs)dZ {local_request_id} %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=logging.INFO,
    )
    run_loop()
