# Test Suite (`tests/`)

Comprehensive testing infrastructure.

## Test Structure

```
tests/
├── benchmarks/          # Benchmark tests
│   ├── conftest.py      # Benchmark fixtures (session-scoped `app`, `db`)
│   └── test_benchmarks.py
├── conftest.py          # Pytest fixtures (session-scoped `app`, `ensure_buffer_disabled` autouse)
├── e2e/                 # End-to-end Playwright tests
│   ├── conftest.py      # E2E fixtures (Playwright setup, app server on port 5010)
│   └── test_e2e.py      # E2E tests with classes: TestAdminLogin, TestPostCreation, TestNewsletterSubscription, TestMobileResponsiveness
├── shared_fixtures.py   # Shared fixtures (`ensure_buffer_disabled` autouse)
├── test_*.py            # Unit/integration tests (flat structure, NOT in unit/ or integration/ subdirs)
└── __init__.py
```

## Test Types

| Type | Location | Tool |
|------|----------|------|
| Unit/Integration | `tests/` (flat) | pytest |
| Benchmark | `tests/benchmarks/` | pytest |
| E2E | `tests/e2e/` | Playwright |

## Fixtures (`conftest.py`)

### Fixture Locations

| Fixture | Location | Scope |
|---------|----------|-------|
| `app` | `conftest.py`, `benchmarks/conftest.py` | session |
| `db` | `conftest.py` (function), `benchmarks/conftest.py` (session) | varies |
| `client` | `conftest.py` | function |
| `admin_user` | `conftest.py`, `benchmarks/conftest.py` | function |
| `authenticated_client` | `conftest.py`, `benchmarks/conftest.py` | function |
| `sample_post`, `sample_tag`, `sample_subscriber` | `conftest.py` | function |
| `mock_render`, `mock_smtp`, `mock_email` | `conftest.py` | function |
| `clean_analytics_cache` | `conftest.py`, `benchmarks/conftest.py` | function |
| `cleanup_uploads` | `conftest.py` | session (autouse) |
| `ensure_buffer_disabled` | `conftest.py`, `benchmarks/conftest.py`, `e2e/conftest.py`, `shared_fixtures.py` | autouse |
| `browser_type_launch_args` | `e2e/conftest.py` | session |
| `app_server` | `e2e/conftest.py` | session |

### Key Fixtures

- `app` - Flask application (session-scoped)
- `client` - Test client
- `db` - Database session
- `admin_user` and `authenticated_client` - Logged-in admin user
- `sample_post`, `sample_tag`, `sample_subscriber` - Sample data fixtures
- `mock_render`, `mock_smtp`, `mock_email` - Mock fixtures for external services
- `clean_analytics_cache` - Cleans analytics cache before tests
- `cleanup_uploads` - Session-scoped cleanup of uploaded files

## Key Configuration

From `pytest.ini`:
```ini
[pytest]
testpaths = tests
addopts = --cov=app --cov-report=term-missing
```

Minimum coverage: 80%

## Running Tests

### Setup

E2E tests require Playwright:
```bash
npm install -D @playwright/test
npx playwright install chromium
```

The E2E tests start the Flask server on port 5010.

### Commands

```bash
# All tests (requires environment variables)
ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest

# Specific type
pytest tests/
pytest tests/benchmarks/
pytest tests/e2e/

# With coverage
ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest --cov=app
```

### Environment Variables

Required for all tests:
- `SECRET_KEY` - Flask session key (minimum 32 characters)
- `ADMIN_PASSWORD` - Admin password for test user

Optional:
- `TESTING=True` - Enables test mode
- `PAGE_VIEW_BUFFER_SIZE=0` - Disables page view buffer at environment level

## Page View Buffer

The page view buffer (`app/page_view_buffer.py`) can cause test interference:
- Disable via `app.config.PAGE_VIEW_BUFFER_SIZE = 0`
- Call `shutdown_page_view_buffer()` in tests
- The `ensure_buffer_disabled` fixture (autouse) handles this automatically

## Database Session Considerations

### `db.session.refresh()` Limitation

`db.session.refresh()` fails if the object is not in the current session. If you need an up-to-date version of an object after a commit, re-query it from the database instead:

```python
# Wrong - may fail
db.session.refresh(post)

# Correct - always works
post = db.session.get(Post, post.id)
```

### E2E Test `app` Fixture

The E2E tests in `tests/e2e/conftest.py` define their own session-scoped `app` fixture which:
- Creates a temporary database
- Initializes FTS search
- Creates an admin user
- Starts the Flask server on port 5010
- Has function-scoped buffer shutdown via `ensure_buffer_disabled`

## SQLAlchemy 2.0 Query Patterns

Modern SQLAlchemy 2.0 patterns are used throughout the tests:

```python
# Modern select pattern
from sqlalchemy import select
result = db.session.execute(select(Post).filter(Post.published == True))

# Pagination with db.paginate
posts = db.paginate(query, per_page=10)

# Fetching related objects
post = db.session.get(Post, post_id)
```

## See Also
- [CI/CD](../deployment/cicd.md) - CI test execution
