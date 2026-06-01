# Testing Architecture Review

**Reviewed:** 2026-05-31
**Architecture Docs:** `architecture/testing/test-suite.md`
**Source Files:** `tests/`, `tests/conftest.py`, `tests/e2e/conftest.py`, `tests/benchmarks/conftest.py`, `tests/shared_fixtures.py`, `pytest.ini`, `pyproject.toml`

## Findings

### Verified Claims (Correct)

1. **Directory structure** matches doc (`test-suite.md:7-19`): `tests/`, `tests/benchmarks/`, `tests/e2e/`, `tests/shared_fixtures.py`, flat `test_*.py` files. All confirmed via `ls tests/`.

2. **E2E `app` fixture creates separate database `blog_e2e`** (`tests/e2e/conftest.py:11-43`): Confirmed. Uses `tmp_path_factory.mktemp("blog_e2e")` and yields a separate Flask app instance. Shadows main `conftest.py` `app` fixture for E2E tests.

3. **E2E `app_server` starts Flask on port 5010** (`tests/e2e/conftest.py:61-109`): Confirmed. Creates admin user, starts `BaseWSGIServer` in a daemon thread, polls socket for readiness, yields `app_url`, then shuts down server on teardown.

4. **playwright in requirements.txt** (`requirements.txt:18-19`): Confirmed. `playwright>=1.58.0,<2.0` and `pytest-playwright>=0.7.0,<1.0` both present.

5. **`page` fixture from pytest-playwright** (`test-suite.md:93`): Confirmed. Not defined in project code; provided by `pytest-playwright`. Used in `tests/e2e/test_e2e.py`.

6. **`FakeSubscriber` dataclass** (`tests/conftest.py:61-70`): Confirmed. Matches doc exactly — fields `email`, `token`, `confirmed`, `created_at`, `expires_at`, `unsubscribed_at`.

7. **`ensure_buffer_disabled` autouse fixture** (`tests/shared_fixtures.py:8-14`): Confirmed. Sets `PAGE_VIEW_BUFFER_SIZE=0` and calls `shutdown_page_view_buffer()` before/after each test. Imported via `from tests.shared_fixtures import *` in all three conftest files.

8. **`pytest_configure` registers `slow` marker** (`tests/conftest.py:20-23`): Confirmed.

9. **Celery eager configuration** (`tests/conftest.py:50-56`): Confirmed. Sets `task_always_eager=True` and `task_eager_propagates=True`.

10. **Coverage config in `pyproject.toml`** (`pyproject.toml:24-33`): Confirmed. `fail_under = 80`, `branch = true`, `source = ["app"]`, `addopts = "--cov=app --cov-report=term-missing"`.

11. **`pytest.ini` marker definitions** (`pytest.ini:1-4`): Confirmed. Registers `e2e` and `slow` markers.

12. **`mock_render` and `mock_smtp` fixtures** (`tests/conftest.py:169-184`): Confirmed. Patches `app.email.render_template` and `app.email._connect_smtp` respectively.

13. **`cleanup_uploads` session-scoped autouse** (`tests/conftest.py:198-209`): Confirmed. Cleans `app/static/uploads/` after session.

14. **`sample_post`, `sample_tag`, `sample_subscriber` fixtures** (`tests/conftest.py:133-166`): Confirmed. All create expected objects with documented values.

15. **Benchmark `db` is session-scoped** (`tests/benchmarks/conftest.py:38-49`): Confirmed. Differs from main `conftest.py` `db` which is function-scoped.

16. **Benchmark helpers exist** (`tests/benchmarks/conftest.py:93-141`): Confirmed. `create_posts_bulk(db, count=50)` and `create_subscribers_bulk(db, count=100)` match doc.

17. **Benchmark `clean_db` fixture** (`tests/benchmarks/conftest.py:52-61`): Confirmed. Cleans data after each test function, preserving `users` and `alembic_version` tables.

18. **E2E test classes** (`tests/e2e/test_e2e.py`): Confirmed. Contains `TestAdminLogin`, `TestPostCreation`, `TestNewsletterSubscription`, `TestMobileResponsiveness` — all four documented classes exist.

19. **E2E `browser_type_launch_args`** (`tests/e2e/conftest.py:46-52`): Confirmed. Adds `--no-sandbox` and `--disable-setuid-sandbox` args.

