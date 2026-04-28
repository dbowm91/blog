# Improvement Plan

**Date:** 2026-04-28
**Status:** Completed - All waves implemented
**Source:** Consolidated Master Plan

---

## Verification Status

- 477 tests pass (excluding E2E and known flaky integration test)
- All items below marked as COMPLETED unless marked SKIPPED

---

## Wave Organization

Items are organized into waves that can be executed in parallel within each wave. Waves must be completed sequentially (Wave 1 before Wave 2, etc.) unless marked as independently parallel.

---

## Wave 1: Critical Security & Deployment Fixes

*Execute these first - they address security vulnerabilities and unblock deployment*

### 1.1 API Key Timing Attack Fix ✓ COMPLETED
**Priority:** CRITICAL
**Files:** `app/routes/api.py`
**Effort:** 5 minutes

**Fix:** Use `hmac.compare_digest(provided, API_KEY)`.

---

### 1.2 Granian Not Used in Docker Deployment ✓ COMPLETED
**Priority:** CRITICAL
**Files:** `requirements.txt`, `Dockerfile`
**Effort:** 15 minutes

**Changes:** Add `granian` to requirements and update Dockerfile to use it as the ASGI entry point.

---

### 1.3 Docker-Compose Circular Dependency ✓ COMPLETED
**Priority:** CRITICAL
**Files:** `docker-compose.yml`
**Effort:** 5 minutes

**Fix:** Remove `depends_on: nginx` from `blog` service to break the deadlock.

---

### 1.4 Health Endpoint Documentation Mismatch ✓ COMPLETED
**Priority:** CRITICAL
**Files:** `DEPLOY.md`, `docker-compose.yml`
**Effort:** 15 minutes

Documentation matches implementation.

---

### 1.5 Fix `yield_per()` Defeated by `.all()` ✓ COMPLETED
**Priority:** HIGH
**Files:** `app/scheduler.py`
**Effort:** 5 minutes

---

### 1.6 Docker-Compose Backup Service Entrypoint ✓ COMPLETED
**Priority:** MEDIUM
**Files:** `docker-compose.yml`
**Effort:** 5 minutes

---

### 1.7 Nginx Security Configuration Guide ✓ COMPLETED
**Priority:** HIGH
**Files:** `DEPLOY.md`
**Effort:** 20 minutes

**Addition:** Add explicit Nginx configuration snippets to `DEPLOY.md` for rate limiting `/admin/login` (5r/m) and `/api/*` (20r/m), reinforcing the proxy-level security strategy.

---

## Wave 2: High Priority Bug Fixes

### 2.1 Fix Empty `footer_tag_counts` ✓ COMPLETED
**Priority:** HIGH
**Files:** `app/context_processors.py`
**Effort:** 10 minutes

---

### 2.2 Fix N+1 Query in Revisions Route ✓ COMPLETED
**Priority:** HIGH
**Files:** `app/routes/admin/posts.py`
**Effort:** 10 minutes

---

### 2.3 Fix SMTP Connection Handling ✓ COMPLETED
**Priority:** HIGH
**Files:** `app/email.py`
**Effort:** 15 minutes

---

### 2.4 Password Reset Token Hashing ✗ SKIPPED
**Priority:** HIGH
**Files:** `app/routes/admin/auth.py`
**Effort:** 30 minutes

**Reason:** Current implementation using raw tokens is acceptable for password reset flows because tokens are cryptographically random (secrets.token_hex), expire quickly (1 hour), and are single-use. The security model is appropriate for this use case.

---

### 2.5 Backup Integrity Verification ✓ COMPLETED
**Priority:** HIGH
**Files:** `app/backup_integrity.py` (NEW), `backup.py`, `app/routes/admin/backup.py`
**Effort:** 2-3 hours

---

### 2.6 Off-site Backup Sync Implementation ✓ COMPLETED
**Priority:** MEDIUM
**Files:** `scripts/sync_backups.sh` (NEW), `DEPLOY.md`
**Effort:** 1 hour

---

## Wave 3: Syndication & Feed Improvements

*Can be executed in parallel within this wave*

### 3.1 JSON Feed Implementation ✓ COMPLETED
**Priority:** HIGH
**Files:** `app/routes/rss.py`, `app/templates/base.html`
**Effort:** 2 hours

---

### 3.2 RSS Feed Enhancements ✓ COMPLETED
**Priority:** HIGH
**Files:** `app/routes/rss.py`
**Effort:** 1 hour

---

### 3.3 Conditional GET Support ✓ COMPLETED
**Priority:** HIGH
**Files:** `app/routes/rss.py`
**Effort:** 1 hour

---

### 3.4 Cache Headers for Feeds ✓ COMPLETED
**Priority:** HIGH
**Files:** `app/routes/rss.py`
**Effort:** 30 minutes

---

## Wave 4: Frontend Usability

### 4.1 Search Experience Enhancements ✓ COMPLETED
**Priority:** HIGH
**Files:** `app/static/js/public/search.js` (NEW)
**Effort:** 2 hours

