# Implementation Plan - Blog CMS (Consolidated)

**Project:** Blog CMS
**Status:** WAVE M - COMPLETED
**Last Updated:** May 2026

---

## Overview

This file contains the consolidated implementation plan for the Blog CMS project. It was created by merging findings from 8 architecture review modules (routes, infrastructure, services, frontend, overview, core, deployment, testing, tasks) into a single actionable plan.

**For Future Agents:** This plan is designed to be executable by sub-agents. Each item includes detailed implementation steps and file locations. Read all sections before starting implementation.

---

## Quick Reference: Critical Bugs (Fix First)

| ID | Description | Impact | Status |
|----|-------------|--------|--------|
| M-1.1 | `image-review.js` import should be `image-preview.js` | Admin image preview broken | FIXED |
| M-1.2 | Email task retry logic broken | Exceptions swallowed, no auto-retry | FIXED |
| M-2.8 | docker-compose.yml SESSION_COOKIE_SECURE string vs boolean | Config issue | FIXED |
| M-2.9 | Celery missing blog_logs volume mount | Logs not persisted | FIXED |

---

## WAVE STRUCTURE

### Wave M-1 (CRITICAL - Sequential)
Must complete before parallel work. All items affect security or correctness.

### Wave M-2 (HIGH - Can Parallelize After M-1)
Documentation fixes that can be done in parallel by multiple agents.

### Wave M-3 (MEDIUM - Can Parallelize)
More documentation fixes, can use multiple agents.

### Wave M-4 (LOW - Can Parallelize)
Minor improvements, documentation cleanup.

### Completed Items
Items verified as already correct in codebase (no action needed).

---

## WAVE M-1: CRITICAL BUGS (Sequential - Must Fix First)

### M-1.1: image-preview.js Import Fix (CRITICAL)

**Impact:** Admin image preview functionality is broken.

**Files to Change:**
- `app/static/js/main.js:15,40,51`

**Current Code (WRONG):**
```javascript
'./image-review.js',
```

**Fixed Code:**
```javascript
'./image-preview.js',
```

**Implementation Steps:**
1. Read `app/static/js/main.js`
2. Find all occurrences of `'./image-review.js'` (should be 3: lines 15, 40, 51)
3. Replace with `'./image-preview.js'`
4. Verify: `ls app/static/js/image-preview.js` should show the file exists

**Verification:**
- Run: `rg "image-review" app/static/js/` - should find no matches
- Check admin post editor loads image preview correctly

**Dependencies:** None

---

### M-1.2: Email Task Retry Logic Fix (HIGH)

**Impact:** `send_confirmation_task` and `send_password_reset_task` catch exceptions and return `False` without raising. With `max_retries=3`, tasks will NOT automatically retry because exceptions are swallowed.

**Files to Change:**
- `app/tasks.py:262-290` (`send_confirmation_task`)
- `app/tasks.py:292-320` (`send_password_reset_task`)

**Current Code (BROKEN):**
```python
@celery_task(max_retries=3)
def send_confirmation_task(email: str, confirmation_url: str):
    try:
        return send_confirmation_email(email, confirmation_url)
    except (SQLAlchemyError, OSError, ImportError) as e:
        current_app.logger.error(f"Confirmation email failed: {e}")
        return False
```

**Fix Option A (PREFERRED):** Remove `max_retries=3` since sync function already handles errors:
```python
@celery_task
def send_confirmation_task(email: str, confirmation_url: str):
    try:
        return send_confirmation_email(email, confirmation_url)
    except Exception as e:
        current_app.logger.error(f"Confirmation email failed: {e}")
        return False
```

**Fix Option B:** Implement proper retry with `self.retry()`:
```python
@celery_task(max_retries=3)
def send_confirmation_task(email: str, confirmation_url: str):
    try:
        return send_confirmation_email(email, confirmation_url)
    except Exception as e:
        current_app.logger.error(f"Confirmation email failed: {e}")
        self.retry(exc=e, countdown=60)
```

**Implementation Steps:**
1. Read `app/tasks.py`
2. Find `send_confirmation_task` around line 262
3. Find `send_password_reset_task` around line 283
4. Choose Option A or Option B and apply to both functions
5. Update the exception handling to catch `Exception` (broader) if using Option A

