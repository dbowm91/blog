# Implementation Plan - Blog CMS (Consolidated)

**Project:** Blog CMS
**Status:** WAVE N - COMPLETED
**Last Updated:** May 2026

---

## Overview

This file contains the consolidated implementation plan for the Blog CMS project, derived from architecture review findings across 8 modules. It serves as the single source of truth for implementation tasks.

All previously identified items (Waves A through N) have been completed.

---

## Wave N: Completed Implementation Items (May 2026)

### N-1: HIGH PRIORITY (Code Fixes)

#### N-1.1: Email Tasks Don't Retry Properly - FIXED
- **File:** `app/tasks.py:264-303`
- **Fix Applied:** Added `max_retries=3` to both task decorators and implemented `self.retry()` after catching exceptions
- **Status:** ✅ COMPLETED (commit: 3cfd1fe)
- **Verification:** Run tests with SMTP disabled to confirm retry behavior

#### N-1.2: mobile-menu.jsx Import Bug - FIXED
- **File:** `app/static/js/main.js:18,72`
- **Fix Applied:** Updated import from `./shared/mobile-menu.js` to `./shared/mobile-menu.jsx`
- **Status:** ✅ COMPLETED (commit: 0ac4662)

---

### N-2: MEDIUM PRIORITY - DOCUMENTATION (All Fixed)

| Item | File | Status | Commit |
|------|------|--------|--------|
| N-2.1: Document ADMIN_RATE_LIMITS | `docs/core/configuration.md` | ✅ COMPLETED | 068c12b |
| N-2.2: S3 Storage Documentation Misleading | `docs/infrastructure/storage.md` | ✅ COMPLETED | e28f7d2 |
| N-2.3: Webhook.secret Documentation Wrong | `docs/core/models.md` | ✅ COMPLETED | bff8f3b |
| N-2.4: WebhookEvent.delivery_status Not Documented | `docs/core/models.md` | ✅ COMPLETED | bff8f3b |
| N-2.5: Search.md Config Location Wrong | `docs/services/search.md` | ✅ COMPLETED | f2c453e |
| N-2.6: Search.md Indexing Description Wrong | `docs/services/search.md` | ✅ COMPLETED | f2c453e |
| N-2.7: admin-routes.md posts/list.py Doesn't Exist | `architecture/routes/admin-routes.md` | ✅ COMPLETED | 770c1fd |
| N-2.8: Page Route Paths Incorrect in admin-routes.md | `architecture/routes/admin-routes.md` | ✅ COMPLETED | 770c1fd |
| N-2.9: Docker Compose v2 Syntax in CI | `.github/workflows/test.yml` | ✅ COMPLETED | 1f064c3 |
| N-2.10: Permissions-Policy Header Missing from nginx | `nginx/conf.d/blog.conf` | ✅ COMPLETED | 1f064c3 |
| N-2.11: Python Version Sync Issue | `.github/workflows/test.yml` | ✅ COMPLETED | 1f064c3 |

---

### N-3: LOW PRIORITY - IMPROVEMENTS (All Fixed)

| Item | File | Status | Commit |
|------|------|--------|--------|
| N-3.1: Email.md "Wrapper Pattern" Description Inaccurate | `docs/infrastructure/email.md` | ✅ COMPLETED | 5951ad9 |
| N-3.2: Serialization.md Missing Fields | `architecture/services/serialization.md` | ✅ COMPLETED | 532d1ee |
| N-3.3: slug.md Parameter Table Too Restrictive | `docs/services/slug.md` | ✅ COMPLETED | f43eb7d |
| N-3.4: Benchmark admin_user Fixture Missing email Parameter | `tests/benchmarks/conftest.py` | ✅ COMPLETED | ce1deda |
| N-3.5: Remove Redundant ensure_buffer_disabled Import | `tests/conftest.py` | ✅ COMPLETED | b50cae3 |
| N-3.6: Benchmark clean_db FTS Cleanup Missing | `tests/benchmarks/conftest.py` | ✅ COMPLETED | bff8f3b |
| N-3.7: Celery Tasks Documentation Stale Line Numbers | `architecture/tasks/scheduler.md` | ✅ COMPLETED | bff8f3b |
| N-3.8: deliver_webhook Deprecation Not Documented in docs/ | `docs/infrastructure/webhooks.md` | ✅ COMPLETED | bff8f3b |
| N-3.9: Backup Naming Documentation Incomplete | `docs/tasks/celery-tasks.md` | ✅ COMPLETED | bff8f3b |
| N-3.10: AGENTS.override.md vite-plugin-flask Reference Wrong | `app/static/AGENTS.override.md` | ✅ COMPLETED | 326efb7 |

---

## Important Context for Future Agents

### Configuration Options
- `PAGE_VIEW_BUFFER_SIZE` - Controls page view buffer size (default 0)
- `ADMIN_RATE_LIMITS` - Rate limits for admin operations: login (5/60s), api_write (100/60s), api_read (500/60s), settings (50/60s), post_create (100/60s), post_update (100/60s)

### Context Processors
Actual context processor function names (not the injected variable names):
- `inject_csrf()` - Injects `csrf_token` and `csp_nonce`
- `inject_config()` - Injects site config variables
- `inject_theme()` - Injects theme settings and `custom_css`
- `inject_footer_data()` - Injects footer links and data
- `inject_show_footer_posts()` - Injects `show_footer_posts` boolean

### Template Filters
Actual filters (defined in `app/filters.py`):
- `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`, `post_image_avif_url_stub`
- NOT `format_date`, `markdown`, `slugify` (these don't exist)

### Backup Naming
Both `create_backup()` (Celery) and `run_daily_backup()` (scheduler) use `blog_*.db` pattern:
- `blog_YYYYMMDD_HHMMSS.db` - plain backup
- `blog_YYYYMMDD_HHMMSS.db.gz` - compressed
- `blog_YYYYMMDD_HHMMSS.db.gpg` - encrypted

### S3 Storage Configuration
S3 settings are read from environment variables, NOT from config.toml:
- `S3_BUCKET`, `S3_REGION`, `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_PUBLIC_URL`

### Email Task Retry Logic
`send_confirmation_task` and `send_password_reset_task` in `app/tasks.py` now have `max_retries=3` and call `self.retry(exc=e)` on exception for automatic retry with exponential backoff.

---

## Previously Completed Items (Reference)

### Wave M - All Items Completed (May 2026)
All critical bugs and documentation issues from Wave M review have been verified as completed.

### Wave L - All Items Completed (Previously)
All items from earlier reviews verified correct.

---

*Last updated: May 2026 - Wave N COMPLETED*