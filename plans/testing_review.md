# Testing Review - Test Suite Documentation vs Implementation

## Overview

Reviewed `architecture/testing/test-suite.md` against actual test implementation in `tests/` directory. Found multiple discrepancies between documented structure and actual code.

---

## Discrepancies Identified

### 1. `ensure_buffer_disabled` Fixture Location

**Doc claims:** `ensure_buffer_disabled` is defined in `conftest.py`, `benchmarks/conftest.py`, `e2e/conftest.py`, and `shared_fixtures.py`.

**Actual:** The fixture is ONLY defined in `tests/shared_fixtures.py:8`. Other conftest files import it via `from tests.shared_fixtures import *`.

**Impact:** Documentation is misleading. The fixture is properly centralized but the table in the doc incorrectly implies it's defined in multiple places.

---

### 2. E2E Test Structure - Non-existent Files

**Doc claims (test-suite.md:15):** E2E tests have `test_e2e.py` with classes: `TestAdminLogin`, `TestPostCreation`, `TestNewsletterSubscription`, `TestMobileResponsiveness`.

**AGENTS.override.md:51-56 claims:**
```
tests/e2e/                 # Playwright E2E tests (has buffer protection)
    ├── test_home.py
    ├── test_post.py
    └── test_admin.py
```

**Actual:** Only `tests/e2e/test_e2e.py` exists with these exact classes. The files `test_home.py`, `test_post.py`, and `test_admin.py` do not exist.

**Impact:** AGENTS.override.md is completely wrong about E2E test file structure. The file `test_e2e.py` with the 4 classes is correctly documented in test-suite.md.

---

### 3. Feed Tests Location

**AGENTS.override.md:47 claims:** `test_rss.py` contains RSS/Atom feed tests.

**Actual:** Feed tests are in `tests/test_coverage.py:7-40` (test_atom_feed_content_structure, test_rss_feed_excludes_drafts, etc.).

**Impact:** Documentation references a non-existent file.

---

### 4. `mock_email` Fixture Description Inaccurate

**Doc claims (test-suite.md:55):** `mock_email` is a "Combined mock for email rendering and SMTP sending."

**Actual code (`tests/conftest.py:168-171`):**
```python
@pytest.fixture(scope="function")
def mock_email(mock_render, mock_smtp):
    """Combined mock for email rendering and SMTP sending."""
    yield
```

The fixture has dependencies on `mock_render` and `mock_smtp` but doesn't actually combine them - it just yields without doing anything. The mocks are used independently.

**Impact:** Documentation overstates what the fixture does.

---

### 5. `cleanup_uploads` Scope

**Doc (test-suite.md:57):** Lists `cleanup_uploads` as "session (autouse)".

**Actual code (`tests/conftest.py:174-183`):**
```python
@pytest.fixture(scope="session", autouse=True)
def cleanup_uploads():
```

This is correct, but the doc format is confusing (shows scope and autouse separately).

---

### 6. `client` Fixture Scope Inconsistency

**Doc (test-suite.md:35):** Shows `client` in main conftest as function-scoped.

**Benchmark conftest:** The `client` is NOT defined as a fixture in `benchmarks/conftest.py`. Tests use `app.test_client()` directly within the test function.

**Actual:** Benchmark tests don't use a `client` fixture at all - they create clients ad-hoc.

---

### 7. `db` Fixture Scope Inconsistency

**Doc (test-suite.md:35):** Notes `db` is "function in main conftest, session in benchmarks".

This is correctly documented but highlights an inconsistency that could cause confusion.

---

## Missing Test Coverage

### 1. No 2FA/TOTP Tests (CRITICAL)

AGENTS.md section "Implemented Features > 2FA Implementation" documents:
- TOTP secrets encrypted at rest using AES-256-GCM
- Backup codes SHA-256 hashed, single-use (8 codes generated)
- Routes: `/admin/2fa/setup`, `/admin/2fa/verify`, `/admin/2fa/backup-codes`, `/admin/2fa/disable`

**Actual:** No test files contain tests for 2FA functionality:
```bash
grep -r "2fa\|totp\|backup_code" tests/ --include="*.py"
# Returns no matches
```

The routes exist in `app/routes/admin/auth.py:263-466` and handle:
- `setup_2fa` - Generate TOTP secret, QR code
- `verify_2fa` - Verify token, generate backup codes
- `login_2fa` - Login with TOTP or backup code
- `backup_codes` - Display backup codes
- `disable_2fa` - Disable 2FA

**Impact:** Critical security feature has zero test coverage.

---

### 2. No Backup Codes Tests

Related to 2FA, backup codes are mentioned in AGENTS.md but no tests exist for:
- Backup code generation
- Backup code verification
- Single-use enforcement
- Backup code hashing

---

### 3. No SearchProvider Abstraction Tests

AGENTS.md documents `SearchProvider` abstract class with:
- `SQLiteSearchProvider` - Current default using FTS5
- `PostgreSQLSearchProvider` - Stub for future PostgreSQL support
- `get_search_provider()` factory function

**Actual:** `test_search.py` tests FTS directly but does NOT test:
- The `SearchProvider` abstract base class
- The `get_search_provider()` factory
- Provider selection based on `SEARCH_PROVIDER` config

The search service exists at `app/services/search/__init__.py:7-83` but isn't tested as an abstraction.

---

### 4. No Tests for WebhookEvent.delivery_status Field

AGENTS.md documents `WebhookEvent.delivery_status` field with values:
- `'delivered'` - All webhooks succeeded
- `'partial_failure'` - Some succeeded, some failed
- `'failed'` - All failed

