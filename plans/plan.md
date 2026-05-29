# Implementation Plan - Blog CMS Architecture Reviews

**Project:** DevLog (Blog CMS)
**Status:** IN PROGRESS
**Last Updated:** May 29, 2026
**Source:** Consolidated from 10 architecture review files

---

## Overview

This plan consolidates findings from comprehensive architecture reviews of all modules conducted May 29, 2026. The plan addresses code bugs, documentation discrepancies, and project polish items identified across 10 review documents.

**Total items:** ~100 across 5 waves
**Previous plan:** 96 items marked complete May 29, 2026 (see historical notes at end)

---

## Wave 1: Critical Code Bugs (High Priority)

Items that are actual code bugs requiring fixes, not documentation issues.

### 1A: APScheduler Multi-Container Race Condition

**Bug:** APScheduler uses FileLock with `timeout=0` which only works on single machine. Multiple container replicas will each run their own APScheduler and execute jobs concurrently.

**Files affected:**
- `app/scheduler.py:3-8` (FileLock documentation)
- `docker-compose.yml:60` (celery service - no warning against scaling)

**Fixes needed:**
1. Add prominent warning comment in `docker-compose.yml` celery service that scaling beyond 1 container will cause duplicate job execution
2. Document this limitation in `architecture/deployment/docker.md` and `architecture/overview.md`

**Verification:** `docker compose config` should show warning comment

---

### 1B: Webhook Delivery Status Tracking Bug

**Bug:** `_update_delivery_status()` at `tasks.py:311-330` sets `event.delivered = True` at dispatcher level BEFORE `deliver_single_webhook_task` calls complete. Per-webhook status is never checked. Webhook delivery status in DB will be misleading.

**Files affected:**
- `app/tasks.py:226-227,311-330`

**Fix needed:**
1. Modify `_update_delivery_status()` to track per-webhook success/failure properly
2. Change logic to check individual webhook results, not just dispatcher's `event.delivered` flag
3. Update status to "partial_failure" when some webhooks fail

**Verification:** Write test that verifies status is "partial_failure" when some webhooks fail

---

### 1C: E2E Test Fixture Bugs

**Bug 1:** `tests/conftest.py:100` uses `"testpassword"` (no hyphen) but `tests/e2e/conftest.py:44` uses `"test-password"` (with hyphen). Different passwords cause test failures.

**Bug 2:** `tests/e2e/conftest.py` has no own `app` fixture. Running `pytest tests/e2e/` alone fails because it relies on import chain.

**Files affected:**
- `tests/conftest.py:100`
- `tests/e2e/conftest.py:44, missing app fixture`
- `tests/e2e/test_e2e.py:18`

**Fixes needed:**
1. Choose one password and use consistently across all test fixtures
2. Add proper `app` fixture to `tests/e2e/conftest.py` (or ensure import chain is explicit)

**Verification:** `ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/e2e/ -v` should pass

---

### 1D: Backup Encryption Silent Failure

**Bug:** `app/services/backup.py:103-106` catches exceptions and returns `False` silently. If `BACKUP_ENCRYPTION_KEY` is set but cannot be loaded, backup proceeds unencrypted without error.

**Files affected:**
- `app/services/backup.py:103-106`

**Fix needed:**
1. Add validation that BACKUP_ENCRYPTION_KEY can be loaded before proceeding with encrypted backup
2. If key is set but cannot be loaded, raise an error or log a WARNING (not silently proceed unencrypted)
3. Update `architecture/deployment/docker.md` to document this behavior

**Verification:** Run backup with invalid BACKUP_ENCRYPTION_KEY and verify error/warning is logged

---

### 1E: Python Version Mismatch

**Bug:** `dev.sh:11` requires Python >= 3.14 but `Dockerfile:1` uses python:3.12-slim.

**Files affected:**
- `scripts/dev.sh:11`
- `Dockerfile:1`

**Fix needed:**
1. Align versions: either update dev.sh to accept 3.12, or update Dockerfile to 3.14-slim
2. Document the aligned version in `architecture/deployment/docker.md`

**Verification:** `python --version` and `docker build` should use same major.minor version

---

### 1F: Thread-Unsafe Storage Singleton

**Bug:** `app/storage.py:260-265` singleton `get_storage()` is not thread-safe. Multiple threads could create multiple storage instances.

