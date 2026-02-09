# Production Dockerfile
# Multi-stage build for optimized image size

# Stage 1: Builder
FROM python:3.13-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies to a virtual environment
RUN uv sync --frozen --no-dev

# Stage 2: Runtime
FROM python:3.13-slim

WORKDIR /app

# Install speedtest CLI (only runtime dependency)
RUN apt-get update && apt-get install -y curl sudo \
    && curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | sudo bash \
    && apt-get install -y speedtest-cli \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN useradd -m -u 1000 speedtest && \
    mkdir -p /app/results /app/logs /app/uploads && \
    chown -R speedtest:speedtest /app

# Copy virtual environment from builder
COPY --from=builder --chown=speedtest:speedtest /app/.venv /app/.venv

# Copy application code
COPY --chown=speedtest:speedtest speedsnake/ /app/speedsnake/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    RESULT_DIR=/app/results \
    LOG_DIR=/app/logs \
    UPLOAD_DIR=/app/uploads

# Switch to non-root user
USER speedtest

# Health check
HEALTHCHECK --interval=5m --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import pathlib; import sys; sys.exit(0 if pathlib.Path('/app/logs/speedtest.log').exists() else 1)"

# Run the application
CMD ["python", "-m", "speedsnake.handlers.loop"]
