# Improvement Plan

**Date:** 2026-04-28
**Status:** Active - Work not yet started
**Source:** Consolidated Master Plan

---

## Verification Status

- 487 tests pass (1 known flaky media upload test)
- All items below are unverified unless marked as already present in codebase

---

## Wave Organization

Items are organized into waves that can be executed in parallel within each wave. Waves must be completed sequentially (Wave 1 before Wave 2, etc.) unless marked as independently parallel.

---

## Wave 1: Critical Security & Deployment Fixes

*Execute these first - they address security vulnerabilities and unblock deployment*

### 1.1 API Key Timing Attack Fix
**Priority:** CRITICAL
**Files:** `app/routes/api.py`
**Effort:** 5 minutes

**Problem:** Line 32 uses `provided != API_KEY` which is vulnerable to timing attack. Python's `!=` short-circuits on first mismatched character.

**Fix:** Use `hmac.compare_digest(provided, API_KEY)`.

---

### 1.2 Granian Not Used in Docker Deployment
**Priority:** CRITICAL
**Files:** `requirements.txt`, `Dockerfile`
**Effort:** 15 minutes

**Changes:** Add `granian` to requirements and update Dockerfile to use it as the ASGI entry point.

---

### 1.3 Docker-Compose Circular Dependency
**Priority:** CRITICAL
**Files:** `docker-compose.yml`
**Effort:** 5 minutes

**Fix:** Remove `depends_on: nginx` from `blog` service to break the deadlock.

---

### 1.4 Health Endpoint Documentation Mismatch
**Priority:** CRITICAL
**Files:** `DEPLOY.md`, `docker-compose.yml`
**Effort:** 15 minutes

---

### 1.5 Fix `yield_per()` Defeated by `.all()`
**Priority:** HIGH
**Files:** `app/scheduler.py`
**Effort:** 5 minutes

---

### 1.6 Docker-Compose Backup Service Entrypoint
**Priority:** MEDIUM
**Files:** `docker-compose.yml`
**Effort:** 5 minutes

---

### 1.7 Nginx Security Configuration Guide
**Priority:** HIGH
**Files:** `DEPLOY.md`
**Effort:** 20 minutes

**Addition:** Add explicit Nginx configuration snippets to `DEPLOY.md` for rate limiting `/admin/login` (5r/m) and `/api/*` (20r/m), reinforcing the proxy-level security strategy.

---

## Wave 2: High Priority Bug Fixes

### 2.1 Fix Empty `footer_tag_counts`
**Priority:** HIGH
**Files:** `app/context_processors.py`
**Effort:** 10 minutes

---

### 2.2 Fix N+1 Query in Revisions Route
**Priority:** HIGH
**Files:** `app/routes/admin/posts.py`
**Effort:** 10 minutes

---

### 2.3 Fix SMTP Connection Handling
**Priority:** HIGH
**Files:** `app/email.py`
**Effort:** 15 minutes

---

### 2.4 Password Reset Token Hashing
**Priority:** HIGH
**Files:** `app/routes/admin/auth.py`
**Effort:** 30 minutes

---

### 2.5 Backup Integrity Verification
**Priority:** HIGH
**Files:** `app/backup_integrity.py` (NEW), `backup.py`, `app/routes/admin/backup.py`
**Effort:** 2-3 hours

---

### 2.6 Off-site Backup Sync Implementation
**Priority:** MEDIUM
**Files:** `scripts/sync_backups.sh` (NEW), `DEPLOY.md`
**Effort:** 1 hour

**Implementation:** Create a script using `rclone` or `aws s3 sync` to move backups to remote storage. Add a section to `DEPLOY.md` explaining how to automate this via crontab.

---

## Wave 3: Syndication & Feed Improvements

*Can be executed in parallel within this wave*

### 3.1 JSON Feed Implementation
**Priority:** HIGH
**Files:** `app/routes/rss.py`, `app/templates/base.html`
**Effort:** 2 hours

---

### 3.2 RSS Feed Enhancements
**Priority:** HIGH
**Files:** `app/routes/rss.py`
**Effort:** 1 hour

---

### 3.3 Conditional GET Support
**Priority:** HIGH
**Files:** `app/routes/rss.py`
**Effort:** 1 hour

---

### 3.4 Cache Headers for Feeds
**Priority:** HIGH
**Files:** `app/routes/rss.py`
**Effort:** 30 minutes

---

## Wave 4: Frontend Usability

### 4.1 Search Experience Enhancements
**Priority:** HIGH
**Files:** `app/search.py`, `app/routes/public.py`, `app/static/js/public/search.js` (NEW)
**Effort:** 2 hours

---

### 4.2 Client-Side Form Validation
**Priority:** HIGH
**Files:** `app/static/js/lib/formageddon.js` (NEW), forms
**Effort:** 1 hour

---

### 4.3 Editor Preview Latency Reduction
**Priority:** HIGH
**Files:** `app/static/js/lib/minigfm.min.js` (NEW), `app/static/js/admin/editor.js`
**Effort:** 1 hour

---

### 4.4 Bulk Operation Feedback Enhancement
**Priority:** HIGH
**Files:** `app/static/js/admin/bulk.js`
**Effort:** 30 minutes