**Files affected:**
- `app/storage.py:260-265`

**Fix needed:**
1. Add double-checked locking pattern with `threading.Lock()`
2. Use `_storage_lock = threading.Lock()` and check `_storage is None` twice (inside/outside lock)

```python
_storage_lock = threading.Lock()
def get_storage() -> StorageBackend:
    global _storage
    if _storage is None:
        with _storage_lock:
            if _storage is None:
                _storage = get_storage_backend()
    return _storage
```

**Verification:** Concurrent `get_storage()` calls from multiple threads should return same instance

---

## Wave 2: Documentation Corrections (High Priority)

Docs contain false claims that must be corrected.

### 2A: Rewrite `architecture/testing/test-suite.md`

**Issue:** Contains two confirmed false claims:
1. Line 113: "pytest-playwright not in requirements" - FALSE, it IS in requirements.txt lines 18-19
2. Lines 190-196: "E2E conftest creates its own app fixture" - FALSE, e2e/conftest.py does NOT define app fixture

**Also incorrect:**
- `ensure_buffer_disabled` location (says in conftest.py, actually only in shared_fixtures.py)
- `db` fixture scope in benchmarks (says function, actually session)
- `mock_email` description (says it composes, actually just yields)

**Files affected:**
- `architecture/testing/test-suite.md`

**Fix needed:**
1. Rewrite sections 113-117 with correct information about playwright being in requirements
2. Rewrite sections 190-196 with correct information about E2E conftest import chain
3. Add note that `ensure_buffer_disabled` lives in `shared_fixtures.py` and is imported via `*`
4. Clarify `db` scope is session in benchmarks
5. Clarify `mock_email` is a no-op that relies on autouse

**Verification:** Review rewritten sections against actual code

---

### 2B: Fix Module Boundary Documentation

**Issues in `architecture/overview.md`:**
1. `app/tag_cache.py` not in any module table
2. `app/middleware/rate_limit.py` not in module table
3. `app/csrf.py` missing from Security sources
4. `app/utils.py` missing from Infrastructure sources (SSRF)
5. Search straddles Infrastructure and Services confusingly
6. Redis shown as two boxes but single REDIS_URL

**Files affected:**
- `architecture/overview.md`

**Fix needed:**
1. Add `app/tag_cache.py` to Core Application or Infrastructure module table
2. Add `app/middleware/rate_limit.py` to Security module sources
3. Add `app/csrf.py` to Security module sources
4. Add `app/utils.py` to Infrastructure sources
5. Clarify search layer: `app/services/search/` wraps `app/search.py`
6. Clarify Redis is single instance with multiple purposes

**Verification:** Compare module table against actual directory structure

---

### 2C: Fix Stale Line References

**Issues:**
- `architecture/services/backup.md:140` references scheduler.py line 261, actual is 262
- `architecture/infrastructure/webhooks.md:116-118` deliver_single_webhook_task at line 234, doc says 233
- `architecture/tasks/scheduler.md:64-68` Celery queue line numbers inaccurate

**Files affected:**
- `architecture/services/backup.md`
- `architecture/infrastructure/webhooks.md`
- `architecture/tasks/scheduler.md`

**Fix needed:**
1. Replace hardcoded line numbers with function names (more maintainable)
2. Verify line numbers against actual code

---

## Wave 3: Missing Documentation (Medium Priority)

Significant gaps where docs are silent on important behavior.

### 3A: APScheduler Multi-Container Detection

**Gap:** No documentation on how to detect if multiple APScheduler instances are running, and no alerting mechanism.

**Files affected:**
- `architecture/deployment/docker.md`
- `architecture/tasks/scheduler.md`

**Fix needed:**
1. Add section on detection/alerting for APScheduler races
2. Document that FileLock with timeout=0 only works single-node
3. Add warning that scaling beyond 1 container causes duplicate jobs

---

### 3B: Vite Build Requirement

**Gap:** Production deployment requires `npm run build` and manifest.json but this is undocumented.

**Files affected:**
- `architecture/overview.md`
- `architecture/frontend/static-assets.md`

**Fix needed:**
1. Add prominent note that Vite build must run before production
2. Document that `manifest.json` must be present
3. If Vite build hasn't run, JS assets return hashed paths that don't exist

---

### 3C: Backup Encryption Key Documentation

