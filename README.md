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
uv run pyrefly check speedtest/ tests/
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

## CI/CD Pipeline

The project uses GitHub Actions for automated deployment to AWS and Docker Hub. The pipeline consists of three main components: infrastructure deployment, testing, and Docker image publishing.

### Architecture Overview

```
GitHub Actions Workflow
├── Lint & Test (Python 3.13, 3.14) - Using reusable composite action
├── Deploy Infrastructure (per universe)
│   ├── Deploy Deployment Role (IAM)
│   └── Deploy Infrastructure (S3)
└── Build & Push Docker Image
```

### Reusable Actions

The project uses composite actions to maintain consistency and reduce duplication:

**`deploy-cloudformation`** (`.github/actions/deploy-cloudformation/`)
- Handles AWS CloudFormation stack deployments
- Features AWS credential configuration via OIDC
- Validates templates before deployment
- Provides deployment summaries with stack outputs

### AWS Infrastructure

The infrastructure is managed using CloudFormation templates in the `infrastructure/` directory:

**1. Deployment Role** (`deployment-role.yml`)
- Creates an IAM role that GitHub Actions assumes to deploy infrastructure
- Grants permissions for CloudFormation stack management and S3 bucket operations
- Role ARN: `arn:aws:iam::020844256789:role/github-actions-<owner>-<repo>-deployment`

**2. Infrastructure Stack** (`template.yml`)
- Deploys an S3 bucket for storing speedtest results
- Bucket naming: `speedsnake-<universe>` (e.g., `speedsnake-production`)
- Features:
  - AES256 encryption at rest
  - Public access blocked
  - HTTPS-only connections enforced
  - 90-day lifecycle policy for `results/` prefix
  - Retention policy enabled (bucket not deleted on stack deletion)

### Universe Support

The pipeline supports multiple deployment environments (universes) using matrix strategy:

- **Current**: `production` only
- **Expandable**: Add `development` or `staging` to the matrix in `.github/workflows/deploy-infrastructure.yml`

Each universe gets:
- Separate CloudFormation stacks: `speedsnake-deployment-role-<universe>`, `speedsnake-infrastructure-<universe>`
- Separate S3 buckets: `speedsnake-<universe>`
- Universe-tagged Docker images: `latest-production`, `v1.2.3-production`

### Workflow Files

- **`ci.yml`**: Runs on pull requests to validate code quality
- **`deploy-infrastructure.yml`**: Runs on push to main, tags, or manual dispatch for deployment

### Workflow Triggers

The pipeline runs automatically on:

| Workflow                  | Trigger                              | Lint/Test | Infrastructure | Docker Build |
| ------------------------- | ------------------------------------ | --------- | -------------- | ------------ |
| `ci.yml`                  | Pull request to `main`               | ✓         | ✗              | ✗            |
| `deploy-infrastructure.yml` | Push to `main` (infra files changed) | ✓         | ✓              | ✓            |
| `deploy-infrastructure.yml` | Push to `main` (other files)         | ✗         | ✗              | ✗            |
| `deploy-infrastructure.yml` | Tag push (`v*.*.*`)                  | ✓         | ✗              | ✓            |
| `deploy-infrastructure.yml` | Manual workflow dispatch             | ✓         | ✓              | ✓            |

**Path filters** (deploy-infrastructure.yml): Infrastructure deployment only runs when these files change:
- `infrastructure/deployment-role.yml`
- `infrastructure/template.yml`
- `.github/workflows/deploy-infrastructure.yml`

**Important**: Code changes that don't touch infrastructure files won't trigger any deployment workflow on push to main. Use tags or manual dispatch for releases without infrastructure changes.

### Pipeline Stages

**1. Quality Gates (Parallel)**
- **Lint** (Python 3.13):
  - ruff check - Linting rules (E, F, I, W)
  - ruff format - Code formatting validation
  - pyrefly - Type checking
- **Test** (Python 3.13 & 3.14):
  - pytest - Unit and integration tests with verbose output
  - Matrix strategy runs tests against multiple Python versions
- **Caching**: uv binary, Python interpreters, and dependencies are cached for faster runs (70-90% speed improvement)

**2. Infrastructure Deployment (Sequential, per universe)**
- **Deploy Deployment Role**: Only runs when `deployment-role.yml` changes
- **Deploy Infrastructure**: Only runs when `template.yml` or workflow changes
- **Universe Matrix**: Currently deploys to `production` only, easily expandable to `development`, `staging`
- Requires: All quality gates passing

