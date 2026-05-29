# Testing Module Architecture Review

**Reviewed:** May 29, 2026
**Architecture Docs:** test-suite.md
**Source Files:** tests/, pytest.ini, tests/conftest.py, tests/shared_fixtures.py

## Findings

### Verified Claims (Correct)

- Directory structure in `test-suite.md:7-18` matches actual test files
- E2E test classes `TestAdminLogin`, `TestPostCreation`, `TestNewsletterSubscription`, `TestMobileResponsiveness` exist in `tests/e2e/test_e2e.py`
- `app` fixture is session-scoped in both `tests/conftest.py:25` and `tests/benchmarks/conftest.py:19`
- `db` fixture is function-scoped in `tests/conftest.py:72`, session-scoped in `tests/benchmarks/conftest.py:38`
- `client` fixture is function-scoped in `tests/conftest.py:87`
- `admin_user` is function-scoped in both `tests/conftest.py:93` and `tests/benchmarks/conftest.py:64`
- `authenticated_client` is function-scoped in both `tests/conftest.py:106` and `tests/benchmarks/conftest.py:79`
- `sample_post`, `sample_tag`, `sample_subscriber` are in `tests/conftest.py` (lines 119, 135, 144)
- `mock_render`, `mock_smtp`, `mock_email` are in `tests/conftest.py` (lines 155, 163, 173)
- `mock_render` patches `app.email.render_template` (`tests/conftest.py:158`)
- `mock_smtp` patches `app.email._connect_smtp` (`tests/conftest.py:169`)
- `clean_analytics_cache` clears `app.routes.admin._analytics_cache` (`tests/conftest.py:182`)
- `cleanup_uploads` is session-scoped autouse in `tests/conftest.py:189`
- `ensure_buffer_disabled` is autouse in `tests/shared_fixtures.py:8`
- `browser_type_launch_args` and `app_server` exist in `tests/e2e/conftest.py` (lines 11, 26)
- `page` fixture provided by pytest-playwright (not defined in project code)
- E2E tests use port 5010 (`tests/e2e/conftest.py:23`)
- `app_url` returns `http://127.0.0.1:5010` (`tests/e2e/conftest.py:23`)
- `create_posts_bulk` and `create_subscribers_bulk` helpers exist (`tests/benchmarks/conftest.py:93,127`)
- `clean_db` fixture exists (`tests/benchmarks/conftest.py:52`)
- Minimum coverage 80% matches `pyproject.toml:33` (`fail_under = 80`)
- pytest-playwright not in committed requirements
- `api_client` fixture exists in `tests/test_api.py:16`

### Discrepancies (Doc vs Code)

1. **`test-suite.md:79-84` — pytest.ini reference is incorrect**
   Doc says "From `pytest.ini`:" and shows `testpaths = tests` and `addopts = --cov=app --cov-report=term-missing`. The actual `pytest.ini` (3 lines) only contains marker definitions. The real pytest configuration is in `pyproject.toml:20-22`. This is misleading for anyone looking at `pytest.ini` first.

2. **`test-suite.md:86` — "Minimum coverage: 80%" location**
   This claim is correct but the value comes from `pyproject.toml:33` (`fail_under = 80`), not from `pytest.ini` as implied by the surrounding context.

3. **`tests/AGENTS.override.md:68` — `regular_user` fixture does not exist**
   Listed as a key fixture but no `def regular_user` exists anywhere in `tests/`. This is a phantom fixture.

4. **`tests/AGENTS.override.md:69` — `post` fixture does not exist**
   Listed as a key fixture but no `def post\b` exists anywhere in `tests/`. The actual fixture is `sample_post`.

5. **`test-suite.md:38` — `clean_analytics_cache` listed as in `conftest.py` and `benchmarks/conftest.py`**
   It's also defined in `shared_fixtures.py:17-24`. Additionally, `conftest.py:179-186` defines its own `clean_analytics_cache` which shadows the one imported from `shared_fixtures.py` via `import *`. This creates a redundant duplicate definition.

6. **`test-suite.md:44` — `ensure_buffer_disabled` described as in four locations**
   It's only *defined* in `shared_fixtures.py:8`. The other three files (`conftest.py`, `benchmarks/conftest.py`, `e2e/conftest.py`) import it via `from tests.shared_fixtures import *`. The doc implies it's independently defined in all four, which is misleading.

