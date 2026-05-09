# Implementation Plan - Consolidated

**Project:** Blog CMS
**Status:** Active
**Last Updated:** May 2026

---

## Overview

This plan consolidates items from architecture review batches and existing Waves A-E (completed).
New items are organized into waves F-I by priority: Security bugs first, then functional bugs, then code quality, then documentation, then enhancements.

---

## Part 1: Completed Waves (Reference)

| Wave | Description | Status |
|------|-------------|--------|
| A | 2FA Security (TOTP + Backup Codes) | COMPLETED |
| B | Rate Limiting Infrastructure | COMPLETED |
| C | Search Infrastructure (PostgreSQL) | COMPLETED |
| D | Frontend Enhancements (Vite + AVIF) | COMPLETED |
| E | Performance (Brotli) | COMPLETED |

---

## Part 2: Wave F - Bug Fixes (Security & Functional)

**Priority:** HIGH - Security issues and functional bugs
**Items:** 12

### Wave F Execution Order

Items marked with ★ have dependencies and should run after their dependency completes.
Items marked with ● can run in parallel with other F items.

| Order | Item | Dependencies | Parallel Group |
|-------|------|--------------|---------------|
| 1 | F.1 | None | A - Security |
| 2 | F.2 | None | A - Functional |
| 3 | F.3 | None | A - Functional |
| 4 | F.4 | None | A - Functional |
| 5 | F.5 | None | A - Functional |
| 6 | F.6 | None | A - Infrastructure |
| 7 | F.11 | None | A - Security |
| 8 | F.12 | None | A - Frontend |
| 9 | F.7 | None | B - Testing |
| 10 | F.8 | None | B - CI/CD |
| 11 | F.9 | None | B - CI/CD |
| 12 | F.10 | None | B - Docker |

---

### F.1: Preview Route Security Bypass
**File:** `app/routes/public/posts.py:94-140`
**Severity:** HIGH (Security)
**Issue:** The public preview route (`/preview/<int:post_id>`) validates an HMAC-signed token but does NOT verify that the user requesting the preview has any relationship to the post. Any valid HMAC signature with a post ID grants access to ANY post including drafts.
**Fix:** Add admin session verification OR store preview tokens in database with post association. Require that the current user either authored the post or is an admin.
**Implementation Details:**
- The route validates HMAC signature using `hmac.new(secret_key, f"{post_id}:{expires}", hashlib.sha256)`
- Token and expiry are passed as query params: `?token=<b64>&expires=<timestamp>`
- No session or authentication check occurs after token validation
- Any user with the app's SECRET_KEY could generate valid preview URLs for draft posts
**Solution Approach:**
Option A (Recommended): Add admin session check - if `session.get('admin_user_id')` exists, allow access. Otherwise deny.
Option B: Store preview tokens in `preview_tokens` table with `post_id` and `created_at`, require matching token.
**Dependencies:** None
**Verification:** After fix, draft post preview URLs should return 403 for unauthenticated users without valid tokens tied to that specific post.

---

### F.2: APScheduler Backup Retention Never Runs
**File:** `app/services/backup.py:132-133`
**Severity:** HIGH (Functional)
**Issue:** `cleanup_old_backups()` filters with `f.startswith("blog_")` but `run_daily_backup()` creates `backup_*.db` files. Result: APScheduler backups are never cleaned up, backup directory grows indefinitely.
**Fix:** Change `cleanup_old_backups()` to also match `backup_*.db` files OR change `run_daily_backup()` to use `blog_*.db` naming.
**Implementation Details:**
- Line 132: `if f.startswith("blog_") and (f.endswith(".db") or f.endswith(".db.gz") or f.endswith(".db.gpg")):`
- Line 167: `f"backup_{timestamp}.db"` - APScheduler uses different naming
- Celery task `run_backup_task` uses `blog_*.db` naming (line 45)
**Recommendation:** Align `run_daily_backup()` to use `blog_*.db` naming to match Celery task convention. This ensures consistent retention policy.
**Code Location for Fix:** `app/services/backup.py:167` - change `f"backup_{timestamp}.db"` to `f"blog_{timestamp}.db"`
**Dependencies:** None

---

### F.3: Prism Loading Hardcoded Theme
**File:** `app/static/js/main.js:97-112`
**Severity:** MEDIUM (Functional)
**Issue:** Prism syntax highlighting loads hardcoded `prism-okaidia.css`, ignoring `syntax_theme` setting. JS files loaded directly from `/static/` bypassing `vite_asset()` - no content hashing.
**Fix:** Pass `syntax_theme` from template context and use `vite_asset()` for hashed filenames.
**Implementation Details:**
- Currently line 102: `prismCSS.href = '/static/css/prism-okaidia.css';` (hardcoded)
- Line 90-91: `prism.min.js` loaded directly from `/static/`
- Template context already has `syntax_theme` available via `inject_theme()`
- Vite asset manifest available via `app/vite.py:47-77`
**Steps:**
1. Pass `syntax_theme` to template (already available in context)
2. In `main.js`, read `document.body.dataset.syntaxTheme` or pass via template variable
3. Use `import.meta.glob` to dynamically import correct theme CSS
4. Replace direct `/static/` links with Vite-hashed asset paths
**Dependencies:** `syntax_theme` setting exists in theme config

