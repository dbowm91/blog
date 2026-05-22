# Implementation Plan - Blog CMS

**Project:** Blog CMS
**Status:** IN PROGRESS
**Last Updated:** May 2026

---

## Overview

This plan consolidates items from architecture reviews across testing, frontend, services, tasks, deployment, infrastructure, and routes. Items are organized into **waves** indicating parallelization potential.

---

## Wave A: Critical Bugs (Can Run in Parallel)

### A1: Fix mobile-menu.jsx Syntax Error
**File:** `app/static/js/shared/mobile-menu.jsx:42`
**Issue:** Extra `});` closing on line 42 prevents JSX compilation. The `if` block closes with `});` instead of just `}`.
**Fix:** Remove the extra `});`. Line 42 should be `    });` closing the event listener, and the `if` block closes with just `}`.
**Verification:** `npm run build` should produce `dist/mobile-menu*.js`

### A2: Fix marked-wrapper.js Production Build
**File:** `app/static/js/lib/marked-wrapper.js:6-18`
**Issue:** Uses `fetch()` to load `marked.min.js` at runtime - fails in production Vite builds because relative paths don't resolve correctly after bundling.
**Fix:** Replace with proper ES module import. Import marked directly: `import { marked } from 'marked'` or bundle marked into the file.
**Verification:** Markdown preview works in production build

### A3: Fix public preview Redundant Session Check
**File:** `app/routes/public/posts.py:128`
**Issue:** HMAC token validation (lines 117-126) already authorizes access; `session.get('admin_user_id')` check at line 128 is redundant since HMAC tokens don't involve admin_user_id.
**Fix:** Remove `if not session.get('admin_user_id'): abort(403)` or document why it's required (legacy check, etc.)
**Verification:** Preview works with valid HMAC token without admin session

### A4: Add CSRF Protection to Comment Submission
**File:** `app/routes/public/comments.py:12-52`
**Issue:** Comment submission has no CSRF token validation while other public routes (like subscribe) do validate CSRF.
**Fix:** Add CSRF token validation similar to `app/routes/public/subscribe.py:59`. Add hidden form field with `csrf_token()` and validate on submission.
**Verification:** Comments work with CSRF token, fail without it

### A5: Add Rate Limiting to Comment Submission
**File:** `app/routes/public/comments.py`
**Issue:** No `@limiter.limit()` decorator exists. API has 10/min, subscribe has 10/min, but comments have no rate limit.
**Fix:** Add `@limiter.limit("10/minute")` decorator to the comment POST route. Also add to the CSRF protection in A4.
**Verification:** Rate limiting applies to `POST /post/<slug>/comment`

---

## Wave B: High-Priority Security & Data Integrity (Can Run in Parallel)

### B1: Add Database-Level Unique Constraint on Slugs
**File:** `app/services/slug.py`
**Issue:** Race condition exists - concurrent requests could check slug uniqueness and both pass before one inserts. The application-level check is racy. However, database models DO have `unique=True` constraints on `Post.slug`, `Page.slug`, and `Tag.slug`.
**Current State:** DB constraints exist and prevent duplicates from being persisted, but concurrent requests can still cause constraint violation errors.
**Fix:** Add retry logic to handle `IntegrityError` when slug uniqueness constraint is violated. Catch the error and regenerate slug with counter suffix.
**Verification:** Concurrent slug generation doesn't cause unhandled exceptions

### B2: Add Per-Webhook Retry with Exponential Backoff
**File:** `app/tasks.py:234-246`
**Issue:** When a webhook fails with `requests.RequestException`, the exception is caught but NOT re-raised. Celery's `max_retries=3` only triggers on propagated exceptions. Failed webhooks are silently skipped.
**Fix:** Either re-raise the exception to trigger Celery retry, or implement per-webhook retry within task using a failed_webhooks list and a inner retry loop with exponential backoff.
**Verification:** Failed webhooks are retried up to max_retries

