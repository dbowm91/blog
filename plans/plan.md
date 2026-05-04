# Improvement Plan

This plan tracks remaining work and deferred items. Completed waves have been pruned.

---

## Remaining Deferred Items

### 1.3 Module Coverage (Goal: 80%+)
- **[ ]** `app/routes/admin/users.py` (Current: 49%) - NOT STARTED
- **[ ]** `app/filters.py` (Current: 47%) - NOT STARTED
- **[ ]** `app/page_view_buffer.py` (Current: 39%) - NOT STARTED
- **[ ]** `app/storage.py` (Current: 52%) - NOT STARTED
- **[ ]** `app/scheduler.py` (Current: 61%) - NOT STARTED

**Note:** Would require significant test writing effort to reach 80%+ goal. Low priority.

### 3.2 Documentation Overhaul
- **[ ]** Documentation overhaul - PENDING (low priority)

---

## Completed Waves (History)

The following waves were completed in May 2026. This is historical reference only.

### Wave 1: Security & Stability (COMPLETED May 2026)
- **S-1 (FTS SQL Injection):** Fixed `app/search.py:get_search_snippets()` - use individual bindparams for IN clause
- **S-2 (CSS Injection):** Replaced regex with tinycss2 parser + allowlist in `app/utils.py:sanitize_css()`
- **S-3 (Webhook Encryption):** Created `app/webhook_encryption.py` with AES-256-GCM
- **CQ-3 (Exception Handling):** Fixed in `meta.py` and `email.py`
- Test stability: db.session.refresh → expire+re-query, duplicate fixtures removed, page view buffer disabled

### Wave 2: Refactoring & Performance (COMPLETED May 2026)
- **N+1 Queries:** Fixed in `series_list()`, `series_posts()`, and `series_view()` using JOIN/joinedload
- **Missing Indexes:** Added indexes for `webhook_events.webhook_id` and `comments.parent_id`
- **FTS5vocab:** Created `posts_fts_vocab` virtual table
- **API Modularization:** Split `app/routes/api.py` into `app/routes/api/` package
- **Utility Consolidation:** Centralized `generate_slug()` in `app/utils.py`, models (Tag, Page, Post, Series) each have `generate_slug()` method
- **Logging:** Replaced `print()` with proper `logging` in `app/services/backup.py`

### Wave 3: Features & Future (COMPLETED May 2026)
- **CDN Support:** Added `CDN_URL` config, updated `vite_asset()` and `post_image_srcset_filter()`
- **S3 Security:** Added `_clear_credentials()` to clear S3 access_key/secret_key after client init
- **Benchmarking:** Performance tests in `tests/benchmarks/test_benchmarks.py`
- **Audit:** All reviewed modules are in active use

---

## Verification Fixes (May 2026)
- **S-1 tuple fix:** The original S-1 fix used `IN :id_list` with a tuple which doesn't expand in SQLite - corrected to use individual bindparams (`:id0`, `:id1`, etc.)
- **Page/Series generate_slug:** Found that Page and Series models were missing `generate_slug()` method despite plan claiming they were updated - added to both models

## Commit History
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
- `49e80c9` verification-fixes: Fix S-1 SQL injection - use individual bindparams for IN clause (add Page/Series generate_slug)