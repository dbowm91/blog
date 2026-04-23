---
name: blog_cms
description: "Blog CMS - Flask-based blogging platform with admin dashboard, newsletter scheduling, FTS5 search, multi-admin sessions, custom CSS theming. Triggers: Flask app, SQLAlchemy, session management, CSRF, newsletter, APScheduler, FTS5, REST API, password reset, post revisions, preview links, toasts, dashboard charts, graceful shutdown, Docker deployment."
metadata:
  requires: "python>=3.12, flask>=3.1"
  homepage: "https://github.com/sugarwookie/blog"
---

## Project Overview

Flask-based blogging platform with:
- SQLAlchemy + SQLite (WAL mode) with PostgreSQL migration path
- FTS5 full-text search with LIKE fallback and snippet extraction
- Admin dashboard with session management and multi-admin support
- Newsletter scheduling via APScheduler with file locking
- Custom CSS theming with sanitization
- REST API for post/subscriber management
- Post revisions, scheduled publishing, shareable preview links

## Quick Reference

### Running Tests
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
# Without E2E tests (require Playwright):
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ --ignore=tests/e2e
```

### Development Server
```bash
python run.py
```

### Database Migrations
```bash
flask db migrate -m "description" && flask db upgrade
```

### CLI Commands
```bash
flask export-data <output_file>     # JSON export
flask import-data <input_file>      # JSON import
flask promote-admin <username>     # CLI admin promotion
flask check-integrity               # DB integrity check
flask seed                          # Sample data
flask rebuild-search                # Rebuild FTS5 index
flask cleanup-orphaned-images      # Clean unused images
```

## Core Features

### REST API (`app/routes/api.py`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/posts` | List posts (paginated) |
| GET | `/api/posts/<id>` | Get single post |
| POST | `/api/posts` | Create post |
| PUT | `/api/posts/<id>` | Update post |
| DELETE | `/api/posts/<id>` | Delete post |
| GET | `/api/subscribers` | List subscribers (paginated) |
| POST | `/api/subscribers` | Create subscriber |
| DELETE | `/api/subscribers/<id>` | Delete subscriber |
| GET | `/api/stats` | Dashboard statistics |

Authentication: `X-API-Key` header (env var `API_KEY`)

### Admin Routes (`app/routes/admin/`)
- `/admin/` - Dashboard with widgets (traffic chart, top shares, trending)
- `/admin/posts` - Post CRUD with bulk operations
- `/admin/posts/<id>/revisions` - Post revision history
- `/admin/subscribers` - Subscriber management with bulk resend
- `/admin/users` - User management with promote/demote/make-owner
- `/admin/sessions` - Active session viewing/revocation
- `/admin/media` - Media library with upload/delete
- `/admin/backup` - Database backup/restore
- `/admin/settings` - Theme presets, custom CSS, logo

### Public Routes (`app/routes/public.py`)
- `/` - Home page with post listing
- `/post/<slug>` - Individual post with lightbox, TOC
- `/archive` - Archive by year/month
- `/tag/<tag>` - Posts by tag
- `/search` - Full-text search with suggestions
- `/page/<slug>` - Static pages
- `/subscribe` - Newsletter subscription
- `/confirm/<token>` - Email confirmation
- `/unsubscribe/<token>` - Unsubscribe
- `/preview/<post_id>?token=&expires=` - Shareable preview links
- `/health` - Health check endpoint

### Post Features
- Markdown rendering with HTML sanitization via nh3
- Table of contents from h2/h3 headings
- Image lightbox with swipe/zoom/keyboard nav
- Share tracking (Twitter, LinkedIn, Hacker News)
- Schema.org JSON-LD structured data
- Twitter card meta tags
- Canonical URLs
- Draft autosave to localStorage
- Scheduled publishing (scheduler checks every 5 minutes)
- Post revisions tracked on each publish

## Security Features

