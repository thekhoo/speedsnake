# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SpeedSnake is a Python application that periodically runs Ookla Speedtest CLI, collects results, and stores them as CSV files in Hive partition format. Complete days (before today) are automatically converted to numbered Parquet files with location metadata for efficient storage and analysis.

## Commands

### Run locally

```bash
./bootstrap.sh  # Sets up venv, installs deps, runs with 10-min intervals
```

### Run with Docker

All Docker files are organized in the `docker/` directory with separate `development/` and `production/` configurations.

#### Development

```bash
# Build and run development container
docker-compose -f docker/development/docker-compose.yml up --build

# Run in detached mode
docker-compose -f docker/development/docker-compose.yml up -d

# View logs
docker-compose -f docker/development/docker-compose.yml logs -f

# Stop container
docker-compose -f docker/development/docker-compose.yml down
```

#### Production

```bash
# Using docker-compose (pulls from Docker Hub)
docker-compose -f docker/production/docker-compose.yml up -d

# Build locally instead of pulling from Docker Hub
docker-compose -f docker/production/docker-compose.yml up --build -d

# Or run directly with docker
docker run -d \
  --name speedtest-service \
  -e SLEEP_SECONDS=600 \
  -e SPEEDTEST_LOCATION_UUID=your-uuid-here \
  -v speedtest-results:/app/results \
  -v speedtest-logs:/app/logs \
  -v speedtest-uploads:/app/uploads \
  thekhoo/speedsnake:latest
```

#### Build production image locally

```bash
docker build -f docker/production/Dockerfile -t speedsnake:latest .
```

### Run directly

```bash
uv run python -m speedsnake.handlers.loop
```

### Testing

```bash
uv run pytest                     # run all tests
uv run pytest tests/test_speedtest.py  # run specific file
uv run pytest -k "test_name"      # run tests matching pattern
```

### Linting, formatting, and type checking

```bash
uv run ruff check speedsnake/ tests/      # lint
uv run ruff format speedsnake/ tests/     # format
uv run pyrefly check                     # type check
```

### Install dependencies

```bash
uv sync                    # production deps
uv sync --group development  # with dev deps
```

## Architecture

```
speedsnake/
├── handlers/loop.py    # Entry point - polling loop with @loop decorator
├── service/
│   ├── speedtest.py    # Wrapper around speedtest-cli binary (subprocess)
│   └── environment.py  # Environment variable configuration
├── data/
│   ├── results.py      # CSV file persistence with Hive partitioning
│   └── parquet.py      # Parquet conversion and CSV cleanup
└── core/
    └── logging.py      # JSON logging with rotating file handler
```

### Data Flow

1. `handlers/loop.py` runs infinitely, calling `speedtest.run()` at configured intervals
2. `speedtest.py` executes `speedtest-cli --secure --json --bytes` via subprocess
3. Results are written as CSV files in Hive partition format: `results/year=YYYY/month=MM/day=DD/speedtest_HH-MM-SS.csv`
4. After each loop iteration, complete days (before today) are automatically converted:
   - All CSVs for the day are combined into a numbered Parquet file
   - `speedtest_address` column is added from environment variable
   - Parquet file is verified (row count + column check)
   - Original CSV files are deleted after successful conversion
   - Parquet files written to: `uploads/year=YYYY/month=MM/day=DD/speedtest_NNN.parquet`

### Output Format

- **Format**: CSV with headers
- **Partitioning**: Hive format (`year=YYYY/month=MM/day=DD/`)
- **Filename**: `speedtest_HH-MM-SS.csv` (one file per test run)
- **Column names**: Flattened from JSON structure
  - Top-level fields: `download`, `upload`, `ping`, `timestamp`, etc.
  - Nested fields: joined with underscore (e.g., `server_name`, `client_ip`)

**Example structure:**

```
results/
└── year=2025/
    └── month=01/
        └── day=23/
            ├── speedtest_10-30-45.csv
            ├── speedtest_10-40-45.csv
            └── speedtest_10-50-45.csv
```

### Parquet Conversion (Automatic)

Complete days (before today) are automatically converted to Parquet format at the end of each loop iteration:

- **Trigger**: Runs after each speedtest execution (in finally block)
- **Conversion**: All CSV files for a day → single numbered Parquet file
- **Location tracking**: Location UUID is part of the Hive partition path structure
- **Numbering**: Finds highest existing number in partition, increments (001, 002, 003...)
- **Verification**: Validates row count before deleting CSVs
- **Fire-and-forget**: No state tracking; always creates new numbered file
- **Error handling**: Conversion errors logged but don't stop main loop

**Parquet output structure:**

