# Implementation Plan - Blog CMS (Consolidated)

**Project:** Blog CMS
**Status:** WAVE M - Implementation Phase
**Last Updated:** May 2026

---

## Overview

This file contains the consolidated implementation plan for the Blog CMS project. Wave M consolidates all findings from Wave L architecture reviews (8 modules) into actionable items organized by parallelization potential.

### Wave Summary

| Wave | Description | Items | Status |
|------|-------------|-------|--------|
| A-J | Implementation waves (2FA, Rate Limiting, Search, etc.) | 61+ | COMPLETED |
| K | Architecture Reviews (8 modules) | All 8 | COMPLETED |
| L | Wave K Findings Implementation | 37 | COMPLETED |
| M | Wave M Consolidation | See below | IN PROGRESS |

---

## WAVE M: Consolidated Implementation Plan

All items verified against codebase. Items marked "COMPLETED" were found to already be correct during verification.

---

## PHASE 1: CRITICAL BUGS (Sequential - Must Fix First)

### M-1.1: image-review.js vs image-preview.js Naming Mismatch (CRITICAL)
**File:** `app/static/js/main.js:15,40,51`

**Issue:** Code imports `'./image-review.js'` but actual file is `image-preview.js`. Admin image review functionality is broken.

**Fix:** Change imports in main.js from `'./image-review.js'` to `'./image-preview.js'`

**Verification:** `ls app/static/js/image-preview.js` should exist; `image-review.js` should not exist.

---

### M-1.2: Email Task Retry Logic Broken (HIGH)
**File:** `app/tasks.py:274-278`, `app/tasks.py:295-299`

**Issue:** `send_confirmation_task` and `send_password_reset_task` catch exceptions and return `False` without raising. With `max_retries=3`, tasks will NOT automatically retry because exceptions are swallowed.

**Fix Options:**

**Option A (Preferred):** Remove `max_retries=3` from these tasks since they wrap synchronous functions that already handle failures:

```python
@celery_task
def send_confirmation_task(email: str, confirmation_url: str):
    # Remove max_retries - sync function already handles errors
    try:
        return send_confirmation_email(email, confirmation_url)
    except Exception as e:
        current_app.logger.error(f"Confirmation email failed: {e}")
        return False
```

**Option B:** Implement proper retry with `self.retry()`:
```python
@celery_task(max_retries=3)
def send_confirmation_task(email: str, confirmation_url: str):
    try:
        return send_confirmation_email(email, confirmation_url)
    except Exception as e:
        current_app.logger.error(f"Confirmation email failed: {e}")
        self.retry(exc=e, countdown=60)
```

**Verification:** Test that failed emails actually retry (if using Option B).

---

### M-1.3: S3StorageBackend Credential Clearing Bug (ALREADY FIXED)
**File:** `app/storage.py:168,171-174`

**Status:** NO ACTION NEEDED - The `_clear_credentials()` method has been removed from the codebase. S3StorageBackend now properly initializes the boto3 client once and reuses it via the `client` property.

**Verification:** `_clear_credentials()` does not exist in storage.py.

---

### M-1.4: SMTP Context Manager Exception Safety (FALSE POSITIVE)
**File:** `app/email.py:36`

**Status:** NO ACTION NEEDED - Python's `smtplib.SMTP` context manager guarantees `quit()` is called via `__exit__` even if exceptions occur within the `with` block. The bug claim was incorrect.

**Verification:** Code uses proper `with smtplib.SMTP(...) as server:` pattern.

---

## PHASE 2: HIGH-PRIORITY IMPROVEMENTS (Can Parallelize with Phase 1)

### M-2.1: Add Missing API Endpoint Documentation
**Files:** `docs/routes/api-routes.md`, `app/routes/api/subscribers.py:76`

**Issue:** Missing `POST /api/subscribers` endpoint documentation.

**Fix:** Add to api-routes.md:
```markdown
### POST /api/subscribers

Create a new subscriber.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response:** `201 Created`
```

