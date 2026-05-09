# Tests Agent Override

Specialized handling for testing patterns, fixtures, and E2E testing.

## Running Tests

Use the project's `.venv` Python to avoid fixture errors:
```bash
ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/ -v
```

To run without E2E tests:
```bash
ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/ --ignore=tests/e2e
```

## E2E Tests

Require `pytest-playwright` and Chromium browser installed in `.venv`:
```bash
.venv/bin/pip install pytest-playwright
.venv/bin/playwright install chromium
```

## Required Environment Variables

Both `ADMIN_PASSWORD` and `SECRET_KEY` are **required**—the app raises `RuntimeError` when `create_app()` is called without them.

## Test Configuration

Tests disable CSRF via `CSRF_ENABLED=False` + `TESTING=True` in config.

## Test Counts

- 524 tests pass (514 unit + 10 E2E)
- New tests added for: password reset flow, settings routes, pages routes, content hashing

## Test Structure

```
tests/
├── conftest.py          # Pytest fixtures and configuration
├── test_models.py       # Model unit tests
├── test_public.py       # Public routes tests
├── test_admin.py        # Admin routes tests
├── test_api.py          # REST API tests (has its own app fixture with buffer protection)
├── test_rss.py          # RSS/Atom feed tests
├── test_search.py       # FTS5 search tests
├── test_utils.py        # Utility function tests
├── test_cli.py          # CLI command tests
├── benchmarks/          # Benchmark tests (has buffer protection)
└── e2e/                 # Playwright E2E tests (has buffer protection)
    ├── test_home.py
    ├── test_post.py
    └── test_admin.py
```

## Key Fixtures

- `app` - Flask application instance
- `client` - Flask test client
- `db` - Database fixture
- `admin_user` - Admin user fixture
- `regular_user` - Regular user fixture
- `post` - Sample post fixture

## Page View Buffer in Tests

The page view buffer is disabled in all tests via the shared `ensure_buffer_disabled` autouse fixture defined in `tests/shared_fixtures.py`.

All test conftest files (`tests/conftest.py`, `tests/e2e/conftest.py`, `tests/benchmarks/conftest.py`) and `tests/test_api.py` import this fixture via `from tests.shared_fixtures import *`.

Do NOT re-enable the buffer in tests as it causes interference with other tests.

## SQLAlchemy 2.0 Query Patterns in Tests

```python
db.session.execute(select(Model).filter(...)).scalar_one_or_none()  # single result
db.session.execute(select(Model).filter_by(...)).scalars().all()    # multiple results
db.session.execute(select(func.count(...))).scalar_one()           # counts
db.paginate(select(...), page=..., per_page=..., error_out=False)    # pagination
```