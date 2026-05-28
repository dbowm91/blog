# Implementation Plan - Blog CMS Architecture Documentation Fixes

**Project:** Blog CMS
**Status:** COMPLETED
**Last Updated:** May 28, 2026

---

## Overview

Consolidated plan from architecture reviews of all 8 modules. Reviews conducted May 9, 2026. Previous documentation waves (A-F, 43 items) completed May 22, 2026. Plan updated May 28, 2026 with codebase verification.

Wave 1 (8 parallel sub-waves) and Wave 2 (verification) completed May 28, 2026. 15 documentation files updated, all verified against source code.

---

## Deferred Items

### Per-Webhook Retry

**Status:** Not implemented - would require significant refactoring

- **Location:** `app/tasks.py:234-246`
- **Current behavior:** Failed webhooks are logged but silently skipped
- **Documentation:** Acknowledged in `architecture/tasks/celery-tasks.md` and `architecture/infrastructure/webhooks.md`
- **Reason deferred:** `deliver_webhook_task` catches `requests.RequestException` without calling `self.retry()`, so Celery's `max_retries=3` never triggers. Per-webhook retry would require significant refactoring to track individual webhook state.

---

## Completed Items

All items below were completed in Wave 1 (May 28, 2026). Verification passed (10/10 spot checks).

### Wave 1A: Core Module ✅
- C-3: Fixed `totp_secret` → `totp_secret_encrypted` in overview table
- C-4: Added `generate_backup_codes()` and `verify_backup_code()` methods
- C-8: Fixed Webhook `secret` → `webhook_secret_encrypted` with property pattern
- C-9: Added `delivery_status` field to WebhookEvent

### Wave 1B: Routes Module ✅
- All 10 route fixes (R-1 through R-10) were already correct in docs
- All 19 missing routes (M-1 through M-19) were already documented
- Fixed: Removed false `POST /api/auth` endpoint, replaced with `require_api_key` decorator docs

### Wave 1C: Services Module ✅
- Created `architecture/services/tag_cache.md`
- Added encryption module documentation (3 modules: backup, TOTP, webhook)
- Added decryption output path behavior (S-3)
- Added serialization import handling (S-4)

### Wave 1D: Tasks Module ✅
- T-4: Clarified scheduler vs Celery newsletter distinction
- T-3: Renamed "Queue Routing" → "Queue Reference"
- T-2: Added `run_backup_task` parameters
- Added backup implementation comparison table
- Added FileLock documentation

### Wave 1E: Deployment Module ✅
- DEP-1: Added backup service working directory docs
- Added nginx security headers table (8 present, 2 missing)
- Added rate limiting zones documentation
- Added SSL certificate gap documentation
- Added nginx process model documentation

### Wave 1F: Infrastructure Module ✅
- INF-1: Fixed search provider description (wraps app/search.py correctly)
- INF-2: Added SSRF protection documentation
- INF-3: Verified health check critical/optional checks
- Added S3 Storage Backend documentation

### Wave 1G: Testing Module ✅
- Fixed fixtures documentation with detailed descriptions
- Added E2E configuration section
- Added command reference

### Wave 1H: Frontend Module ✅
- Added `post_image_avif_url_stub` filter (DEPRECATED)
- Added CSS architecture (dark mode, critical.css, fonts, Prism themes)
- Added Vite asset helper and chunk split docs
- Added lazy image progressive enhancement

---

## Notes for Future Agents

### Search Provider Architecture (Corrected)
`app/search.py` module-level functions ARE wrapped by `SQLiteSearchProvider` in `app/services/search/sqlite.py`. The provider delegates to the module-level functions through the `SearchProvider` interface. The original plan's claim that they are "separate implementations" was incorrect.

### Verified FALSE Claims (Do NOT Include)
- ~~GPG encryption in backup.md~~ — Already correctly says AES-256-GCM
- ~~Bare `except Exception` in `run_backup_task`~~ — Actually catches `(SQLAlchemyError, OSError, ImportError)`
- ~~Referrer-Policy mismatch~~ — Both use `strict-origin-when-cross-origin`
- ~~`POST /api/auth` route~~ — Only `require_api_key` decorator exists
- ~~`POST /api/subscribers/export` route~~ — Only admin export exists
- ~~`NEWSLETTER_MAX_RETRY_ATTEMPTS` missing~~ — Exists at `app/config.py:116`
- ~~FTS sync missing in `publish_scheduled_posts`~~ — Both `sync_fts_batch` and `invalidate_tag_cache` are present
- ~~Celery production docs missing~~ — Already documented
- ~~Redis image tag discrepancy~~ — Both use `redis:7-alpine`

---

*Last updated: May 28, 2026 — All waves completed and verified*