---

### M-2.2: Fix Webhook Model Documentation
**File:** `docs/infrastructure/webhooks.md:17-30`

**Issue:** Documentation shows `secret = db.Column(db.String(64))` but actual uses `webhook_secret_encrypted = db.Column(db.LargeBinary(256))` with property getter/setter.

**Fix:** Update documentation:
```markdown
### Webhook Model

| Field | Type | Description |
|-------|------|-------------|
| webhook_secret_encrypted | LargeBinary(256) | Encrypted webhook secret using AES-256-GCM |
| secret | Property | Decrypted secret (read/write via property) |
```

---

### M-2.3: Add WebhookEvent delivery_status Documentation
**File:** `docs/infrastructure/webhooks.md`

**Issue:** Missing `delivery_status` field that tracks `'failed'`, `'partial_failure'`, `'delivered'`.

**Fix:** Add to WebhookEvent section:
```markdown
### delivery_status Values

| Value | Description |
|-------|-------------|
| `delivered` | All webhooks succeeded |
| `partial_failure` | Some succeeded, some failed |
| `failed` | All failed |
```

---

### M-2.4: Create Search Provider Documentation
**Files:** `docs/services/search.md` (new), `docs/services/overview.md`

**Issue:** Search provider abstraction (`SearchProvider`, `SQLiteSearchProvider`, `PostgreSQLSearchProvider`) has no module documentation.

**Fix:** Create `docs/services/search.md`:
```markdown
# Search Service

## Overview

Provides abstraction over search implementations with `SearchProvider` abstract class.

## Providers

### SQLiteSearchProvider

Default provider using SQLite FTS5.

**Implementation:** `app/services/search/sqlite.py`

### PostgreSQLSearchProvider

Stub implementation for future PostgreSQL support.

**Implementation:** `app/services/search/postgresql.py`

## Configuration

```toml
[search]
provider = "sqlite"  # or "postgresql"
config = { }
```

## Interface

See `app/services/search/__init__.py:7-68` for `SearchProvider` abstract class.
```

**Update `docs/services/overview.md`** to add Search to services table.

---

### M-2.5: Document Two Backup Implementations
**File:** `docs/services/overview.md`, `docs/tasks/scheduler.md`

**Issue:** Overview implies both backup implementations have encryption/compression but scheduler version does not.

**Fix:** Add explicit documentation:
```markdown
## Backup Implementations

There are two separate backup implementations:

| Implementation | Location | Encryption | Compression |
|---------------|----------|------------|-------------|
| Celery task | `app/services/backup.py:create_backup()` | AES-256-GCM with PBKDF2 | Yes (.gz) |
| APScheduler | `app/scheduler.py:run_daily_backup()` | None | None |

Both use `blog_*.db` naming pattern.
```

---

### M-2.6: Add HEALTH_CHECK_SECRET Documentation
**File:** `docs/deployment/docker.md`

**Issue:** `HEALTH_CHECK_SECRET` for authenticated detailed health checks not documented.

**Fix:** Add section:
```markdown
### Authenticated Health Check

For detailed health information, authenticate with `HEALTH_CHECK_SECRET`:

```
GET /health?secret=<value>&detailed=true
```

Requires `HEALTH_CHECK_SECRET` environment variable.
```

---

### M-2.7: Add Optional Health Checks Clarification
**File:** `docs/overview.md`, `docs/deployment/docker.md`

**Issue:** Which checks are optional and don't affect overall status not documented.

**Fix:** Add table to docker.md:
```markdown
### Health Check Status

| Check | Category | Affects Overall Status |
|-------|----------|------------------------|
| database | critical | Yes |
| scheduler | critical | Yes |
| search | critical | Yes |
| disk_space | critical | Yes |
| db_integrity | critical | Yes |
| backup_freshness | optional | No |
| email | optional | No |
| redis | optional | No |
| celery | optional | No |
```

---

### M-2.8: Fix docker-compose.yml SESSION_COOKIE_SECURE
**File:** `docker-compose.yml:14`

**Issue:** `SESSION_COOKIE_SECURE=${SESSION_COOKIE_SECURE:-true}` passes string "true" not boolean.

**Fix:** Use proper boolean handling:
```yaml
SESSION_COOKIE_SECURE: "true"  # String is fine for env interpolation
# OR in nginx config, handle as string comparison
```

**Verification:** Check that Flask receives boolean, not string "true".

---

### M-2.9: Add blog_logs Volume to Celery
**File:** `docker-compose.yml`

**Issue:** Celery service mounts `blog_data` and `blog_uploads` but not `blog_logs`. Celery logs go to container stdout only.

**Fix:** Add to celery volumes:
```yaml
volumes:
  - blog_logs:/home/blog/logs
```

---

### M-2.10: Fix image-preview.js Documentation
**File:** `docs/frontend/static-assets.md`

**Issue:** Documents `image-review.js` but actual file is `image-preview.js`.

**Fix:** Update documentation:
```markdown
| File | Purpose |
|------|---------|
| image-preview.js | Admin image preview/selection for posts |
```

---

## PHASE 3: MEDIUM-PRIORITY DOCUMENTATION FIXES (Can Parallelize)

### M-3.1: Add Missing Routes Documentation

**M-3.1a:** Document `POST /admin/preview-markdown` (markdown preview)
**Location:** `app/routes/admin/posts/editor.py:328`

**M-3.1b:** Document `POST /admin/series/<int:series_id>/reorder` (AJAX reorder)
**Location:** `app/routes/admin/series.py:259`

**M-3.1c:** Document `GET /confirm/<token>` and `GET /unsubscribe/<token>` (subscribe routes)
**Location:** `app/routes/public/subscribe.py`

---

### M-3.2: Fix HTTP Method Documentation

**M-3.2a:** Tag delete uses POST not DELETE
**Location:** `app/routes/admin/tags.py:87`
**Doc fix:** Change `DELETE /admin/tags/delete/<id>` to `POST /admin/tags/delete/<id>`

**M-3.2b:** Series delete uses POST not DELETE
**Location:** `app/routes/admin/series.py:132`
**Doc fix:** Change `DELETE /admin/series/<id>/delete` to `POST /admin/series/<id>/delete`

---

### M-3.3: Clarify Tag Pagination
**File:** `docs/routes/public-routes.md`

**Issue:** Documents `/tag/<slug>/<int:page>` but actual uses `?page=N` query parameter.

**Fix:** Update to:
```markdown
### GET /tag/<slug>

Query parameters:
- `page` - Page number (default: 1)
```

---

### M-3.4: Document Feed Caching
**File:** `docs/routes/rss-feeds.md`

**Issue:** 5-minute cache and ETag support not documented.

**Fix:** Add section:
```markdown
## Caching

- Response cached for 5 minutes
- ETag support with `If-None-Match` header
- Conditional GET returns `304 Not Modified` when cached
```

---

### M-3.5: Add Missing Configuration Options
**File:** `docs/core/configuration.md`

**Add documentation for:**
- `PAGE_VIEW_BUFFER_SIZE` - Page view buffering threshold
- `SEARCH_PROVIDER` - Search provider selection
- `SEARCH_CONFIG` - Provider-specific config
- `DATA_BACKUP_DIR` - Backup directory location

---

### M-3.6: Document AdminSession.last_activity
**File:** `docs/core/models.md`

**Issue:** `last_activity` field on AdminSession model not documented.

**Fix:** Add to AdminSession model table:
```markdown
| last_activity | DateTime | Last activity timestamp |
```

---

### M-3.7: Document PostRevision.author_id
**File:** `docs/core/models.md`

**Issue:** `author_id` foreign key field on PostRevision not documented.

**Fix:** Add to PostRevision model table:
```markdown
| author_id | Integer | Foreign key to User who created revision |
```

---

### M-3.8: Clarify RATE_LIMIT_STORAGE_URI Logic
**File:** `docs/core/configuration.md`

**Issue:** Redis only used when FLASK_ENV=production not documented.

**Fix:** Add note:
```markdown
### RATE_LIMIT_STORAGE_URI

Redis is only used when `FLASK_ENV=production`. In development, in-memory storage is used.
```

---

### M-3.9: Add Account Lockout Configuration
**File:** `docs/deployment/security.md`

**Fix:** Add section:
```markdown
## Account Lockout

Failed login attempts are tracked with:
- `MAX_FAILED_ATTEMPTS` - Number of failed attempts before lockout (default: 5)
- `LOCKOUT_DURATION_MINUTES` - Lockout duration in minutes (default: 15)
```

---

### M-3.10: Document Backup Filename Security
**File:** `docs/routes/admin-routes.md` or `docs/infrastructure/storage.md`

**Issue:** `BACKUP_FILENAME_RE` security measure not documented.

**Fix:** Add note about filename validation preventing path traversal.

---

### M-3.11: Add Series Relationship Ordering Note
**File:** `docs/core/models.md`

**Fix:** Add to PostSeries model:
```markdown
### Series.posts Relationship

Posts are ordered by `PostSeries.order_index` (not by date or title).
```

---

### M-3.12: Remove STORAGE_BACKEND from Environment Table
**File:** `docs/deployment/docker.md`

**Issue:** `STORAGE_BACKEND` not used in docker-compose.yml.

**Fix:** Remove from environment variables table, or add to docker-compose.yml.

---

## PHASE 4: LOW-PRIORITY IMPROVEMENTS (Can Parallelize)

### M-4.1: Remove Dead Code extract_snippet()
**File:** `app/search.py:253-279`

**Issue:** `extract_snippet()` function is defined but never called. `get_search_snippets()` uses native FTS5 snippet() instead.

**Fix:** Either use the function or remove it.

---

### M-4.2: Document AVIF Status
**File:** `docs/infrastructure/storage.md`

**Issue:** `post_image_avif_url_stub` filter exists but AVIF encoding not implemented.

**Fix:** Add note:
```markdown
## AVIF Support

AVIF variant generation is planned but not yet implemented. The `post_image_avif_url_stub` filter returns `None`.
```

---

### M-4.3: Add Multi-Container Deployment Warning
**File:** `docs/tasks/scheduler.md`

**Issue:** APScheduler jobs use FileLock which only works on single machine.

**Fix:** Add warning:
```markdown
## Multi-Container Deployment

APScheduler uses FileLock which only works on a single machine. In multi-container deployments, each container runs its own scheduler. Without external coordination (Redis, etcd), jobs may run on all replicas simultaneously.
```

---

### M-4.4: Document Email Wrapper Task Pattern
**File:** `docs/infrastructure/email.md` or `docs/tasks/celery-tasks.md`

**Issue:** `send_confirmation_task` and `send_password_reset_task` wrap synchronous functions but not documented.

**Fix:** Add note explaining these tasks wrap sync email functions.

---

### M-4.5: Add Celery Task Failure Logging
**File:** `app/tasks.py:172-175`

**Issue:** `send_newsletter_task` increments `newsletter_attempts` on failure but has no logging equivalent to scheduler.py:100-106.

**Fix:** Add logging when newsletter attempts fail repeatedly.

---

### M-4.6: Document Slug Collision Limit
**File:** `docs/services/slug.md` or `docs/core/models.md`

**Fix:** Add note:
```markdown
## Slug Generation

Slug collision limit is 100 tries before falling back to UUID suffix.
```

---

### M-4.7: Document APScheduler Daemon Mode
**File:** `docs/tasks/scheduler.md`

**Issue:** Scheduler runs as daemon thread and will not prevent process exit.

**Fix:** Add note:
```markdown
The scheduler runs as a daemon thread and will not prevent process exit.
```

---

### M-4.8: Document Newsletter Retry Configuration
**File:** `docs/tasks/celery-tasks.md`

**Fix:** Add note:
```markdown
## Newsletter Retry Behavior

`NEWSLETTER_MAX_RETRY_ATTEMPTS` (default: 5) controls retry behavior. The Celery task does not have the same retry-exclusion logic as APScheduler scheduler.
```

---

### M-4.9: Add E2E Server Startup Race Condition Note
**File:** `docs/testing/e2e-tests.md` or `e2e/conftest.py`

**Issue:** Server startup uses `time.sleep(1)` - potential race conditions on slow systems.

**Fix:** Document potential race conditions and solution (increase sleep or use health check).

---

### M-4.10: Document celery --concurrency=1
**File:** `docs/deployment/docker.md` or `docker-compose.yml` comment

**Fix:** Add comment in docker-compose.yml:
```yaml
# Celery worker runs with single concurrency
command: celery -A app.tasks worker --loglevel=info --concurrency=1
```

---

### M-4.11: Add docker wait redis Documentation
**File:** `docs/deployment/cicd.md`

**Fix:** Add note about `docker-compose wait redis` in e2e-tests setup.

---

### M-4.12: Document FakeSubscriber Dataclass
**File:** `docs/testing/test-suite.md`

**Issue:** `FakeSubscriber` at `tests/conftest.py:56-64` not documented.

**Fix:** Add to fixture documentation:
```markdown
### FakeSubscriber

Dataclass useful for newsletter tests without real subscribers.
```

---

### M-4.13: Clarify mock_email Fixture Chaining
**File:** `docs/testing/test-suite.md`

**Fix:** Clarify that `mock_email` chains `mock_render` and `mock_smtp` but actual mocking happens in those individual fixtures.

---

### M-4.14: Document clean_db Nested Transaction Pattern
**File:** `docs/testing/test-suite.md`

**Fix:** Add note explaining `db.session.begin_nested()` for test data cleanup in benchmarks.

---

## PHASE 5: VERIFIED COMPLETED ITEMS

The following items were verified to already be correct in the codebase:

### Wave L Completed Items (Previously Verified)

- **L-1.1 (mobile-menu.jsx)**: NO SYNTAX ERROR - code is syntactically correct
- **L-1.2 (webhook logger)**: `logger = logging.getLogger(__name__)` already defined at module level
- **L-1.3 (preview route docs)**: Both HMAC AND session required (correct)
- **L-2.1 (search.html srcset)**: srcset properly defined before use
- **L-2.2 (APScheduler SMTP)**: Only newsletter disabled, other jobs run unconditionally
- **L-3.1 (tag cache TTL)**: 60 seconds documented correctly
- **L-3.2 (slug signature)**: Documentation matches implementation
- **L-3.3 (backup retention)**: `blog_*.db` pattern documented correctly
- **L-3.5 (Post user_id)**: Documentation does NOT claim user_id exists (correct)
- **L-3.6 (image fields)**: Documentation shows image and image_alt_text (correct)
- **L-3.7 (admin revisions route)**: Route correctly documented
- **L-4.1 (celery concurrency)**: `--concurrency=1` already in docker-compose.yml
- **L-4.2 (pip-audit)**: `--fail-on=all` already in CI

### Wave M Verified Items (New)

- **Benchmark conftest import**: Both files use same path `app.routes.admin`
- **Webhook encryption docs**: Already shows `app/webhook_encryption.py`
- **Queue line numbers**: Match actual code
- **Lock files**: All 4 documented correctly
- **Indexes in models.md**: All indexes present
- **prism.min.js location**: At `app/static/js/prism.min.js`
- **_breadcrumbs.html**: Only admin version exists
- **API routes**: Fixed (removed non-existent `POST /api/subscribers/export`)
- **[search] section**: Present in config example
- **Health check docs**: All details documented
- **Encryption key requirements**: Both files accurate
- **Resource limits**: Memory limits documented

---

## Parallelization Strategy

