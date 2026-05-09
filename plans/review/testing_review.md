# Testing Architecture Review

## Summary

Reviewed `architecture/testing/test-suite.md` against actual implementation in `tests/` directory. Document is mostly accurate but has several discrepancies and improvement opportunities.

---

## Verified Claims

| Claim | Status | Reference |
|-------|--------|-----------|
| Test structure with benchmarks/ and e2e/ directories | ✓ Verified | `tests/benchmarks/`, `tests/e2e/` exist |
| conftest.py at root of tests/ | ✓ Verified | `tests/conftest.py:1-205` |
| Unit/integration tests in flat structure | ✓ Verified | `tests/test_*.py` files |
| Key fixtures: app, client, db, admin_user, authenticated_client | ✓ Verified | `tests/conftest.py:23-112` |
| Page view buffer disable mechanism documented | ✓ Verified | Lines 60-62 match `tests/conftest.py:185-193` |
| Minimum coverage 80% | ✓ Verified | `pytest.ini:22` - `fail_under = 80` |
| E2E tests use Playwright | ✓ Verified | `tests/e2e/test_e2e.py` |

---

## Discrepancies

### 1. Test Structure Description Incomplete

**Document (lines 7-14)** shows:
```
tests/
├── benchmarks/          # Benchmark tests
├── conftest.py           # Pytest fixtures
├── e2e/                  # End-to-end Playwright tests
├── test_*.py             # Unit/integration tests (flat)
└── __init__.py
```

**Actual structure**: The document omits that `benchmarks/` and `e2e/` have their own `conftest.py` files with duplicated `ensure_buffer_disabled` fixtures:

| File | ensure_buffer_disabled |
|------|----------------------|
| `tests/conftest.py` | Lines 185-193 |
| `tests/e2e/conftest.py` | Lines 11-19 |
| `tests/benchmarks/conftest.py` | Lines 10-18 |
| `tests/test_api.py` | Lines 12-20 (also has its own) |

**Issue**: Code duplication of buffer shutdown logic across 4 files.

### 2. pytest.ini Coverage Options Mismatch

**Document (lines 34-39)** shows:
```ini
addopts = --cov=app --cov-report=term-missing
```

**Actual** (`pytest.ini:6`):
```ini
addopts = --cov=app --cov-report=term-missing
```

✓ Verified - matches.

### 3. Document Missing e2e Test Execution

**Document (lines 46-56)** shows:
```bash
pytest tests/
pytest tests/benchmarks/
pytest tests/e2e/
```

But doesn't mention E2E tests require Playwright installation and a running server on port 5010.

**Actual** (`tests/e2e/conftest.py:34-63`): E2E tests spin up a Flask server on port 5010.

---

## Bugs Found

### 1. Duplicate ensure_buffer_disabled Fixture (Code Duplication)

**Files affected**:
- `tests/conftest.py:185-193`
- `tests/e2e/conftest.py:11-19`
- `tests/benchmarks/conftest.py:10-18`
- `tests/test_api.py:12-20`

**Problem**: Same 9-line fixture is copied 4 times. If buffer shutdown logic changes, all 4 must be updated.

**Recommendation**: Create a shared `tests/shared_fixtures.py`:
```python
# tests/shared_fixtures.py
@pytest.fixture(autouse=True)
def ensure_buffer_disabled():
    """Ensure page view buffer is disabled during tests."""
    from app.page_view_buffer import shutdown_page_view_buffer
    import app.config as _app_config
    _app_config.PAGE_VIEW_BUFFER_SIZE = 0
    shutdown_page_view_buffer()
    yield
    shutdown_page_view_buffer()
```

Then import in each conftest.py:
```python
from tests.shared_fixtures import ensure_buffer_disabled
```

### 2. Document Doesn't Mention test_api.py Has Its Own app Fixture

**Reference**: `tests/test_api.py:29-45`

**Issue**: `test_api.py` has a session-scoped `app` fixture that does NOT use the shared `ensure_buffer_disabled`. It only has function-scoped buffer shutdown (lines 12-20), which is correct but undocumented.

---

## Improvement Recommendations

### HIGH Priority

1. **Consolidate ensure_buffer_disabled fixture**
   - File: Create `tests/shared_fixtures.py`
   - Remove duplicate from: `tests/conftest.py:185-193`, `tests/e2e/conftest.py:11-19`, `tests/benchmarks/conftest.py:10-18`, `tests/test_api.py:12-20`
   - Replace each with import from shared module

2. **Update document structure to reflect actual layout**
   - File: `architecture/testing/test-suite.md:7-14`
   - Add `tests/e2e/conftest.py` and `tests/benchmarks/conftest.py` to structure diagram
   - Document that each subdirectory has its own fixtures

### MEDIUM Priority

3. **Add E2E test requirements to documentation**
   - File: `architecture/testing/test-suite.md:46-56`
   - Add note: E2E tests require Playwright and start a Flask server on port 5010
   - Add setup instructions

4. **Document test_api.py special handling**
   - File: `architecture/testing/test-suite.md`
   - Note that `test_api.py` has its own `app` fixture due to API-specific needs

5. **Add session management warning**
   - File: `architecture/testing/test-suite.md`
   - Document the `db.session.refresh()` caveat from AGENTS.md

### LOW Priority

6. **Add conftest.py fixtures reference table**
   - File: `architecture/testing/test-suite.md:24-31`
   - Table showing which fixtures exist in which conftest.py

---

## Security Notes

✓ No security issues found in test infrastructure.
✓ Environment variables properly set in test fixtures.
✓ CSRF disabled appropriately via `CSRF_ENABLED=False` + `TESTING=True`.

---

## Coverage Status

Current coverage requirement: **80%** (verified in `pytest.ini:22`)

Coverage configuration is correct:
- Source: `app`
- Branch coverage: enabled
- Test/migration/pycache omitted
- Missing line reporting enabled