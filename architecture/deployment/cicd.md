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
- **Purpose**: Verify Dockerfile builds successfully

### 6. e2e-tests
- **Tool**: Playwright
- **Environment**: Docker-based with `--profile production`
- **Browser**: Chromium
- **Setup**: Uses `docker compose wait blog` to ensure the blog service is ready before running tests

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
