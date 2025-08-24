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
source .venv/bin/activate
pip install -e .


# run the processing loop
python -m speedtest.handlers.loop