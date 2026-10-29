# Test Suite (`tests/`)

Comprehensive testing infrastructure.

## Test Structure

```
tests/
├── benchmarks/          # Benchmark tests
│   ├── conftest.py      # Benchmark fixtures (session-scoped `app`, `db`)
│   ├── test_benchmarks.py
│   └── test_theme_performance.py  # Theme performance benchmarks (Phase 13)
├── conftest.py          # Pytest fixtures (session-scoped `app`, `ensure_buffer_disabled` autouse)
├── e2e/                 # End-to-end Playwright tests
│   ├── conftest.py      # E2E fixtures (session-scoped `app`, `app_server`, `browser_type_launch_args`)
│   └── test_e2e.py      # E2E tests with classes: TestAdminLogin, TestPostCreation, TestNewsletterSubscription, TestMobileResponsiveness
├── shared_fixtures.py   # Shared fixtures (`ensure_buffer_disabled` autouse)
├── themes/              # Theme-specific tests
│   ├── test_reliability.py  # Theme reliability and resilience tests (Phase 13)
│   └── ...
├── test_*.py            # Unit/integration tests (flat structure, NOT in unit/ or integration/ subdirs)
└── __init__.py
```

## Test Types

| Type | Location | Tool |
|------|----------|------|
| Unit/Integration | `tests/` (flat) | pytest |
| Benchmark | `tests/benchmarks/` | pytest |
| E2E | `tests/e2e/` | Playwright (via `pytest-playwright`) |

## Fixtures (`conftest.py`)

### Fixture Locations

| Fixture | Location | Scope |
|---------|----------|-------|
| `app` | `conftest.py`, `benchmarks/conftest.py`, `e2e/conftest.py` | session |
| `db` | `conftest.py` (function), `benchmarks/conftest.py` (session) | varies |
| `client` | `conftest.py` | function |
| `admin_user` | `conftest.py`, `benchmarks/conftest.py` | function |
| `authenticated_client` | `conftest.py`, `benchmarks/conftest.py` | function |
| `sample_post`, `sample_tag`, `sample_subscriber` | `conftest.py` | function |
| `mock_render`, `mock_smtp` | `conftest.py` | function |
| `clean_analytics_cache` | `shared_fixtures.py` (imported via `*` into conftest files) | function |
| `cleanup_uploads` | `conftest.py` | session (autouse) |
| `ensure_buffer_disabled` | `shared_fixtures.py` (imported via `*` into other conftest files) | autouse |
| `browser_type_launch_args` | `e2e/conftest.py` | session |
| `app_url` | `e2e/conftest.py` | session |
| `app_server` | `e2e/conftest.py` | session |

### Key Fixtures

- `app` - Flask application (session-scoped)
- `client` - Test client
- `db` - Database session (function-scoped in main conftest, session-scoped in benchmarks)
- `admin_user` and `authenticated_client` - Logged-in admin user
- `sample_post` - Creates a published `Post` with title "Test Post", slug "test-post", and sample body/summary
- `sample_tag` - Creates a `Tag` with name "Python" and slug "python"
- `sample_subscriber` - Creates a confirmed `Subscriber` with email "test@example.com"
- `mock_render` - Patches `app.email.render_template` to return `"<html>Mock</html>"`
- `mock_smtp` - Patches `app.email._connect_smtp` with a `MagicMock` server (has `sendmail`, `quit`)
- `clean_analytics_cache` - Clears the analytics memoization cache via `_clear_analytics_cache()` in `app/routes/admin/helpers/analytics.py` before and after tests
- `cleanup_uploads` - Session-scoped autouse; removes files from `app/static/uploads/` after session ends
- `ensure_buffer_disabled` - Autouse fixture (from `shared_fixtures.py`) that sets `PAGE_VIEW_BUFFER_SIZE=0` and calls `shutdown_page_view_buffer()` before/after each test

### FakeSubscriber

`FakeSubscriber` is a dataclass (`tests/conftest.py:60-69`) for newsletter testing without real subscriber database records:

```python
@dataclass
class FakeSubscriber:
    email: str
    token: str = "test"
    confirmed: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    unsubscribed_at: datetime | None = None
```

Used to test newsletter rendering and email logic without creating actual `Subscriber` model instances.

### Benchmark-Only Fixtures

- `clean_db` - Cleans up test data after each benchmark function, keeping user records
- `create_posts_bulk(db, count=50)` - Helper to create multiple posts for benchmarking
- `create_subscribers_bulk(db, count=100)` - Helper to create multiple subscribers for benchmarking

### E2E-Only Fixtures

- `app` - Session-scoped fixture defined in `e2e/conftest.py`; creates a separate database (`blog_e2e`) and disables CSRF. `E2E_DATABASE_URI` replaces that database with one owned by another process, which is how CI shares one database with the container it browses. This fixture **shadows** the main `conftest.py` `app` fixture for E2E tests.
- `app_url` - Base URL for the Flask application (`http://127.0.0.1:5010`)
- `browser_type_launch_args` - Configured browser launch arguments (`--no-sandbox`, `--disable-setuid-sandbox`)
- `app_server` - Session-scoped fixture that starts the Flask server on port 5010 and seeds the administrator (created when missing, updated when the database already has one)
- `page` - Provided by `pytest-playwright` (not defined in project conftest); standard Playwright page fixture for browser interaction

