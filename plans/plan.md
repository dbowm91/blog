# Implementation Plan - Blog CMS

**Project:** Blog CMS
**Status:** ACTIVE - Maintenance mode
**Last Updated:** May 2026

---

## Overview

This is the consolidated implementation plan for the Blog CMS project. It serves as the single source of truth for:
- Completed implementation waves (A-I)
- Key implementation details verified against the codebase
- Important patterns and conventions for future agents
- Guidance for creating new implementation waves

**Note:** This file was consolidated in May 2026. All prior plan files have been merged into this document.

---

## Completed Implementation Waves

| Wave | Description | Items | Status |
|------|-------------|-------|--------|
| A | 2FA Security (TOTP + Backup Codes) | 2 | COMPLETED |
| B | Rate Limiting Infrastructure | 1 | COMPLETED |
| C | Search Infrastructure (PostgreSQL) | 1 | COMPLETED |
| D | Frontend Enhancements (Vite + AVIF) | 2 | COMPLETED |
| E | Performance (Brotli) | 1 | COMPLETED |
| F | Bug Fixes (Security & Functional) | 12 | COMPLETED |
| G | Code Quality | 5 | COMPLETED |
| H | Documentation | 37 | COMPLETED |
| I | Enhancements | 0 | N/A |
| J | Architecture Review Fixes | 39+ | COMPLETED |

**Total: 61+ items completed**

---

## Wave J: Architecture Review Fixes

**Completed:** May 2026

Fixed documentation issues identified during architecture review in May 2026. Subagents were used to fix Core, Services, Infrastructure, Routes, Tasks, Testing, Frontend, and Deployment documentation.

### Core Documentation Fixes

**Files:** `architecture/core/models.md`

- Added missing model documentation: AdminSession, Series, PostSeries, Webhook, WebhookEvent
- Verified totp_secret property documentation (encrypted column with property that decrypts on access)
- SESSION_IP_BINDING modes documented ("warn" vs "enforce")

### Services Documentation Fixes

**Files:** `architecture/services/backup.md`

- Clarified backup naming: both `create_backup()` and `run_daily_backup()` create `blog_*.db` files
- `cleanup_old_backups()` only handles `blog_*` files
- `run_daily_backup()` manages retention internally via `backup_*.db` pattern
- Decryption output path clarified (`.decrypted` appended for non-.gpg files)

### Routes Documentation Fixes

**Files:** `architecture/routes/admin-routes.md`, `architecture/routes/public-routes.md`, `architecture/routes/api-routes.md`

- 2FA routes corrected: `/admin/2fa/setup`, `/admin/2fa/verify` (not `/admin/2fa-setup`)
- Series route added: `GET /series/<slug>`
- Archive route added: `GET /archive`
- Short URL route added: `GET /s/<code>`
- Rate limits corrected: reads 20/min, writes 10/min

### Tasks Documentation Fixes

**Files:** `architecture/tasks/scheduler.md`

- `send_daily_newsletter` runs synchronously (not via Celery)
- FileLock details: `timeout=0` behavior, lock file locations
- Newsletter retry logic documented (`NEWSLETTER_MAX_RETRY_ATTEMPTS`)
- `publish_scheduled_posts` syncs FTS and invalidates tag cache

### Testing Documentation Fixes

**Files:** `architecture/testing/test-suite.md`

- Directory structure corrected: flat `tests/` structure (no unit/integration subdirs)
- E2E file corrected: `test_e2e.py` with classes
- All fixtures documented
- Buffer protection autouse pattern documented

### Frontend Documentation Fixes

**Files:** `architecture/frontend/static-assets.md`, `architecture/frontend/templates.md`

- JS module initialization pattern documented (`export default function initXxx()`)
- `post_image_avif_url_stub` filter documented
- Context processors and cache invalidation functions documented

### Deployment Documentation Fixes

**Files:** `architecture/deployment/docker.md`, `architecture/deployment/security.md`, `architecture/deployment/cicd.md`

