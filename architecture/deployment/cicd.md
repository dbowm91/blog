# CI/CD (`.github/workflows/`)

GitHub Actions workflows for testing and deployment.

## Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `test.yml` | push, pull_request | Full test suite |

## test.yml Jobs

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

### 4. e2e-tests
- **Tool**: Playwright
- **Environment**: Docker-based with `--profile production`
- **Browser**: Chromium
- **Setup**: Uses `docker-compose wait redis` to ensure Redis is ready before running tests

## Test Configuration

From `pytest.ini`:
- Test discovery: `tests/`
- Coverage HTML: `htmlcov/`
- Minimum coverage: 80%

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
