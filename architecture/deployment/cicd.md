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
- **Setup**: Uses `docker compose wait redis` to ensure Redis is ready before running tests

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
ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/ --ignore=tests/e2e -v --cov=app --cov-fail-under=80
```

Required environment variables:
- `ADMIN_PASSWORD` - Set to any value for admin tests
- `SECRET_KEY` - Set to any value for session/CSRF tests

## See Also
- [Docker](deployment/docker.md) - Docker setup
- [Testing](../testing/test-suite.md) - Test infrastructure