---

### F.4: Silent Failure in Webhook Event Queuing
**File:** `app/webhooks.py:97-101`
**Severity:** HIGH (Functional - Silent Failure)
**Issue:** Currently swallows all failures silently with `pass`. If Celery is down, events are created in DB but never delivered with no error indication.
**Fix:**
```python
except (RequestException, ValueError, OSError) as e:
    logger.error("Failed to queue webhook event %d for delivery: %s", event_id, e)
```
**Code Location:** `app/webhooks.py:97-101`
**Current Code:**
```python
try:
    from app.tasks import deliver_webhook_task
    deliver_webhook_task.delay(event_id)
except (RequestException, ValueError, OSError):
    pass
```
**Dependencies:** Celery infrastructure for logging

---

### F.5: Broad Exception in Backup Task
**File:** `app/tasks.py:320`
**Severity:** HIGH (Functional)
**Issue:** Currently catches `Exception` including `KeyboardInterrupt`, `SystemExit`, `CeleryTaskError`. These should not be caught as they indicate critical shutdown situations.
**Fix:** Change to:
```python
except (SQLAlchemyError, OSError, ImportError) as e:
```
**Implementation Details:**
- SQLAlchemyError must be imported from `sqlalchemy.exc`
- The catch should NOT include `CeleryTaskError`, `KeyboardInterrupt`, `SystemExit`
- These exceptions indicate critical shutdown and should propagate
**Dependencies:** SQLAlchemy exceptions must be imported (line 6 already has `from sqlalchemy.exc import SQLAlchemyError`)

---

### F.6: nginx.conf Duplicate HTTP Block
**File:** `nginx/nginx.conf:39`
**Severity:** MEDIUM (Infrastructure)
**Issue:** Second `http {}` block (lines 39-70) overrides first (lines 10-37). Brotli comments in first block are unreachable.
**Fix:** Merge the two `http {}` blocks into one, combining all directives.
**Implementation Details:**
- First block (lines 10-37): contains server config, error_log, pid, commented brotli
- Second block (lines 39-70): contains http directives, sever blocks
- Merge all directives into single http block
- Ensure Brotli configuration is included if enabled
**Dependencies:** None

---

### F.7: Duplicate ensure_buffer_disabled Fixture
**File:** `tests/conftest.py:185-193`, `tests/e2e/conftest.py:11-19`, `tests/benchmarks/conftest.py:10-18`, `tests/test_api.py:12-20`
**Severity:** MEDIUM (Code Quality)
**Issue:** Same 9-line fixture is copied 4 times across test files.
**Fix:** Create `tests/shared_fixtures.py` with the fixture, then import in each conftest.py:
```python
# tests/shared_fixtures.py
import pytest
from app.page_view_buffer import shutdown_page_view_buffer
import app.config as _app_config

@pytest.fixture(autouse=True)
def ensure_buffer_disabled():
    """Ensure page view buffer is disabled during tests."""
    _app_config.PAGE_VIEW_BUFFER_SIZE = 0
    shutdown_page_view_buffer()
    yield
    shutdown_page_view_buffer()
```

Then update each conftest:
```python
from tests.shared_fixtures import ensure_buffer_disabled
```

**Files to Update:**
1. Create `tests/shared_fixtures.py` with the fixture
2. Update `tests/conftest.py` - remove lines 185-193, add import
3. Update `tests/e2e/conftest.py` - remove lines 11-19, add import
4. Update `tests/benchmarks/conftest.py` - remove lines 10-18, add import
5. Update `tests/test_api.py` - remove lines 12-20, add import

**Dependencies:** None

---

### F.8: e2e-tests Redis Health Check Uses Arbitrary Sleep
**File:** `.github/workflows/test.yml:119-124`
**Severity:** MEDIUM (CI/CD)
**Issue:** Currently uses `sleep 2` instead of waiting for redis health. Flaky timing-based test.
**Fix:** Change to use health-based waiting:
```yaml
- name: Start services
  run: docker-compose up -d redis
  wait: redis
```
**Implementation Details:**
- docker-compose.yml:55-62 already defines redis healthcheck
- Replace `sleep 2` with docker-compose wait functionality
- If `wait` subcommand not available, use `healthcheck` with curl/wait-for-it
**Dependencies:** Redis healthcheck already defined in `docker-compose.yml:55-62`

---

### F.9: e2e-tests Missing Production Profile
**File:** `.github/workflows/test.yml:117-124`
**Severity:** MEDIUM (CI/CD)
**Issue:** Currently uses default profile, not production. nginx and celery not started during e2e tests.
**Fix:** Use `docker-compose up -d --profile production`
**Implementation Details:**
- docker-compose.yml has `profiles: ["production"]` on nginx and celery services
- Current workflow: `docker-compose up -d blog` (uses default profile)
- Fix: `docker-compose up -d --profile production` to include nginx and celery
**Dependencies:** Production profile already exists in docker-compose

