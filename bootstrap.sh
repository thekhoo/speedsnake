#!/bin/bash

# make sure the latest version is pulled
git pull origin main

COMMIT_HASH=$(git rev-parse HEAD)
echo "Current commit hash: $COMMIT_HASH"

# create a virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "No virtual environment found. Creating one with python version $(python --version)"
    python -m venv .venv
fi

# activate the virtual environment and install the requirements
# upgrade pip and install dependencies (no source, just use venv paths)
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -e .

# set the environment variable for commit hash and sleep seconds
export COMMIT_HASH
export SLEEP_SECONDS=600 # 10 minutes

# run the processing loop using venv's python
# Run Python loop **in foreground**
exec ./.venv/bin/python -m speedtest.handlers.loop