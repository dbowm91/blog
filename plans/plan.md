# Improvement Plan

This plan outlines the roadmap for security, performance, and architectural improvements. It is organized into parallelizable "Waves".

---

## Wave 1: Security & Stability (Immediate/Critical)
*Target: Fix high-risk vulnerabilities and stabilize the test suite.*

### 1.1 Critical Security Remediations
- **[x] Fix SQL Injection Risk in FTS Search (S-1):** COMPLETED
    - Fixed in `app/search.py:get_search_snippets()` - use individual bindparams for IN clause (not tuple)
- **[x] Fix CSS Injection via Custom CSS (S-2):** COMPLETED
    - Replaced regex with tinycss2 parser + allowlist in `app/utils.py:sanitize_css()`
    - Added `tinycss2>=1.3.0` to requirements.txt
- **[x] Encrypt Webhook Secrets at Rest (S-3):** COMPLETED
    - Created `app/webhook_encryption.py` with AES-256-GCM
    - Added `WEBHOOK_ENCRYPTION_KEY` config
    - Updated `tasks.py` to decrypt secrets on delivery (backward compatible)
- **[x] Fix Broad Exception Handling (CQ-3):** COMPLETED
    - Fixed in `app/routes/public/meta.py` and `app/email.py`

### 1.2 Test Suite Stability & Reliability
- **[x] Database Session Compliance:** COMPLETED
    - Replaced `db.session.refresh()` with `db.session.expire() + re-query` in:
      test_admin_users.py, test_scheduler.py, test_comments_admin.py, test_cli.py,
      test_series.py, test_phase3b.py, test_integration.py
- **[x] Test Isolation (Page View Buffer):** COMPLETED
    - Page view buffer disabled by default in tests (PAGE_VIEW_BUFFER_SIZE=0 env var)
    - session-scoped `app` fixture properly shuts down buffer
- **[x] Remove Duplicate Fixtures:** COMPLETED
    - Removed duplicate `mock_image_processing` fixture from conftest.py
    - All fixtures properly restored (db, client, admin_user, authenticated_client, etc.)
- **[x] Restore Missing Tests:** CANCELLED (file did not exist)

### 1.3 Module Coverage (Goal: 80%+)
- **[ ]** `app/routes/admin/users.py` (Current: 49%) - NOT STARTED
- **[ ]** `app/filters.py` (Current: 47%) - NOT STARTED
- **[ ]** `app/page_view_buffer.py` (Current: 39%) - NOT STARTED
- **[ ]** `app/storage.py` (Current: 52%) - NOT STARTED
- **[ ]** `app/scheduler.py` (Current: 61%) - NOT STARTED

---

## Wave 2: Refactoring & Performance (Short-term)
*Target: Optimize database access and modularize the codebase.*

### 2.1 Database & Query Optimization
- **[x] Eliminate N+1 Queries:** COMPLETED
    - Refactored Series Admin route (`app/routes/admin/series.py`) to use single query with OUTER JOIN for counts
    - Refactored `series_posts()` to use `joinedload(PostSeries.post)`
    - Refactored public `series_view()` to use `joinedload(PostSeries.post)`
- **[x] Add Missing Indexes:** COMPLETED
    - Created migration `add_missing_indexes.py` for `webhook_events.webhook_id` and `comments.parent_id`
    - Added index definitions to respective models in `app/models.py`
- **[x] FTS5 Performance:** COMPLETED
    - Created `fts5vocab` virtual table (`posts_fts_vocab`) in `app/search.py:init_fts()`

### 2.2 Codebase Architecture & Maintenance
- **[x] Modularize API:** COMPLETED
    - Split `app/routes/api.py` (546 lines) into `app/routes/api/` package with:
      - `__init__.py` - Blueprint definition and imports
      - `auth.py` - API key authentication
      - `posts.py` - Post CRUD endpoints
      - `subscribers.py` - Subscriber management endpoints
      - `stats.py` - Dashboard statistics endpoint
- **[x] Consolidate Utility Logic:** COMPLETED
    - Centralized `generate_slug` in `app/utils.py` - updated models (Tag, Page, Post, Series) to use local import
    - Updated `app/services/slug.py` to use `app.utils.generate_slug` directly
    - Updated `app/services/tag.py` to use `app.utils.generate_slug`
    - NOTE: `webhook signing` already consolidated in `app/webhooks.py:sign_webhook_payload()` - no changes needed
    - NOTE: `image variants` already consolidated via `app/tasks.py:generate_image_variants` - no changes needed
- **[x] Improve Logging:** COMPLETED
    - Replaced `print()` statements with `logging` module in `app/services/backup.py`

---

## Wave 3: Features & Future (Long-term)
*Target: Infrastructure enhancements and advanced security.*