### Phase 1 (Critical) - Sequential
Must fix before parallel work due to security/correctness:
- M-1.1, M-1.2, M-1.3, M-1.4

### Phase 2 (High) - Can Parallelize After Phase 1
- M-2.1 through M-2.10

### Phase 3 (Medium) - Can Parallelize (Multiple Agents)
- M-3.1 through M-3.12

### Phase 4 (Low) - Can Parallelize (Multiple Agents)
- M-4.1 through M-4.14

### Phase 5 (Completed) - No Action Needed
- All verified items

---

## Files Requiring Changes Summary

| Priority | Items | Files |
|----------|-------|-------|
| Critical | M-1.1, M-1.2, M-1.3, M-1.4 | main.js, tasks.py, storage.py, email.py |
| High | M-2.1-M-2.10 | api-routes.md, webhooks.md, services/*.md, docker.md, docker-compose.yml, static-assets.md |
| Medium | M-3.1-M-3.12 | public-routes.md, rss-feeds.md, configuration.md, models.md, security.md, admin-routes.md, storage.md |
| Low | M-4.1-M-4.14 | search.py, scheduler.md, celery-tasks.md, e2e/conftest.py, test-suite.md |

---

## Notes for Future Agents

### Plan Item Verification
Always verify plan items against actual code. Architecture review findings may contain errors or be outdated. Several items in this plan were found to already be correct during verification.

### Critical Bug Fixes
Priority should be given to Phase 1 items (M-1.1 through M-1.4) as they affect security and correctness.

### Parallel Execution
Phases 2-4 can be executed in parallel by multiple agents. Each agent can take a subset of items.

### Backup Implementations
There are two separate backup implementations:
- `app/services/backup.py:create_backup()` - Used by Celery task, supports AES-256-GCM encryption with PBKDF2/compression
- `app/scheduler.py:run_daily_backup()` - Used by APScheduler, no encryption/compression

Both use `blog_*.db` naming pattern.

### APScheduler Job Schedules
- `cleanup_expired_subscribers` runs every 5 minutes (`minute="*/5"`)
- `run_daily_backup` runs at 02:00 UTC
- When SMTP_HOST is not configured, only the daily newsletter job is disabled

### Health Check Status Logic
Health check only considers critical checks for overall status (optional services don't affect degraded):
- Critical: `database`, `scheduler`, `search`, `disk_space`, `db_integrity`
- Optional: `backup_freshness`, `email`, `redis`, `celery`

### Search Provider Abstraction
`SearchProvider` abstract class in `app/services/search/__init__.py` with:
- `SQLiteSearchProvider` - Current default using FTS5
- `PostgreSQLSearchProvider` - Stub for future PostgreSQL support

Use `get_search_provider()` factory function to get configured provider.

### Webhook Encryption
`Webhook.secret` is encrypted at rest using AES-256-GCM via `app/webhook_encryption.py`.

### 2FA Implementation
- TOTP secrets encrypted at rest using AES-256-GCM
- Backup codes SHA-256 hashed and single-use (8 codes)
- Routes: `/admin/2fa/setup`, `/admin/2fa/verify`, `/admin/2fa/backup-codes`, `/admin/2fa/disable`

### WebhookEvent Delivery Status
`WebhookEvent` has `delivery_status` field tracking:
- `'delivered'` - All webhooks succeeded
- `'partial_failure'` - Some succeeded, some failed
- `'failed'` - All failed

### Context Processors
- `inject_csrf()` - Injects `csrf_token` and `csp_nonce`
- `inject_config()` - Injects site config variables
- `inject_theme()` - Injects theme settings and `custom_css`
- `inject_footer_data()` - Injects footer links and data
- `inject_show_footer_posts()` - Injects `show_footer_posts` boolean

### Template Filters
- `markdown_safe`, `reading_time`, `sanitize_css`
- `post_image_url`, `post_image_srcset`, `post_image_avif_url_stub`

---

*Last updated: May 2026 - Wave M consolidated from 8 architecture review files*