20. **E2E `app_url`** (`tests/e2e/conftest.py:55-58`): Confirmed. Returns `"http://127.0.0.1:5010"`.

21. **`sample_post` fixture creates published post** (`tests/conftest.py:136-143`): Confirmed. `title="Test Post"`, `slug="test-post"`, `published=True`.

22. **`sample_tag` fixture creates tag** (`tests/conftest.py:152-153`): Confirmed. `name="Python"`, `slug="python"`.

23. **`sample_subscriber` fixture creates confirmed subscriber** (`tests/conftest.py:163`): Confirmed. `email="test@example.com"`, `confirmed=True`.

### Discrepancies (Doc vs Code)

1. **`slow` marker registered redundantly** — `test-suite.md:117-123` documents `pytest_configure` in `conftest.py` as the registration mechanism, but `pytest.ini:3` also registers `slow` in its markers list. Both exist, creating duplicate marker registration. The doc does not mention the `pytest.ini` registration.

2. **E2E admin password not derived from env var** — `tests/e2e/conftest.py:75` hardcodes `admin.set_password("test-password")` instead of reading `os.environ["ADMIN_PASSWORD"]`. The `tests/conftest.py:10` sets `os.environ["ADMIN_PASSWORD"] = "test-password"`, so they happen to match. But if someone changes the env var, E2E tests would still use the hardcoded value. The `tests/conftest.py:101` also hardcodes `user.set_password("test-password")` — same pattern, same risk.

3. **`cleanup_uploads` uses fragile relative path** — `tests/conftest.py:202` computes the uploads path as `os.path.join(os.path.dirname(__file__), "..", "app", "static", "uploads")`. This relies on `__file__` being `tests/conftest.py` relative to the project root. If tests are run from a different working directory or if the file is moved, this path could break silently (the `if os.path.exists` guard would skip cleanup without warning).

4. **`api_client` fixture not documented** — `tests/conftest.py:120-130` defines `api_client` fixture (function-scoped, creates authenticated client via login). The architecture doc does not list it in the fixture table (lines 33-48). It is functionally identical to `authenticated_client` — both just call `/admin/login` with the same credentials. The doc's `AGENTS.override.md:71` mentions it briefly as "From test_api.py" but it's actually in `conftest.py`.

5. **`mock_email` fixture not documented** — `tests/conftest.py:188-194` defines `mock_email` (combines `mock_render` + `mock_smtp`). Architecture doc does not mention it anywhere. Used by `tests/test_tasks.py:60,137`.

6. **Benchmark `app` fixture lacks Celery/buffer/page_view_config** — `tests/benchmarks/conftest.py:19-35` creates app but does NOT configure Celery eager mode, does NOT call `shutdown_page_view_buffer()`, and does NOT set `PAGE_VIEW_BUFFER_SIZE=0`. The `ensure_buffer_disabled` autouse fixture (imported via `shared_fixtures`) handles buffer shutdown, but Celery tasks in benchmark tests would go to a real broker if one is configured. The main `conftest.py:50-56` and E2E `conftest.py:36-41` both configure Celery, but benchmarks do not.

### Missing Documentation

1. **`api_client` fixture** — Defined in `tests/conftest.py:120-130`. Not in the architecture doc fixture table.

2. **`mock_email` fixture** — Defined in `tests/conftest.py:188-194`. Not in the architecture doc fixture table or description.

3. **Benchmark Celery configuration** — The doc does not address whether benchmarks configure Celery eager mode. The code (`tests/benchmarks/conftest.py`) does NOT configure it, unlike main and E2E conftest files.

4. **`pytest.ini` marker duplication** — The doc does not mention that `pytest.ini` also registers `slow` alongside `pytest_configure`.

5. **`clean_analytics_cache` fixture source** — `test-suite.md:42` says it's defined in `conftest.py` and `benchmarks/conftest.py`, but it's actually defined in `tests/shared_fixtures.py:17-24`. Both conftest files import it via `from tests.shared_fixtures import *`.

6. **`requirements.txt` line references** — `test-suite.md:131` says playwright is on "lines 18-19" of `requirements.txt`. This is correct but could drift. No other version pinning notes.

7. **Test file count** — `AGENTS.override.md:35,60` says "~36 test files". Actual count of `test_*.py` files in `tests/` root: 28 files. Including `tests/benchmarks/test_benchmarks.py` and `tests/e2e/test_e2e.py` = 30 total. The "~36" claim is inflated.

