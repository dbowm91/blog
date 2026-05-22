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
**Issue:** Extra `});` closing on line 42 prevents JSX compilation
**Fix:** Remove extra closing - line 42 should end after `});` with only one closing brace
**Verification:** `npm run build` should produce `dist/mobile-menu*.js`

### A2: Fix marked-wrapper.js Production Build
**File:** `app/static/js/lib/marked-wrapper.js:6-18`
**Issue:** Uses `fetch()` to load `marked.min.js` at runtime - fails in production Vite builds
**Fix:** Replace with proper ES module import or bundle marked directly
**Verification:** Markdown preview works in production build

### A3: Fix public preview Redundant Session Check
**File:** `app/routes/public/posts.py:128`
**Issue:** HMAC token validation (lines 117-126) already authorizes access; session check at line 128 is redundant
**Fix:** Remove `if not session.get('admin_user_id'): abort(403)` or document why it's needed
**Verification:** Preview works with valid HMAC token without admin session

### A4: Add CSRF Protection to Comment Submission
**File:** `app/routes/public/comments.py:12-52`
**Issue:** Comment submission has no CSRF token validation while subscribe route does
**Fix:** Add `@csrf.exempt` only if intentional, or add CSRF validation like subscribe route
**Verification:** Comments work with CSRF token, fail without it

### A5: Add Rate Limiting to Comment Submission
**File:** `app/routes/public/comments.py`
**Issue:** No `@limiter.limit()` decorator (API has 10/min, subscribe has 10/min)
**Fix:** Add rate limit decorator (recommend 10-20/min)
**Verification:** Rate limiting applies to POST /post/<slug>/comment

---

## Wave B: High-Priority Security & Data Integrity (Can Run in Parallel)

### B1: Add Database-Level Unique Constraint on Slugs
**File:** `app/services/slug.py`
**Issue:** Race condition - concurrent requests could generate same slug causing integrity errors
**Fix:** Add unique constraint on model.slug columns at database migration level
**Verification:** Concurrent slug generation doesn't cause duplicate key errors

### B2: Add Per-Webhook Retry with Exponential Backoff
**File:** `app/tasks.py:234-246`
**Issue:** When webhook fails, exception is caught but not re-raised - Celery retry never triggers
**Fix:** Either re-raise to trigger Celery retry, or implement per-webhook retry within task
**Verification:** Failed webhooks are retried up to max_retries

### B3: Remove No-op Assertion in Webhook Task
**File:** `app/tasks.py:248`
**Issue:** `assert event is not None` is always true at that point
**Fix:** Remove assertion or replace with meaningful check
**Verification:** Task completes without assertion errors

### B4: Fix Backup Compression Error Cleanup
**File:** `app/services/backup.py:68-90`
**Issue:** If gzip fails after creating backup file, incomplete cleanup may occur
**Fix:** Ensure `tmp_path` cleanup happens in all error paths
**Verification:** Compression failures don't leave orphaned temp files

### B5: PostgreSQL Search Provider Configuration Error
**File:** `app/services/search/postgresql.py`
**Issue:** Silently falls back to SQLite when PostgreSQL is configured - no warning
**Fix:** Either implement PostgreSQL properly, or raise `ConfigurationError` when configured but not implemented
**Verification:** Using unsupported SEARCH_PROVIDER=postgresql raises error

---

## Wave C: Documentation Updates - Architecture (Can Run in Parallel)

### C1: Update Line Numbers in Task Documentation
**Files:**
- `architecture/tasks/celery-tasks.md:57-61`
- `architecture/tasks/scheduler.md:57-61`
- `architecture/infrastructure/webhooks.md:131-135`

**Issue:** Line numbers for task decorators are off by 3-4 lines

**Corrections:**
| Task | Doc Says | Actually Is |
|------|----------|-------------|
| `deliver_webhook_task` | 182 | 185 |
| `send_confirmation_task` | 262 | 265 |
| `send_password_reset_task` | 283 | 286 |
| `run_backup_task` | 304 | 307 |

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
**Issue:** Missing `get_or_create_tags()`, `get_tag_by_slug()`, `get_all_tags()`, `delete_tag_if_unused()`
**Fix:** Document all 5 public functions and clarify `get_tag_post_count` only counts published posts
**Verification:** All tag service functions documented

### C5: Add S3 Variant Generation Documentation
**File:** `architecture/infrastructure/storage.md`
**Issue:** S3 flow for variant generation is undocumented
**Fix:** Document that `upload_with_processing()` uploads to S3, then Celery task downloads, processes, and re-uploads variants
**Verification:** S3 variant flow documented

### C6: Add init() to SearchProvider Abstraction
**File:** `app/services/search/__init__.py`
**Issue:** `SearchProvider` base class has no `init()` method; `init_fts()` called separately
**Fix:** Add `initialize()` method to abstract class for consistency
**Verification:** Provider abstraction has initialization method

### C7: Update Routes Documentation with Missing Routes
**Files:**
- `architecture/routes/admin-routes.md` - Add: preview-markdown, sessions/revoke, series management
- `architecture/routes/api-routes.md` - Add: POST /api/subscribers, webhook event triggering
- `architecture/routes/public-routes.md` - Add: preview auth requirements, comment rate limit

**Verification:** All actual routes documented

---

## Wave D: Deployment & Configuration (Can Run in Parallel)

### D1: Add Missing Environment Variables to docker-compose.yml
**File:** `docker-compose.yml`
**Missing:**
- `SMTP_HOST` - Required for newsletter/email tasks
- `BACKUP_ENCRYPTION_KEY` - For encrypted backups
- `WEBHOOK_ENCRYPTION_KEY` - For webhook secrets
- `CACHE_REDIS_URL` - For Flask-Caching in production
- `CELERY_BROKER_URL` - For Celery task queue
- `HEALTH_CHECK_SECRET` - For detailed health checks