## Key Configuration

From `pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=app --cov-report=term-missing"
```

Coverage settings in `pyproject.toml`:
```toml
[tool.coverage.report]
fail_under = 75
```

Additional markers are defined in `pytest.ini`:
```ini
[pytest]
markers =
    e2e: end-to-end browser tests
```

A `slow` marker is registered in `conftest.py` via `pytest_configure`:
```python
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
```

Skip slow tests with: `pytest -m "not slow"`

## Running Tests

### Setup

E2E tests require `pytest-playwright`, which **is** in `requirements.txt` (lines 18-19):
```bash
pip install -r requirements.txt
playwright install chromium
```

The E2E conftest uses the `page` fixture from `pytest-playwright` (not defined in project code). CI runs E2E tests on port 5010.

### Commands

```bash
# All tests (requires environment variables)
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python3 -m pytest

# Exclude E2E tests
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python3 -m pytest --ignore=tests/e2e

# List test count without running
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python3 -m pytest --collect-only

# Specific type
pytest tests/
pytest tests/benchmarks/
pytest tests/e2e/

# With coverage
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python3 -m pytest --cov=app
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

## Celery Test Configuration

Celery is configured to run tasks eagerly (synchronously) during tests in `conftest.py`:

```python
from celery import current_app as celery_app

celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
)
```

This ensures all Celery tasks (newsletter, webhooks, email) execute inline during tests rather than being dispatched to a broker.

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

The E2E tests in `tests/e2e/conftest.py` define their **own** session-scoped `app` fixture that creates a separate database (`blog_e2e`). This fixture **shadows** the main `tests/conftest.py` `app` fixture for E2E tests. Running `pytest tests/e2e/` alone works because the E2E conftest provides its own `app` fixture. The `E2E_DATABASE_URI` env var replaces that database with one owned by another process; CI uses it so the suite and the container read and write the same SQLite file.

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
- [E2E Testing Skill](../../.skills/e2e_testing/skill.md) - Running the Playwright suite, its fixtures and its rules
- [Release Validation Skill](../../.skills/release_validation/skill.md) - The full pre-release gate and the known failure baseline

## CI and Benchmark Policy

### Correctness vs. Performance

Correctness tests (unit, integration, theme reliability) are **mandatory** and must pass on every commit. Performance benchmarks use generous thresholds designed to tolerate normal CI variance while catching order-of-magnitude regressions.

### Benchmark Threshold Design

Theme performance benchmarks in `tests/benchmarks/test_theme_performance.py` use thresholds calibrated for typical CI hardware:

| Benchmark | Threshold | Rationale |
|-----------|-----------|-----------|
| Cold registry (bundled) | < 0.5s | Includes 5 iterations averaged |
| Cold registry (50 external) | < 1.0s | 3 iterations averaged |
| Bundled catalog enumeration | < 0.1s | 20 iterations averaged |
| Warm list_themes() | < 0.01s | 100 iterations averaged, O(1) expected |
| Cold parse/translate/serialize | < 0.25s | Single theme, 5 iterations averaged |
| Warm theme load | < 0.01s | 200 iterations averaged, O(1) expected |
| Warm get_context() | < 0.01s | 50 iterations averaged, O(1) expected |
| Context after invalidation | < 0.5s | 10 iterations averaged |
| Template render | < 0.005s | 200 iterations averaged |
| Full registry invalidation | < 0.5s | 10 iterations averaged |
| Single theme invalidation | < 0.15s | 20 iterations averaged |
| E2E pipeline (10 themes) | < 2.0s | Scan + load all |

### Interpreting Failures

- **Threshold exceeded by < 2x**: Likely CI variance. Re-run the test. If it passes on retry, the threshold may need adjustment.
- **Threshold exceeded by > 5x**: Investigate for real regression. Check if a new dependency or code path was introduced.
- **Consistent failure across runs**: Indicates a real performance regression. Profile and optimize before merging.

### Adding New Benchmarks

When adding new benchmarks:

1. Set thresholds generously (at least 2x the measured typical time on CI hardware).
2. Use multiple iterations with `time.perf_counter()` averaging for stable measurements.
3. Focus on end-to-end operations, not microbenchmarks of individual lines.
4. Benchmark correctness tests must also pass (the benchmark file includes assertions about output validity).

### Diagnostic Counters

The `ThemeRegistry` and `ThemeCache` classes expose diagnostic counters via read-only properties:

| Counter | Property | Description |
|---------|----------|-------------|
| Cache hits | `registry.cache_hits` | Number of cache lookups that returned a valid entry |
| Cache misses | `registry.cache_misses` | Number of cache lookups that returned None |
| Refresh count | `registry.refresh_count` | Number of successful catalog rebuilds |
| Refresh failures | `registry.refresh_failure_count` | Number of failed catalog rebuilds |
| Fallback count | `registry.fallback_count` | Number of emergency fallback activations |
| External overrides | `registry.external_override_count` | Number of external themes overriding bundled themes |

These counters are reset via `registry.reset_refresh_counters()` and `registry._cache.reset_counters()`. They are intended for diagnostics and testing, not for production metrics export.
