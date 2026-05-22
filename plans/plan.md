# Implementation Plan - Blog CMS (Consolidated)

**Project:** Blog CMS
**Status:** WAVE N - NEW ITEMS IDENTIFIED (see below)
**Last Updated:** May 2026

---

## Overview

This file contains the consolidated implementation plan for the Blog CMS project. It was created by merging findings from 8 architecture review modules (routes, infrastructure, services, frontend, overview, core, deployment, testing, tasks) into a single actionable plan.

All previously identified items (Waves A through M) have been completed. This document now tracks new items identified in the Wave N review.

---

## Wave N: New Items Identified

### N-1: HIGH PRIORITY

#### N-1.1: Email Tasks Don't Retry Properly
- **File:** `app/tasks.py:264-303`
- **Issue:** `send_confirmation_task` and `send_password_reset_task` catch exceptions and return `False` without calling `self.retry()`. These tasks do NOT have `max_retries` set and will not retry on failure.
- **Impact:** Email tasks may fail permanently on first error with no retry.
- **Fix:** Either:
  1. Add `max_retries=3` and implement `self.retry()` after catching exceptions, OR
  2. Remove `retry_backoff=True` if retry behavior is not desired
- **Status:** PENDING

---

### N-2: MEDIUM PRIORITY - DOCUMENTATION

#### N-2.1: Document ADMIN_RATE_LIMITS
- **File:** `docs/core/configuration.md`
- **Issue:** `ADMIN_RATE_LIMITS` (config.py:145-152) is not documented. `PAGE_VIEW_BUFFER_SIZE` is already documented.
- **Fix:** Add documentation for `ADMIN_RATE_LIMITS` configuration.
- **Status:** PENDING

#### N-2.2: S3 Storage Documentation Misleading
- **File:** `docs/storage.md`
- **Issue:** Documentation claims settings are read from `config.toml` but actual code reads from environment variables in `app/storage.py`.
- **Fix:** Update storage.md to clarify env var usage.
- **Status:** PENDING

#### N-2.3: Webhook.secret Documentation Wrong
- **File:** `architecture/core/models.md`
- **Issue:** Line 187 incorrectly states `# Plain text storage`. `Webhook.secret` is actually AES-256-GCM encrypted via `app/webhook_encryption.py`.
- **Fix:** Update models.md to reflect encrypted storage.
- **Status:** PENDING

#### N-2.4: WebhookEvent.delivery_status Not Documented
- **File:** `architecture/core/models.md`
- **Issue:** `WebhookEvent.delivery_status` field exists but not documented.
- **Fix:** Add documentation for `delivery_status` field values: `'delivered'`, `'partial_failure'`, `'failed'`.
- **Status:** PENDING

#### N-2.5: Search.md Config Location Wrong
- **File:** `docs/services/search.md`
- **Issue:** Claims `_FTS_CHECK_TTL` and `_SQLITE_MAX_VARS` are in `app/config.py` but they are hardcoded in `app/search.py`.
- **Fix:** Update search.md to reflect actual locations.
- **Status:** PENDING

#### N-2.6: Search.md Indexing Description Wrong
- **File:** `docs/services/search.md`
- **Issue:** Documentation claims "indexing via signals" but posts are indexed via direct function calls, not automatic signals.
- **Fix:** Clarify that indexing is triggered manually in routes.
- **Status:** PENDING

#### N-2.7: admin-routes.md posts/list.py Doesn't Exist
- **File:** `architecture/routes/admin-routes.md`
- **Issue:** Module structure includes `posts/list.py` which does not exist. Post listing is in `admin/posts/__init__.py` as `dashboard()` function.
- **Fix:** Remove reference to `posts/list.py` and clarify actual location.
- **Status:** PENDING

#### N-2.8: Page Route Paths Incorrect in admin-routes.md
- **File:** `architecture/routes/admin-routes.md`
- **Issue:** Page routes use wrong paths (e.g., `/admin/pages/create` vs actual `/admin/pages/new`).
- **Fix:** Update page route paths to match actual implementation.
- **Status:** PENDING

#### N-2.9: Docker Compose v2 Syntax in CI
- **File:** `.github/workflows/test.yml:119-120`
- **Issue:** Uses `docker-compose` (v1 syntax) but GitHub Actions includes Docker Compose v2 which uses `docker compose` (space).
- **Fix:** Update to `docker compose` (space) syntax.
- **Status:** PENDING

#### N-2.10: Permissions-Policy Header Missing from nginx
- **File:** `nginx/conf.d/blog.conf`
- **Issue:** Documentation claims header is set but `nginx/conf.d/blog.conf` does not contain `Permissions-Policy`.
- **Fix:** Add: `add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;`
- **Status:** PENDING

#### N-2.11: Python Version Sync Issue
- **Files:** `architecture/cicd.md` vs `.github/workflows/test.yml`
- **Issue:** `cicd.md` says lint-and-type tests Python 3.12 and 3.13, but `test.yml` only tests 3.12.
- **Fix:** Either update cicd.md to match test.yml or update test.yml to include 3.13.
- **Status:** PENDING

---

### N-3: LOW PRIORITY - IMPROVEMENTS

