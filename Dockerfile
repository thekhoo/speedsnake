FROM python:3.13-slim

WORKDIR /app

# we need grep to install the speedtest cli
RUN apt-get update && apt-get install -y curl sudo

RUN curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | sudo bash
RUN apt-get install -y speedtest-cli

# remove lists from apt-get to reduce image size
RUN rm -rf /var/lib/apt/lists/*

# install requirements
COPY pyproject.toml .
RUN pip install -e .