- APScheduler multi-worker limitation documented
- Referrer-Policy mismatch noted (Flask vs nginx)
- Test running command documented

---

## Key Implementation Details (Verified May 2026)

### 2FA Implementation (Wave A)

**Location:** `app/routes/admin/auth.py`, `app/models.py`, `app/services/encryption.py`

**TOTP Encryption:**
- TOTP secrets are encrypted at rest using AES-256-GCM (`app/services/encryption.py`)
- `User.totp_secret` is a property that decrypts on access (lines 43-52 in `app/models.py`)
- `KEY_SIZE = 32` (256 bits) for AES-256-GCM

**Backup Codes:**
- Stored as SHA-256 hashed strings in `backup_codes_hashed`
- Single-use: verified codes are removed from the list
- 10 backup codes generated per setup

**Routes:**
- `/admin/2fa/setup` - Initialize 2FA (line 263 in `auth.py`)
- `/admin/2fa/verify` - Verify TOTP code (line 312)
- `/admin/2fa/backup-codes` - View/generate backup codes (line 420)
- `/admin/2fa/disable` - Disable 2FA (line 436)

---

### Rate Limiting (Wave B)

**Location:** `app/config.py`, `app/middleware/rate_limit.py`

- `ADMIN_RATE_LIMITS` defined in `app/config.py` (lines 145-152)
- `AdminRateLimiter` class in `app/middleware/rate_limit.py` (line 32)
- Flask-Limiter integrated with `key_func=get_client_ip`

---

### Search Abstraction (Wave C)

**Location:** `app/services/search/__init__.py`, `app/services/search/sqlite.py`, `app/services/search/postgresql.py`

**Architecture:**
- `SearchProvider` abstract class with `@abstractmethod` decorators
- Methods: `search`, `index_post`, `remove_post`, `rebuild_index`, `get_snippets`

**Implementations:**
- `SQLiteSearchProvider` - wraps existing FTS5 functionality in `app/search.py`
- `PostgreSQLSearchProvider` - stub for future implementation (requires schema changes)

**Factory:**
- `get_search_provider()` selects provider based on `SEARCH_PROVIDER` config

---

### Frontend (Wave D)

**Location:** `vite.config.js`, `app/filters.py`

**Vite Configuration:**
- Code splitting with `manualChunks` (lines 14-19)
- Chunks: 'vendor', 'admin', 'public'

**AVIF Support:**
- `post_image_avif_url_stub` filter in `app/filters.py` (lines 75-85)
- Currently returns `None` - placeholder until AVIF encoding is implemented

---

### Brotli Compression (Wave E)

**Location:** `nginx/nginx.conf`

- Nginx configuration includes commented Brotli settings (lines 26-34)
- Requires custom nginx image with `--with-http_brotli_module`

---

### Error Handling Fixes (Wave F)

All high-risk files have been fixed with specific exception handling:

| File | Issue Fixed | Verification |
|------|-------------|--------------|
| `app/routes/public/meta.py` | Uses `OperationalError, ProgrammingError` for DB checks; generic `except Exception` only for optional checks (redis, celery, backup_freshness) | Line 214, 232, 248 |
| `app/email.py` | Catches specific SMTP exceptions: `SMTPAuthenticationError, SMTPConnectError, SMTPSenderRefused, SMTPServerDisconnected, SMTPException` plus `OSError` | Lines 94, 115-120 |
| `app/backup_integrity.py` | Catches `sqlite3.Error, OSError, ValueError, TypeError` | Lines 77-80 |
| `app/webhooks.py` | `deliver_webhook()` returns `(False, str(e))` on error; `create_webhook_event()` logs with `logger.error()` | Lines 83, 111 |
| `app/tasks.py` | All tasks use specific exceptions: `ClientError, BotoCoreError`, `SQLAlchemyError, OSError, ImportError`, `requests.RequestException` | Multiple locations |
| `app/page_view_buffer.py` | Uses `SQLAlchemyError, OSError` - specific types | Lines 126, 189 |