### Potential Bugs / Concerns

1. **E2E `db` fixture absence** — `tests/e2e/conftest.py` does NOT define a `db` fixture. E2E tests interact via browser HTTP requests, so this is by design. However, if any E2E test fixture ever needs direct DB access, it would fall through to the main `conftest.py` `db` fixture (function-scoped), which creates/drops tables per test — potentially conflicting with the E2E server's database. Currently not a bug, but a latent risk.

2. **`cleanup_uploads` session-scoped autouse may interfere** — If a test relies on a file existing in `app/static/uploads/` during the session, the cleanup only runs after all tests. But if tests are run in a specific order where later tests create files that earlier tests expect, the session-scoped cleanup is fine. The real concern: if tests run in parallel (`pytest-xdist` is in `requirements.txt:21`), multiple workers would share the same `app/static/uploads/` directory, and session-scoped cleanup from one worker could delete files another worker's tests need.

3. **Benchmark Celery tasks not eagerly executed** — Since `tests/benchmarks/conftest.py` does not set `task_always_eager=True`, any Celery task triggered during benchmarks would be dispatched to a broker. If no broker is available, tasks would fail silently or hang. This is a real bug for benchmark tests that exercise code paths involving Celery tasks.

4. **`authenticated_client` and `api_client` are duplicates** — `tests/conftest.py:107-117` and `tests/conftest.py:120-130` are functionally identical (both just login via POST). The `api_client` fixture provides no additional value. If they're meant to diverge in the future (e.g., `api_client` sets an API key header), the current duplication is confusing.

5. **Test command inconsistency** — `AGENTS.md` specifies `ADMIN_PASSWORD=test` (no hyphen), but `tests/conftest.py:10` sets `os.environ["ADMIN_PASSWORD"] = "test-password"` (with hyphen). The conftest.py value overrides the env var, so the command works regardless. But the AGENTS.md command is misleading — it suggests the env var matters when it's actually overridden.

### Improvement Suggestions

1. **Consolidate marker registration** — Remove `slow` from `pytest.ini:3` since it's already registered in `conftest.py:20-23` via `pytest_configure`. Keep only one source of truth.

2. **Use env var for E2E admin password** — In `tests/e2e/conftest.py:75`, change to `admin.set_password(os.environ["ADMIN_PASSWORD"])` to stay in sync with the environment.

3. **Document `api_client` and `mock_email` fixtures** — Add both to the architecture doc fixture table.

4. **Fix benchmark Celery configuration** — Add Celery eager mode configuration to `tests/benchmarks/conftest.py` to match main and E2E conftest files.

5. **Make `cleanup_uploads` more robust** — Either use a pytest `tmp_path`-based approach, or at minimum log a warning if the uploads directory doesn't exist at the expected path.

6. **Remove `api_client` duplication** — If it serves no purpose beyond `authenticated_client`, remove it. If it's intended for API-key-based auth, implement that differentiation.

7. **Update test file count** — Correct "~36" in `AGENTS.override.md:35,60` to the actual count (~30).

8. **Clarify `clean_analytics_cache` source** — Update `test-suite.md:42` to note it's defined in `shared_fixtures.py`, not `conftest.py` directly.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | High | Fix benchmark Celery configuration — add `task_always_eager=True` to `tests/benchmarks/conftest.py` | `tests/benchmarks/conftest.py` |
| 2 | High | Use `os.environ["ADMIN_PASSWORD"]` in E2E admin creation (`tests/e2e/conftest.py:75`) instead of hardcoded string | `tests/e2e/conftest.py` |
| 3 | Medium | Consolidate `slow` marker registration — remove from `pytest.ini` or `conftest.py` | `pytest.ini`, `tests/conftest.py` |
| 4 | Medium | Document `api_client` and `mock_email` fixtures in architecture doc | `architecture/testing/test-suite.md` |
| 5 | Medium | Fix `clean_analytics_cache` source attribution in doc — it's in `shared_fixtures.py`, not `conftest.py` | `architecture/testing/test-suite.md` |
| 6 | Low | Remove or differentiate `api_client` fixture (currently duplicate of `authenticated_client`) | `tests/conftest.py` |
| 7 | Low | Update test file count from "~36" to "~30" in `tests/AGENTS.override.md` | `tests/AGENTS.override.md` |
| 8 | Low | Make `cleanup_uploads` path resolution more robust or add logging | `tests/conftest.py` |
