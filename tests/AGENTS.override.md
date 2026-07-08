# Tests Agent Override

Specialized handling for testing patterns, fixtures, and E2E testing.

## Running Tests

Use the project's `.venv` Python to avoid fixture errors:
```bash
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python3 -m pytest tests/ -v
```

To run without E2E tests:
```bash
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python3 -m pytest tests/ --ignore=tests/e2e
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

## Test Count

Tests are organized across ~39 test files covering models, routes, API, search, security, and more. Run `ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python3 -m pytest tests/ --collect-only` to get current count.

## Test Structure

```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── test_models.py          # User, Post, Tag, Subscriber models (test_ at line 6)
├── test_2fa.py              # TOTP setup/verify, 2FA login (test_ at line 10)
├── test_search.py          # FTS5 search, snippets (test_ at line 51)
├── test_webhooks.py        # Webhook signing, delivery (test_ at line 14)
├── test_tasks.py            # Celery tasks: newsletter, webhooks, email (test_ at line 8)
├── test_scheduler.py       # APScheduler jobs, health checks (test_ at line 8)
├── test_newsletter.py       # Newsletter scheduling, attempts (test_ at line 9)
├── test_comments_admin.py   # Comment moderation (test_ at line 6)
├── test_coverage.py         # 404/500 handlers, feeds, bulk ops, search (test_ at line 9)
├── test_cli.py              # CLI commands (test_ at line 24)
├── test_*.py                # Other unit tests (admin, api, public, etc.)
├── shared_fixtures.py       # Shared fixtures (ensure_buffer_disabled here)
├── benchmarks/              # Benchmark tests
│   └── conftest.py          # Benchmark fixtures (clean_db fixture here)
└── e2e/                     # Playwright E2E tests
    └── test_e2e.py          # Contains TestAdminLogin, TestPostCreation, TestNewsletterSubscription, TestMobileResponsiveness
```

Note: There are ~39 test files total. Run `ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python3 -m pytest tests/ --collect-only` to get exact count.

## Key Fixtures

- `app` - Flask application instance
- `client` - Flask test client
- `db` - Database fixture
- `admin_user` - Admin user fixture
- `sample_post`, `sample_tag`, `sample_subscriber` - From conftest.py
- `clean_analytics_cache` - From shared_fixtures.py:17-24
- `clean_db` - From benchmarks/conftest.py:52
- `api_client` - From conftest.py:120-130 (functionally identical to authenticated_client)
- `mock_email` - From conftest.py:188-194 (combines mock_render + mock_smtp)

## Page View Buffer in Tests

The page view buffer is disabled in all tests via the shared `ensure_buffer_disabled` autouse fixture defined in `tests/shared_fixtures.py`.

Only `tests/e2e/conftest.py` and `tests/benchmarks/conftest.py` import from shared_fixtures. The `tests/test_api.py` does NOT import from shared_fixtures.

Do NOT re-enable the buffer in tests as it causes interference with other tests.

## SQLAlchemy 2.0 Query Patterns in Tests

```python
db.session.execute(select(Model).filter(...)).scalar_one_or_none()  # single result
db.session.execute(select(Model).filter_by(...)).scalars().all()    # multiple results
db.session.execute(select(func.count(...))).scalar_one()           # counts
db.paginate(select(...), page=..., per_page=..., error_out=False)    # pagination
```