---

### Code Quality (Wave G)

**Deprecation Notice:**
- `deliver_webhook()` in `app/webhooks.py` is deprecated (lines 55-59)
- Use `deliver_webhook_task` Celery task instead for all webhook deliveries

---

## Additional Implementation Details

The following features were implemented but not originally documented in plan waves. They are verified and included here for completeness.

### Comment Model

**Location:** `app/models.py:573-596`

**Pattern:** Uses `back_populates` for parent/child relationships:
```python
parent = db.relationship("Comment", remote_side=[id], back_populates="replies")
replies = db.relationship("Comment", back_populates="parent", lazy="select")
```

### Feed Endpoints

**Location:** `app/routes/rss.py`

Three feed endpoints with caching and ETag support:
- `/atom` - Atom 1.0 feed
- `/rss` - RSS 2.0 feed  
- `/json` - JSON Feed 1.1

**Cache Pattern:**
```python
flask_cache.delete("rss_feed_posts")  # Invalidates on post changes
```

### Webhook Event Triggering

**Pattern:** Trigger webhooks at key state transitions:
```python
# Post publish/unpublish in app/routes/api/posts.py:294-295
if "published" in data and was_published != post.published:
    from app.webhooks import create_webhook_event
    create_webhook_event(
        event_type="post.published" if post.published else "post.unpublished",
        payload={"post_id": post.id, "title": post.title, "slug": post.slug},
        target_id=post.id,
        target_type="post"
    )

# Subscriber confirmation in app/routes/public/subscribe.py:147-148
sub.confirmed = True
# ... after commit ...
create_webhook_event(
    event_type="subscriber.confirmed",
    payload={"subscriber_id": sub.id, "email": sub.email},
    target_id=sub.id,
    target_type="subscriber"
)
```

**Models:** `Webhook` and `WebhookEvent` in `app/models.py:484-520`

### Snippet Batching (SQLite Parameter Limits)

**Location:** `app/search.py:298`, `app/services/search/sqlite.py`

```python
_SQLITE_MAX_VARS = 500  # Maximum variables per query

# Batch processing pattern:
chunk_size = 500
for i in range(0, len(post_ids), chunk_size):
    chunk = post_ids[i:i + chunk_size]
```

### Health Check Critical Checks

**Location:** `app/routes/public/meta.py:286-294`

Only critical checks affect overall status:
```python
critical_checks = {
    k: v for k, v in checks.items()
    if k in ("database", "scheduler", "search", "disk_space", "db_integrity")
}
```

Optional checks (`backup_freshness`, `email`) do not affect degraded status.

### Page View Buffer System

**Location:** `app/page_view_buffer.py`

- `PageViewBuffer` class handles async page view recording
- `init_page_view_buffer()` - starts buffer on app creation
- `shutdown_page_view_buffer()` - flushes and shuts down
- `record_page_view()` - records view to buffer
- Buffer flushes when size reaches `PAGE_VIEW_BUFFER_SIZE`

**Test Interference:** Disable via `app.config.PAGE_VIEW_BUFFER_SIZE = 0` and call `shutdown_page_view_buffer()`. Use `ensure_buffer_disabled` fixture from `tests/shared_fixtures.py`.

### Admin Audit Log

**Location:** `app/models.py:461-481`

- `AdminAuditLog` model tracks admin actions
- Uses `actor` relationship to User
- Indexes on `action`, `target_type`, `target_id`, `created_at`

### Post Revisions

**Location:** `app/models.py:236-249`

- `PostRevision` model tracks post history
- Stores `title`, `content`, `slug`, `status` at revision time

### User Model Security

**Location:** `app/models.py:63-64`

```python
def __repr__(self):
    return f"<User id={self.id}>"  # Returns ID only, NOT username - PII protection
```

### APScheduler Multi-Worker Limitation

**Location:** `architecture/tasks/scheduler.md`, `architecture/deployment/docker.md`