---

### F.10: Celery Service Missing SMTP Environment
**File:** `docker-compose.yml:34-53`
**Severity:** MEDIUM (Infrastructure)
**Issue:** blog service has SMTP_USER and SMTP_PASSWORD env vars but celery service missing these despite needing them for email tasks.
**Fix:** Add SMTP_USER and SMTP_PASSWORD to celery service environment section.
**Implementation Details:**
- blog service (lines 7-14) has: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
- celery service (lines 34-53) only has: REDIS_URL, SECRET_KEY, PYTHONPATH
- Add the same SMTP variables to celery service environment section
**Dependencies:** None

---

### F.11: Webhook Secret Decryption Failure Handling
**File:** `app/tasks.py:229-233`
**Severity:** HIGH (Security)
**Issue:** If decryption fails, encrypted secret is used directly as HMAC key, producing incorrect signatures without failing closed.
**Fix:** If decryption fails, log error and fail the delivery rather than using secret as-is.
**Current Code:**
```python
if secret and not secret.startswith("sha256="):
    try:
        secret = decrypt_webhook_secret(secret)
    except WebhookEncryptionError:
        logger.warning("Failed to decrypt webhook secret for %s, using as-is", webhook.name)
```
**Fix:**
```python
if secret and not secret.startswith("sha256="):
    try:
        secret = decrypt_webhook_secret(secret)
    except WebhookEncryptionError:
        logger.error("Failed to decrypt webhook secret for %s, delivery aborted", webhook.name)
        return False  # or raise exception
```
**Dependencies:** None

---

### F.12: AVIF Filter Stub Never Implemented
**File:** `app/filters.py:75-83`
**Severity:** LOW (Enhancement)
**Issue:** `post_image_avif_url` filter always returns `None`. Either implement actual AVIF variant lookup or rename to indicate it's a stub.
**Fix Options:**
Option A: Rename filter to `post_image_avif_url_stub` and add deprecation notice in docstring
Option B: Implement actual AVIF variant lookup in storage backend
**Implementation Details:**
- Storage backend (`app/storage.py`) supports local and S3 backends
- Image variants are generated by `generate_image_variants` task (`app/tasks.py:55-70`)
- AVIF encoding requires `pillow-avif-plugin` or similar
**Recommendation:** Option A (rename to stub) until AVIF encoding is properly implemented
**Dependencies:** Storage backend implementation if AVIF is implemented

---

## Part 3: Wave G - Code Quality

**Priority:** MEDIUM - Refinements for consistency and maintainability
**Items:** 5

### Wave G Execution Order

All G items can run in parallel since they are independent.

| Item | Parallel Group |
|------|---------------|
| G.1 | A - Webhooks |
| G.2 | A - Email |
| G.3 | A - Scheduler |
| G.4 | A - Tasks |
| G.5 | B - Deprecation |

---

### G.1: Duplicate Webhook Signing Function
**File:** `app/webhooks.py:28` and `app/tasks.py:181-189`
**Issue:** Same `_sign_webhook_payload()` function is duplicated in both files.
**Fix:** Remove `app/tasks.py:181-189` `_sign_webhook_payload()` and have `deliver_webhook_task` import from `app/webhooks.py`.

**Implementation Steps:**
1. Verify `sign_webhook_payload` in `app/webhooks.py:28` is correct
2. In `app/tasks.py`, remove lines 181-189 (the `_sign_webhook_payload` function)
3. Add import at top of `app/tasks.py`: `from app.webhooks import sign_webhook_payload`
4. Update `deliver_webhook_task` to call `sign_webhook_payload(payload, secret)` instead of `_sign_webhook_payload(payload, secret)`
5. Ensure no other code in `tasks.py` depends on local `_sign_webhook_payload`

**Verification:** Run webhook delivery tests to ensure signatures match.

---

### G.2: SMTP Exception Handling Too Broad
**File:** `app/email.py:94`
**Issue:** `_connect_smtp()` function catches broad `smtplib.SMTPException` and `OSError`. While the retry logic in `_send_email_with_retry()` handles `SMTPServerDisconnected` specifically, the initial connection at line 94 catches ALL SMTP exceptions undifferentiated.
**Fix:** Change to catch specific subclasses: `SMTPAuthenticationError`, `SMTPConnectError`, `SMTPRecipientsRefused`, etc.

**Available SMTP Exceptions (Python 3.10+):**
- `SMTPAuthenticationError` - Authentication failed
- `SMTPConnectError` - Connection failed
- `SMTPRecipientsRefused` - All recipients refused
- `SMTPSenderRefused` - Sender refused
- `SMTPServerDisconnected` - Server disconnected (already handled separately in retry logic at line 124)

