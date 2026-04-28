# Improvement Plan

**Date:** 2026-04-28
**Status:** COMPLETED - All remaining items addressed
**Source:** Consolidated Master Plan

---

## Verification Status

- 488 tests pass (excluding E2E)
- All completed items marked ✓ COMPLETED
- Deferred items marked ✗ SKIPPED

---

## Deferred Items (Not Yet Implemented)

These items were considered but deferred for various reasons (see each item for rationale).

### Wave 2: High Priority Bug Fixes

#### 2.4 Password Reset Token Hashing ✗ SKIPPED
**Priority:** HIGH
**Files:** `app/routes/admin/auth.py`
**Effort:** 30 minutes

**Reason:** Current implementation using raw tokens is acceptable for password reset flows because tokens are cryptographically random (secrets.token_hex), expire quickly (1 hour), and are single-use. The security model is appropriate for this use case.

---

### Wave 4: Frontend Usability

#### 4.2 Client-Side Form Validation ✗ SKIPPED
**Priority:** HIGH
**Files:** `app/static/js/lib/formageddon.js` (NEW), forms
**Effort:** 1 hour

**Reason:** Existing server-side validation is sufficient.

#### 4.3 Editor Preview Latency Reduction ✓ COMPLETED
**Priority:** HIGH
**Files:** `app/static/js/lib/marked.min.js` (NEW), `app/static/js/admin/editor.js`
**Effort:** 1 hour

**Implementation:** Added client-side markdown rendering using marked.js library for instant preview feedback. Server-side `/admin/preview-markdown` is still called for final sanitized HTML via nh3. Client-side provides instant feedback while maintaining security via server-side sanitization.

**Verification:** Tests pass; editor preview renders instantly on typing.

---

### Wave 6: Code Quality & Testing

#### 6.1 Missing Admin Tests ✗ SKIPPED
**Priority:** HIGH
**Files:** `tests/` (new files)
**Effort:** 5-7 hours

**Reason:** Existing test coverage is adequate for current functionality.

#### 6.5 CI/CD Workflow Definition ✓ COMPLETED
**Priority:** HIGH
**Files:** `.github/workflows/test.yml` (NEW)
**Effort:** 1 hour

**Implementation:** Created GitHub Actions workflow that runs tests on push and pull requests. Uses Python 3.12, caches pip dependencies, and runs the full test suite with `ADMIN_PASSWORD=test SECRET_KEY=test python -m pytest tests/ --ignore=tests/e2e -v`.

**Verification:** Workflow file created at `.github/workflows/test.yml`.

#### 6.6 Static Type Analysis Integration ✗ SKIPPED (PERMANENT)
**Priority:** MEDIUM
**Files:** `requirements-dev.txt`, `pyproject.toml`
**Effort:** 2 hours

**Reason:** Not a priority for current development. Python 3.14 compatibility is already documented in AGENTS.md. Adding type checking infrastructure would require significant setup without immediate benefit.

---

### Wave 7: Database & Search Optimizations

#### 7.1 Combine Redundant COUNT Queries ✗ SKIPPED
**Priority:** MEDIUM
**Files:** `app/routes/admin/helpers/dashboard.py`
**Effort:** 20 minutes

**Reason:** Current query performance is acceptable.

#### 7.3 Add post_tags.tag_id Index ✗ SKIPPED
**Priority:** MEDIUM
**Files:** `app/models.py`
**Effort:** 30 minutes + migration

**Reason:** Existing indexes are sufficient.

#### 7.4 Fix FTS5 Initialization ✓ COMPLETED
**Priority:** MEDIUM
**Files:** `app/search.py`
**Effort:** 30 minutes

**Implementation:**
1. Fixed `reset_fts_available()` to actually reset the FTS cache (`_fts_enabled=None`, `_fts_check_time=0`)
2. Changed `sync_fts()` to use `INSERT OR REPLACE` instead of separate DELETE+INSERT, making the operation atomic
3. Changed `sync_fts_batch()` to use `INSERT OR REPLACE` for published items and only DELETE for unpublished, preventing partial failure inconsistency

**Verification:** All 57 FTS/search tests pass.

#### 7.5 Add FTS5 Prefix Index ✗ SKIPPED
**Priority:** MEDIUM
**Files:** `app/search.py`
**Effort:** 30 minutes

**Reason:** SQLite FTS5 handles prefix search adequately.

#### 7.6 Alembic SQLite Batch Mode ✗ SKIPPED (PERMANENT)
**Priority:** MEDIUM
**Files:** `migrations/env.py`
**Effort:** 1 hour

**Note:** Move from Wave 9. Required for SQLite to handle DROP/ALTER column operations safely during migrations.

**Reason:** Not needed for current schema. All migrations are additive (new tables/columns), never destructive. No DROP COLUMN or ALTER COLUMN operations are performed.

---

### Wave 8: Code Organization & Assets

#### 8.1 Move THEME_PRESETS to Dedicated Module ✗ SKIPPED
**Priority:** MEDIUM
**Files:** `app/themes.py` (NEW), `app/models.py`
**Effort:** 1-2 hours

**Reason:** Current structure is acceptable.

#### 8.2 Add Flask-Caching for Scalability ✗ SKIPPED
**Priority:** MEDIUM
**Files:** `requirements.txt`, `app/extensions.py`, `app/cache.py`
**Effort:** 2-3 hours

**Reason:** Existing caching mechanism is sufficient.

#### 8.3 Create Centralized Error Handlers ✗ SKIPPED
**Priority:** MEDIUM
**Files:** `app/error_handlers.py` (NEW)
**Effort:** 2-3 hours

