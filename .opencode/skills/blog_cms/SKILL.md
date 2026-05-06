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
4. **CSRF** - Sliding window of 5 valid tokens with `hmac.compare_digest`

## Testing Fixtures

All test fixtures should disable page view buffer:
- `tests/conftest.py` - has `ensure_buffer_disabled` autouse fixture
- `tests/e2e/conftest.py` - needs `ensure_buffer_disabled`
- `tests/benchmarks/conftest.py` - needs `ensure_buffer_disabled`
- `tests/test_api.py` - needs `ensure_buffer_disabled`
