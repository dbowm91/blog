# CI/CD (`.github/workflows/`)

GitHub Actions workflows for testing and deployment.

## Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | push, pull_request, schedule | Full test suite |

## ci.yml Jobs

### 1. lint-and-type
- **Tool**: `ruff` (linting), `mypy` (type checking)
- **Python**: 3.12

### 2. test
- **Tool**: `pytest` with coverage
- **Coverage**: Minimum 80%
- **Python**: 3.12, 3.13
- **Database**: SQLite

### 3. security-audit
- **Tool**: `pip-audit`
- **Purpose**: Vulnerability scanning
- **Mode**: `--fail-on=all` (strict mode — fails on any known vulnerability, including informational)

### 4. frontend-build
- **Tool**: Node.js 20, `npm ci` + `npm run build`
- **Purpose**: Build frontend assets

### 5. docker-build
- **Tool**: `docker build .`
- **Purpose**: Verify Dockerfile builds successfully and the resulting image is functional
- **Smoke test steps**:
  1. Builds image with tag `devlog:ci-smoke`
  2. Verifies `app/static/dist/.vite/manifest.json` exists in the image (confirms frontend builder stage produced assets)
  3. Starts container with test env vars (`SECRET_KEY`, `ADMIN_PASSWORD`, `SESSION_COOKIE_SECURE=false`)
  4. Polls the `/health` endpoint for up to 60 seconds (30 iterations × 2s sleep)
  5. Cleans up the container on completion (always runs, even on failure)

This job validates the full multi-stage build pipeline: Node.js frontend build → Python dependency install → runtime image assembly.

### 6. e2e-tests
- **Tool**: Playwright
- **Environment**: Docker-based with `--profile production`
- **Browser**: Chromium
- **Compose files**: `docker-compose.yml` + `docker-compose.ci.yml` (CI override publishes port 5000)
- **Base URL**: Configured via `E2E_BASE_URL` env var (default: `http://localhost:5000` in CI)
- **Depends on**: `test`, `docker-build`
- **Failure diagnostics**: Dumps logs for blog, redis, celery services

### Job Dependency Chain

```
lint-and-type ──> test ──> e2e-tests
frontend-build
security-audit
docker-build ──> e2e-tests
```

- `lint-and-type` must pass before `test` runs
- `test` must pass before `e2e-tests` runs
- `docker-build` must pass before `e2e-tests` runs (E2E needs the Docker image)
- `frontend-build`, `security-audit`, and `docker-build` run in parallel with each other

### Schedule

The CI workflow runs on a weekly schedule (Monday 08:00 UTC) in addition to push/PR triggers.

## Test Configuration

From `pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=app --cov-report=term-missing"

[tool.coverage.report]
fail_under = 80
```

Additional markers are defined in `pytest.ini`:
```ini
[pytest]
markers =
    e2e: end-to-end browser tests
```

Minimum coverage: 80%

### Running Tests Locally

```bash
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python3 -m pytest tests/ --ignore=tests/e2e -v --cov=app --cov-fail-under=80
```

Required environment variables:
- `ADMIN_PASSWORD` - Set to any value for admin tests
- `SECRET_KEY` - Set to any value for session/CSRF tests

## See Also
- [Docker](docker.md) - Docker setup
- [Testing](../testing/test-suite.md) - Test infrastructure
- [Release Validation Skill](../../.skills/release_validation/skill.md) - The local equivalent of the CI gate, and how to diagnose a failing stage