### B3: Remove No-op Assertion in Webhook Task
**File:** `app/tasks.py:248`
**Issue:** `assert event is not None` is always true at that point - `event` is assigned at line 204 before the try block and is never modified to None.
**Fix:** Remove the assertion. It serves no purpose.
**Verification:** Task completes without assertion errors

### B4: Fix Backup Compression Error Cleanup
**File:** `app/services/backup.py:68-78`
**Issue:** If `os.replace(tmp_path, backup_path)` fails after compression succeeds (e.g., disk full, permission error), the `.tmp` file is left orphaned. The `except OSError` only catches errors from `gzip.open()` and `shutil.copyfileobj()`, not from `os.replace()`.
**Fix:** Add cleanup of `tmp_path` in a `finally` block or after the `os.replace()` call.
**Verification:** Compression failures don't leave orphaned temp files

### B5: PostgreSQL Search Provider Configuration Error
**File:** `app/services/search/postgresql.py`
**Issue:** Silently falls back to SQLite when PostgreSQL is configured. All methods (search, index_post, remove_post, rebuild_index, get_snippets) delegate to SQLiteSearchProvider without warning.
**Fix:** When `SEARCH_PROVIDER=postgresql` is configured, raise `ConfigurationError` with a clear message that PostgreSQL is not yet implemented. Alternatively, log a warning.
**Verification:** Using unsupported `SEARCH_PROVIDER=postgresql` raises error

---

## Wave C: Documentation Updates - Architecture (Can Run in Parallel)

### C1: Update Line Numbers in Task Documentation
**Files:**
- `architecture/tasks/celery-tasks.md`
- `architecture/tasks/scheduler.md`
- `architecture/infrastructure/webhooks.md`

**Issue:** Line numbers for task decorators are off by 2-3 lines from actual positions.

**Actual line numbers in `app/tasks.py`:**
| Task | Actual Line | scheduler.md says |
|------|-------------|-------------------|
| `generate_image_variants` | 28 | 31 |
| `send_newsletter_task` | 127 | 130 |
| `deliver_webhook_task` | 184 | 182 |
| `send_confirmation_task` | 264 | 262 |
| `send_password_reset_task` | 285 | 283 |
| `run_backup_task` | 306 | 304 |

**Verification:** Line references match actual code

### C2: Document All Public Search Functions
**File:** `architecture/services/search.md`
**Issue:** Missing functions: `sync_fts_batch`, `reset_fts_available`, `get_did_you_mean`, `highlight_query`, `get_indexed_terms`, `extract_snippet`
**Fix:** Add documentation for all public functions in `app/search.py`
**Verification:** All public functions documented

### C3: Update Tag Cache Invalidation Triggers
**File:** `architecture/services/tag_cache.md`
**Issue:** Lists only 2 invalidation locations, actual is 8+
**Actual locations:**
- `app/routes/admin/__init__.py:67,100`
- `app/routes/admin/posts/editor.py:88,206`
- `app/routes/admin/posts/revisions.py:98`
- `app/routes/admin/posts/manage.py:83`
- `app/routes/admin/tags.py:79,109,147`
- `app/routes/admin/posts/__init__.py:155,176,195,213`
- `app/scheduler.py:225,255`

**Verification:** All invalidation locations documented

### C4: Document All Tag Service Functions
**File:** `architecture/services/tag.md`
**Issue:** Functions exist in `app/services/tag.py` but are not documented:
- `get_or_create_tags()` - line 12
- `get_tag_by_slug()` - line 34
- `get_all_tags()` - line 41
- `delete_tag_if_unused()` - line 58
**Fix:** Document all 4 public functions and clarify `get_tag_post_count` only counts published posts
**Verification:** All tag service functions documented

