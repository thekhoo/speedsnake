# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Internet Speed Check is a Python application that periodically runs Ookla Speedtest CLI, collects results, and stores them as CSV files in Hive partition format for monitoring internet connection speed over time.

## Commands

### Run locally

```bash
./bootstrap.sh  # Sets up venv, installs deps, runs with 10-min intervals
```

### Run with Docker

```bash
docker-compose up
```

### Run directly

```bash
uv run python -m speedtest.handlers.loop
```

### Testing

```bash
uv run pytest                     # run all tests
uv run pytest tests/test_speedtest.py  # run specific file
uv run pytest -k "test_name"      # run tests matching pattern
```

### Linting, formatting, and type checking

```bash
uv run ruff check speedtest/ tests/      # lint
uv run ruff format speedtest/ tests/     # format
uv run pyrefly check                     # type check
```

### Install dependencies

```bash
uv sync                    # production deps
uv sync --group development  # with dev deps
```

## Architecture

```
speedtest/
├── handlers/loop.py    # Entry point - polling loop with @loop decorator
├── speedtest.py        # Wrapper around speedtest-cli binary (subprocess)
├── data/results.py     # CSV file persistence with Hive partitioning
├── environment.py      # Environment variable configuration
└── logging.py          # JSON logging with rotating file handler
```

### Data Flow

1. `handlers/loop.py` runs infinitely, calling `speedtest.run()` at configured intervals
2. `speedtest.py` executes `speedtest-cli --secure --json --bytes` via subprocess
3. Results are written as CSV files in Hive partition format: `results/year=YYYY/month=MM/day=DD/speedtest_HH-MM-SS.csv`

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

### Configuration (Environment Variables)

- `SLEEP_SECONDS`: Interval between tests (default: 5 seconds; bootstrap uses 600)
- `RESULT_DIR`: Output directory (default: `./results`)
- `LOG_DIR`: Log output directory (default: `./logs`)
- `COMMIT_HASH`: Git commit tracking

### Logging

- JSON formatted logs written to `logs/speedtest.log`
- Rotating file handler: 5MB max per file, keeps 10 backup files (`.log.1`, `.log.2`, etc.)

## Code Style

- Line length: 120 (ruff)
- Linting: ruff (E, F, I, W rules)
- Formatting: ruff format
- Type checking: pyrefly
- Python version: 3.13

## Claude Instructions

- Ask clarifying questions in requirements are ambiguous
- Explain _why_ changes are suggested

## Coding Preferences

- Prefer small, composable functions where possible
- Write code that is easy to test

## Merge Behaviours

- Always create a new branch that's up to date with main and give it a suitable name
- Create a PR that goes into main
- Fill the description explaining the changes that have been made
- Add comments to section that serve as points of interest on the PR

## Agents and Planning

- Scope the work that needs to be done and form a dependency tree.
- If there are multiple tasks in the dependency tree that can be handled in parallel, spawn agents to complete them

## Out of Scope

- Do not introduce new frameworks without asking
- If there is a package/framework that could reduce the amount of code needed, suggest it
- Do not optimize prematurely