**Gap:** BACKUP_ENCRYPTION_KEY can come from config.toml (not just env var) but this is undocumented.

**Files affected:**
- `architecture/deployment/docker.md`
- `architecture/services/backup.md`

**Fix needed:**
1. Document that encryption key can be from config.toml or environment
2. Clarify silent fallback behavior if key loading fails

---

### 3D: Tag/Series RSS/Atom/JSON Feeds

**Gap:** Routes for `/tag/<slug>/{rss,atom,json}` and `/series/<slug>/{rss,atom,json}` exist but undocumented.

**Files affected:**
- `architecture/routes/rss-feeds.md`

**Fix needed:**
1. Document tag and series RSS/Atom/JSON feed endpoints

---

### 3E: API Error Response Codes

**Gap:** API error codes (400, 401, 403, 404, 409, 429, 503) undocumented.

**Files affected:**
- `architecture/routes/api-routes.md`

**Fix needed:**
1. Add API error response documentation

---

### 3F: Rate Limits for Pages/Series/Tags API

**Gap:** Pages, series, tags API endpoints have rate limits but docs don't mention.

**Files affected:**
- `architecture/routes/api-routes.md`

**Fix needed:**
1. Document rate limits for pages, series, tags API endpoints

---

### 3G: Newsletter Three-Way Path

**Gap:** Architecture shows scheduler -> email.py -> Celery task relationship but it's not clearly documented.

**Files affected:**
- `architecture/overview.md`
- `architecture/tasks/celery-tasks.md`

**Fix needed:**
1. Add architecture note clarifying: scheduler.send_daily_newsletter() -> send_newsletter_task Celery task -> email.send_newsletter()

---

### 3H: Health Check start_period

**Gap:** Container won't be marked healthy for 10 seconds after startup (start_period) but undocumented.

**Files affected:**
- `architecture/deployment/docker.md`
- `architecture/overview.md`

**Fix needed:**
1. Document start_period behavior (10s before healthy)

---

### 3I: SESSION_IP_BINDING Status

**Gap:** Config option exists but enforcement uncertain.

**Files affected:**
- `architecture/overview.md`
- `architecture/core/app-factory.md`

**Fix needed:**
1. Verify implementation exists in `app/__init__.py` before_request_handler
2. Either confirm it's implemented or document as unimplemented

---

### 3J: Silent FTS Initialization Failure

**Gap:** FTS init failures are caught silently and rolled back. User never informed.

**Files affected:**
- `architecture/overview.md`
- `architecture/core/app-factory.md`

**Fix needed:**
1. Consider failing loudly if FTS init fails (add user-visible error)
2. Document current behavior

---

### 3K: Webhook SSRF DNS Time-of-Check Gap

**Gap:** is_safe_webhook_url() resolves DNS once; no lock to hold resolved IP.

**Files affected:**
- `architecture/infrastructure/webhooks.md`

**Fix needed:**
1. Add note about DNS rebinding vulnerability limitation

---

### 3L: Celery Worker Scaling Warning

**Gap:** --concurrency=1 is per-container, not total. Scaling to 3 containers = 3x parallelism.

**Files affected:**
- `architecture/deployment/docker.md`

**Fix needed:**
1. Add warning that scaling celery changes parallelism

---

### 3M: E2E Test CI Race Condition

**Gap:** `docker compose wait redis` only waits for redis. Blog may not be healthy.

**Files affected:**
- `.github/workflows/ci.yml`
- `docker-compose.yml`

**Fix needed:**
1. Add wait for blog health directly, not just redis

---

## Wave 4: Frontend Code Fixes (Medium Priority)

### 4A: Login Template Asset Loading

**Bug:** `admin/login_base.html:8-13,56-58` uses `url_for` directly instead of `vite_asset()`.

**Files affected:**
- `app/templates/admin/login_base.html`
- `app/templates/admin/login.html`

**Fix needed:**
1. Change `url_for('static', ...)` to `vite_asset()` for CSS/JS assets
2. This enables CDN prefix support for login pages

**Verification:** Check login page loads assets correctly with CDN_URL set

---

### 4B: Prism CSS CDN Bypass

**Bug:** `main.js:102` loads Prism CSS via direct path `/static/css/...` bypassing vite_asset.

**Files affected:**
- `app/static/js/main.js:102`