**Verification:** All required env vars present with comments

### D2: Fix Backup Service PYTHONPATH
**File:** `docker-compose.yml:92-103`
**Issue:** backup.py imports `from app.services.backup` requiring PYTHONPATH=/home/blog
**Fix:** Add `PYTHONPATH=/home/blog` to backup service environment
**Verification:** Backup service starts without import errors

### D3: Add PROXY_COUNT Documentation
**File:** `architecture/deployment/docker.md`
**Issue:** `PROXY_COUNT` not documented but essential for IP detection behind nginx
**Fix:** Add `PROXY_COUNT` to environment variables table
**Verification:** PROXY_COUNT documented

### D4: Add Variant Cleanup on Image Replacement
**File:** `app/storage.py`
**Issue:** When image is replaced, old variants (400_, 800_, 1200_) are orphaned
**Fix:** Delete old variants before creating new ones
**Verification:** Re-uploading same filename cleans up old variants

### D5: Align or Document Rate Limit Discrepancy
**Files:** `nginx/conf.d/blog.conf`, `app/config.py`
**Issue:** nginx login limit is 1/min, Flask is 5/min
**Fix:** Align limits or document why they differ
**Verification:** Rate limits consistent or rationale documented

### D6: CSRF Privilege Rotation Claim
**File:** `architecture/deployment/security.md`
**Issue:** Claims token rotation on privilege changes but code doesn't implement it
**Fix:** Either implement the feature or remove the claim
**Verification:** Documentation matches implementation

---

## Wave E: Testing Improvements (Can Run in Parallel)

### E1: Add 2FA/TOTP Tests (CRITICAL)
**Files:** New test file or add to `tests/test_admin.py`
**Coverage needed:**
- `setup_2fa` route - Generate secret, QR code
- `verify_2fa` route - Verify token, enable 2FA
- `login_2fa` - Login with TOTP token
- `login_2fa` - Login with backup code
- `backup_codes` route - Display backup codes
- `disable_2fa` route - Disable 2FA
- TOTP secret encryption/decryption

**Verification:** All 2FA routes have test coverage

### E2: Add SearchProvider Abstraction Tests
**File:** `tests/test_search.py`
**Coverage needed:**
- `get_search_provider()` factory function
- `SEARCH_PROVIDER` config switching
- `SQLiteSearchProvider` methods
- `PostgreSQLSearchProvider` stub behavior

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
**Issue:** Duplicates `app` and `db` fixtures instead of importing from shared_fixtures
**Fix:** Import from `tests.shared_fixtures` instead of redefining
**Verification:** test_api.py uses shared fixtures

### E5: Remove Duplicate clean_analytics_cache
**File:** `tests/benchmarks/conftest.py:92-99`
**Issue:** Redefines `clean_analytics_cache` already in shared_fixtures
**Fix:** Remove duplicate definition, rely on imported one
**Verification:** Only one definition exists

### E6: Fix AGENTS.override.md Test Structure
**File:** `tests/AGENTS.override.md:51-56`
**Issue:** Lists non-existent `test_home.py`, `test_post.py`, `test_admin.py`
**Actual:** Only `tests/e2e/test_e2e.py` exists with 4 classes
**Also:** Claims `test_rss.py` exists but feed tests are in `tests/test_coverage.py`

**Verification:** AGENTS.override.md matches actual test structure

### E7: Remove Duplicate BACKUP_RETENTION_COUNT
**File:** `app/scheduler.py:261`
**Issue:** Defined in both `app/services/backup.py:21` and `app/scheduler.py:261`
**Fix:** Import from `app.services.backup` in scheduler
**Verification:** Single source of truth for retention count

---

## Wave F: Code Quality Improvements (Lower Priority)

### F1: Document db.session.remove() Pattern
**File:** `architecture/tasks/celery-tasks.md`
**Issue:** Pattern used but not documented
**Fix:** Note all Celery tasks using DB should call `db.session.remove()` in finally block
**Verification:** Pattern documented

### F2: Document generate_image_variants Non-Retry
**File:** `architecture/tasks/celery-tasks.md`
**Issue:** Returns False on failure, not retried - intentional but undocumented
**Fix:** Document image variant failures are not retried
**Verification:** Non-retry behavior documented

### F3: Extract Backup Path Validation Helper
**File:** `app/routes/admin/backup.py:95,120,182,213`
**Issue:** `BACKUP_FILENAME_RE` pattern repeated 4 times
**Fix:** Extract to shared helper function
**Verification:** DRY principle applied

### F4: Expose or Remove cleanup_orphaned_images
**File:** `app/routes/admin/media.py:186`
**Issue:** Function exists but never exposed as route/task
**Fix:** Add admin route to expose it, or remove as dead code
**Verification:** Function is usable or removed

### F5: Make Analytics Days Range Configurable
**File:** `app/routes/admin/helpers/analytics.py:23`
**Issue:** `days = min(max(days, 7), 365)` has magic numbers
**Fix:** Move to config or environment variable
**Verification:** Analytics range is configurable

### F6: Add Variant Cleanup to Image Upload
**File:** `app/storage.py`
**Issue:** Old variants not deleted when replacing image
**Fix:** Delete variants (webp, avif) before creating new ones
**Verification:** Replaced images don't leave orphaned variants

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

- **Wave A5** (rate limiting comments) depends on **Wave A4** (CSRF protection) for proper security order
- **Wave D4** (variant cleanup) is independent but related to **Wave F6** (same file)
- **Wave E7** (remove duplicate BACKUP_RETENTION_COUNT) should happen before **Wave D2** (backup service PYTHONPATH)

---

*Last updated: May 2026 - Consolidated from architecture reviews*