### C5: Add S3 Variant Generation Documentation
**File:** `architecture/infrastructure/storage.md`
**Issue:** S3 flow for variant generation is undocumented
**Actual flow:** `upload_with_processing()` uploads to S3, then Celery task `generate_image_variants()` downloads from S3, processes, and re-uploads variants back to S3.
**Fix:** Document the S3-specific processing flow
**Verification:** S3 variant flow documented

### C6: Add init() to SearchProvider Abstraction
**File:** `app/services/search/__init__.py`
**Issue:** `SearchProvider` base class has no `init()` method; `init_fts()` is called separately during app initialization.
**Fix:** Add `initialize()` method to abstract class and implement in `SQLiteSearchProvider` to wrap `init_fts()`.
**Verification:** Provider abstraction has initialization method

### C7: Update Routes Documentation with Missing Routes
**Files:**
- `architecture/routes/admin-routes.md` - Add: preview-markdown, sessions/revoke, series management routes (create, edit, delete, manage posts, reorder)
- `architecture/routes/api-routes.md` - Add: POST /api/subscribers, webhook event triggering on publish/unpublish
- `architecture/routes/public-routes.md` - Add: preview auth requirements, comment rate limit (when A5 is implemented)

**Verification:** All actual routes documented

---

## Wave D: Deployment & Configuration (Can Run in Parallel)