#### N-3.1: Email.md "Wrapper Pattern" Description Inaccurate
- **File:** `docs/email.md`
- **Issue:** Says `send_confirmation()` and `send_password_reset()` are synchronous wrapper functions called by Celery tasks. In reality, tasks directly call these functions.
- **Fix:** Update email.md to accurately describe direct function calling pattern.
- **Status:** PENDING

#### N-3.2: Serialization.md Missing Fields
- **File:** `docs/services/serialization.md`
- **Issue:** Omits additional fields returned by functions (`published`, `scheduled_publish_at` for posts; `id`, `expires_at`, `unsubscribed_at` for subscribers).
- **Fix:** Document all fields returned by each serialization function.
- **Status:** PENDING

#### N-3.3: slug.md Parameter Table Too Restrictive
- **File:** `docs/services/slug.md`
- **Issue:** Says supported models are "Post, Page, Tag, Series" but actual code accepts any model with `slug` attribute.
- **Fix:** Update parameter table to clarify model flexibility.
- **Status:** PENDING

#### N-3.4: Benchmark admin_user Fixture Missing email Parameter
- **File:** `tests/benchmarks/conftest.py:71`
- **Issue:** Benchmark's `admin_user` fixture creates users without email while main conftest creates with `email="admin@example.com"`.
- **Fix:** Add `email="admin@example.com"` to benchmark's admin_user fixture.
- **Status:** PENDING

#### N-3.5: Remove Redundant ensure_buffer_disabled Import
- **File:** `tests/conftest.py:4,187`
- **Issue:** `conftest.py` has `from tests.shared_fixtures import *` but also defines its own `ensure_buffer_disabled`. The import is redundant since local definition shadows imported one.
- **Fix:** Remove redundant import and keep only local definition or consolidate.
- **Status:** PENDING

#### N-3.6: Benchmark clean_db FTS Cleanup Missing
- **File:** `tests/benchmarks/conftest.py:52-60`
- **Issue:** `clean_db` fixture deletes all data but doesn't clean up FTS index entries. Orphaned FTS entries may affect benchmark accuracy.
- **Fix:** Consider adding FTS cleanup to `clean_db` fixture.
- **Status:** PENDING

#### N-3.7: Celery Tasks Documentation Stale Line Numbers
- **Files:** `docs/celery-tasks.md`, `architecture/tasks/scheduler.md`
- **Issue:** Line numbers in documentation are stale (code has shifted ~5-7 lines).
- **Fix:** Remove specific line numbers or note they may be outdated.
- **Status:** PENDING

#### N-3.8: deliver_webhook Deprecation Not Documented
- **File:** `docs/services/webhooks.md`
- **Issue:** Should note that `deliver_webhook()` raises `DeprecationWarning` when called.
- **Fix:** Add deprecation notice to webhooks.md.
- **Status:** PENDING

#### N-3.9: Backup Naming Documentation Incomplete
- **Files:** `docs/celery-tasks.md`, `architecture/tasks/scheduler.md`
- **Issue:** `scheduler.md:49` mentions `blog_*.db` naming, `celery-tasks.md:88` claims `blog_YYYYMMDD_HHMMSS.db.gz` for compressed backup - may be inconsistent.
- **Fix:** Verify actual naming and update documentation.
- **Status:** PENDING

---

## Parallelization Analysis (Waves)

Items that can be executed in parallel are grouped into waves:

### Wave N-A (Can run in parallel - Documentation fixes):
- N-2.1 through N-2.11 (all documentation items)
- N-3.1 through N-3.9 (all low priority improvements)

### Wave N-B (Must run sequentially - Code fixes):
- N-1.1 (Email retry logic - requires code change + testing)

---

## Previously Completed Items (Reference)

### Wave M - All Items Completed (May 2026)
All critical bugs and documentation issues from Wave M review have been verified as completed.

### Wave L - All Items Completed (Previously)
All items from earlier reviews verified correct.

---

## Important Context for Future Agents

### Email Task Retry Issue
`send_confirmation_task` and `send_password_reset_task` in `app/tasks.py` catch exceptions and return `False` without calling `self.retry()`. With `retry_backoff=True`, tasks will NOT automatically retry because exceptions are swallowed.

### Configuration Options Not in Docs
- `PAGE_VIEW_BUFFER_SIZE` - Controls page view buffer size (default 0)
- `ADMIN_RATE_LIMITS` - Rate limits for admin operations: login (5/60s), api_write (100/60s), api_read (500/60s), settings (50/60s), post_create (100/60s), post_update (100/60s)

### Context Processors
Actual context processor function names (not the injected variable names):
- `inject_csrf()` - Injects `csrf_token` and `csp_nonce`
- `inject_config()` - Injects `site_title`, `site_description`, `author_name`, `author_role`, `author_avatar`, `base_url`, `current_year`, `canonical_url`
- `inject_theme()` - Injects theme settings and `custom_css`
- `inject_footer_data()` - Injects footer links and data
- `inject_show_footer_posts()` - Injects `show_footer_posts` boolean

---

*Last updated: May 2026 - Wave N items identified, pending implementation*