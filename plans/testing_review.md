# Testing Architecture Review

**Reviewed:** 2026-05-29
**Architecture Docs:** architecture/testing/test-suite.md
**Source Files:** tests/, pytest.ini

## Findings

### Verified Claims (Correct)

1. **Test Structure (Overview)** - Correct that tests are organized with:
   - `tests/conftest.py` - main pytest fixtures
   - `tests/benchmarks/` - benchmark tests
   - `tests/e2e/` - Playwright E2E tests
   - `tests/shared_fixtures.py` - shared autouse fixtures
   - Flat `test_*.py` files (not in subdirs)
   - `__init__.py` present in all test packages

2. **Fixture Locations & Scopes** - Largely correct:
   - `app` is session-scoped in all three conftest.py files (lines 25-26 main, 19-20 benchmarks, 11 e2e)
   - `db` is function-scoped in main conftest.py (line 72-73), **session-scoped in benchmarks** (line 38-39)
   - `client`, `admin_user`, `authenticated_client`, `sample_post`, `sample_tag`, `sample_subscriber`, `mock_render`, `mock_smtp`, `mock_email`, `clean_analytics_cache` are all function-scoped
   - `cleanup_uploads` is session-scoped autouse (line 180-181)
   - `ensure_buffer_disabled` is autouse in shared_fixtures and imported everywhere

3. **E2E Test Setup** - Correct:
   - Uses Playwright with `pytest-playwright`
   - `page` fixture provided by pytest-playwright (not redefined)
   - `browser_type_launch_args` adds `--no-sandbox`, `--disable-setuid-sandbox`
   - Server runs on port 5010
   - Test classes match: TestAdminLogin, TestPostCreation, TestNewsletterSubscription, TestMobileResponsiveness

4. **Slow Marker** - Correct registration via `pytest_configure` in conftest.py (lines 19-22)

5. **Coverage Configuration** - Correct in pyproject.toml:
   - `testpaths = ["tests"]`
   - `addopts = "--cov=app --cov-report=term-missing"`
   - `fail_under = 80`
   - Source: `app`, branch coverage enabled

6. **Admin Password Handling** - **CORRECT in source but doc is misleading**:
   - All three conftest files set `os.environ["ADMIN_PASSWORD"] = "test-password"` (hardcoded)
   - CI workflow (ci.yml:69, 172) sets `ADMIN_PASSWORD: test` as env var
   - The doc claims "Required for all tests: ADMIN_PASSWORD - Admin password for test user"
   - **In practice**, the env var is overridden by hardcoded values in conftest files before tests run

7. **ensure_buffer_disabled** - Correct behavior:
   - Sets `PAGE_VIEW_BUFFER_SIZE=0` and calls `shutdown_page_view_buffer()` before/after each test
   - Autouse from `shared_fixtures.py`

8. **Celery Test Configuration** - Correct:
   - `task_always_eager=True` and `task_eager_propagates=True` set in main conftest (lines 50-55)

9. **Mock Fixtures** - Correct:
   - `mock_render` patches `app.email.render_template` returning `"<html>Mock</html>"`
   - `mock_smtp` patches `app.email._connect_smtp` with MagicMock having `sendmail` and `quit`
   - `mock_email` composes both

10. **SQLAlchemy 2.0 Patterns** - Correct usage in tests (select, db.paginate, db.session.get)

## Discrepancies (Doc vs Code)

| Location | Doc Claims | Actual Code |
|----------|-----------|-------------|
| test-suite.md:12 | conftest.py has "session-scoped `app`, `ensure_buffer_disabled` autouse" | `ensure_buffer_disabled` is NOT in conftest.py directly - it is imported from `shared_fixtures.py` via `from tests.shared_fixtures import *` |
| test-suite.md:43 | `ensure_buffer_disabled` is in `conftest.py`, `benchmarks/conftest.py`, `e2e/conftest.py`, `shared_fixtures.py` | `ensure_buffer_disabled` lives only in `shared_fixtures.py`; other conftest files IMPORT it via `from tests.shared_fixtures import *` |
| test-suite.md:36 | `db` scope is "(function)" in main conftest, "(session)" in benchmarks | Correct for function in main, but benchmarks conftest.py:38-39 shows `db` is session-scoped, not function |
| test-suite.md:44 | Fixture table shows `cleanup_uploads` scope as "session (autouse)" | This is correct, but doc doesn't note that `ensure_buffer_disabled` uses `yield` pattern properly |
| test-suite.md:60 | `mock_email` "Combined fixture composing `mock_render` and `mock_smtp`" - the implementation is empty | conftest.py:173-176 shows `mock_email` just yields without wrapping/mock composition - it relies on autouse of component fixtures |
| test-suite.md:113-117 | "E2E tests require pytest-playwright, which is **not** in committed requirements files" | **FALSE** - requirements.txt lines 18-19 explicitly include `playwright>=1.58.0,<2.0` and `pytest-playwright>=0.7.0,<1.0` |
| test-suite.md:190-196 | E2E conftest creates its own "session-scoped `app` fixture" | **INCORRECT** - e2e/conftest.py does NOT define its own `app` fixture. The `app` fixture is NOT defined in e2e/conftest.py at all. The e2e tests use the `page` fixture and `app_server` fixture which uses the `app` from the main conftest import chain via `shared_fixtures` import |
| test-suite.md:43 | `ensure_buffer_disabled` scope is "autouse" | This is correct but it's imported via `from tests.shared_fixtures import *` - the fixture itself lives in shared_fixtures.py |
| pyproject.toml:22 | addopts shown as `--cov=app --cov-report=term-missing` | **CORRECT** - this matches |