**Recommended Fix:**
```python
except (smtplib.SMTPAuthenticationError, smtplib.SMTPConnectError, smtplib.SMTPSenderRefused, OSError) as e:
```

**Dependencies:** None

---

### G.3: Lock Warning Logs Missing
**File:** `app/scheduler.py:75,149,193,249`
**Issue:** When `FileLockTimeout` occurs, silently skips without logging. No visibility into skipped jobs.
**Fix:** Add warning logs to all four lock acquisitions.

**Implementation:** Change all four lock acquisitions from:
```python
except FileLockTimeout:
    return
```
To:
```python
except FileLockTimeout:
    app.logger.warning("Could not acquire lock %s, skipping run", lock_path)
    return
```

**Apply to:**
- Line 75: `send_daily_newsletter`
- Line 149: `cleanup_expired_subscribers`
- Line 193: `publish_scheduled_posts`
- Line 249: `run_daily_backup`

**Dependencies:** None

---

### G.4: Duplicate os Import
**File:** `app/tasks.py:37`
**Issue:** `import os` appears at line 7 (global) and line 37 (local). Redundant.
**Fix:** Remove local import at line 37.

**Current State:**
- Line 7: `import os` (module level)
- Line 37: `import os` (inside function, redundant)

**Dependencies:** None

---

### G.5: Deprecate Direct deliver_webhook Function
**File:** `app/webhooks.py`
**Issue:** Since `deliver_webhook_task` handles all delivery with proper SSRF protection, the direct `deliver_webhook()` function may be unnecessary.
**Fix:** Mark `deliver_webhook()` as deprecated with note that all deliveries should go through Celery task `deliver_webhook_task`.

**Implementation Steps:**
1. Add deprecation warning to `deliver_webhook()` docstring
2. Search codebase to ensure no other code path calls `deliver_webhook()` directly
3. If safe to remove after verification, remove the function
4. If not safe to remove, keep but mark as deprecated

**Verification:** Search for any direct imports/usages of `deliver_webhook` function (not the task).

**Dependencies:** Verify no code path requires direct call before removal

---

## Part 4: Wave H - Documentation Fixes

**Priority:** MEDIUM - Accuracy improvements
**Items:** 33

### Wave H Execution Order

Documentation items can be parallelized by module. Dependencies noted.

| Order | Item | Module | Dependencies |
|-------|------|--------|--------------|
| 1 | H.1-H.8 | Core Architecture | None |
| 2 | H.9-H.18 | Routes | None |
| 3 | H.19-H.20 | Services | F.2 before H.20 |
| 4 | H.21-H.25 | Testing | F.7 before H.21-H.25 |
| 5 | H.26-H.29 | Frontend | None |
| 6 | H.30-H.33 | Infrastructure | None |
| 7 | H.34-H.35 | Tasks | G.5 before H.32 |
| 8 | H.36-H.37 | Deployment | None |

**Recommended Parallelization:**
- 4 subagents can work in parallel on different documentation modules
- Subagent 1: H.1-H.8 (Core Architecture)
- Subagent 2: H.9-H.18 (Routes) + H.19-H.20 (Services)
- Subagent 3: H.21-H.29 (Testing + Frontend)
- Subagent 4: H.30-H.37 (Infrastructure + Tasks + Deployment)

---

### Core Architecture (8 items)

### H.1: Fix User Model TOTP Documentation
**File:** `architecture/core/models.md:97`
**Issue:** Doc says `totp_secret = db.Column(db.String(32))` but actual implementation uses `totp_secret_encrypted = db.Column(db.String(256))` with property accessor.
**Fix:** Replace with:
- `totp_secret_encrypted = db.Column(db.String(256), nullable=True)` (encrypted storage)
- `totp_enabled = db.Column(db.Boolean, default=False, nullable=False)`
- `backup_codes_hashed = db.Column(db.JSON, nullable=True)`
Document the `totp_secret` property that decrypts on access.

**Actual Code Reference:** `app/models.py:33-52`
- Line 33: `totp_secret_encrypted = db.Column(db.String(256), nullable=True)`
- Line 34: `totp_enabled = db.Column(db.Boolean, default=False, nullable=False)`
- Line 72: `backup_codes_hashed = db.Column(db.JSON, nullable=True)`
- Lines 44-52: `totp_secret` property getter that decrypts

**Dependencies:** None

---

### H.2: Document SESSION_IP_BINDING Behavior
**File:** `architecture/core/configuration.md:16`
**Issue:** Valid values "off", "warn", "enforce" not documented.
**Fix:** Add section explaining: "warn" logs IP changes but doesn't block, "enforce" blocks sessions with IP changes.

**Actual Behavior (from code):**
- `"off"`: No IP binding check
- `"warn"`: Logs IP changes but allows session
- `"enforce"`: Blocks session if IP changes

**Dependencies:** None

---