**Critical:** APScheduler jobs use FileLock which only works on a single machine. In multi-container deployments, each container runs its own APScheduler. Without external coordination (Redis, etcd), jobs may run on all replicas simultaneously.

### Context Processors (Actual Function Names)

**Location:** `app/context_processors.py`

| Function | Injects |
|----------|---------|
| `inject_csrf()` | `csrf_token`, `csp_nonce` |
| `inject_config()` | Site config variables |
| `inject_theme()` | Theme settings, `custom_css` |
| `inject_footer_data()` | Footer links and data |
| `inject_show_footer_posts()` | `show_footer_posts` boolean |

### Tag Cache

**Location:** `app/services/tag.py`, `app/tag_cache.py`

Invalidation pattern:
```python
flask_cache.delete_memoized(_get_tag_counts_cached)
```

### Custom Encryption Errors

**Locations:**
- `app/services/encryption.py:17` - `EncryptionError`
- `app/webhook_encryption.py:17` - `WebhookEncryptionError`

### Celery Backup Isolation

```python
@celery_task
def run_backup_task(backup_dir, compress):
    from app.services.backup import create_backup
    return create_backup(db_path, backup_dir, compress=compress)
```

Run backups as Celery tasks to avoid blocking web requests.

---

## Important Notes for Future Agents

### Security

- **Log ID, not Username**: When logging user actions, always use `user.id`. Never log raw User objects or usernames to prevent PII leakage.
- **Credential Protection**: Never log `SECRET_KEY`, `ADMIN_PASSWORD`, or API keys.

### Configuration

- Configuration priority: env vars > config.toml > defaults
- Newsletter retry count default is 5

### APScheduler Job Schedules

- `cleanup_expired_subscribers` runs every 5 minutes (`minute="*/5"`), NOT hourly
- `run_daily_backup` runs at 02:00 (`hour=2, minute=0`), NOT midnight

### Slug Generation

- Slug collision limit is hardcoded to 100 tries before falling back to UUID suffix (`app/services/slug.py`)

### Celery Queue Names

- Tasks use specific queues: `images`, `newsletter`, `webhooks`, `email`, `backup` (see `app/tasks.py` lines 29, 130, 182, 255, 276, 297)

### Actual Routes (Verify Before Using)

When documenting or referring to routes, verify against actual implementation:
- New post: `/admin/new` (NOT `/admin/posts/new`)
- Edit post: `/admin/edit/<id>` (NOT `/admin/posts/<id>/edit`)
- Tag delete: `POST /admin/tags/delete/<id>` (NOT `DELETE`)
- Comment submission: `POST /post/<slug>/comment` (NOT `/comment/<int:post_id>`)
- Subscribe: Only `POST /subscribe` exists (no GET handler)
- API post publish: Use `PUT /api/posts/<id>` with `{"published": true}` body (NOT `POST /api/posts/<id>/publish`)

### Template Filters (Actual)

Defined in `app/filters.py`:
- `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`, `post_image_avif_url_stub`
- NOT `format_date`, `markdown`, `slugify` (these don't exist)

---

## Wave Execution Pattern

When executing multi-wave implementation plans:

1. **Create separate branches** for each parallel wave to avoid conflicts
2. **Use subagents** with separate branches to parallelize work
3. **Merge to main** after each wave completes
4. **Update plan status** in plan.md after each wave

### Branch Naming Convention

```
wave-j-enhancements
wave-k-bugfixes
```

---

## Creating New Implementation Waves

To propose a new enhancement or bug fix:

1. Create a branch: `wave-<letter>-<description>`
2. Implement the changes following existing patterns
3. Update this file with the new wave information
4. Create a PR for review

---

## File Structure Reference

```
plans/
├── plan.md              # This file - consolidated implementation plan
└── AGENTS.override.md   # Module-specific agent guidance
```

---

*Last updated: May 2026 - Consolidated from prior plan files*
*All items verified against codebase May 2026*