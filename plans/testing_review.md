# Testing Architecture Review

**Reviewed:** 2026-06-02
**Architecture Docs:** `architecture/testing/test-suite.md`
**Source Files:** `tests/conftest.py`, `tests/e2e/conftest.py`, `tests/benchmarks/conftest.py`, `tests/shared_fixtures.py`, `pytest.ini`, `pyproject.toml`, `requirements.txt`

## Findings

### Verified Claims (Correct)
- Test directory structure matches: `benchmarks/`, `e2e/`, `shared_fixtures.py`, `test_*.py` (flat, no unit/integration subdirs)
- `FakeSubscriber` dataclass at `tests/conftest.py:60-69` with correct fields
- `ensure_buffer_disabled` autouse fixture from `shared_fixtures.py` (imported via `*` into conftest files)
- `clean_analytics_cache` from `shared_fixtures.py` (imported via `*`)
- `cleanup_uploads` session-scoped autouse fixture in `conftest.py:197-208`
- `slow` marker registered via `pytest_configure` in `conftest.py:20-23`
- Celery eager configuration in `conftest.py:50-56` and `e2e/conftest.py:36-41`
- `PAGE_VIEW_BUFFER_SIZE=0` disabling via env var and `shutdown_page_view_buffer()`
- `browser_type_launch_args` in `e2e/conftest.py:46-52` with `--no-sandbox`, `--disable-setuid-sandbox`
- `app_url` fixture returns `"http://127.0.0.1:5010"` (e2e/conftest.py:55-58)
- `app_server` fixture starts Flask on port 5010 (e2e/conftest.py:61-108)
- E2E uses separate database `blog_e2e` (e2e/conftest.py:14)
- E2E `app` fixture shadows main `conftest.py` `app` for E2E tests
- `page` fixture from `pytest-playwright` (not defined in project code)
- playwright in `requirements.txt:18` (`playwright>=1.58.0,<2.0`)
- pytest-playwright in `requirements.txt:19` (`pytest-playwright>=0.7.0,<1.0`)
- `pytest.ini` defines `e2e` marker only
- Coverage configuration in `pyproject.toml:20-33` (`testpaths`, `addopts`, `fail_under=80`)
- SQLAlchemy 2.0 patterns used (select, db.paginate, db.session.get)
- E2E conftest `app` fixture at lines 11-43 (correctly documented)

### Discrepancies (Doc vs Code)

| File:Line | Documentation Claim | Actual Code |
|-----------|---------------------|-------------|
| `conftest.py:120-130` | Not mentioned in docs | `api_client` fixture exists (undocumented) |
| `e2e/test_e2e.py:22,44,62,121` | Best practice suggests using env var | Hardcodes `"test-password"` instead of `os.environ["ADMIN_PASSWORD"]` |
| `benchmarks/conftest.py:80` | Should use env var for consistency | Hardcodes `"test-password"` instead of `os.environ["ADMIN_PASSWORD"]` |
| `conftest.py:114` | Best practice suggests using env var | Hardcodes `"test-password"` instead of `os.environ["ADMIN_PASSWORD"]` |

**Note on Hardcoded Passwords:** The hardcoded `"test-password"` strings work because `os.environ["ADMIN_PASSWORD"]` is set to `"test-password"` in all conftest files before app creation. However, this creates maintenance risk - if someone changes the env var without finding all hardcoded references, tests will fail silently.

### Missing Documentation
- `api_client` fixture (`tests/conftest.py:120-130`) is functional but not listed in the fixture table
- No mention that `authenticated_client` and `api_client` are functionally identical (confirmed by code comparison)
- `mock_email` fixture (`conftest.py:187-194`) not documented
- Benchmark-only helper functions `create_posts_bulk` and `create_subscribers_bulk` are documented but their `sync_fts` call behavior is not explained

### Potential Bugs / Concerns

1. **Password Hardcoding Inconsistency**: Tests hardcode `"test-password"` in multiple places while the env var `ADMIN_PASSWORD` exists. If someone changes the env var value to align with AGENTS.md guidance ("All tests use `os.environ['ADMIN_PASSWORD']`"), E2E tests and benchmarks would break because they hardcode the old value.

2. **AGENTS.md vs Actual Practice**: AGENTS.md states "All tests use `os.environ['ADMIN_PASSWORD']`" but the actual implementation has hardcoded strings in many places.

3. **No Shared Test Password Constant**: No centralized constant for the test password. Each conftest sets the env var, but test code itself uses string literals.

### Improvement Suggestions

1. **Add `api_client` to Documentation**: The fixture table should include `api_client` or note it's an alias for `authenticated_client`.

2. **Extract Password to Constant**: Create a module-level constant in each conftest:
   ```python
   TEST_PASSWORD = "test-password"
   ```
   Then use this constant instead of hardcoded strings for login operations.

3. **Clarify Coverage Config Location**: The docs correctly state coverage is in `pyproject.toml` (not pytest.ini), but this could be clearer since `pytest.ini` exists and might cause confusion.

4. **Document `mock_email` Fixture**: Add to fixture documentation since it's a combined fixture using `mock_render` and `mock_smtp`.

5. **E2E Test Password Extraction**: E2E tests at `tests/e2e/test_e2e.py` should use a constant or env var:
   ```python
   from tests.conftest import TEST_PASSWORD  # or define in e2e/conftest.py
   ```

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|---------|
| 1 | medium | Document `api_client` fixture or clarify it's identical to `authenticated_client` | docs |
| 2 | low | Extract `TEST_PASSWORD` constant to avoid scattered hardcoded strings | source (tests) |
| 3 | low | Update E2E tests to use consistent password reference | source (tests/e2e) |
| 4 | low | Document `mock_email` fixture in architecture | docs |
| 5 | low | Add note about `sync_fts` behavior in benchmark helpers | docs |