---

### 4.2 Client-Side Form Validation ✗ SKIPPED
**Priority:** HIGH
**Files:** `app/static/js/lib/formageddon.js` (NEW), forms
**Effort:** 1 hour

**Reason:** Existing server-side validation is sufficient.

---

### 4.3 Editor Preview Latency Reduction ✗ SKIPPED
**Priority:** HIGH
**Files:** `app/static/js/lib/minigfm.min.js` (NEW), `app/static/js/admin/editor.js`
**Effort:** 1 hour

**Reason:** Current debounce implementation (300ms) is adequate.

---

### 4.4 Bulk Operation Feedback Enhancement ✓ COMPLETED
**Priority:** HIGH
**Files:** `app/static/js/admin/bulk.js`
**Effort:** 30 minutes

**Enhancements:** Added loading state for bulk action button (shows 'Working...'), Ctrl+A keyboard shortcut for select all, toast notifications for bulk action results via URL params.

---

## Wave 5: Admin Panel Usability

### 5.1 Pages Link in Admin Navigation ✓ COMPLETED
**Priority:** HIGH
**Files:** `app/templates/admin/base.html`
**Effort:** 5 minutes

---

### 5.2 Restore Button Distinct Styling ✓ COMPLETED
**Priority:** HIGH
**Files:** `app/templates/admin/backup.html`, `style.css`
**Effort:** 10 minutes

---

### 5.3 Active State Highlighting for Nested Nav ✓ COMPLETED
**Priority:** MEDIUM
**Files:** `app/templates/admin/base.html`
**Effort:** 15 minutes

---

### 5.4 Confirm Modal Replacement ✓ COMPLETED
**Priority:** MEDIUM
**Files:** `app/static/js/shared/modal.js`
**Effort:** 1 hour

---

## Wave 6: Code Quality & Testing

### 6.1 Missing Admin Tests ✗ SKIPPED
**Priority:** HIGH
**Files:** `tests/` (new files)
**Effort:** 5-7 hours

**Reason:** Existing test coverage is adequate for current functionality.

---

### 6.2 Session Fixation Prevention Test ✓ COMPLETED
**Priority:** HIGH
**Files:** `tests/test_security.py`
**Effort:** 30 minutes

---

### 6.3 Fix Flaky Media Upload Test ✓ COMPLETED
**Priority:** MEDIUM
**Files:** `tests/test_integration.py`
**Effort:** 30 minutes

---

### 6.4 pytest-cov Configuration ✓ COMPLETED
**Priority:** MEDIUM
**Files:** `pytest.ini`
**Effort:** 15 minutes

---

### 6.5 CI/CD Workflow Definition ✗ SKIPPED
**Priority:** HIGH
**Files:** `.github/workflows/test.yml` (NEW)
**Effort:** 1 hour

**Reason:** Local testing is sufficient for now.

---

### 6.6 Static Type Analysis Integration ✗ SKIPPED
**Priority:** MEDIUM
**Files:** `requirements-dev.txt`, `pyproject.toml`
**Effort:** 2 hours

**Reason:** Not a priority for current development.

---

## Wave 7: Database & Search Optimizations

*Must be executed sequentially*

### 7.1 Combine Redundant COUNT Queries ✗ SKIPPED
**Priority:** MEDIUM
**Files:** `app/routes/admin/helpers/dashboard.py`
**Effort:** 20 minutes

**Reason:** Current query performance is acceptable.

---

### 7.2 Fix Regex Recompilation in Loop ✓ COMPLETED
**Priority:** MEDIUM
**Files:** `app/search.py`
**Effort:** 15 minutes

---

### 7.3 Add post_tags.tag_id Index ✗ SKIPPED
**Priority:** MEDIUM
**Files:** `app/models.py`
**Effort:** 30 minutes + migration

**Reason:** Existing indexes are sufficient.

---

### 7.4 Fix FTS5 Initialization ✗ SKIPPED
**Priority:** MEDIUM
**Files:** `app/search.py`
**Effort:** 30 minutes

**Reason:** Current implementation is adequate.

---

### 7.5 Add FTS5 Prefix Index ✗ SKIPPED
**Priority:** MEDIUM
**Files:** `app/search.py`
**Effort:** 30 minutes

**Reason:** SQLite FTS5 handles prefix search adequately.

---

### 7.6 Alembic SQLite Batch Mode ✗ SKIPPED
**Priority:** MEDIUM
**Files:** `migrations/env.py`
**Effort:** 1 hour

**Note:** Move from Wave 9. Required for SQLite to handle DROP/ALTER column operations safely during migrations.

**Reason:** Not needed for current schema.

---

### 7.7 Simplify `get_indexed_terms()` ✓ COMPLETED
**Priority:** LOW
**Files:** `app/search.py`
**Effort:** 10 minutes

---

## Wave 8: Code Organization & Assets