### D1: Add Missing Environment Variables to docker-compose.yml
**File:** `docker-compose.yml`
**Note:** Many config values are loaded from `config.toml` via `app/config.py`, not all environment variables need to be in docker-compose.yml. However, these are still missing or should be documented:
- `SMTP_HOST` - Required for newsletter/email tasks (currently only in config.toml)
- `BACKUP_ENCRYPTION_KEY` - For encrypted backups
- `WEBHOOK_ENCRYPTION_KEY` - For webhook secrets
- `CACHE_REDIS_URL` - For Flask-Caching in production (defaults to redis://localhost:6379/0 which won't work in Docker)
- `CELERY_BROKER_URL` - For Celery (currently uses REDIS_URL)
- `HEALTH_CHECK_SECRET` - For detailed health checks

**Fix:** Add these environment variables with explanatory comments
**Verification:** All required env vars present with comments

### D2: Fix Backup Service PYTHONPATH
**File:** `docker-compose.yml:92-103`
**Issue:** backup.py imports `from app.services.backup` requiring PYTHONPATH=/home/blog, but backup service does NOT have this environment variable set. (Celery service has it on line 45.)
**Fix:** Add `PYTHONPATH=/home/blog` to backup service environment
**Verification:** Backup service starts without import errors

### D3: Add PROXY_COUNT Documentation
**File:** `architecture/deployment/docker.md`
**Issue:** `PROXY_COUNT` not documented but essential for IP detection behind nginx
**Actual code:** `app/__init__.py:187-188` uses `PROXY_COUNT` for `ProxyFix` middleware
**Fix:** Add `PROXY_COUNT` to environment variables table
**Verification:** PROXY_COUNT documented

### D4: Add Variant Cleanup on Image Replacement
**File:** `app/storage.py`
**Issue:** When image is replaced, old variants (400_, 800_, 1200_, webp, avif) are orphaned - only the base image is deleted, not its variants.
**Fix:** Before creating new variants in `upload_with_processing()`, check for and delete existing variants with the same base filename.
**Verification:** Re-uploading same filename cleans up old variants

### D5: Align or Document Rate Limit Discrepancy
**Files:** `nginx/conf.d/blog.conf`, `app/config.py`
**Status:** nginx and Flask BOTH use 5/min for login - no actual mismatch exists. Both are consistent.
**Note:** nginx burst setting is 5, Flask limit is 5 per 60 seconds = 5/min.
**Fix:** If documentation claims a mismatch, correct the documentation to reflect actual values.
**Verification:** Rate limits consistent or rationale documented

### D6: Remove CSRF Privilege Rotation Claim
**File:** `architecture/deployment/security.md`
**Issue:** Claims token rotation on privilege changes but `app/csrf.py` does NOT implement privilege change detection. Tokens rotate on every successful validation, not on privilege changes.
**Fix:** Either implement the feature or remove the claim from security.md. Current implementation rotates on every use, not on privilege changes.
**Verification:** Documentation matches implementation

---

## Wave E: Testing Improvements (Can Run in Parallel)

### E1: Add 2FA/TOTP Tests (CRITICAL)
**Files:** New test file `tests/test_2fa.py` or add to `tests/test_admin.py`
**Coverage needed:**
- `setup_2fa` route - Generate secret, QR code
- `verify_2fa` route - Verify token, enable 2FA, generate backup codes
- `login_2fa` - Login with TOTP token
- `login_2fa` - Login with backup code
- `backup_codes` route - Display backup codes
- `disable_2fa` route - Disable 2FA
- TOTP secret encryption/decryption via `User.totp_secret` property
- Backup code single-use enforcement

**Verification:** All 2FA routes have test coverage

### E2: Add SearchProvider Abstraction Tests
**File:** `tests/test_search.py`
**Coverage needed:**
- `get_search_provider()` factory function returns correct provider
- `SEARCH_PROVIDER` config switches between SQLite and PostgreSQL providers
- `SQLiteSearchProvider` methods work correctly
- `PostgreSQLSearchProvider` raises ConfigurationError when configured (since it's a stub)

**Verification:** Search abstraction fully tested

### E3: Add WebhookEvent.delivery_status Tests
**File:** `tests/test_webhooks.py`
**Coverage needed:**
- `'delivered'` when all webhooks succeed
- `'partial_failure'` when some fail
- `'failed'` when all fail
- Status when no webhooks configured

**Verification:** Delivery status field updates correctly

### E4: Unify test_api.py Fixtures
**File:** `tests/test_api.py:19-50`
**Issue:** Duplicates `app` and `db` fixtures instead of importing from shared_fixtures. This is ~30 lines of redundant code.
**Fix:** Remove local fixture definitions, import `app` and `db` from `tests.shared_fixtures`
**Verification:** test_api.py uses shared fixtures

### E5: Remove Duplicate clean_analytics_cache
**File:** `tests/benchmarks/conftest.py:92-99`
**Issue:** Redefines `clean_analytics_cache` already in `tests/shared_fixtures.py:16-23`
**Fix:** Remove duplicate definition, rely on imported one via `from tests.shared_fixtures import *`
**Verification:** Only one definition exists

### E6: Fix AGENTS.override.md Test Structure
**File:** `tests/AGENTS.override.md:51-56` (this is the correct file for test structure)
**Issue:** If documentation references non-existent test files like test_home.py, test_post.py, test_admin.py, correct them.
**Current:** `tests/AGENTS.override.md` correctly shows E2E tests are in `tests/e2e/test_e2e.py` with 4 classes.
**Verification:** AGENTS.override.md matches actual test structure

### E7: Remove Duplicate BACKUP_RETENTION_COUNT
**File:** `app/scheduler.py:261`
**Issue:** Defined in both `app/services/backup.py:21` AND `app/scheduler.py:261`
**Fix:** Remove from `app/scheduler.py`, import from `app.services.backup`
**Verification:** Single source of truth for retention count

---

## Wave F: Code Quality Improvements (Lower Priority)

### F1: Document db.session.remove() Pattern
**File:** `architecture/tasks/celery-tasks.md`
**Issue:** Pattern used in `app/tasks.py` (lines 181, 261, 282, 303) but not documented
**Fix:** Note all Celery tasks using DB should call `db.session.remove()` in finally block to clean up scoped session
**Verification:** Pattern documented

### F2: Document generate_image_variants Non-Retry
**File:** `architecture/tasks/celery-tasks.md`
**Issue:** Returns `False` on failure, not retried - intentional but undocumented
**Fix:** Document that image variant failures are not retried (non-critical operation, failures are logged and return False)
**Verification:** Non-retry behavior documented

### F3: Extract Backup Path Validation Helper
**File:** `app/routes/admin/backup.py:95,120,182,213`
**Issue:** `BACKUP_FILENAME_RE.match(filename)` pattern repeated 4 times
**Fix:** Extract to shared helper function `validate_backup_filename(filename)` in the same module
**Verification:** DRY principle applied

### F4: Expose or Remove cleanup_orphaned_images
**File:** `app/routes/admin/media.py:186-242`
**Issue:** Function exists but never exposed as route/task - dead code
**Fix:** Either add admin route to expose it (e.g., `POST /admin/media/cleanup-orphaned`) or remove as dead code
**Verification:** Function is usable or removed

### F5: Make Analytics Days Range Configurable
**File:** `app/routes/admin/analytics.py:23`
**Issue:** `days = min(max(days, 7), 365)` has magic numbers 7 and 365
**Fix:** Move to config or environment variable `ANALYTICS_DAYS_MIN` and `ANALYTICS_DAYS_MAX`
**Verification:** Analytics range is configurable

### F6: Add Variant Cleanup to Image Upload
**File:** `app/storage.py`
**Issue:** Old variants (400_, 800_, 1200_, webp, avif) not deleted when replacing image
**Fix:** Same fix as D4 - when `upload_with_processing()` is called, delete existing variants before creating new ones
**Note:** D4 and F6 are the same issue, implement once

---

## Phase Summary

| Wave | Items | Priority | Parallelizable |
|------|-------|----------|----------------|
| A | 5 | Critical | Yes |
| B | 5 | High | Yes |
| C | 7 | Medium | Yes |
| D | 6 | Medium | Yes |
| E | 7 | High | Yes |
| F | 6 | Low | Yes |

---

## Dependencies

- **Wave A5** (rate limiting comments) depends on **Wave A4** (CSRF protection) - add CSRF first, then rate limiting
- **Wave D4** and **Wave F6** are the same issue - variant cleanup in storage.py - implement once
- **Wave E7** (remove duplicate BACKUP_RETENTION_COUNT) should happen before **Wave D2** (backup service PYTHONPATH) since both involve the backup service

---

## Implementation Notes

### Parallelization Strategy

**Wave A (Critical Bugs)** - All items are independent and can run in parallel via sub-agents:
- A1 (mobile-menu.jsx) + A2 (marked-wrapper.js) + A3 (public preview) + A4 (CSRF comments) + A5 (rate limit comments)

**Wave B (Security & Data)** - All items are independent:
- B1 (slug retry) + B2 (webhook retry) + B3 (remove assertion) + B4 (backup cleanup) + B5 (PostgreSQL error)

**Wave C (Documentation)** - All items are independent:
- C1 (line numbers) + C2 (search functions) + C3 (tag cache) + C4 (tag service) + C5 (S3 flow) + C6 (SearchProvider init) + C7 (missing routes)

**Wave D (Deployment)** - All items are independent:
- D1 (env vars) + D2 (PYTHONPATH) + D3 (PROXY_COUNT) + D4 (variant cleanup) + D5 (rate limit docs) + D6 (CSRF claim)

**Wave E (Testing)** - E4, E5, E6, E7 are trivial fixes; E1, E2, E3 are larger:
- E1 (2FA tests), E2 (SearchProvider tests), E3 (webhook status tests) can run in parallel
- E4, E5, E7 are quick fixes
- E6 is already correct in the actual file

**Wave F (Code Quality)** - F3, F4, F5 are quick fixes; F1, F2 are documentation:
- All can run in parallel

### Suggested Agent Assignment

For fastest implementation, use multiple sub-agents:
- Agent 1: Wave A items
- Agent 2: Wave B items
- Agent 3: Wave C items (documentation, faster)
- Agent 4: Wave D items
- Agent 5: Wave E items (testing, careful)
- Agent 6: Wave F items

---

*Last updated: May 2026 - Consolidated from architecture reviews*