### H.3: Reorganize Key Indexes Section
**File:** `architecture/core/models.md:57-82`
**Issue:** Indexes not grouped by model clearly. Comment indexes not separated. PostRevision and AdminAuditLog indexes missing. `ix_post_series_series_id` and `ix_post_series_post_id` incorrectly under Series.
**Fix:** Group indexes by model with clear section headers. Move comment indexes to "Comments" section. Add PostRevision and AdminAuditLog indexes. Fix series indexes under PostSeries.

**Actual Index Locations:**
- PostRevision indexes: `ix_post_revisions_post_id`, `ix_post_revisions_created_at`
- AdminAuditLog indexes: `ix_admin_audit_logs_user_id`, `ix_admin_audit_logs_action`
- Comment indexes should be under Comments section
- PostSeries indexes: `ix_post_series_series_id`, `ix_post_series_post_id`

**Dependencies:** None

---

### H.4: Add PostRevision to Post Relationship Diagram
**File:** `architecture/core/models.md:28-39`
**Issue:** Diagram shows Post relationships but doesn't show PostRevision relationship.
**Fix:** Add: `Post` → `revisions (1:N)`

**Actual Relationship:** `Post.revisions` via `PostRevision.post_id` foreign key

**Dependencies:** None

---

### H.5: Document SiteSettings Singleton Pattern
**File:** `architecture/core/models.md:156-172`
**Issue:** `get_instance()` class method not documented.
**Fix:** Add note about `get_instance()` class method and that only one SiteSettings row should exist.

**Actual Code Reference:** `app/models.py:354-361`

**Dependencies:** None

---

### H.6: Update CSP Documentation
**File:** `architecture/core/app-factory.md:73-84`
**Issue:** Missing `style-src-attr 'unsafe-inline'` required for inline style attributes used by theme system.
**Fix:** Add the directive with note about intentional support for theme system.

**Actual CSP (from `app/__init__.py:359`):**
```
style-src-attr 'unsafe-inline';
```

**Dependencies:** None

---

### H.7: Clarify SESSION_COOKIE_SECURE Behavior
**File:** `architecture/core/app-factory.md:18`
**Issue:** Currently says "True (in production)" which is vague.
**Fix:** Change to "Set via SESSION_COOKIE_SECURE env var, defaults to True in production". Add note about enforcement.

**Actual Behavior (from `app/__init__.py:182-184,197-201`):**
- Default is `"true"` when not set
- Only enforced to `True` when `ENV == "production"`

**Dependencies:** None

---

### H.8: Document Missing PostRevision Model
**File:** `architecture/core/models.md:5-25`
**Issue:** `PostRevision` model mentioned in relationships but not as standalone entry in overview table.
**Fix:** Add `PostRevision` to overview table with purpose "Post edit history".

**Dependencies:** None

---

### Routes Documentation (10 items)

### H.9: Fix Admin Routes Paths
**File:** `architecture/routes/admin-routes.md`
**Issue:** Multiple route path errors: 2FA paths wrong (`/admin/2fa-setup` → `/admin/2fa/setup`), logout should be POST not GET, backup routes missing filename param, tag routes incorrect, newsletter routes wrong.
**Fix:** Correct all paths:
- 2FA: `/admin/2fa-setup` → `/admin/2fa/setup`, `/admin/2fa-verify` → `/admin/2fa/verify`
- Logout: `GET /admin/logout` → `POST /admin/logout`
- Backup routes: include `<filename>` parameter
- Tags: `POST /admin/tags` → `POST /admin/tags/create`, rename is `POST /admin/tags/rename/<int:tag_id>`
- Newsletter: `POST /admin/newsletter/preview` → `GET /admin/newsletter/preview`, add `/admin/newsletter-test` (POST)
- Posts list is at `/admin/` not `/admin/posts`

**Actual Route Paths (from code):**
- 2FA setup: `app/routes/admin/auth.py:263` - `GET /admin/2fa/setup`
- 2FA verify: `app/routes/admin/auth.py:312` - `GET /admin/2fa/verify`
- Logout: `app/routes/admin/auth.py:99-122` - `POST /admin/logout`
- Tag create: `app/routes/admin/tags.py:115` - `POST /admin/tags/create`
- Tag rename: `app/routes/admin/tags.py:40` - `POST /admin/tags/rename/<int:tag_id>`
- Tag delete: `app/routes/admin/tags.py:87` - `POST /admin/tags/delete/<int:tag_id>`
- Newsletter test: `app/routes/admin/newsletter.py:24` - `POST /admin/newsletter-test`
- Posts list: `app/routes/admin/posts/__init__.py:51` - dashboard at `/admin/`

**Dependencies:** None

---

### H.10: Remove Non-existent Publish Endpoint
**File:** `architecture/routes/api-routes.md:67-70`
**Issue:** Documents `POST /api/posts/<id>/publish` which doesn't exist.
**Fix:** Remove endpoint. Publishing is done via `PUT /api/posts/<id>` with `published` field body.

**Actual Code:** `app/routes/api/posts.py:263-268` uses `PUT /api/posts/<id>` with `{"published": true}`

**Dependencies:** None

---