---

## Wave 5: Admin Panel Usability

### 5.1 Pages Link in Admin Navigation
**Priority:** HIGH
**Files:** `app/templates/admin/base.html`
**Effort:** 5 minutes

---

### 5.2 Restore Button Distinct Styling
**Priority:** HIGH
**Files:** `app/templates/admin/backup.html`, `style.css`
**Effort:** 10 minutes

---

### 5.3 Active State Highlighting for Nested Nav
**Priority:** MEDIUM
**Files:** `app/templates/admin/base.html`
**Effort:** 15 minutes

---

### 5.4 Confirm Modal Replacement
**Priority:** MEDIUM
**Files:** `app/static/js/shared/modal.js`
**Effort:** 1 hour

---

## Wave 6: Code Quality & Testing

### 6.1 Missing Admin Tests
**Priority:** HIGH
**Files:** `tests/` (new files)
**Effort:** 5-7 hours

---

### 6.2 Session Fixation Prevention Test
**Priority:** HIGH
**Files:** `tests/test_auth.py`
**Effort:** 30 minutes

---

### 6.3 Fix Flaky Media Upload Test
**Priority:** MEDIUM
**Files:** `tests/test_media.py`
**Effort:** 30 minutes

---

### 6.4 pytest-cov Configuration
**Priority:** MEDIUM
**Files:** `pytest.ini`
**Effort:** 15 minutes

---

### 6.5 CI/CD Workflow Definition
**Priority:** HIGH
**Files:** `.github/workflows/test.yml` (NEW)
**Effort:** 1 hour

**Implementation:** Create GitHub Actions workflow to run `pytest` and `ruff check` on every push/PR.

---

### 6.6 Static Type Analysis Integration
**Priority:** MEDIUM
**Files:** `requirements-dev.txt`, `pyproject.toml`
**Effort:** 2 hours

**Implementation:** Add `mypy` to dev requirements and configure basic type checking for the `app/` directory to catch potential runtime errors.

---

## Wave 7: Database & Search Optimizations

*Must be executed sequentially*

### 7.1 Combine Redundant COUNT Queries
**Priority:** MEDIUM
**Files:** `app/routes/admin/helpers/dashboard.py`
**Effort:** 20 minutes

---

### 7.2 Fix Regex Recompilation in Loop
**Priority:** MEDIUM
**Files:** `app/search.py`
**Effort:** 15 minutes

---

### 7.3 Add post_tags.tag_id Index
**Priority:** MEDIUM
**Files:** `app/models.py`
**Effort:** 30 minutes + migration

---

### 7.4 Fix FTS5 Initialization
**Priority:** MEDIUM
**Files:** `app/search.py`
**Effort:** 30 minutes

---

### 7.5 Add FTS5 Prefix Index
**Priority:** MEDIUM
**Files:** `app/search.py`
**Effort:** 30 minutes

---

### 7.6 Alembic SQLite Batch Mode
**Priority:** MEDIUM
**Files:** `migrations/env.py`
**Effort:** 1 hour

**Note:** Move from Wave 9. Required for SQLite to handle DROP/ALTER column operations safely during migrations.

---

### 7.7 Simplify `get_indexed_terms()`
**Priority:** LOW
**Files:** `app/search.py`
**Effort:** 10 minutes

---

## Wave 8: Code Organization & Assets

### 8.1 Move THEME_PRESETS to Dedicated Module
**Priority:** MEDIUM
**Files:** `app/themes.py` (NEW), `app/models.py`
**Effort:** 1-2 hours

---

### 8.2 Add Flask-Caching for Scalability
**Priority:** MEDIUM
**Files:** `requirements.txt`, `app/extensions.py`, `app/cache.py`
**Effort:** 2-3 hours

---

### 8.3 Create Centralized Error Handlers
**Priority:** MEDIUM
**Files:** `app/error_handlers.py` (NEW)
**Effort:** 2-3 hours

---

### 8.4 Strategic Logic Extraction
**Priority:** LOW
**Files:** `app/routes/public.py`, `app/services/` (NEW)
**Effort:** 4-6 hours

**Refinement:** Instead of just splitting `public.py` by route, extract complex business logic (e.g., search term processing, subscription validation) into a new `app/services/` layer to improve testability and reduce route handler size.

---

### 8.5 Asset Minification/Bundling
**Priority:** LOW
**Files:** `requirements.txt`, `scripts/build_assets.py` (NEW)
**Effort:** 1-2 hours

---

### 8.6 Extract CSP Headers to Helper
**Priority:** LOW
**Files:** `app/__init__.py`
**Effort:** 1 hour

---

### 8.7 Consider Lazy-Loading Config
**Priority:** LOW
**Files:** `app/config.py`
**Effort:** 2-3 hours

---

## Wave 9: Documentation

### 9.1 README.md Restructuring
**Priority:** HIGH
**Files:** `README.md`
**Effort:** 3-4 hours

---

### 9.2 AGENTS.md Updates
**Priority:** LOW
**Files:** `AGENTS.md`
**Effort:** 30 minutes

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
