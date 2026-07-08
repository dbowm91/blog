# Blog CMS Skill

Specialized knowledge for working with this Flask-based blog CMS codebase.

## Architecture Overview

This is a Flask-based blog CMS with:
- SQLAlchemy 2.0 with SQLite (WAL mode)
- APScheduler for background jobs
- Celery for async tasks
- FTS5 full-text search
- Custom CSS theming with theme presets
- 2FA via pyotp
- RSS/Atom/JSON feed endpoints
- Webhook delivery system

## Key File Locations

| Component | Location |
|-----------|----------|
| App factory | `app/__init__.py` |
| Models | `app/models.py` |
| Routes (API) | `app/routes/api/` |
| Routes (Admin) | `app/routes/admin/` |
| Routes (Public) | `app/routes/public/` |
| Routes (RSS) | `app/routes/rss.py` |
| Services | `app/services/` |
| Tasks | `app/tasks.py` |
| Webhooks | `app/webhooks.py` |
| Email | `app/email.py` |
| Search | `app/search.py` |
| Storage | `app/storage.py` |
| Templates | `app/templates/` |
| Static CSS | `app/static/css/` |

## Important Patterns

### Feed Endpoints (since May 2026)
Three feed endpoints available at `/atom`, `/rss`, `/json`:
- `/atom` - Atom 1.0 feed
- `/rss` - RSS 2.0 feed
- `/json` - JSON Feed 1.1

Implementation in `app/routes/rss.py`.

### Webhook Event Triggering
Events are triggered at these points:
```python
# Post publish/unpublish - app/routes/api/posts.py
if "published" in data and was_published != post.published:
    from app.webhooks import create_webhook_event
    create_webhook_event(
        event_type="post.published" if post.published else "post.unpublished",
        payload={"post_id": post.id, "title": post.title, "slug": post.slug},
        target_id=post.id,
        target_type="post"
    )

# Subscriber confirmation - app/routes/public/subscribe.py
create_webhook_event(
    event_type="subscriber.confirmed",
    payload={"subscriber_id": sub.id, "email": sub.email},
    target_id=sub.id,
    target_type="subscriber"
)
```

### Page View Buffer
The page view buffer (`app/page_view_buffer.py`) can cause test interference. Disable in tests:
```python
app.config["PAGE_VIEW_BUFFER_SIZE"] = 0
from app.page_view_buffer import shutdown_page_view_buffer
shutdown_page_view_buffer()
```

### Snippet Batching for SQLite
When batching post_ids for SQLite, use 500 at a time:
```python
chunk_size = 500
for i in range(0, len(post_ids), chunk_size):
    chunk = post_ids[i:i + chunk_size]
```

## Deployment

- Docker with Granian ASGI server
- Celery worker requires `PYTHONPATH=/home/blog`
- nginx runs as `nginx` user (not `blog`)
- Backup encryption uses AES-256-GCM (NOT GPG)

## Security Rules

1. **Log ID, not Username** - When logging user actions, always use `user.id`
2. **Credential Protection** - Never log `SECRET_KEY`, `ADMIN_PASSWORD`, or API keys
3. **SSRF Protection** - Webhook URLs validated via `app/utils.py:is_safe_webhook_url()`
4. **CSRF** - Sliding window of 5 valid tokens with `hmac.compare_digest`, API blueprint exempt via `should_skip_csrf()`

## Testing Fixtures

All test fixtures should disable page view buffer:
- `tests/conftest.py` - has `ensure_buffer_disabled` autouse fixture
- `tests/e2e/conftest.py` - has `ensure_buffer_disabled` autouse fixture
- `tests/benchmarks/conftest.py` - has `ensure_buffer_disabled` autouse fixture
- `tests/test_api.py` - has `ensure_buffer_disabled` autouse fixture

## Template Filters