**Verification:**
- Run tests: `pytest tests/test_tasks.py -v` or similar
- Check that failed email tasks actually retry (if using Option B)

**Dependencies:** None

---

### M-1.3: S3StorageBackend Credential Clearing (ALREADY FIXED)

**Status:** NO ACTION NEEDED - The `_clear_credentials()` method has been removed.

**Verification:**
- `_clear_credentials()` does not exist in `app/storage.py`
- S3StorageBackend now properly initializes boto3 client once and reuses it

---

### M-1.4: SMTP Context Manager Exception Safety (FALSE POSITIVE)

**Status:** NO ACTION NEEDED - Python's `smtplib.SMTP` context manager guarantees `quit()` is called via `__exit__` even if exceptions occur.

**Verification:**
- Code uses proper `with smtplib.SMTP(...) as server:` pattern

---

## WAVE M-2: HIGH-PRIORITY IMPROVEMENTS (Can Parallelize)

**Each item can be executed by a separate sub-agent.**

### M-2.1: Add Missing API Endpoint Documentation

**File:** `docs/routes/api-routes.md`

**Issue:** Missing `POST /api/subscribers` endpoint documentation.

**Implementation:**
Add to `docs/routes/api-routes.md` after the subscribers section:
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
```json
{
  "id": 1,
  "email": "user@example.com",
  "confirmed": false,
  "created_at": "2026-05-22T10:00:00Z"
}
```

**Location in code:** `app/routes/api/subscribers.py:76`
```python
@api.route("/subscribers", methods=["POST"])
@require_api_key
@limiter.limit(WRITE_LIMIT)
def create_subscriber() -> any:
```

---

### M-2.2: Fix Webhook Model Documentation

**File:** `docs/infrastructure/webhooks.md:17-30`

**Issue:** Documentation shows `secret = db.Column(db.String(64))` but actual uses `webhook_secret_encrypted = db.Column(db.LargeBinary(256))` with property getter/setter.

**Implementation:**
Update the Webhook Model section:
```markdown
### Webhook Model

| Field | Type | Description |
|-------|------|-------------|
| webhook_secret_encrypted | LargeBinary(256) | Encrypted webhook secret using AES-256-GCM |
| secret | Property | Decrypted secret (read/write via property) |
```

**Location in code:** `app/models.py:490-517`
```python
webhook_secret_encrypted = db.Column(db.LargeBinary(256), nullable=True)
# ... property secret getter/setter at lines 499-517
```

---

### M-2.3: Add WebhookEvent delivery_status Documentation

**File:** `docs/infrastructure/webhooks.md`

**Issue:** Missing `delivery_status` field that tracks `'failed'`, `'partial_failure'`, `'delivered'`.

**Implementation:**
Add to WebhookEvent section:
```markdown
### delivery_status Values

| Value | Description |
|-------|-------------|
| `delivered` | All webhooks succeeded |
| `partial_failure` | Some succeeded, some failed |
| `failed` | All failed |

**Field location:** `app/models.py:533`
```python
delivery_status = db.Column(db.String(32), nullable=True)
```

---

### M-2.4: Create Search Provider Documentation

**Files:** `docs/services/search.md` (NEW), `docs/services/overview.md`

**Issue:** Search provider abstraction (`SearchProvider`, `SQLiteSearchProvider`, `PostgreSQLSearchProvider`) has no module documentation.

**Implementation:**

Create `docs/services/search.md`:
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
```

## Interface

See `app/services/search/__init__.py:7-68` for `SearchProvider` abstract class with methods:
- `search(query, limit)` - Full-text search
- `index_post(post_id, title, body, summary)` - Index a post
- `remove_post(post_id)` - Remove from index
- `rebuild_index()` - Rebuild entire index
- `get_snippets(post_ids, query)` - Get search snippets
```

Update `docs/services/overview.md` to add Search to services table:
```markdown
| Search | `app/services/search/` | FTS5 and PostgreSQL support |
```

---

### M-2.5: Document Two Backup Implementations

**File:** `docs/services/overview.md`, `docs/tasks/scheduler.md`

**Issue:** Overview implies both backup implementations have encryption/compression but scheduler version does not.

**Implementation:**
Add to `docs/services/overview.md`:
```markdown
## Backup Implementations

There are two separate backup implementations:

| Implementation | Location | Encryption | Compression |
|---------------|----------|------------|-------------|
| Celery task | `app/services/backup.py:create_backup()` | AES-256-GCM with PBKDF2 | Yes (.gz) |
| APScheduler | `app/scheduler.py:run_daily_backup()` | None | None |

Both use `blog_*.db` naming pattern.
```

Update `docs/tasks/scheduler.md` to note the backup implementation differences.

---

### M-2.6: Add HEALTH_CHECK_SECRET Documentation

**File:** `docs/deployment/docker.md`

**Issue:** `HEALTH_CHECK_SECRET` for authenticated detailed health checks not documented.

**Implementation:**
Add section:
```markdown
### Authenticated Health Check

For detailed health information, authenticate with `HEALTH_CHECK_SECRET`:

```
GET /health?secret=<value>&detailed=true
```

Requires `HEALTH_CHECK_SECRET` environment variable in docker-compose.yml.

**Location:** `app/routes/public/meta.py:199-203`
```

---

### M-2.7: Add Optional Health Checks Clarification

**File:** `docs/deployment/docker.md`

**Implementation:**
Add table:
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

**Location:** `app/routes/public/meta.py:286-293`

---

### M-2.8: Fix docker-compose.yml SESSION_COOKIE_SECURE

**File:** `docker-compose.yml:14`

**Issue:** `SESSION_COOKIE_SECURE=${SESSION_COOKIE_SECURE:-true}` passes string "true" not boolean.

**Implementation:**
Option A - Use string for env interpolation (Flask handles truthiness):
```yaml
SESSION_COOKIE_SECURE: "${SESSION_COOKIE_SECURE:-true}"
```
Note: Flask will evaluate the string "true" as truthy.

Option B - Document that string handling is intentional:
Add comment in docker-compose.yml:
```yaml
# SESSION_COOKIE_SECURE: Flask evaluates string "true"/"false" as boolean
SESSION_COOKIE_SECURE: "${SESSION_COOKIE_SECURE:-true}"
```

---

### M-2.9: Add blog_logs Volume to Celery

**File:** `docker-compose.yml`

**Issue:** Celery service mounts `blog_data` and `blog_uploads` but not `blog_logs`. Celery logs go to container stdout only.

**Implementation:**
In docker-compose.yml, find the celery service volumes section and add:
```yaml
- blog_logs:/home/blog/logs
```

Current celery volumes (missing blog_logs):
```yaml
volumes:
  - blog_data:/home/blog/instance
  - blog_uploads:/home/blog/app/static/uploads
```

Fixed:
```yaml
volumes:
  - blog_data:/home/blog/instance
  - blog_logs:/home/blog/logs
  - blog_uploads:/home/blog/app/static/uploads
```

---

### M-2.10: Fix image-preview.js Documentation

**File:** `docs/frontend/static-assets.md`

**Issue:** Documents `image-review.js` but actual file is `image-preview.js`.

**Implementation:**
Update the Admin JS section:
```markdown
| File | Purpose |
|------|---------|
| image-preview.js | Admin image preview/selection for posts |
```

Also remove any references to `image-review.js` in the documentation.

---

## WAVE M-3: MEDIUM-PRIORITY DOCUMENTATION FIXES (Can Parallelize)

**Each item can be executed by a separate sub-agent.**

### M-3.1: Add Missing Routes Documentation

**M-3.1a:** Document `POST /admin/preview-markdown`
- Location: `app/routes/admin/posts/editor.py:328`
- For markdown preview during editing

**M-3.1b:** Document `POST /admin/series/<int:series_id>/reorder`
- Location: `app/routes/admin/series.py:259`
- AJAX reorder endpoint

**M-3.1c:** Document `GET /confirm/<token>` and `GET /unsubscribe/<token>`
- Location: `app/routes/public/subscribe.py:117,159`
- Public subscription confirmation and unsubscription

---

### M-3.2: Fix HTTP Method Documentation

**M-3.2a:** Tag delete uses POST not DELETE
- Location: `app/routes/admin/tags.py:87`
- Doc fix: Change `DELETE /admin/tags/delete/<id>` to `POST /admin/tags/delete/<id>`

**M-3.2b:** Series delete uses POST not DELETE
- Location: `app/routes/admin/series.py:132`
- Doc fix: Change `DELETE /admin/series/<id>/delete` to `POST /admin/series/<id>/delete`

---

### M-3.3: Clarify Tag Pagination

**File:** `docs/routes/public-routes.md`

**Issue:** Documents `/tag/<slug>/<int:page>` but actual uses `?page=N` query parameter.

**Implementation:**
Update to:
```markdown
### GET /tag/<slug>

Query parameters:
- `page` - Page number (default: 1)
```

**Location:** `app/routes/public/browse.py:228`
```python
page = request.args.get("page", 1, type=int)
```

---

### M-3.4: Document Feed Caching

**File:** `docs/routes/rss-feeds.md`

**Implementation:**
Add section:
```markdown
## Caching

- Response cached for 5 minutes
- ETag support with `If-None-Match` header
- Conditional GET returns `304 Not Modified` when cached
```

**Location:** `app/routes/rss.py:108-110,192-194,243-245`

---

### M-3.5: Add Missing Configuration Options

**File:** `docs/core/configuration.md`

**Add documentation for:**
- `PAGE_VIEW_BUFFER_SIZE` - Page view buffering threshold (default: 100)
- `SEARCH_PROVIDER` - Search provider selection ("sqlite" or "postgresql")
- `SEARCH_CONFIG` - Provider-specific config
- `DATA_BACKUP_DIR` - Backup directory location

---

### M-3.6: Document AdminSession.last_activity

**File:** `docs/core/models.md`

**Implementation:**
Add to AdminSession model table:
```markdown
| last_activity | DateTime | Last activity timestamp |
```

**Location:** `app/models.py:333`
```python
last_activity = db.Column(UTCDateTime, default=utc_now)
```

---

### M-3.7: Document PostRevision.author_id

**File:** `docs/core/models.md`

**Implementation:**
Add to PostRevision model table:
```markdown
| author_id | Integer | Foreign key to User who created revision |
```

**Location:** `app/models.py:246`
```python
author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
```

---

### M-3.8: Clarify RATE_LIMIT_STORAGE_URI Logic

**File:** `docs/core/configuration.md`

**Implementation:**
Add note:
```markdown
### RATE_LIMIT_STORAGE_URI

Redis is only used when `FLASK_ENV=production`. In development, in-memory storage is used.
```

**Location:** `app/config.py:129-132`
```python
if FLASK_ENV == "production":
    RATE_LIMIT_STORAGE_URI = REDIS_URL
else:
    RATE_LIMIT_STORAGE_URL = "memory://"
```

---

### M-3.9: Add Account Lockout Configuration

**File:** `docs/deployment/security.md`

**Implementation:**
Add section:
```markdown
## Account Lockout

Failed login attempts are tracked with:
- `MAX_FAILED_ATTEMPTS` - Number of failed attempts before lockout (default: 5)
- `LOCKOUT_DURATION_MINUTES` - Lockout duration in minutes (default: 15)
```

**Location:** `app/config.py:142-143`

---

### M-3.10: Document Backup Filename Security

**File:** `docs/routes/admin-routes.md` or `docs/infrastructure/storage.md`

**Implementation:**
Add note about `BACKUP_FILENAME_RE` security measure preventing path traversal:
```markdown
### Backup Filename Validation

Backups must match pattern `blog_\d{8}_\d{6}\.db(\.gz)?` to prevent path traversal attacks.
The regex `BACKUP_FILENAME_RE` validates all backup filenames.
```

**Location:** `app/routes/admin/backup.py:95,120,182,213`

---

### M-3.11: Add Series Relationship Ordering Note

**File:** `docs/core/models.md`

**Implementation:**
Add to PostSeries model:
```markdown
### Series.posts Relationship

Posts are ordered by `PostSeries.order_index` (not by date or title).
```

**Location:** `app/models.py:558`
```python
posts = db.relationship("Post", secondary="post_series", back_populates="series", order_by="PostSeries.order_index")
```

---

### M-3.12: Remove STORAGE_BACKEND from Environment Table

**File:** `docs/deployment/docker.md`

**Issue:** `STORAGE_BACKEND` not used in docker-compose.yml.

**Implementation:**
Remove from environment variables table, or add actual usage to docker-compose.yml.

---

## WAVE M-4: LOW-PRIORITY IMPROVEMENTS (Can Parallelize)

**Each item can be executed by a separate sub-agent.**

### M-4.1: Remove Dead Code extract_snippet()

**File:** `app/search.py:253-279`

**Issue:** `extract_snippet()` function is defined but never called by `get_search_snippets()` which uses native FTS5 snippet() instead.

**Implementation:**
Either:
1. Remove the function if truly unused, OR
2. Update `get_search_snippets()` to use it instead of native FTS5 snippet()

Note: Function is used in tests (`tests/test_search.py:189-210`), so it's not completely dead code.

---

### M-4.2: Document AVIF Status

**File:** `docs/infrastructure/storage.md`

**Implementation:**
Add note:
```markdown
## AVIF Support

AVIF variant generation is planned but not yet implemented. The `post_image_avif_url_stub` filter returns `None`.
```

**Location:** `app/filters.py:75-84` - `post_image_avif_url_stub` filter

---

### M-4.3: Add Multi-Container Deployment Warning

**File:** `docs/tasks/scheduler.md`

**Implementation:**
Add warning:
```markdown
## Multi-Container Deployment

APScheduler uses FileLock which only works on a single machine. In multi-container deployments, each container runs its own scheduler. Without external coordination (Redis, etcd), jobs may run on all replicas simultaneously.
```

**Location:** `app/scheduler.py:3-8`

---

### M-4.4: Document Email Wrapper Task Pattern

**File:** `docs/infrastructure/email.md` or `docs/tasks/celery-tasks.md`

**Implementation:**
Add note explaining `send_confirmation_task` and `send_password_reset_task` wrap synchronous email functions:
```markdown
## Email Task Wrappers

`send_confirmation_task` and `send_password_reset_task` wrap synchronous email functions (`send_confirmation_email` and `send_password_reset_email`). They provide async execution via Celery but don't add retry logic on top of the sync functions.
```

---

### M-4.5: Add Celery Task Failure Logging

**File:** `app/tasks.py:172-175`

**Implementation:**
Add logging when newsletter attempts fail repeatedly (similar to scheduler.py:100-106):
```python
if total_subscribers and i % 50 == 0:
    current_app.logger.info(f"Newsletter progress: {i}/{total_subscribers}")
# Add: log failed post info if retries fail
```

---

### M-4.6: Document Slug Collision Limit

**File:** `docs/services/slug.md` or `docs/core/models.md`

**Implementation:**
Add note:
```markdown
## Slug Generation

Slug collision limit is 100 tries before falling back to UUID suffix.

**Location:** `app/services/slug.py:32,40`
```python
for counter in range(1, 101):  # 100 attempts
    # ...
if counter > 100:
    slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"
```
```

---

### M-4.7: Document APScheduler Daemon Mode

**File:** `docs/tasks/scheduler.md`

**Implementation:**
Add note:
```markdown
The scheduler runs as a daemon thread and will not prevent process exit.
```

**Location:** `app/scheduler.py:290`
```python
scheduler = BackgroundScheduler(deamon=True)  # Note: daemon=True
```

---

### M-4.8: Document Newsletter Retry Configuration

**File:** `docs/tasks/celery-tasks.md`

**Implementation:**
Add note:
```markdown
## Newsletter Retry Behavior

`NEWSLETTER_MAX_RETRY_ATTEMPTS` (default: 5) controls retry behavior. The Celery task does not have the same retry-exclusion logic as APScheduler scheduler.

Celery task has `max_retries=3` but email tasks (`send_confirmation_task`, `send_password_reset_task`) catch exceptions and return False, making max_retries ineffective.
```

---

### M-4.9: Add E2E Server Startup Race Condition Note

**File:** `docs/testing/e2e-tests.md` or `e2e/conftest.py`

**Implementation:**
Document potential race conditions and solution:
```markdown
## Server Startup

E2E tests use `time.sleep(1)` for server startup synchronization. On slow systems, this may be insufficient. If tests fail with connection errors on port 5010, increase the sleep duration or implement health check polling.
```

---

### M-4.10: Document celery --concurrency=1

**File:** `docs/deployment/docker.md` or `docker-compose.yml` comment

**Implementation:**
Add comment in docker-compose.yml:
```yaml
# Celery worker runs with single concurrency
command: celery -A app.tasks worker --loglevel=info --concurrency=1
```

---

### M-4.11: Add docker wait redis Documentation

**File:** `docs/deployment/cicd.md`

**Implementation:**
Add note:
```markdown
In CI/CD e2e-tests job, `docker-compose wait redis` ensures Redis is ready before starting application services.
```

**Location:** `.github/workflows/test.yml:120`

---

### M-4.12: Document FakeSubscriber Dataclass

**File:** `docs/testing/test-suite.md`

**Implementation:**
Add to fixture documentation:
```markdown
### FakeSubscriber

Dataclass at `tests/conftest.py:56-64` useful for newsletter tests without real subscribers.

```python
@dataclass
class FakeSubscriber:
    id: int
    email: str
    confirmed: bool = True
```
```

---

### M-4.13: Clarify mock_email Fixture Chaining

**File:** `docs/testing/test-suite.md`

**Implementation:**
Clarify that `mock_email` chains `mock_render` and `mock_smtp` but actual mocking happens in those individual fixtures:
```markdown
## mock_email Fixture

`mock_email` is a pass-through fixture that yields `mock_render` and `mock_smtp`. The actual mocking happens via autouse in those individual fixtures.
```

---

### M-4.14: Document clean_db Nested Transaction Pattern

**File:** `docs/testing/test-suite.md`

**Implementation:**
Add note explaining `db.session.begin_nested()` for test data cleanup in benchmarks:
```markdown
## clean_db Fixture

Uses `db.session.begin_nested()` to create a savepoint for test data cleanup. On cleanup, rollback reverts all changes made during the test.