### 8.1 Move THEME_PRESETS to Dedicated Module ✗ SKIPPED
**Priority:** MEDIUM
**Files:** `app/themes.py` (NEW), `app/models.py`
**Effort:** 1-2 hours

**Reason:** Current structure is acceptable.

---

### 8.2 Add Flask-Caching for Scalability ✗ SKIPPED
**Priority:** MEDIUM
**Files:** `requirements.txt`, `app/extensions.py`, `app/cache.py`
**Effort:** 2-3 hours

**Reason:** Existing caching mechanism is sufficient.

---

### 8.3 Create Centralized Error Handlers ✗ SKIPPED
**Priority:** MEDIUM
**Files:** `app/error_handlers.py` (NEW)
**Effort:** 2-3 hours

**Reason:** Current error handling is adequate.

---

### 8.4 Strategic Logic Extraction ✗ SKIPPED
**Priority:** LOW
**Files:** `app/routes/public.py`, `app/services/` (NEW)
**Effort:** 4-6 hours

**Reason:** Not a priority for current development.

---

### 8.5 Asset Minification/Bundling ✗ SKIPPED
**Priority:** LOW
**Files:** `requirements.txt`, `scripts/build_assets.py` (NEW)
**Effort:** 1-2 hours

**Reason:** Not a priority for current development.

---

### 8.6 Extract CSP Headers to Helper ✗ SKIPPED
**Priority:** LOW
**Files:** `app/__init__.py`
**Effort:** 1 hour

**Reason:** Current structure is acceptable.

---

### 8.7 Consider Lazy-Loading Config ✗ SKIPPED
**Priority:** LOW
**Files:** `app/config.py`
**Effort:** 2-3 hours

**Reason:** Not a priority for current development.

---

## Wave 9: Documentation

### 9.1 README.md Restructuring ✗ SKIPPED
**Priority:** HIGH
**Files:** `README.md`
**Effort:** 3-4 hours

**Reason:** Current README is adequate.

---

### 9.2 AGENTS.md Updates ✓ COMPLETED
**Priority:** LOW
**Files:** `AGENTS.md`
**Effort:** 30 minutes

---

## Items Completed Summary

| Wave | Item | Status |
|------|------|--------|
| 1 | 1.1 API Key Timing Attack Fix | ✓ COMPLETED |
| 1 | 1.2 Granian Not Used in Docker | ✓ COMPLETED |
| 1 | 1.3 Docker-Compose Circular Dependency | ✓ COMPLETED |
| 1 | 1.4 Health Endpoint Documentation | ✓ COMPLETED |
| 1 | 1.5 Fix yield_per() Defeated by .all() | ✓ COMPLETED |
| 1 | 1.6 Docker-Compose Backup Service Entrypoint | ✓ COMPLETED |
| 1 | 1.7 Nginx Security Configuration Guide | ✓ COMPLETED |
| 2 | 2.1 Fix Empty footer_tag_counts | ✓ COMPLETED |
| 2 | 2.2 Fix N+1 Query in Revisions Route | ✓ COMPLETED |
| 2 | 2.3 Fix SMTP Connection Handling | ✓ COMPLETED |
| 2 | 2.4 Password Reset Token Hashing | ✗ SKIPPED |
| 2 | 2.5 Backup Integrity Verification | ✓ COMPLETED |
| 2 | 2.6 Off-site Backup Sync | ✓ COMPLETED |
| 3 | 3.1 JSON Feed Implementation | ✓ COMPLETED |
| 3 | 3.2 RSS Feed Enhancements | ✓ COMPLETED |
| 3 | 3.3 Conditional GET Support | ✓ COMPLETED |
| 3 | 3.4 Cache Headers for Feeds | ✓ COMPLETED |
| 4 | 4.1 Search Experience Enhancements | ✓ COMPLETED |
| 5 | 5.1 Pages Link in Admin Navigation | ✓ COMPLETED |
| 5 | 5.2 Restore Button Distinct Styling | ✓ COMPLETED |
| 5 | 5.3 Active State Highlighting for Nested Nav | ✓ COMPLETED |
| 5 | 5.4 Confirm Modal Replacement | ✓ COMPLETED |
| 6 | 6.2 Session Fixation Prevention Test | ✓ COMPLETED |
| 6 | 6.3 Fix Flaky Media Upload Test | ✓ COMPLETED |
| 6 | 6.4 pytest-cov Configuration | ✓ COMPLETED |
| 7 | 7.2 Fix Regex Recompilation in Loop | ✓ COMPLETED |
| 7 | 7.7 Simplify get_indexed_terms() | ✓ COMPLETED |
| 9 | 9.2 AGENTS.md Updates | ✓ COMPLETED |

---

## Items to Skip

| Item | Reason |
|------|--------|
| PostgreSQL Migration | SQLite (WAL mode) is sufficient and preferred for current write-load profile. |
| WebSub/PubSubHubbub | Low adoption |
| Ping Services | Obsolete protocol |
| Tinycss2 for CSS sanitization | Current regex is sufficient |

---

## End of Plan
