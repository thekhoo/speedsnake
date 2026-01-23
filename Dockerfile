FROM python:3.13-slim

WORKDIR /app

# install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# install speedtest cli
RUN apt-get update && apt-get install -y curl sudo \
    && curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | sudo bash \
    && apt-get install -y speedtest-cli \
    && rm -rf /var/lib/apt/lists/*

# install dependencies with uv
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev
