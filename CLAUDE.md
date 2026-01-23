# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Internet Speed Check is a Python application that periodically runs Ookla Speedtest CLI, collects results, and stores them as JSON files for monitoring internet connection speed over time.

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
├── data/results.py     # JSON file persistence (read/append to daily files)
└── environment.py      # Environment variable configuration
```

### Data Flow
1. `handlers/loop.py` runs infinitely, calling `speedtest.run()` at configured intervals
2. `speedtest.py` executes `speedtest-cli --secure --json --bytes` via subprocess
3. Results are appended to `{DATE}_speedtest.json` files in the results directory

### Configuration (Environment Variables)
- `SLEEP_SECONDS`: Interval between tests (default: 5 seconds; bootstrap uses 600)
- `RESULT_DIR`: Output directory (default: `./results`)
- `COMMIT_HASH`: Git commit tracking

### Bandwidth Conversion
True speed in Mbps = `bandwidth * 8 / 1024 / 1024` (bandwidth is bytes/sec)

## Code Style
- Line length: 120 (ruff)
- Linting: ruff (E, F, I, W rules)
- Formatting: ruff format
- Type checking: pyrefly
- Python version: 3.13
