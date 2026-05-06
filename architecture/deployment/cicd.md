# CI/CD (`.github/workflows/`)

GitHub Actions workflows for testing and deployment.

## Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `test.yml` | push, pull_request | Full test suite |

## test.yml Jobs

### 1. lint-and-type
- **Tool**: `ruff` (linting), `mypy` (type checking)
- **Python**: 3.12, 3.13

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
- **Environment**: Docker-based
- **Browser**: Chromium

## Test Configuration

From `pytest.ini`:
- Test discovery: `tests/`
- Coverage HTML: `htmlcov/`
- Minimum coverage: 80%

## See Also
- [Docker](deployment/docker.md) - Docker setup
- [Testing](../testing/test-suite.md) - Test infrastructure
