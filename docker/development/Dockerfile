# Development Dockerfile
# Optimized for fast rebuilds and volume mounts

FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install speedtest CLI
RUN apt-get update && apt-get install -y curl sudo \
    && curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | sudo bash \
    && apt-get install -y speedtest-cli \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies with development group
RUN uv sync --frozen --group development

# Create directories for mounted volumes
RUN mkdir -p /app/results /app/logs /app/uploads

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Note: Application code will be mounted as a volume
# This allows for hot-reload during development

CMD ["python", "-m", "speedsnake.handlers.loop"]