```
uploads/
└── location=<UUID>/
    └── year=2025/
        └── month=01/
            ├── day=20/
            │   ├── speedtest_001.parquet  # First conversion
            │   └── speedtest_002.parquet  # Second conversion (if re-run)
            ├── day=21/
            │   └── speedtest_001.parquet
            └── day=22/
                └── speedtest_001.parquet
```

**Note**: Original CSV files are deleted after successful Parquet conversion and verification.

### Configuration (Environment Variables)

- `SLEEP_SECONDS`: Interval between tests (default: 5 seconds; bootstrap uses 600)
- `RESULT_DIR`: CSV output directory (default: `./results`)
- `UPLOAD_DIR`: Parquet output directory (default: `./uploads`)
- `SPEEDTEST_LOCATION_UUID`: Location identifier used in Parquet partition path (default: `unknown-location`, recommended: UUID4 string)
- `LOG_DIR`: Log output directory (default: `./logs`)
- `COMMIT_HASH`: Git commit tracking

### Logging

- JSON formatted logs written to `logs/speedtest.log`
- Rotating file handler: 5MB max per file, keeps 10 backup files (`.log.1`, `.log.2`, etc.)

## Docker

The project supports both development and production Docker setups with different optimizations. All Docker files are organized in the `docker/` directory.

### Directory Structure

```
docker/
├── development/
│   ├── Dockerfile              # Development Dockerfile
│   └── docker-compose.yml      # Development compose config
├── production/
│   ├── Dockerfile              # Production Dockerfile
│   └── docker-compose.yml      # Production compose config
└── .dockerignore               # Files to exclude from build
```

### Docker Files

- **`docker/development/Dockerfile`** - Development-focused build
  - Faster rebuilds
  - Includes development dependencies
  - Designed for volume mounts (hot-reload)
  - Root user for easier development

- **`docker/production/Dockerfile`** - Production-ready multi-stage build
  - Minimal image size using multi-stage build
  - Non-root user for security
  - Application code baked into image
  - Health check configured
  - No volume mounts for code (only data)

- **`docker/development/docker-compose.yml`** - Development configuration
  - Uses local `Dockerfile`
  - Mounts source code for hot-reload
  - Short sleep intervals (30s default)
  - Local directory mounts for data

- **`docker/production/docker-compose.yml`** - Production configuration
  - Uses pre-built image from Docker Hub (can be built locally)
  - Named volumes for data persistence
  - Longer sleep intervals (600s default)
  - Restart policy: `unless-stopped`
  - Health checks enabled

### Docker Hub Deployment

Images are automatically built and pushed to `thekhoo/speedsnake` on Docker Hub when:

- Push to `main` branch (tagged as `latest`)
- Tagged with semantic version (e.g., `v1.2.3`)

**Required GitHub Secrets:**

- `DOCKERHUB_USERNAME` - Docker Hub username
- `DOCKERHUB_TOKEN` - Docker Hub access token

### Production Deployment

1. Pull the image:

   ```bash
   docker pull thekhoo/speedsnake:latest
   ```

2. Run with docker-compose:

   ```bash
   docker-compose -f docker/production/docker-compose.yml up -d
   ```

3. Set environment variables:
   ```bash
   export SPEEDTEST_LOCATION_UUID="your-uuid-here"
   export SLEEP_SECONDS=600
   docker-compose -f docker/production/docker-compose.yml up -d
   ```

### Data Persistence

Production setup uses named Docker volumes:

- `speedtest-results` - CSV files (before conversion)
- `speedtest-logs` - JSON logs with rotation
- `speedtest-uploads` - Parquet files organized by location

## Code Style

- Line length: 120 (ruff)
- Linting: ruff (E, F, I, W rules)
- Formatting: ruff format
- Type checking: pyrefly
- Python version: 3.13

## Claude Instructions

- Ask clarifying questions in requirements are ambiguous
- Explain _why_ changes are suggested
- Always use full names when describing the universe (development or production)

## IaaC Instructions for AWS

- Always use SAM templates where possible
- Use principle of least permission to grant permissions to resources
- Where possible, use ResourceTag based permissions

## Coding Preferences

- Prefer small, composable functions where possible
- Write code that is easy to test

## Merge and Commit Behaviour

- When making a change, always checkout a new branch first so code can be commited in increments
- Each task that is generated should be it's own commit
- Don't bundle everything together in one big commit
- Use conventional commits for the commit message structure

## Agents and Planning

- Scope the work that needs to be done and form a dependency tree.
- If there are multiple tasks in the dependency tree that can be handled in parallel, spawn agents to complete them

## Out of Scope

- Do not introduce new frameworks without asking
- If there is a package/framework that could reduce the amount of code needed, suggest it
- Do not optimize prematurely