### CSRF Protection (`app/csrf.py`)
- Sliding window of 5 valid tokens per session
- Token rotation on privilege changes (promote/demote/make-owner)
- Timing-safe comparison via `hmac.compare_digest`
- `X-CSRF-Token` header for JSON endpoints

### Session Security
- `session.clear()` before `login_user()` prevents session fixation
- Admin sessions track `session_id`, `ip_address`, `user_agent`
- Session IP binding logs warning on address change
- Cascade delete removes AdminSession when User deleted

### Password Reset (`/admin/forgot-password`)
- Token expires in 1 hour, stored as hash
- Fake success pattern prevents username enumeration
- Password complexity: 3 of 4 character classes, min 8 chars

### Token Enumeration Prevention
- `/confirm/<token>` and `/unsubscribe/<token>` use `time.sleep(0.1)` delay
- Invalid tokens return success (not 404)

### CSS Sanitization (`app/utils.py:sanitize_css`)
Strips dangerous properties: `url()`, `expression()`, `content`, `behavior`, `-webkit-text-security`, `unicode-bidi`, `direction`

### Rate Limiting
Application does NOT include rate limiting. Configure at reverse proxy/WAF/CDN level:
- `/admin/login`: 5 req/min per IP
- `/admin/*`: 20 req/min per IP
- Public routes: 100 req/min per IP

## Performance Patterns

### Caching
- Tag counts: TTL-based in-memory cache with double-checked locking
- Site settings: singleton pattern with cache
- Footer data: invalidate on post CRUD
- Media listing: 30s TTL cache
- FTS table check: 5-minute TTL cache
- Dashboard analytics: 5-minute TTL cache
- **Template filter results**: Use `{% set %}` in template loops to cache filter results (e.g., `post_image_url`, `reading_time`) and avoid repeated computation/file I/O

### Query Optimization
- Bulk eager loading with `joinedload(Post.tags)` in bulk operations
- Batch tag queries (single `IN` query instead of per-tag)
- `yield_per(100)` for newsletter post streaming
- LEFT JOIN for combined queries
- Subqueries with OUTER JOIN for dashboard metrics

### Database Indexes
- `ix_posts_published_created` - post listings
- `ix_posts_published_updated` - dashboard
- `ix_page_views_post_created` - view counts
- `ix_share_events_post_created` - share counts
- `ix_subscribers_confirmed_unsubscribed` - subscriber queries

## Structured Logging

`app/__init__.py` uses JSON log format:
```json
{"timestamp": "2026-04-21T14:30:00Z", "level": "INFO", "request_id": "a1b2c3d4", "message": "Post published"}
```

## Graceful Shutdown (`run.py`)

SIGTERM handler:
1. Sets shutdown event
2. Waits for in-flight requests
3. Scheduler finishes current newsletter
4. Closes DB connections via `db.engine.dispose()`

## Deferred/Low Priority Items

All items have been completed as of 2026-04-23:

| Item | Status |
|------|--------|
| C3: `reading_time` filter repeated calls | **Completed** - template caching with `{% set %}` |
| C4: `post_image_url` file I/O | **Completed** - request-level cache via Flask g |
| C5: Theme CSS regenerated | **Completed** - 5-min TTL cache |
| L5: `backdrop-filter: blur()` GPU | **Completed** - `will-change: backdrop-filter` hints |
| L6: Redundant `tag_counts.get()` | **Completed** - template caching |
| L7: `truncate` called 4x | **Completed** - template caching |

See `plan.md` for detailed verification status.

## Testing

- 486 unit tests pass (1 known flaky media upload test)
- Media upload test occasionally fails due to async timing issues
- E2E tests require Playwright installation

## Shell Context

`flask shell` provides: `db`, `User`, `Post`, `Tag`, `Subscriber`, `Page`, `PageView`, `ShareEvent`, `AdminSession`, `SiteSettings`, `PostRevision`