**Location:** `benchmarks/conftest.py:55-60`
```

---

## PHASE 5: VERIFIED COMPLETED ITEMS

The following items were verified to already be correct in the codebase:

### Wave L Completed Items (Previously Verified)

| Item | Status | Notes |
|------|--------|-------|
| L-1.1 (mobile-menu.jsx) | NO SYNTAX ERROR | code is syntactically correct |
| L-1.2 (webhook logger) | ALREADY EXISTS | `logger = logging.getLogger(__name__)` at module level |
| L-1.3 (preview route docs) | CORRECT | Both HMAC AND session required |
| L-2.1 (search.html srcset) | CORRECT | srcset properly defined before use |
| L-2.2 (APScheduler SMTP) | CORRECT | Only newsletter disabled, other jobs run unconditionally |
| L-3.1 (tag cache TTL) | CORRECT | 60 seconds documented correctly |
| L-3.2 (slug signature) | CORRECT | Documentation matches implementation |
| L-3.3 (backup retention) | CORRECT | `blog_*.db` pattern documented correctly |
| L-3.5 (Post user_id) | CORRECT | Documentation does NOT claim user_id exists |
| L-3.6 (image fields) | CORRECT | Documentation shows image and image_alt_text |
| L-3.7 (admin revisions route) | CORRECT | Route correctly documented |
| L-4.1 (celery concurrency) | CORRECT | `--concurrency=1` already in docker-compose.yml |
| L-4.2 (pip-audit) | CORRECT | `--fail-on=all` already in CI |

### Wave M Verified Items (New)

| Item | Status | Notes |
|------|--------|-------|
| Benchmark conftest import | CORRECT | Both files use same path `app.routes.admin` |
| Webhook encryption docs | CORRECT | Already shows `app/webhook_encryption.py` |
| Queue line numbers | CORRECT | Match actual code |
| Lock files | CORRECT | All 4 documented correctly |
| Indexes in models.md | CORRECT | All indexes present |
| prism.min.js location | CORRECT | At `app/static/js/prism.min.js` |
| _breadcrumbs.html | CORRECT | Only admin version exists |
| API routes | FIXED | Removed non-existent `POST /api/subscribers/export` |
| [search] section | CORRECT | Present in config example |
| Health check docs | CORRECT | All details documented |
| Encryption key requirements | CORRECT | Both files accurate |
| Resource limits | CORRECT | Memory limits documented |

---

## Parallelization Strategy for Sub-Agents

### Agent Assignment Recommendations

**Agent 1 (Critical - Sequential):**
- Execute M-1.1, M-1.2 first (these fix bugs)
- M-1.3, M-1.4 are already fixed (verify only)

**Agent 2 (High Priority - 10 items):**
- Execute M-2.1 through M-2.10
- These are documentation fixes, can parallelize

**Agent 3 (Medium Priority - 12 items):**
- Execute M-3.1 through M-3.12
- Documentation fixes, can parallelize

**Agent 4 (Low Priority - 14 items):**
- Execute M-4.1 through M-4.14
- Minor improvements, can parallelize

### Execution Order

```
1. Agent 1 completes M-1.1, M-1.2 (MUST be sequential)
2. Agents 2, 3, 4 can run in PARALLEL after M-1 completion
```

### Verification Steps

Each agent should:
1. Read the implementation details for their items
2. Locate the file(s) and line numbers specified
3. Make the change
4. Run verification commands specified
5. Update the item status when complete

---

## Files Requiring Changes Summary

| Priority | Items | Files |
|----------|-------|-------|
| Critical | M-1.1, M-1.2 | main.js, tasks.py |
| High | M-2.1-M-2.10 | api-routes.md, webhooks.md, services/*.md, docker.md, docker-compose.yml, static-assets.md |
| Medium | M-3.1-M-3.12 | public-routes.md, rss-feeds.md, configuration.md, models.md, security.md, admin-routes.md, storage.md |
| Low | M-4.1-M-4.14 | search.py, scheduler.md, celery-tasks.md, e2e/conftest.py, test-suite.md |

---

## Important Context for Future Agents

### When Implementing Plan Items

1. **Always verify against actual code** - Plan items are derived from architecture reviews and may contain errors. Double-check file locations and line numbers before making changes.

2. **Check for dependencies** - Some items may depend on others being completed first. Check the wave structure before starting.

3. **Use subagents for parallel work** - Phases 2-4 can be executed by multiple sub-agents working in parallel.

4. **Test after making changes** - Run relevant tests to verify fixes didn't break anything.

5. **Update status when complete** - Mark items as completed when verified.

### Key Implementation Patterns

**Backup Implementations:**
- `app/services/backup.py:create_backup()` - Celery task with AES-256-GCM encryption
- `app/scheduler.py:run_daily_backup()` - APScheduler version, no encryption

**APScheduler Jobs:**
- `cleanup_expired_subscribers` - every 5 minutes (`minute="*/5"`)
- `run_daily_backup` - at 02:00 UTC (`hour=2, minute=0`)
- `send_daily_newsletter` - only runs when SMTP_HOST is configured

**Health Check:**
- Critical checks: database, scheduler, search, disk_space, db_integrity
- Optional checks: backup_freshness, email, redis, celery (don't affect status)

**Email Task Retry:**
- `send_confirmation_task` and `send_password_reset_task` catch exceptions and return False
- This makes `max_retries=3` ineffective (fix in M-1.2)

**Webhook Encryption:**
- `Webhook.secret` uses AES-256-GCM via `app/webhook_encryption.py`
- Stored as `webhook_secret_encrypted` (LargeBinary) in database

**Search Provider:**
- `SearchProvider` abstract class in `app/services/search/__init__.py`
- `SQLiteSearchProvider` - current default using FTS5
- `PostgreSQLSearchProvider` - stub for future

**Slug Generation:**
- Collision limit is 100 tries before UUID fallback
- UUID format: `{base_slug}-{8_char_hex}`

**Context Processors:**
- `inject_csrf()` - csrf_token and csp_nonce
- `inject_config()` - site config variables
- `inject_theme()` - theme settings and custom_css
- `inject_footer_data()` - footer links and data
- `inject_show_footer_posts()` - show_footer_posts boolean

**Template Filters:**
- `markdown_safe`, `reading_time`, `sanitize_css`
- `post_image_url`, `post_image_srcset`, `post_image_avif_url_stub`

---

*Last updated: May 2026 - Wave M consolidated plan*