**3. Docker Build (After infrastructure)**
- Builds production Docker image (multi-stage, non-root user)
- Multi-platform: `linux/amd64` and `linux/arm64`
- Pushes to Docker Hub: `thekhoo/speedsnake`
- Universe-aware tagging (e.g., `latest-production`, `v1.2.3-production`)
- Requires: Quality gates passing, infrastructure deployed/skipped

### Docker Image Tags

Images are tagged based on the trigger type and universe:

| Git Event                  | Docker Tags                                                                     |
| -------------------------- | ------------------------------------------------------------------------------- |
| Push to `main`             | `latest-production`, `main-abc123-production` (git sha)                         |
| Tag `v1.2.3`               | `1.2.3-production`, `1.2-production`, `1-production`, `main-abc123-production` |
| Manual dispatch from `main` | `latest-production`, `main-abc123-production`                                   |

### Required GitHub Secrets

Configure these in your repository settings:

- `DOCKERHUB_USERNAME`: Docker Hub username
- `DOCKERHUB_TOKEN`: Docker Hub access token (not password)

**AWS credentials** are handled via OIDC role assumption (no long-lived credentials required).

### AWS Permissions

The deployment role has permissions to:
- Manage CloudFormation stacks with names matching `speedsnake-*`
- Create and manage S3 buckets with names matching `speedsnake*`
- No permissions for EC2, Lambda, or other services (principle of least privilege)

### Manual Deployment

To manually trigger a deployment:

1. Go to Actions tab in GitHub
2. Select "Deploy Infrastructure" workflow
3. Click "Run workflow"
4. Select branch (usually `main`)
5. Click "Run workflow"

This will deploy infrastructure for all universes in the matrix and build Docker images.

### Expanding to Multiple Universes

To add a new universe (e.g., `development`):

1. Update the matrix in `.github/workflows/deploy-infrastructure.yml` (appears twice - once for `deploy-deployment-role`, once for `deploy-infrastructure`):
   ```yaml
   strategy:
     matrix:
       universe: [production, development]
   ```

2. Push to `main` or manually trigger the workflow

3. The pipeline will automatically:
   - Deploy `speedsnake-deployment-role-development`
   - Deploy `speedsnake-infrastructure-development`
   - Create S3 bucket `speedsnake-development`
   - Tag Docker images with `-development` suffix

**Note**: Quality checks (lint/test) run once per workflow execution, not per universe, since they validate code quality, not environment-specific configurations.

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

## GitHub Actions Naming Conventions

All GitHub Actions (composite actions and workflows) follow standardized naming conventions:

### Input Field Names
- **Always use hyphens** instead of underscores for input field names
- **Format**: `kebab-case` (lowercase with hyphens)
- **Examples**:
  - ✅ `template-paths`, `python-version`, `deployment-role-arn`
  - ❌ `template_paths`, `python_version`, `deployment_role_arn`

### Rationale
- Consistent with GitHub Actions ecosystem conventions
- Easier to read and distinguish from variable names
- Follows YAML/Kubernetes naming patterns
- Improves maintainability across workflows and composite actions

### Composite Actions
When creating new composite actions in `.github/actions/`:
1. Define all inputs with hyphenated names
2. Reference inputs using hyphenated syntax: `${{ inputs.my-input-name }}`
3. Document input names clearly in the action's `description` field

### Workflow Files
When calling actions from workflows:
1. Use hyphenated input names in the `with:` block
2. Keep action invocations consistent across all workflow files

**Example**:
```yaml
- name: Validate templates
  uses: thekhoo/github-actions-shared/.github/actions/validate-cloudformation@main
  with:
    template-paths: infrastructure/deployment-role.yml
    validation-role-arn: ${{ env.VALIDATION_ROLE_ARN }}
    aws-region: ${{ env.AWS_REGION }}
```

## Contributing

1. Create a new branch for your changes
2. Make incremental commits (one per logical change)
3. Use conventional commits format
4. Run all quality checks before committing:
   ```bash
   uv run ruff check speedtest/ tests/
   uv run ruff format speedtest/ tests/
   uv run pyrefly check speedtest/ tests/
   uv run pytest -v
   ```
5. Submit a pull request

Pull requests automatically run the full CI pipeline including linting, type checking, and tests across Python 3.13 and 3.14.

## License

MIT (?)