### Missing Documentation

1. **`FakeSubscriber` dataclass** — `tests/conftest.py:60-69` defines a `FakeSubscriber` dataclass for newsletter testing. Not mentioned in architecture docs.

2. **`pytest_configure` hook** — `tests/conftest.py:19-22` registers a `slow` marker via `pytest_configure`. The architecture docs don't mention this marker or how to use it (`-m "not slow"`).

3. **Celery eager configuration** — `tests/conftest.py:49-55` configures Celery to run tasks eagerly in tests. This is critical for understanding test behavior but undocumented.

4. **Environment variables auto-set in conftest** — `tests/conftest.py:8-11` sets `SECRET_KEY`, `ADMIN_PASSWORD`, `TESTING`, `PAGE_VIEW_BUFFER_SIZE` at module level. The doc mentions these as "required" env vars but doesn't note they're automatically configured in tests.

5. **`query_counter` fixture** — `tests/benchmarks/test_benchmarks.py:155-178` defines a `query_counter` fixture for counting database queries per request. Not documented.

6. **Benchmark test classes** — The architecture docs don't mention the seven benchmark test classes in `tests/benchmarks/test_benchmarks.py`: `TestSearchPerformance`, `TestLIKEFallbackPerformance`, `TestDashboardPerformance`, `TestDatabaseQueryCounts`, `TestNewsletterPerformance`, `TestFTSIndexingPerformance`, `TestTagCachingPerformance`.

7. **`api_client` fixture** — `tests/test_api.py:16-26` defines `api_client` (authenticated client for API tests). Mentioned in `tests/AGENTS.override.md:73` but not in `test-suite.md`.

### Potential Bugs / Concerns

1. **Duplicate `clean_analytics_cache` definition** — `tests/conftest.py:179-186` defines `clean_analytics_cache` which shadows the one imported from `tests/shared_fixtures.py:17-24`. Both do the same thing (clear `app.routes.admin._analytics_cache`). This is harmless but confusing for maintenance. One should be removed.

2. **`app_server` doesn't stop Flask server** — `tests/e2e/conftest.py:26-60` starts a Flask server thread but has no teardown logic to shut it down. The thread is daemon so it dies with the process, but this could cause port conflicts if tests are run multiple times in the same process or if the test runner doesn't fully exit.

3. **`cleanup_uploads` only runs on normal exit** — `tests/conftest.py:189-198` cleans uploads after session ends, but if the process is interrupted (SIGKILL, crash), files may persist. This is a minor concern for CI but relevant for local development.

### Improvement Suggestions

1. **Fix pytest.ini reference** — Update `test-suite.md:79-84` to reference `pyproject.toml` instead of `pytest.ini`, since that's where the actual configuration lives.

2. **Remove phantom fixtures** — Delete `regular_user` and `post` from `tests/AGENTS.override.md:68-69` since they don't exist.

3. **Remove duplicate `clean_analytics_cache`** — Remove the definition from `tests/conftest.py:179-186` since it's already in `shared_fixtures.py` and imported via `*`.

4. **Document Celery eager mode** — Add a note to `test-suite.md` explaining that Celery tasks run synchronously in tests.

5. **Document `slow` marker** — Mention the `slow` marker in `test-suite.md` so developers know how to skip slow tests.

6. **Clarify fixture import chain** — Update `test-suite.md:44` to note that `ensure_buffer_disabled` is defined once in `shared_fixtures.py` and imported (not independently defined) in the other three conftest files.

## Action Items

| # | Priority | Description | Docs Affected |
|---|----------|-------------|---------------|
| 1 | high | Fix pytest.ini reference → pyproject.toml | test-suite.md |
| 2 | high | Remove phantom `regular_user` and `post` fixtures | tests/AGENTS.override.md |
| 3 | med | Remove duplicate `clean_analytics_cache` from conftest.py | tests/conftest.py |
| 4 | med | Document Celery eager configuration in tests | test-suite.md |
| 5 | med | Document `slow` marker from pytest_configure | test-suite.md |
| 6 | low | Clarify `ensure_buffer_disabled` import chain vs definition | test-suite.md |
| 7 | low | Document `FakeSubscriber` dataclass | test-suite.md |
| 8 | low | Add server teardown to `app_server` fixture | tests/e2e/conftest.py |