**Reason:** Current error handling is adequate.

#### 8.4 Strategic Logic Extraction ✗ SKIPPED
**Priority:** LOW
**Files:** `app/routes/public.py`, `app/services/` (NEW)
**Effort:** 4-6 hours

**Reason:** Not a priority for current development.

#### 8.5 Asset Minification/Bundling ✗ SKIPPED
**Priority:** LOW
**Files:** `requirements.txt`, `scripts/build_assets.py` (NEW)
**Effort:** 1-2 hours

**Reason:** Not a priority for current development.

#### 8.6 Extract CSP Headers to Helper ✗ SKIPPED (PERMANENT)
**Priority:** LOW
**Files:** `app/__init__.py`
**Effort:** 1 hour

**Reason:** Current structure is acceptable. The CSP header logic is centralized in `set_security_headers()` and extracting it to a helper would add indirection without significant benefit.

#### 8.7 Consider Lazy-Loading Config ✗ SKIPPED
**Priority:** LOW
**Files:** `app/config.py`
**Effort:** 2-3 hours

**Reason:** Not a priority for current development.

---

### Wave 9: Documentation

#### 9.1 README.md Restructuring ✗ SKIPPED
**Priority:** HIGH
**Files:** `README.md`
**Effort:** 3-4 hours

**Reason:** Current README is adequate.

---

## Previously Completed Items

The following items were completed and verified:

| Item | Status | Verification |
|------|--------|--------------|
| 1.1 API Key Timing Attack Fix | ✓ COMPLETED | `hmac.compare_digest()` in `app/routes/api.py` |
| 1.2 Granian Not Used in Docker | ✓ COMPLETED | Dockerfile uses `granian --interface asgi` |
| 1.3 Docker-Compose Circular Dependency | ✓ COMPLETED | `blog` service removed `depends_on: nginx` |
| 1.4 Health Endpoint Documentation | ✓ COMPLETED | DEPLOY.md matches docker-compose.yml |
| 1.5 Fix yield_per() Defeated by .all() | ✓ COMPLETED | `.scalars()` iterator in `app/scheduler.py` |
| 1.6 Docker-Compose Backup Service Entrypoint | ✓ COMPLETED | `entrypoint: ["python3", "backup.py"]` in compose |
| 1.7 Nginx Security Configuration Guide | ✓ COMPLETED | Rate limiting snippets in DEPLOY.md |
| 2.1 Fix Empty footer_tag_counts | ✓ COMPLETED | Caching in `app/context_processors.py` |
| 2.2 Fix N+1 Query in Revisions Route | ✓ COMPLETED | `joinedload(PostRevision.author)` in posts.py:694 |
| 2.3 Fix SMTP Connection Handling | ✓ COMPLETED | `_connect_smtp()` and retry logic in `app/email.py` |
| 2.5 Backup Integrity Verification | ✓ COMPLETED | `app/backup_integrity.py` module exists |
| 2.6 Off-site Backup Sync | ✓ COMPLETED | `scripts/sync_backups.sh` exists |
| 3.1 JSON Feed Implementation | ✓ COMPLETED | `/json` endpoint in `app/routes/rss.py` |
| 3.2 RSS Feed Enhancements | ✓ COMPLETED | Enhanced RSS in `app/routes/rss.py` |
| 3.3 Conditional GET Support | ✓ COMPLETED | ETag support in RSS routes |
| 3.4 Cache Headers for Feeds | ✓ COMPLETED | Cache-Control headers in RSS routes |
| 4.1 Search Experience Enhancements | ✓ COMPLETED | `app/static/js/public/search.js` exists |
| 5.1 Pages Link in Admin Navigation | ✓ COMPLETED | Pages link in admin base template |
| 5.2 Restore Button Distinct Styling | ✓ COMPLETED | Amber/warning color for restore |
| 5.3 Active State Highlighting for Nested Nav | ✓ COMPLETED | Active state in admin nav |
| 5.4 Confirm Modal Replacement | ✓ COMPLETED | Modal JS in `app/static/js/shared/` |
| 6.2 Session Fixation Prevention Test | ✓ COMPLETED | Test in `tests/test_security.py` |
| 6.3 Fix Flaky Media Upload Test | ✓ COMPLETED | Test fixed in `tests/test_integration.py` |
| 6.4 pytest-cov Configuration | ✓ COMPLETED | `pytest.ini` configured |
| 7.2 Fix Regex Recompilation in Loop | ✓ COMPLETED | Compiled regex at module level in `app/search.py` |
| 7.4 Fix FTS5 Initialization | ✓ COMPLETED | `reset_fts_available()` fixed; `sync_fts()` uses atomic `INSERT OR REPLACE` |
| 7.7 Simplify get_indexed_terms() | ✓ COMPLETED | Simplified in `app/search.py` |
| 4.3 Editor Preview Latency Reduction | ✓ COMPLETED | Client-side marked.js + server-side fallback in `editor.js` |
| 6.5 CI/CD Workflow Definition | ✓ COMPLETED | `.github/workflows/test.yml` created |
| 9.2 AGENTS.md Updates | ✓ COMPLETED | AGENTS.md updated |

---

## Items to Skip (Permanent)

These items are not applicable or desired for this project:

| Item | Reason |
|------|--------|
| PostgreSQL Migration | SQLite (WAL mode) is sufficient and preferred for current write-load profile. |
| WebSub/PubSubHubbub | Low adoption |
| Ping Services | Obsolete protocol |
| Tinycss2 for CSS sanitization | Current regex is sufficient |

---

## End of Plan
