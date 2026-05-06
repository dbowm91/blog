# Test Suite (`tests/`)

Comprehensive testing infrastructure.

## Test Structure

```
tests/
├── conftest.py           # Pytest fixtures
├── unit/                 # Unit tests
├── integration/          # Integration tests
└── e2e/                  # End-to-end Playwright tests
```

## Test Types

| Type | Location | Tool |
|------|----------|------|
| Unit | `tests/unit/` | pytest |
| Integration | `tests/integration/` | pytest |
| E2E | `tests/e2e/` | Playwright |

## Fixtures (`conftest.py`)

Key fixtures:
- `app` - Flask application
- `client` - Test client
- `db` - Database session
- `authenticated_admin` - Logged-in admin user

## Key Configuration

From `pytest.ini`:
```ini
[pytest]
testpaths = tests
addopts = --cov=app --cov-report=html --cov-report=term-missing
```

Minimum coverage: 80%

## Running Tests

```bash
# All tests
pytest

# Specific type
pytest tests/unit/
pytest tests/integration/
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
