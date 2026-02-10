import functools

import boto3


def _set_nested(d: dict, keys: list[str], value: str) -> None:
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value


@functools.lru_cache(maxsize=None)
def get_parameter(name: str, region: str = "eu-west-2") -> str:
    ssm = boto3.client("ssm", region_name=region)
    response = ssm.get_parameter(Name=name, WithDecryption=True)
    return response["Parameter"]["Value"]


@functools.lru_cache(maxsize=None)
def get_parameters_by_path(path: str, region: str = "eu-west-2") -> dict:
    ssm = boto3.client("ssm", region_name=region)
    prefix = path.rstrip("/")
    result: dict = {}
    paginator = ssm.get_paginator("get_parameters_by_path")
    for page in paginator.paginate(Path=prefix, Recursive=True, WithDecryption=True):
        for param in page["Parameters"]:
            relative = param["Name"][len(prefix) :].lstrip("/")
            keys = relative.split("/")
            _set_nested(result, keys, param["Value"])
    return result