### H.11: Fix Preview Route Documentation
**File:** `architecture/routes/public-routes.md`
**Issue:** Doc says `GET /post/<slug>/preview/<token>` but actual is `GET /preview/<int:post_id>?token=<hmac>&expires=<timestamp>`.
**Fix:** Update to reflect actual token-based by post ID implementation.

**Actual Implementation:** `app/routes/public/posts.py:94-140`

**Dependencies:** None

---

### H.12: Add Missing Public Routes
**File:** `architecture/routes/public-routes.md`
**Issue:** Missing `/archive`, `/series/<slug>`, `/page/<slug>` routes.
**Fix:** Add:
- `/archive` - `app/routes/public/browse.py:121-206`
- `/series/<slug>` - `app/routes/public/browse.py:314-342`
- `/page/<slug>` - `app/routes/public/browse.py:208-219`

**Dependencies:** None

---

### H.13: Fix Rate Limit Documentation
**File:** `architecture/routes/api-routes.md`
**Issue:** Doc says "Authenticated reads 500/min", "Authenticated writes 100/min" but actual is `DEFAULT_LIMIT = "20 per minute"` and `WRITE_LIMIT = "10 per minute"`.
**Fix:** Update to reflect actual limits.

**Actual Limits (from `app/routes/api/posts.py:18-19`):**
```python
DEFAULT_LIMIT = "20 per minute"
WRITE_LIMIT = "10 per minute"
```

**Dependencies:** None

---

### H.14: Add DELETE Subscribers Endpoint
**File:** `architecture/routes/api-routes.md`
**Issue:** `DELETE /api/subscribers/<id>` not documented.
**Fix:** Add endpoint at `app/routes/api/subscribers.py:132-152`.

**Dependencies:** None

---

### H.15: Document Newsletter Test Route
**File:** `architecture/routes/admin-routes.md`
**Issue:** `/admin/newsletter-test` (POST) exists but not documented.
**Fix:** Add route at `app/routes/admin/newsletter.py:24`.

**Dependencies:** None

---

### H.16: Fix Tag Management Routes Documentation
**File:** `architecture/routes/admin-routes.md`
**Issue:** Routes for create, rename, delete are incorrect.
**Fix:** Correct paths for create, rename, delete.

**Actual Routes:**
- `GET /admin/tags` - list tags
- `POST /admin/tags/create` - create tag
- `POST /admin/tags/rename/<int:tag_id>` - rename tag
- `POST /admin/tags/delete/<int:tag_id>` - delete tag

**Dependencies:** None

---

### H.17: Document Revision Restore Endpoint
**File:** `architecture/routes/admin-routes.md`
**Issue:** `/admin/posts/<int:post_id>/revisions/<int:revision_id>/restore` not documented.
**Fix:** Add endpoint at `app/routes/admin/posts/revisions.py:75`.

**Dependencies:** None

---

### H.18: Document User Make-owner and Password Routes
**File:** `architecture/routes/admin-routes.md`
**Issue:** `/admin/users/<int:user_id>/make-owner` and `/admin/users/<int:user_id>/password` routes exist but not documented.
**Fix:** Add both routes to admin routes documentation.

**Dependencies:** None

---

### Services Documentation (2 items)

### H.19: Correct Encryption Documentation
**File:** `architecture/services/backup.md:8,33`
**Issue:** Doc says "GPG encryption" but code uses AES-256-GCM with PBKDF2. Self-contradictory.
**Fix:** Change "GPG encryption" to "AES-256-GCM encryption with PBKDF2 key derivation".

**Actual Code:** `app/backup_encryption.py:91-134` uses AES-256-GCM with PBKDF2 (600k iterations)

**Dependencies:** None (but F.2 should be fixed first for consistency)

---

### H.20: Document Dual Backup Implementations
**File:** `architecture/services/backup.md`
**Issue:** Two different backup implementations not clearly distinguished.
**Fix:** Add section explaining:
- `create_backup()` for Celery tasks with encryption/compression, uses `blog_*.db` naming
- `run_daily_backup()` for APScheduler without encryption/compression, uses `backup_*.db` naming
Update "See Also" to mention naming difference.

**Implementation Locations:**
- Celery backup: `app/tasks.py:306` calls `run_backup_task` → `app/services/backup.py:create_backup()`
- APScheduler backup: `app/scheduler.py:293-299` calls `run_daily_backup()` → `app/services/backup.py:run_daily_backup()`

**Dependencies:** F.2 (backup retention) should be fixed first for accurate documentation

---

### Testing Documentation (4 items)

### H.21: Update Test Suite Structure
**File:** `architecture/testing/test-suite.md:7-14`
**Issue:** Missing `tests/e2e/conftest.py` and `tests/benchmarks/conftest.py` in structure diagram.
**Fix:** Add both to structure diagram. Document that each subdirectory has its own fixtures.

**Note:** This depends on F.7 (fixture consolidation) being completed first, as the shared fixture will change the structure.

**Dependencies:** F.7

---