## Missing Documentation

1. **shared_fixtures.py** is barely mentioned - it's the central location for `ensure_buffer_disabled` and `clean_analytics_cache`

2. **E2E conftest.py lacks documentation** that it imports via `from tests.shared_fixtures import *` chain to get `ensure_buffer_disabled` behavior

3. **Benchmark fixtures dependency on shared_fixtures.py** is not documented

4. **E2E test password hardcoding** - the E2E conftest creates admin with `"test-password"` but tests hardcode the same value; this is not explicitly documented that E2E admin password differs from function-level tests

5. **`clean_db` fixture** description in doc ("Cleans up test data after each benchmark function, keeping user records") is correct but the implementation detail of using nested transactions is missing

6. **`create_posts_bulk` and `create_subscribers_bulk`** are module-level helpers in benchmarks/conftest.py, not fixtures - doc calls them "Helpers" which is accurate but they are not clearly distinguished as non-fixture helpers

7. **Page view buffer interference** documented but doesn't mention that `ensure_buffer_disabled` only does part of the job - the main conftest also explicitly sets `_app_config.PAGE_VIEW_BUFFER_SIZE = 0` and calls `shutdown_page_view_buffer()` before yielding the app

## Potential Bugs / Concerns

1. **E2E conftest missing own `app` fixture** - The e2e/conftest.py defines `app_server` fixture that references `app` but does NOT define `app` itself. It only imports `from tests.shared_fixtures import *`. This would fail if run in isolation (pytest tests/e2e/). This is a latent bug - E2E tests can only run when the Python path includes the main tests directory.

2. **Admin password hardcoded in multiple places** - `test-password` is hardcoded in:
   - e2e/conftest.py:44
   - Tests themselves (test_e2e.py uses `"test-password"`)
   - Function-level fixtures use `"testpassword"` (no hyphen)
   **Inconsistency**: `tests/conftest.py:100` sets `user.set_password("testpassword")` (no hyphen) but `tests/e2e/conftest.py:44` uses `"test-password"` (with hyphen). This is a bug - they are DIFFERENT passwords.

3. **E2E server shutdown race condition** - e2e/conftest.py:60-62 starts daemon thread and only sleeps 1 second before yielding. If the app isn't fully initialized, tests may fail intermittently.

4. **`mock_email` fixture is effectively a no-op** - conftest.py:173-176 just has `yield` with no actual implementation. It composes nothing - it relies on its component fixtures being autoused. This is confusing but works because `mock_render` and `mock_smtp` are both autouse or manually used.

5. **E2E test isolation** - The E2E conftest reuses the `app` from the import chain but creates its own database and starts its own server. It doesn't go through `cleanup_uploads` since that fixture is only in the main conftest.

## Improvement Suggestions

1. **Clarify fixture import chain** - Document that `conftest.py` files use `from tests.shared_fixtures import *` to pull in shared fixtures rather than duplicating them

2. **Fix password inconsistency** - Standardize `test-password` (with hyphen) across all fixtures and e2e tests or clearly document the difference

3. **Add `app` fixture to e2e/conftest.py** - For proper E2E test isolation, either:
   - Define an explicit E2E-specific `app` fixture in e2e/conftest.py, or
   - Document clearly that E2E tests require being run as part of the full test suite

4. **Remove misleading "pyproject.toml" section from doc** - The test-suite.md shows pytest config coming from pyproject.toml. Only pytest.ini markers are in pytest.ini. Make this clearer.

5. **Improve `mock_email` documentation** - The combined fixture just yields; add a comment explaining it relies on autouse of component fixtures

6. **E2E startup reliability** - Increase sleep in `app_server` fixture or add a proper health check before yielding

7. **Document `__init__.py` requirements** - The existence of `__init__.py` in test subpackages should be explicitly noted as required for Python import resolution

8. **Add explicit note about environment variable override** - Document that hardcoded env values in conftest.py override any externally set ADMIN_PASSWORD/SECRET_KEY values at import time

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|---------|
| 1 | high | Fix password inconsistency: `conftest.py` uses `"testpassword"` (no hyphen) for `admin_user`, but e2e tests use `"test-password"` (with hyphen). These are different passwords. | tests/conftest.py:100, tests/e2e/conftest.py:44, tests/e2e/test_e2e.py:18 |
| 2 | high | E2E conftest.py has no own `app` fixture - relies on import chain. This causes latent isolation bug where `pytest tests/e2e/` alone would fail. | tests/e2e/conftest.py (missing fixture) |
| 3 | med | `test-suite.md` line 113 claim "pytest-playwright **not** in committed requirements files" is FALSE - it IS in requirements.txt lines 18-19 | architecture/testing/test-suite.md:113 |
| 4 | med | `test-suite.md` line 190-196 claim E2E "defines their own session-scoped `app` fixture" is FALSE - e2e/conftest.py does NOT define `app` | architecture/testing/test-suite.md:190-196 |
| 5 | med | `mock_email` fixture (conftest.py:173-176) is a no-op that just yields - doc should clarify it works via autouse of component fixtures | tests/conftest.py:173-176, docs |
| 6 | low | E2E server startup uses `time.sleep(1)` which is fragile - consider health check or longer timeout | tests/e2e/conftest.py:62 |
| 7 | low | Add clarifying note about `ensure_buffer_disabled` living in `shared_fixtures.py` and being imported via `*` in all conftest files | architecture/testing/test-suite.md |
