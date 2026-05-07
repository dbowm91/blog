# Test Suite (`tests/`)

Comprehensive testing infrastructure.

## Test Structure

```
tests/
├── benchmarks/          # Benchmark tests
├── conftest.py           # Pytest fixtures
├── e2e/                  # End-to-end Playwright tests
├── test_*.py             # Unit/integration tests (flat)
└── __init__.py
```

## Test Types

| Type | Location | Tool |
|------|----------|------|
| Unit/Integration | `tests/` (flat) | pytest |
| Benchmark | `tests/benchmarks/` | pytest |
| E2E | `tests/e2e/` | Playwright |

## Fixtures (`conftest.py`)

Key fixtures:
- `app` - Flask application
- `client` - Test client
- `db` - Database session
- `admin_user` and `authenticated_client` - Logged-in admin user

## Key Configuration

From `pytest.ini`:
```ini
[pytest]
testpaths = tests
addopts = --cov=app --cov-report=term-missing
```

Minimum coverage: 80%

## Running Tests

```bash
# All tests
pytest

# Specific type
pytest tests/
pytest tests/benchmarks/
pytest tests/e2e/

# With coverage
pytest --cov=app
```

## Page View Buffer

The page view buffer (`app/page_view_buffer.py`) can cause test interference:
- Disable via `app.config.PAGE_VIEW_BUFFER_SIZE = 0`
- Call `shutdown_page_view_buffer()` in tests

## See Also
- [CI/CD](../deployment/cicd.md) - CI test execution
