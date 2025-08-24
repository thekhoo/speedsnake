import json
import logging
import pathlib

logger = logging.getLogger(__name__)


class TypeException(Exception):
    pass


def read_array(source: pathlib.Path) -> list[dict]:
    if not source.exists():
        logger.warning(f"File {source} does not exist, returning empty array.")
        return []

    with source.open("r") as f:
        current_data = json.load(f)

        if not isinstance(current_data, list):
            raise TypeException(f"Expected list type, received {type(current_data)}")

        return current_data


def update_array(source: pathlib.Path, result: dict):
    current_data = read_array(source)
    new_data = current_data + [result]

    source.parent.mkdir(parents=True, exist_ok=True)
    with source.open("w") as f:
        json.dump(new_data, f, indent=4)

    logger.info(f"Speedtest result saved to {source}")
