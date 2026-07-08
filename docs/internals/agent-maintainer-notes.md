# Agent Maintainer Notes

Historical implementation caveats, known gotchas, and maintainer context for AI agents. This is a living record of things that aren't obvious from the code alone.

## Table of Contents

- [High-Risk Files](#high-risk-files)
- [Test Interference](#test-interference)
- [Implemented Features](#implemented-features)
- [Future-Agent Reminders](#future-agent-reminders)
- [Deprecated Implementations](#deprecated-implementations)
- [Actual Routes vs. Assumed](#actual-routes)
- [Context Processors](#context-processors)
- [Template Filters](#template-filters)
- [Encryption Modules](#encryption-modules)
- [S3 Storage Gotchas](#s3-storage-gotchas)
- [Task Line Numbers](#task-line-numbers)
- [Test Structure](#test-structure)
- [Misc Implementation Notes](#misc-implementation-notes)

---

## High-Risk Files

These files have been flagged for exception handling issues (all now fixed):

| File | Issue | Status |
|------|-------|--------|
| `app/routes/public/meta.py` | Previously broad exception | FIXED |
| `app/email.py` | SMTP exception too broad | FIXED |
| `app/backup_integrity.py` | Previously broad exception | FIXED |
| `app/webhooks.py` | Silent failure with `pass` | FIXED |
| `app/tasks.py` | Email task retry logic | FIXED |
| `app/page_view_buffer.py` | Previously broad exception | FIXED |

---

## Test Interference

### Page View Buffer

- The page view buffer (`app/page_view_buffer.py`) can cause test interference when running full suite
- Buffer is started during `create_app()` if `PAGE_VIEW_BUFFER_SIZE > 0`
- In tests: disable via `app.config.PAGE_VIEW_BUFFER_SIZE = 0` and call `shutdown_page_view_buffer()`
- The `ensure_buffer_disabled` fixture is in `tests/shared_fixtures.py`

### Test Database Session Issues

- `db.session.refresh()` fails if object isn't in current session
- Fix: Re-query object from database instead of using `refresh()`

---

## Implemented Features

### 2FA Implementation

- TOTP secrets are encrypted at rest using AES-256-GCM (`app/services/encryption.py`)
- `User.totp_secret` is now a property that decrypts on access
- Backup codes are SHA-256 hashed and single-use (8 codes generated, not 10)
- Routes: `/admin/2fa/setup`, `/admin/2fa/verify`, `/admin/2fa/backup-codes`, `/admin/2fa/disable`

### Rate Limiting

- `ADMIN_RATE_LIMITS` defined in `app/config.py`
- `app/middleware/rate_limit.py` provides `AdminRateLimiter` class
- Flask-Limiter already integrated with `key_func=get_client_ip`

### Session IP Binding

- `SESSION_IP_BINDING` config in `app/config.py:89` (default: `"warn"`)
- `"warn"`: logs warning on IP change during session
- `"enforce"`: invalidates session and requires re-login (implemented in `app/routes/admin/__init__.py:32`)

### Search Abstraction

- `SearchProvider` abstract class in `app/services/search/__init__.py`
- `SQLiteSearchProvider` wraps existing FTS5 functionality
- `PostgreSQLSearchProvider` is a stub for future implementation (falls back to SQLite silently)
- `get_search_provider()` factory function selects provider by `SEARCH_PROVIDER` config

### Frontend

- Vite configured for code splitting with `manualChunks`
- `post_image_avif_url_stub` filter is DEPRECATED - always returns None (no conditional AVIF check)

### Brotli

- Nginx configuration includes commented Brotli settings
- Requires custom nginx image with `--with-http_brotli_module`

---

## Future-Agent Reminders

### Backup Implementations

There are two separate backup implementations:

- `app/services/backup.py:create_backup()` - Used by Celery task, supports AES-256-GCM encryption with PBKDF2/compression, uses `blog_*.db` naming
- `app/scheduler.py:run_daily_backup()` - Used by APScheduler, no encryption/compression, uses `blog_*.db` naming

Both now use `blog_*.db` naming, so `cleanup_old_backups()` correctly cleans both.

### Backup Encryption

Backup encryption uses AES-256-GCM with PBKDF2-HMAC-SHA256 key derivation (600,000 iterations) via `app/backup_encryption.py`, NOT GPG. Webhook encryption uses `app/webhook_encryption.py` with a direct 32-byte key (not PBKDF2).

### Slug Generation

Slug collision limit is hardcoded to 100 tries before falling back to UUID suffix (`app/services/slug.py`).

### APScheduler Job Schedules

- `cleanup_expired_subscribers` runs every 5 minutes (`minute="*/5"`), NOT hourly
- `run_daily_backup` runs at 02:00 (`hour=2, minute=0`), NOT midnight

### APScheduler SMTP Handling

When SMTP_HOST is not configured, only the daily newsletter job is disabled. Other scheduler jobs (cleanup_expired_subscribers, publish_scheduled_posts, run_daily_backup) continue to run.

### APScheduler Multi-Worker Limitation

APScheduler jobs use FileLock which only works on a single machine. In multi-container deployments, each container runs its own APScheduler. Without external coordination (Redis, etcd), jobs may run on all replicas simultaneously. This is documented in `architecture/tasks/scheduler.md` and `architecture/deployment/docker.md`.

### Health Check Critical Checks

The health check endpoint (`GET /health`) determines overall status using only critical checks:

- `database`, `scheduler`, `search`, `disk_space`, `db_integrity`
- Optional checks (`backup_freshness`, `email`, `redis`, `celery`) do not affect overall status
- Redis and celery checks are included in detailed health output but don't affect degraded status
- See `architecture/infrastructure/overview.md` for details

### Email Retry Count

Newsletter retry count default is 5 (not 3 as some documentation may claim).

### Critical CSS

The `critical.css` file at `app/static/css/critical.css` provides above-the-fold CSS for fast initial paint. It is loaded in `base.html:22` with `media="screen"` for immediate loading.

### Celery Queue Names

Tasks use specific queues: `images`, `newsletter`, `webhooks`, `email`, `backup` (see `app/tasks.py:31,130,182,262,283,304`)

### User Model `__repr__`

Returns `<User id={self.id}>` for PII/security reasons, not username.

### Comment Model Relationships

The Comment model uses `back_populates` for parent/child relationships:

```python
parent = db.relationship("Comment", remote_side=[id], back_populates="replies")
replies = db.relationship("Comment", back_populates="parent", lazy="select")
```

### Health Check Status Logic

Health check only considers critical checks for overall status (optional services don't affect degraded):

```python
critical_checks = {
    k: v for k, v in checks.items()
    if k in ("database", "scheduler", "search", "disk_space", "db_integrity")
}
```

### Snippet Batching

For SQLite parameter limits, batch post_ids:

```python
chunk_size = 500
for i in range(0, len(post_ids), chunk_size):
    chunk = post_ids[i:i + chunk_size]
```

### Backup Isolation

Run backups as Celery tasks to avoid blocking web requests:

```python
@celery_task
def run_backup_task(backup_dir, compress):
    from app.services.backup import create_backup
    return create_backup(db_path, backup_dir, compress=compress)
```

### Webhook Event Triggering

Webhook events are triggered at key state transitions:

```python
# Post publish/unpublish in app/routes/api/posts.py
if "published" in data and was_published != post.published:
    from app.webhooks import create_webhook_event
    create_webhook_event(
        event_type="post.published" if post.published else "post.unpublished",
        payload={"post_id": post.id, "title": post.title, "slug": post.slug},
        target_id=post.id,
        target_type="post"
    )

# Subscriber confirmation in app/routes/public/subscribe.py
sub.confirmed = True
# ... after commit ...
create_webhook_event(
    event_type="subscriber.confirmed",
    payload={"subscriber_id": sub.id, "email": sub.email},
    target_id=sub.id,
    target_type="subscriber"
)
```

### Feed Endpoints

Three main feed endpoints available:

- `/atom` - Atom 1.0 feed
- `/rss` - RSS 2.0 feed
- `/json` - JSON Feed 1.1

Tag-specific feeds:

- `/tag/<slug>/atom` - Atom 1.0 feed for posts with that tag
- `/tag/<slug>/rss` - RSS 2.0 feed for posts with that tag
- `/tag/<slug>/json` - JSON Feed for posts with that tag

Series-specific feeds:

- `/series/<slug>/atom` - Atom 1.0 feed for posts in that series
- `/series/<slug>/rss` - RSS 2.0 feed for posts in that series
- `/series/<slug>/json` - JSON Feed for posts in that series

Tag and series pages include feed discovery links in `<head>` for RSS readers to auto-detect the feeds.

### Webhook Secret Storage

`Webhook.secret` is a property that decrypts `webhook_secret_encrypted` (LargeBinary column) using AES-256-GCM via `app/webhook_encryption.py` (see `app/models.py:490-517`). Do not document `secret` as a plain-text column.

### WebhookEvent Delivery Status

`WebhookEvent` has a `delivery_status` field tracking delivery outcomes:

- `'delivered'` - All webhooks succeeded
- `'partial_failure'` - Some succeeded, some failed
- `'failed'` - All failed

### Search Provider Architecture

`SearchProvider` abstract class in `app/services/search/__init__.py` with implementations:

- `SQLiteSearchProvider` - Current default using FTS5
- `PostgreSQLSearchProvider` - Stub for future PostgreSQL support

Use `get_search_provider()` factory function to get configured provider based on `SEARCH_PROVIDER` config.

**Important**: `SQLiteSearchProvider` wraps the `app/search.py` module-level functions through the `SearchProvider` interface. Each method delegates to the corresponding FTS5 function (`init_fts`, `search`, `sync_fts`, `remove_fts`, `rebuild_fts`, `get_search_snippets`). The `app/search.py` functions are standalone FTS5 implementations that `SQLiteSearchProvider` calls into.

### Comment Submission Rate Limiting

Comments are rate limited at 10 per minute and require CSRF protection via `validate_csrf_token()`.

- Route: `POST /post/<slug>/comment` in `app/routes/public/comments.py`
- Rate limit: `@limiter.limit("10 per minute")`
- CSRF: Hidden `csrf_token` field in form, validated before processing

---

## Deprecated Implementations

### Deprecated Function

`deliver_webhook()` in `app/webhooks.py` is deprecated - use `deliver_webhook_task` Celery task instead for all webhook deliveries.

### S3 Credential Clearing Bug

`_clear_credentials()` method in `S3StorageBackend` was removed because it broke client recreation. The method was called after client initialization in `storage.py:168-174`.

### CSRF Token Rotation Is On Every Use

`app/csrf.py` rotates tokens on every successful validation, not specifically on privilege changes. The claim in `architecture/deployment/security.md` about "token rotation on privilege changes" is not accurate - that feature is not implemented.

### image-preview.js Not image-review.js

The admin image preview module is named `image-preview.js`, NOT `image-review.js`. Code imports in `main.js:15,40,51` reference the wrong filename.

---

## Actual Routes

When documenting or referring to routes, verify against actual implementation:

- New post: `/admin/new` (NOT `/admin/posts/new`)
- Edit post: `/admin/edit/<id>` (NOT `/admin/posts/<id>/edit`)
- Tag delete: `POST /admin/tags/delete/<id>` (NOT `DELETE`)
- Comment submission: `POST /post/<slug>/comment` (NOT `/comment/<int:post_id>`)
- Subscribe: Only `POST /subscribe` exists (no GET handler)
- API post publish: Use `PUT /api/posts/<id>` with `{"published": true}` body (NOT `POST /api/posts/<id>/publish`)
- `POST /api/auth` does NOT exist — `app/routes/api/auth.py` contains only `require_api_key` decorator
- `POST /api/subscribers/export` does NOT exist — only admin export at `GET /admin/subscribers/export`

---

## Context Processors

Actual context processor function names (not the injected variable names):

- `inject_csrf()` - Injects `csrf_token` and `csp_nonce`
- `inject_config()` - Injects site config variables
- `inject_theme()` - Injects theme settings and `custom_css`
- `inject_footer_data()` - Injects footer links and data
- `inject_show_footer_posts()` - Injects `show_footer_posts` boolean

---

## Template Filters

Actual filters (defined in `app/filters.py`):

- `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`, `post_image_avif_url_stub`
- NOT `format_date`, `markdown`, `slugify` (these don't exist)

---

## Encryption Modules

Three distinct encryption modules with different key derivation strategies:

- `app/backup_encryption.py` — PBKDF2-HMAC-SHA256 (600K iterations) for backup files
- `app/webhook_encryption.py` — Direct 32-byte key (no PBKDF2) for webhook secrets
- `app/services/encryption.py` — Direct AES-256-GCM using SECRET_KEY for TOTP secrets

---

## S3 Storage Gotchas

### Client Initialization

S3StorageBackend stores credentials at client creation time (not per-request). Credentials remain on the instance to allow client recreation if needed.

### S3 Storage Configuration

S3 settings are read from environment variables, NOT from config.toml or config files:

- `S3_BUCKET`, `S3_REGION`, `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_PUBLIC_URL`
- See `app/storage.py:41` for direct env var reading

---

## Task Line Numbers

Actual line numbers in `app/tasks.py`:

- `generate_image_variants`: 28
- `send_newsletter_task`: 127
- `deliver_webhook_task`: 184
- `send_confirmation_task`: 263
- `send_password_reset_task`: 284
- `run_backup_task`: 305

---

## Test Structure

- Tests are organized across 36 test files covering models, routes, API, search, security, and more
- Run `ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python3 -m pytest tests/ --collect-only` to get current count
- E2E tests use `pytest-playwright`, NOT `@playwright/test`
- All E2E tests are in `tests/e2e/test_e2e.py` with 4 classes: `TestAdminLogin`, `TestPostCreation`, `TestNewsletterSubscription`, `TestMobileResponsiveness`
- RSS/Atom feed tests are in `tests/test_coverage.py`, NOT in a separate `test_rss.py` file
- Benchmark tests in `tests/benchmarks/` don't use a `client` fixture - they create clients ad-hoc with `app.test_client()` within each test function

---

## Misc Implementation Notes

### SMTP Exception Handling

When catching SMTP exceptions, catch both specific subclasses and base classes:

- `smtplib.SMTPException` (base class)
- `smtplib.SMTPServerDisconnected`

These may leak as unhandled exceptions if not explicitly caught.

### Email Task Retry Logic

`send_confirmation_task` and `send_password_reset_task` in `app/tasks.py` now have `max_retries=3` and call `self.retry(exc=e)` on exception for automatic retry with exponential backoff.

### Series.posts Ordering

Series.posts relationship orders by `PostSeries.order_index` (not by date or title).

### Slug Generation Race Condition Mitigated

The slug generation in `app/services/slug.py` has an application-level race condition, but database models have `unique=True` constraints on `Post.slug`, `Page.slug`, and `Tag.slug`. Concurrent requests that generate the same slug will result in one succeeding and one failing with `IntegrityError`. Consider adding retry logic on `IntegrityError` to handle this gracefully.

### Webhook Delivery Per-Webhook Retry (Implemented)

`deliver_webhook_task` dispatches individual webhook deliveries to `deliver_single_webhook_task` for per-webhook retry support. Each webhook gets its own Celery task invocation with independent retry logic (up to 3 retries with exponential backoff). Failed webhooks are no longer silently skipped.

### nginx and Flask Rate Limits Are Aligned

nginx `limit_req_zone=login` is configured at `rate=5r/m` and Flask `ADMIN_RATE_LIMITS["login"]` is `(5, 60)` - both equal 5/minute. The burst setting in nginx (5) doesn't change the effective rate.

### nginx Security Headers

Present in `nginx/conf.d/blog.conf:25-32`: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, `Content-Security-Policy`, `Strict-Transport-Security`, `Cross-Origin-Opener-Policy: same-origin`, `Permissions-Policy`. Missing: `X-Download-Options`, `X-Permitted-Cross-Domain-Policies`.

### Template Context Variables

Use `site_title` and `site_description` as context variables (NOT `site_name` or `site_tagline`).

### Feed Tests Are in test_coverage.py

RSS/Atom feed tests are in `tests/test_coverage.py`, NOT in a separate `test_rss.py` file.

### Benchmark Tests Don't Use Fixture

Benchmark tests in `tests/benchmarks/` don't use a `client` fixture - they create clients ad-hoc with `app.test_client()` within each test function.