### H.22: Add E2E Test Requirements
**File:** `architecture/testing/test-suite.md:46-56`
**Issue:** E2E tests require Playwright and start a Flask server on port 5010 but this isn't documented.
**Fix:** Add setup instructions for Playwright and note about port 5010.

**Actual Implementation:** `tests/e2e/conftest.py:34-63` starts Flask server on port 5010

**Dependencies:** None

---

### H.23: Document test_api.py Special Handling
**File:** `architecture/testing/test-suite.md`
**Issue:** `test_api.py:29-45` has its own `app` fixture that does NOT use shared `ensure_buffer_disabled` - not documented.
**Fix:** Add note about session-scoped `app` fixture and function-scoped buffer shutdown.

**Note:** Depends on F.7 (fixture consolidation) being completed first.

**Dependencies:** F.7

---

### H.24: Add Session Management Warning
**File:** `architecture/testing/test-suite.md`
**Issue:** `db.session.refresh()` caveat not documented.
**Fix:** Document that `refresh()` fails if object isn't in current session. Use re-query instead.

**Actual Issue:** `db.session.refresh()` fails if object isn't in current session

**Dependencies:** None

---

### H.25: Add Conftest Fixtures Reference Table
**File:** `architecture/testing/test-suite.md:24-31`
**Issue:** No table showing which fixtures exist in which conftest.py.
**Fix:** Add reference table listing fixtures and their locations.

**Note:** Depends on F.7 (fixture consolidation) being completed first.

**Dependencies:** F.7

---

### Frontend Documentation (4 items)

### H.26: Update Templates Directory Listing
**File:** `architecture/frontend/templates.md:6-26`
**Issue:** Currently shows incomplete file listing (~50+ actual files).
**Fix:** Update directory tree to reflect all template files.

**Dependencies:** None

---

### H.27: Clarify Uploads Storage Location
**File:** `architecture/frontend/static-assets.md:14`
**Issue:** Document says `app/static/uploads/` but only `app/static/img/` and `app/static/fonts/` exist.
**Fix:** Note that uploads may be stored in cloud storage (S3, etc.) and the local path is not used in production.

**Actual Storage:** `app/storage.py` supports local and S3 backends

**Dependencies:** None

---

### H.28: Document Route-based Chunk Strategy
**File:** `architecture/frontend/static-assets.md`
**Issue:** Docs don't reflect that splitting is implemented in `main.js:30-83` via `import.meta.glob`, not just `vite.config.js`.
**Fix:** Document that splitting is implemented in `main.js` via `import.meta.glob`.

**Actual Implementation:** `app/static/js/main.js:30-83` uses `import.meta.glob` for dynamic imports

**Dependencies:** None

---

### H.29: Document Mobile-menu.jsx JSX Nature
**File:** `architecture/frontend/static-assets.md` or create `frontend/vite.md`
**Issue:** File is JSX (`.jsx`), not `.js` - not documented.
**Fix:** Note that Vite handles JSX via esbuildOptions at `vite.config.js:34`.

**Actual File:** `app/static/js/shared/mobile-menu.jsx`

**Dependencies:** None

---

### Infrastructure Documentation (4 items)

### H.30: Document Missing Search Functions
**File:** `architecture/infrastructure/search.md`
**Issue:** Functions `remove_fts()`, `sync_fts_batch()`, `reset_fts_available()`, `get_indexed_terms()`, `highlight_query()` not documented.
**Fix:** Add documentation for all undocumented search functions.

**Function Locations:**
- `remove_fts()` - `app/search.py:177`
- `sync_fts_batch()` - `app/search.py:136`
- `reset_fts_available()` - `app/search.py:36`
- `get_indexed_terms()` - `app/search.py:224`
- `highlight_query()` - `app/search.py:356`

**Dependencies:** None

---

### H.31: Clarify Async Email Pattern
**File:** `architecture/infrastructure/email.md:88-93`
**Issue:** `send_confirmation()` and `send_password_reset()` are synchronous wrappers called by async Celery tasks - not clear.
**Fix:** Update documentation to clarify wrapper pattern.

**Actual Pattern:**
- `send_confirmation()` and `send_password_reset()` in `app/email.py` are synchronous
- Celery tasks `send_confirmation_task` and `send_password_reset_task` wrap these

**Dependencies:** None

---

### H.32: Deprecate Direct deliver_webhook Call
**File:** `architecture/infrastructure/webhooks.md`
**Issue:** Direct `webhooks.py:deliver_webhook()` may be unnecessary since task handles all delivery.
**Fix:** Add deprecation notice indicating all deliveries should go through Celery task.

**Note:** Depends on G.5 (deprecate deliver_webhook) being completed first.

**Dependencies:** G.5

---

### Tasks Documentation (5 items)

### H.33: Document Newsletter Synchronous Execution
**File:** `architecture/tasks/scheduler.md`
**Issue:** APScheduler's `send_daily_newsletter` calls `send_newsletter()` directly (synchronous) not documented.
**Fix:** Add note:
```
Note: Unlike other jobs, send_daily_newsletter calls send_newsletter()
directly (synchronous) rather than queuing send_newsletter_task (async).
```