**Actual:** `test_webhooks.py` tests delivery but doesn't verify the `delivery_status` field updates correctly.

---

## Code Issues Found

### 1. `test_api.py` Duplicates Fixture Setup

`tests/test_api.py:19-50` defines its own `app` and `db` fixtures instead of importing from shared_fixtures. This:
- Duplicates code (~30 lines)
- May miss buffer protection (only sets env var, not using `ensure_buffer_disabled`)
- Creates maintenance burden

**Comparison:**
- `test_api.py:19-35`: Custom `app` fixture with temp db
- `tests/conftest.py:22-51`: Shared `app` fixture with temp db and buffer handling

The `test_api.py` does import `from tests.shared_fixtures import *` at line 5, but then re-defines its own `app` and `db` fixtures, which is redundant.

---

### 2. `authenticated_client` Fixture Difference in test_api.py

`test_api.py:74-84` defines `api_client` (similar to `authenticated_client`) but uses the custom `client` fixture from the same file rather than the shared one.

---

### 3. Benchmark `clean_db` Fixture Doesn't Sync FTS

`tests/benchmarks/conftest.py:51-60` - The `clean_db` fixture clears all tables except `users` but doesn't reinitialize FTS, which could cause issues if tests rely on FTS after cleanup.

---

### 4. `test_api.py` Missing Environment Setup

`test_api.py` imports `from tests.shared_fixtures import *` but doesn't set up the required environment variables in the module scope like other test files do:
```python
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-chars-long-for-testing"
os.environ["ADMIN_PASSWORD"] = "test-password"
os.environ["PAGE_VIEW_BUFFER_SIZE"] = "0"
```

It sets them at lines 7-10, but if those env vars are already set before the import, the shared fixtures might not behave correctly.

---

### 5. Potential Session/Function Scope Confusion

- Main conftest `db` is function-scoped (drops/creates each test)
- Benchmarks conftest `db` is session-scoped (reuses across benchmarks)

This is intentional but undocumented rationale could confuse future developers.

---

## Undocumented Fixtures

### 1. `FakeSubscriber` Dataclass

`tests/conftest.py:54-62` defines `FakeSubscriber` but it's not mentioned in any documentation. It appears to be for newsletter testing without real subscribers.

---

### 2. `clean_analytics_cache` Duplicated

Defined in both:
- `tests/conftest.py:173-181`
- `tests/benchmarks/conftest.py:92-99`

The benchmarks conftest imports from shared_fixtures (`from tests.shared_fixtures import *`) but then redefines `clean_analytics_cache` locally, which is redundant.

---

## Test File Inventory

### Unit/Integration Tests (42 files)
- test_admin.py, test_admin_users.py, test_api.py
- test_backup.py, test_backup_integrity.py, test_base62.py
- test_cache.py, test_cli.py, test_comments_admin.py, test_context_processors.py
- test_coverage.py, test_email.py, test_filters.py, test_integration.py
- test_models.py, test_multi_user.py, test_newsletter.py, test_page_view_buffer.py
- test_phase3b.py, test_phase8.py, test_property_based.py
- test_public.py, test_public_comments.py, test_revisions.py
- test_scheduler.py, test_search.py, test_security.py, test_series.py
- test_services_backup.py, test_storage.py, test_tasks.py, test_transaction.py
- test_utils.py, test_validators.py, test_webhooks.py

### Benchmark Tests (1 file)
- benchmarks/test_benchmarks.py

### E2E Tests (1 file)
- e2e/test_e2e.py

### Total: 44 test files with 61 test classes

---

## Recommendations

### High Priority

1. **Add 2FA/TOTP tests** - Critical security feature without any coverage
   - Test `setup_2fa` route
   - Test `verify_2fa` route
   - Test `login_2fa` with TOTP token
   - Test `login_2fa` with backup code
   - Test `backup_codes` route
   - Test `disable_2fa` route
   - Test TOTP secret encryption/decryption

2. **Add backup codes tests**
   - Test generation of 8 codes
   - Test single-use enforcement
   - Test SHA-256 hashing

3. **Fix AGENTS.override.md** - References non-existent files:
   - test_rss.py (should be test_coverage.py)
   - test_home.py, test_post.py, test_admin.py (these don't exist, only test_e2e.py)

### Medium Priority

4. **Add `get_search_provider()` tests** - Test the abstraction layer
   - Test factory returns correct provider based on config
   - Test SQLiteSearchProvider methods
   - Test PostgreSQLSearchProvider stubs

5. **Unify test_api.py fixtures** - Import from shared_fixtures instead of duplicating

6. **Document `FakeSubscriber` dataclass** - Or remove if unused

7. **Add WebhookEvent.delivery_status tests** - Verify status updates

### Low Priority

8. **Clarify fixture scope rationale** - Why benchmarks use session-scoped db

9. **Fix mock_email description** - It's not actually "combined", it's just a passthrough

10. **Fix ensure_buffer_disabled table** - Remove incorrect multiple location claims

11. **Remove duplicate `clean_analytics_cache`** - In benchmarks/conftest.py

---

## Verification Commands

```bash
# Check for 2FA tests
grep -r "2fa\|totp" tests/ --include="*.py"

# Check for SearchProvider tests
grep -r "get_search_provider\|SearchProvider" tests/ --include="*.py"

# List actual E2E files
ls tests/e2e/

# List feed tests
grep -l "atom\|rss\|feed" tests/*.py

# Check for backup code tests
grep -r "backup.code\|backup_codes" tests/ --include="*.py"
```