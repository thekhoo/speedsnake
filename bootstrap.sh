#!/bin/bash

# make sure the latest version is pulled
git pull origin main

COMMIT_HASH=$(git rev-parse HEAD)
echo "Current commit hash: $COMMIT_HASH"

# create venv and install dependencies with uv
uv sync

# set the environment variable for commit hash and sleep seconds
export COMMIT_HASH
export SLEEP_SECONDS=600 # 10 minutes

# run the processing loop using uv
exec uv run python -m speedtest.handlers.loop