Actual filters in `app/filters.py`:
- `markdown_safe` - Render markdown to HTML with nh3 sanitization
- `reading_time` - Calculate reading time from text content
- `sanitize_css` - Sanitize custom CSS input
- `post_image_url` - Get post image URL with request-level caching
- `post_image_srcset` - Generate srcset for responsive images

Note: `truncate` is Jinja2's built-in filter, not defined in app/filters.py
Note: `custom_css` is a context variable (from `inject_theme()`), not a filter

## Context Processors

From `app/context_processors.py`:
- `inject_config()` - site_title, site_description, author_name, etc.
- `inject_theme()` - theme settings including `custom_css`
- `inject_footer_data()` - recent_posts_footer, footer_tags, etc.
- `inject_csrf()` - csrf_token and csp_nonce
- `inject_show_footer_posts()` - show_footer_posts boolean

## Celery Queue Names

Tasks use specific queues for different workloads:
- `images` - Image processing (tasks.py:29)
- `newsletter` - Newsletter delivery (tasks.py:129)
- `webhooks` - Webhook delivery (tasks.py:192)
- `email` - Transactional email (tasks.py:264,285)
- `backup` - Backup tasks (tasks.py:306)

## Backup Implementations

Two separate backup implementations (both use `blog_*.db` naming):
- `app/services/backup.py:create_backup()` - Celery task, supports AES-256-GCM encryption/compression
- `app/scheduler.py:run_daily_backup()` - APScheduler, no encryption/compression

`cleanup_old_backups()` correctly handles both since May 2026 fix.

## Slug Generation

Slug collision limit hardcoded to 100 tries before UUID suffix fallback (`app/services/slug.py`).

## Security Headers

- Flask sets `X-Frame-Options: DENY` and `Cross-Origin-Opener-Policy: same-origin`
- nginx aligned to use `DENY` and `Cross-Origin-Opener-Policy: same-origin`

## 2FA Implementation (Wave A - May 2026)

- TOTP secrets encrypted at rest using AES-256-GCM (`app/services/encryption.py`)
- `User.totp_secret` is a property that decrypts on access
- `User.set_totp_secret()` encrypts before storage
- Backup codes are SHA-256 hashed and single-use
- Routes:
  - `GET/POST /admin/2fa/setup` - Generate TOTP secret
  - `GET/POST /admin/2fa/verify` - Verify code and enable 2FA
  - `GET /admin/2fa/backup-codes` - Display one-time backup codes
  - `GET/POST /admin/2fa/disable` - Disable 2FA
  - `GET/POST /admin/login-2fa` - TOTP verification during login

## Rate Limiting (Wave B - May 2026)

- `ADMIN_RATE_LIMITS` in `app/config.py`:
  - `login`: 5 per 60 seconds
  - `api_write`: 100 per 60 seconds
  - `api_read`: 500 per 60 seconds
  - `settings`: 50 per 60 seconds
- `app/middleware/rate_limit.py` provides `AdminRateLimiter` class
- Flask-Limiter already integrated with `key_func=get_client_ip`

## Search Abstraction (Wave C - May 2026)

- `app/services/search/__init__.py` - `SearchProvider` abstract class
- `app/services/search/sqlite.py` - `SQLiteSearchProvider` (current FTS5)
- `app/services/search/postgresql.py` - `PostgreSQLSearchProvider` (stub for future)
- `get_search_provider()` factory selects by `SEARCH_PROVIDER` config
- `SEARCH_PROVIDER` defaults to 'sqlite', can be set to 'postgresql'

## Frontend (Wave D - May 2026)

- Vite configured for code splitting in `vite.config.js`
- `manualChunks`: vendor, admin, public chunks
- `post_image_avif_url` filter in `app/filters.py` (stub - returns None until AVIF enabled)

## Brotli (Wave E - May 2026)

- `nginx/nginx.conf` includes commented Brotli configuration
- Requires custom nginx image with `--with-http_brotli_module`
- To enable: uncomment Brotli module load and settings sections