**Fix needed:**
1. Change to use vite_asset() so CDN_URL prefix is included
2. Or document that Prism CSS doesn't support CDN prefix

**Verification:** Check Prism CSS loads with CDN_URL configured

---

### 4C: CSS Hash Caching Process-Level

**Bug:** `_css_hash_cache` in vite.py is process-level, won't update without restart.

**Files affected:**
- `app/vite.py:36-45`

**Fix needed:**
1. Document this as known limitation, or implement invalidation

---

## Wave 5: Source Code Cleanup (Low Priority)

### 5A: Remove Dead Imports

**Issues:**
- `app/backup_encryption.py:28` - dead `SQLAlchemyError` import
- `app/webhook_encryption.py:32` - redundant `binascii` re-import

**Files affected:**
- `app/backup_encryption.py`
- `app/webhook_encryption.py`

---

### 5B: Export decrypt_backup_file

**Issue:** `app/services/__init__.py` doesn't export `decrypt_backup_file`.

**Files affected:**
- `app/services/__init__.py`

---

### 5C: /metrics Endpoint Auth

**Issue:** `/metrics` endpoint has no authentication, exposes infrastructure publicly.

**Files affected:**
- `app/routes/meta.py:323`

---

### 5D: Add db.session.remove() Finally Block

**Issue:** `run_backup_task` missing finally block for db.session.remove().

**Files affected:**
- `app/tasks.py:375`

---

### 5E: S3 Error Differentiation

**Issue:** S3StorageBackend.exists() and list_files() return false/empty without differentiating not_found vs error.

**Files affected:**
- `app/storage.py`

---

## Wave 6: Security Hardening (Low Priority)

### 6A: LOGIN_FAILURE_DELAY Verification

**Issue:** LOGIN_FAILURE_DELAY could be 0 allowing fast brute force.

**Files affected:**
- `app/routes/admin/auth.py:90`

---

### 6B: Comment Rate Limit IP Header

**Issue:** X-Forwarded-For header could bypass comment rate limiting.

**Files affected:**
- `app/routes/api/comments.py:78-79`

---

## Dependencies and Parallelization

### Items That Can Run in Parallel

**Wave 1 items are independent:**
- 1A (APScheduler warning) - docker-compose.yml comment
- 1B (webhook status bug) - tasks.py logic
- 1C (E2E fixtures) - conftest fixes
- 1D (backup encryption) - backup.py error handling
- 1E (Python version) - shell script + Dockerfile
- 1F (thread-safe singleton) - storage.py locking

**Wave 2 items are independent:**
- 2A, 2B, 2C all documentation fixes

**Wave 3 items are independent:**
- 3A through 3M are all documentation gaps

**Wave 4 items (4A, 4B) can run together:**
- Both frontend template/asset fixes

**Wave 5 items are independent:**
- 5A through 5E source cleanup

---

## Verification Steps

For each code fix:
1. `ruff check .` - lint
2. `ruff format --check .` - format check
3. `mypy app/` - type check
4. `ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/` - tests

For frontend fixes:
1. `npm run build` - verify build succeeds
2. Check manifest.json exists

For Docker changes:
1. `docker compose config` - validate compose syntax

---

## Historical Notes

### Previous Plan (May 29, 2026)
Previous plan.md showed 96 items completed across 5 waves. Those items addressed documentation discrepancies, code bugs, and project polish for public release readiness.

### Post-Completion Cleanup (Same Day)
After initial completion, 6 items were fixed:
1. Added PostRevision model details to architecture/core/models.md
2. Corrected base.html line numbers in architecture/frontend/static-assets.md
3. Rewrote dark mode description to emphasize OS preference behavior
4. Fixed docker.md line number references to docker-compose.yml
5. Added FLASK_ENV to docker-compose.yml with default production
6. Fixed 23 broken markdown links across 10 architecture and docs files

### Current Plan Focus
This plan focuses on NEW items identified by architecture reviews that were not addressed in the previous plan:
- True code bugs (APScheduler race, webhook status, backup encryption, E2E fixtures)
- Documentation corrections (test-suite.md false claims, module boundaries)
- Missing documentation (Vite build, APScheduler detection, backup encryption key)
- Frontend fixes (login template assets, Prism CSS CDN)

---

*Last updated: May 29, 2026*