**Actual Implementation:** `app/scheduler.py:70-140` - `send_daily_newsletter` calls `send_newsletter()` directly

**Dependencies:** None

---

### H.34: Fix Celery Task Docstring
**File:** `architecture/tasks/celery-tasks.md:36`
**Issue:** `def send_newsletter_task(self, post_ids: List[int])` incorrect - self not first param.
**Fix:** Change to `def send_newsletter_task(self: Any, post_ids: List[int])`

**Actual Code:** `app/tasks.py:130`

**Dependencies:** None

---

### H.35: Clarify Backup Naming Distinction
**File:** `architecture/tasks/scheduler.md:40`
**Issue:** Scheduler's `run_daily_backup()` creates `backup_*.db` (unencrypted) vs Celery task creates `blog_*.db` (encrypted/compressed) - distinction not clear.
**Fix:** Document that these serve different purposes with different naming conventions.

**Note:** Depends on F.2 (backup retention) being fixed first for accurate documentation.

**Dependencies:** F.2

---

### H.36: Update docker.md for Accuracy
**File:** `architecture/deployment/docker.md`
**Issue:** Line 11 says `redis:alpine` but should be `redis:7-alpine`. Line 32 says resource limits are in Dockerfile but they're in docker-compose.yml. Line 48 doesn't note DATABASE_URL is optional.
**Fix:** Correct all three items.

**Actual Values:**
- docker-compose.yml:56 uses `redis:7-alpine`
- Resource limits in docker-compose.yml:26-30
- DATABASE_URL is optional - SQLite is default

**Dependencies:** None

---

### H.37: Add DATABASE_URL to Production Profile
**File:** `docker-compose.yml:1-33`
**Issue:** If PostgreSQL is intended for production, DATABASE_URL should be in blog service environment.
**Fix:** Add DATABASE_URL to production profile environment if PostgreSQL is intended for production use.

**Dependencies:** None

---

## Part 5: Wave I - Enhancements

**Priority:** LOW - Nice to have improvements
**Items:** 0

No enhancement items currently identified. All batch items were either bugs, code quality, or documentation.

---

## Summary

| Wave | Description | Item Count |
|------|-------------|------------|
| F | Bug Fixes | 12 |
| G | Code Quality | 5 |
| H | Documentation | 37 |
| I | Enhancements | 0 |
| **Total** | | **54** |

### Priority Breakdown

| Priority | Count | Wave |
|----------|-------|------|
| HIGH (Security) | 2 | F (F.1, F.11) |
| HIGH (Functional) | 3 | F (F.2, F.4, F.5) |
| MEDIUM | 42 | F, G, H |
| LOW | 1 | F (F.12) |
| Documentation | 37 | H |

### Cross-Cutting Concerns

1. **Silent failure handling** - Webhooks (F.4) and scheduler locks (G.3) both have silent failure issues
2. **Exception handling too broad** - tasks.py (F.5) and email.py (G.2) need refinement
3. **Dual backup implementations** - affects both functional bug (F.2) and documentation (H.20, H.35)
4. **Test fixture duplication** - affects both functional bug (F.7) and documentation (H.21, H.22, H.23, H.24, H.25)

### Dependencies Between Waves

- F.7 (fixture consolidation) must precede H.21, H.23, H.25 (testing docs)
- G.5 (deprecate deliver_webhook) must precede H.32 (webhooks docs)
- F.2 (backup retention) should precede H.19, H.20, H.35 (backup docs)
- F.1 (preview route security) is independent - no dependencies

---

## Wave Execution Strategy

### Recommended Parallelization

**Wave F (12 items):**
- 4 subagents can work in parallel on 3 items each
- Subagent F-A: F.1, F.11 (Security items)
- Subagent F-B: F.2, F.3, F.12 (Functional/Frontend)
- Subagent F-C: F.4, F.5, F.6 (Code/Infrastructure)
- Subagent F-D: F.7, F.8, F.9, F.10 (Testing/CI-CD/Docker)

**Wave G (5 items):**
- 2 subagents can work in parallel
- Subagent G-A: G.1, G.2, G.3 (Core services)
- Subagent G-B: G.4, G.5 (Tasks/Deprecation)

**Wave H (37 items):**
- 4 subagents can work in parallel on ~9 items each
- Subagent H-A: H.1-H.8 (Core Architecture)
- Subagent H-B: H.9-H.18 (Routes) + H.19-H.20 (Services) - Note: H.20 depends on F.2
- Subagent H-C: H.21-H.29 (Testing + Frontend) - Note: H.21, H.23, H.25 depend on F.7
- Subagent H-D: H.30-H.37 (Infrastructure + Tasks + Deployment)

### Branch Naming Convention
```
wave-f-bugfixes
wave-g-code-quality
wave-h-documentation
```

---

*Last updated: May 2026*