### 3.1 Infrastructure & Security Hardening
- **[x] Static Asset CDN Support:** COMPLETED
    - Added `CDN_URL` config option (env var `CDN_URL`)
    - Updated `app/vite.py:vite_asset()` to prepend CDN_URL when configured
    - Updated `app/filters.py:post_image_srcset_filter()` to use CDN_URL when configured
- **[x] S3 Security Hardening:** COMPLETED
    - Added `_clear_credentials()` method to `S3StorageBackend` that clears access_key and secret_key after client initialization
    - Minimizes lifetime of sensitive credentials in memory
- **[x] Performance Benchmarking:** COMPLETED
    - Benchmark tests already exist in `tests/benchmarks/test_benchmarks.py`:
      - `TestSearchPerformance` - FTS5 search timing
      - `TestLIKEFallbackPerformance` - LIKE fallback timing
      - `TestDashboardPerformance` - Dashboard load timing
      - `TestDatabaseQueryCounts` - Query count verification
      - `TestNewsletterPerformance` - Newsletter send timing
      - `TestFTSIndexingPerformance` - FTS indexing timing
      - `TestTagCachingPerformance` - Tag cache timing

### 3.2 Cleanup & Documentation
- **[x] Audit Unused Modules:** COMPLETED
    - Reviewed modules: `backup_encryption` (USED - imported in backup.py, admin/backup.py),
      `backup_integrity` (USED - imported in admin/backup.py), `webhooks` (USED - via tasks.py),
      `celery_app` (USED - imported in tasks.py, conftest.py)
    - All modules are in active use - no removal needed
- **[ ] Documentation Overhaul:** PENDING (low priority)

---

## Execution Guidelines for Agents
- **Parallelization:** Waves can be executed in parallel by different agents, provided they don't modify the same files simultaneously.
- **Testing:** Every change must be accompanied by relevant unit or integration tests.
- **Security:** Prioritize S-1, S-2, and S-3 in Wave 1.

## Diversions from Plan (Documented May 2026)
- **1.2 Test Isolation (Page View Buffer):** The plan mentioned updating `test_search.py` and `test_api.py` to explicitly shutdown the buffer. However, the buffer is now disabled by default via `PAGE_VIEW_BUFFER_SIZE=0` environment variable in conftest.py, which is a cleaner solution.
- **1.2 Restore Missing Tests:** `test_page_view_buffer.py` file did not exist, so this item was cancelled rather than created.
- **1.3 Module Coverage:** Not started - would require significant test writing effort to reach 80%+ goal.
- **2.2 Consolidate Utility Logic - Webhook Signing:** Already consolidated in `app/webhooks.py:sign_webhook_payload()` - no duplication found.
- **2.2 Consolidate Utility Logic - Image Variants:** Already consolidated via `app/tasks.py:generate_image_variants` Celery task - no changes needed.
- **3.2 Audit Unused Modules:** All reviewed modules are in active use - no removal needed.
- **Verification Fixes (May 2026):** During verification, found that S-1 fix used `IN :id_list` with tuple which doesn't work in SQLite/SQLAlchemy - corrected to use individual bindparams. Also found Page and Series models were missing `generate_slug()` method (Plan said Tag, Page, Post, Series were updated but only Tag and Post had it) - added to both models.

## Commits Summary
- `61c3b91` wave1-s1-fts-fix: Fix SQL injection risk in FTS search
- `4b8bd37` wave1-s2-css-fix: Fix CSS injection via custom CSS using tinycss2
- `a8e3614` wave1-s3-webhook-encryption: Add AES-256-GCM encryption for webhook secrets
- `ea8a46d` wave1-cq3-exceptions: Fix broad exception handling in meta.py and email.py
- `8941c4f` wave1-test-stability: Complete Wave 1.2 fixes (db.session.refresh, duplicate fixtures)
- `cbb8d1f` wave2-n1-queries: Fix N+1 in series_list and series_posts admin routes
- `2a61915` wave2-add-indexes: Add missing indexes for webhook_events.webhook_id and comments.parent_id
- `15cb1cb` wave2-fts5-vocab: Create fts5vocab virtual table for efficient term indexing
- `9a1d508` wave2-modularize-api: Split api.py into app/routes/api/ package
- `0aac384` wave2-utility-consolidation: Centralize generate_slug in app/utils.py
- `9fb862e` wave2-backup-logging: Replace print() with proper logging in backup.py
- `9872e6e` wave3-cdn-support: Add CDN_URL config and update vite_asset() and post_image_srcset
- `e0e33a5` wave3-s3-security: Clear S3 credentials from memory after client initialization

---

## Final Updates
- **AGENTS.md and skills updates:** PENDING