# SpeedSnake

A Python application that automatically monitors internet speed by periodically running Ookla Speedtest CLI, collecting results, and storing them in an efficient Parquet format for analysis.

## Features

- **Automated Testing**: Runs speedtest at configurable intervals
- **Efficient Storage**: CSV files automatically converted to Parquet format with compression
- **Location Tracking**: Supports multiple monitoring locations via UUID-based partitioning
- **Hive Partitioning**: Data organized by location, year, month, and day for efficient querying
- **JSON Logging**: Structured logs with rotation (5MB per file, 10 backups)
- **Docker Support**: Production-ready containers with health checks and volume persistence
- **Multi-platform**: Docker images for both amd64 and arm64 architectures

## Quick Start

### Using Docker (Recommended)

Pull and run the latest image from Docker Hub:

```bash
docker run -d \
  --name speedtest-service \
  -e SLEEP_SECONDS=600 \
  -e SPEEDTEST_LOCATION_UUID=your-uuid-here \
  -v speedtest-results:/app/results \
  -v speedtest-logs:/app/logs \
  -v speedtest-uploads:/app/uploads \
  thekhoo/speedsnake:latest
```

Or use docker-compose:

```bash
# Download production compose file
curl -O https://raw.githubusercontent.com/yourusername/speedsnake/main/docker/production/docker-compose.yml

# Set your location UUID
export SPEEDTEST_LOCATION_UUID="your-uuid-here"

# Run
docker-compose up -d
```

### Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/speedsnake.git
cd speedsnake

# Quick start with bootstrap script
./bootstrap.sh  # Sets up venv, installs deps, runs with 10-min intervals

# Or run directly
uv sync
uv run python -m speedtest.handlers.loop
```

## Configuration

Configure the application using environment variables:

| Variable                  | Default            | Description                                                   |
| ------------------------- | ------------------ | ------------------------------------------------------------- |
| `SLEEP_SECONDS`           | `5`                | Interval between speedtests (recommended: 600 for production) |
| `SPEEDTEST_LOCATION_UUID` | `unknown-location` | Location identifier for partitioning (use UUID4)              |
| `RESULT_DIR`              | `./results`        | CSV output directory                                          |
| `UPLOAD_DIR`              | `./uploads`        | Parquet output directory                                      |
| `LOG_DIR`                 | `./logs`           | Log file directory                                            |
| `COMMIT_HASH`             | -                  | Git commit hash for tracking                                  |

## Data Storage

### CSV Files (Temporary)

Raw speedtest results are initially saved as CSV files with Hive partitioning:

```
results/
└── year=2025/
    └── month=01/
        └── day=23/
            ├── speedtest_10-30-45.csv
            ├── speedtest_10-40-45.csv
            └── speedtest_10-50-45.csv
```

### Parquet Files (Permanent)

Complete days (before today) are automatically converted to Parquet format:

```
uploads/
└── location=<UUID>/
    └── year=2025/
        └── month=01/
            ├── day=20/
            │   └── speedtest_001.parquet
            ├── day=21/
            │   └── speedtest_001.parquet
            └── day=22/
                └── speedtest_001.parquet
```

**Conversion process:**

- Runs automatically after each speedtest execution
- Combines all CSV files for a complete day into a single numbered Parquet file
- Adds `speedtest_address` column from `SPEEDTEST_LOCATION_UUID`
- Verifies row count and columns before deleting source CSVs
- Uses incremental numbering (001, 002, etc.) for repeated conversions

### Data Format

**CSV columns** (flattened from JSON):

- Top-level: `download`, `upload`, `ping`, `timestamp`, etc.
- Nested fields joined with underscore: `server_name`, `client_ip`, etc.

**Calculating true speed in Mbps:**

```
Mbps = bandwidth * 8 / 1024 / 1024
```

(bandwidth is in bytes per second)

## Architecture

```
speedtest/
├── handlers/loop.py    # Entry point - polling loop with @loop decorator
├── speedtest.py        # Wrapper around speedtest-cli (subprocess)
├── data/
│   ├── results.py      # CSV persistence with Hive partitioning
│   └── parquet.py      # Parquet conversion and CSV cleanup
├── environment.py      # Environment variable configuration
└── logging.py          # JSON logging with rotating file handler
```

## Development

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (Python package installer)
- Ookla Speedtest CLI (installed automatically via bootstrap.sh)

### Setup

```bash
# Install dependencies
uv sync --group development

# Run tests
uv run pytest

# Lint and format
uv run ruff check speedtest/ tests/
uv run ruff format speedtest/ tests/

# Type checking
uv run pyrefly check
```

### Docker Development

```bash
# Build and run development container
docker-compose -f docker/development/docker-compose.yml up --build

# View logs
docker-compose -f docker/development/docker-compose.yml logs -f

# Stop
docker-compose -f docker/development/docker-compose.yml down
```

### Testing

```bash
uv run pytest                          # Run all tests
uv run pytest tests/test_speedtest.py  # Run specific file
uv run pytest -k "test_name"           # Run tests matching pattern
```

## Docker Deployment

### Production Setup

The production Docker image is automatically built and published to Docker Hub on:

- Push to `main` branch (tagged as `latest`)
- Semantic version tags (e.g., `v1.2.3`)

**Multi-platform support**: Images are built for both `linux/amd64` and `linux/arm64`.

### Docker Files Organization

```
docker/
├── development/
│   ├── Dockerfile              # Fast rebuilds, includes dev deps
│   └── docker-compose.yml      # Local development config
└── production/
    ├── Dockerfile              # Multi-stage build, minimal size
    └── docker-compose.yml      # Production config with volumes
```

### Data Persistence

Production uses named Docker volumes:

- `speedtest-results`: Temporary CSV files
- `speedtest-logs`: JSON logs with rotation
- `speedtest-uploads`: Permanent Parquet files

## Code Style

- **Line length**: 120 characters
- **Linting**: ruff (E, F, I, W rules)
- **Formatting**: ruff format
- **Type checking**: pyrefly
- **Python version**: 3.13

## Contributing

1. Create a new branch for your changes
2. Make incremental commits (one per logical change)
3. Use conventional commits format
4. Run tests and linting before committing
5. Submit a pull request

## License

MIT (?)
