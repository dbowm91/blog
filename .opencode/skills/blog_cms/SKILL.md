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

### Password Reset (`/admin/forgot-password`, `/admin/reset/<token>`)
- Tokens hashed with SHA-256 before storing in database
- Token expires in 1 hour, single-use
- Fake success pattern prevents username enumeration
- Password complexity: 3 of 4 character classes, min 8 chars

### Token Enumeration Prevention
- `/confirm/<token>` and `/unsubscribe/<token>` use `time.sleep(0.1)` delay
- Invalid tokens return success (not 404)

### CSS Sanitization (`app/utils.py:sanitize_css`)
Strips dangerous properties: `url()`, `expression()`, `content`, `behavior`, `-webkit-text-security`, `unicode-bidi`, `direction`

### Rate Limiting
Application includes **flask-limiter** for rate limiting:
- `/admin/login`: 5 req/min per IP
- API GET: 20 req/min, API write: 10/min
- `/subscribe`: 10 req/min, Default: 100 req/min
- Storage: configurable via `RATE_LIMIT_STORAGE_URI` env var (default: memory)

Configure at reverse proxy/WAF/CDN level for production deployments.

## Performance Patterns

### Caching (flask-caching)
- Tag counts: `flask_cache.memoize()` in `app/tag_cache.py`
- Site settings: `flask_cache.cached()` in `app/context_processors.py`
- Footer data: cached with flask-caching
- Media listing: 30s TTL cache
- FTS table check: 5-minute TTL cache
- Dashboard analytics: 2-minute TTL cache
- Analytics data: 5-minute TTL cache
- **Template filter results**: Use `{% set %}` in template loops to cache filter results:
```jinja2
{% set rt = post.body | reading_time %}
{% set img = post|post_image_url %}
{% set truncated_desc = post.body | truncate(160) %}
{% set tc = tag_counts.get(tag.id, 0) %}
```
- **Request-level image cache**: `post_image_url` filter uses Flask `g._post_image_cache` to avoid repeated file I/O
- **GPU acceleration for blur effects**: Use `will-change: backdrop-filter` for elements using `backdrop-filter: blur()`

### Query Optimization
- Bulk eager loading with `joinedload(Post.tags)` in bulk operations
- Batch tag queries (single `IN` query instead of per-tag)
- `yield_per(100)` for newsletter post streaming
- LEFT JOIN for combined queries
- Subqueries with OUTER JOIN for dashboard metrics
- Combined COUNT queries in `/api/stats` using single SQL query with subqueries

### Database Indexes
- `ix_posts_published_created` - post listings
- `ix_posts_published_updated` - dashboard
- `ix_page_views_post_created` - view counts
- `ix_share_events_post_created` - share counts
- `ix_subscribers_confirmed_unsubscribed` - subscriber queries
- `ix_post_tags_tag_id` - reverse tag lookups

## Database Migrations

- `migrations/env.py` configured with `render_as_batch=True` for safe SQLite migrations
- Enables `DROP COLUMN` and `ALTER COLUMN` operations via table recreation
- Use `flask db migrate -m "description"` then `flask db upgrade`

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

## Testing

- 514 unit tests pass (excluding E2E)
- New tests: password reset flow, settings/pages routes, FTS5 prefix search
- E2E tests require Playwright installation

## Shell Context

`flask shell` provides: `db`, `User`, `Post`, `Tag`, `Subscriber`, `Page`, `PageView`, `ShareEvent`, `AdminSession`, `SiteSettings`, `PostRevision`

## SQLAlchemy 2.0 Patterns

```python
# Single result
db.session.execute(select(Model).filter(...)).scalar_one_or_none()

# Multiple results
db.session.execute(select(Model).filter_by(...)).scalars().all()

# Counts
db.session.execute(select(func.count(...))).scalar_one()

# Deletes
db.session.execute(delete(Model).where(...))

# Pagination
db.paginate(select(...), page=..., per_page=..., error_out=False)

# Get by ID (avoids LegacyAPIWarning)
db.session.get(Model, id)
```

**Critical**: `db.session.close_all()` is deprecated—use `db.engine.dispose()` instead.

## Key Operational Lessons

### IntegrityError Rollback Gotcha
In `edit_post()`, `db.session.rollback()` reverts ALL session changes. After rollback, SQLAlchemy marks all attributes as expired. Always reapply all field changes after rollback.

### File Deletion Timing
Old image files are deleted *after* `db.session.commit()` to prevent dangling file references on rollback. Use `safe_delete_file()` from `app/utils.py`.

### Media Cache Invalidation
When uploading images via post creation/edit, the media cache must be invalidated:
```python
from app.routes.admin.media import _invalidate_media_cache
_invalidate_media_cache()
```
The cache is in `app/routes/admin/media.py` and uses 30-second TTL.

### LIKE Wildcard Escaping
Escape `%` and `_` in search:
```python
escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
search_term = f"%{escaped}%"
Post.title.ilike(search_term, escape="\\")
```

### `assert` Under `python -O`
`assert` is stripped with `-O`. Never use for runtime safety checks.

## New Features

### JSON Feed (`/json`)
- JSON Feed 1.1 format implementation
- Includes title, summary, url, tags, image, author
- Conditional GET with ETag support
- Cache-Control headers for feeds

### RSS Feed Enhancements
- Author element and category elements for post tags
- Conditional GET with ETag for both `/rss` and `/json`
- Cache headers: ETag, Cache-Control, Expires

### Backup Integrity (`app/backup_integrity.py`)
- `verify_backup_integrity()` - Single backup verification
- `verify_backup_set()` - Directory verification with summary
- `detect_backup_corruption()` - Heuristic corruption detection
- Admin endpoints: `/admin/backup/verify/<filename>`, `/admin/backup/verify-all`

### Off-site Backup Sync (`scripts/sync_backups.sh`)
- Supports rclone and AWS S3
- Options: --dry-run, --verify, --cleanup
- Cron automation examples in DEPLOY.md

### Granian ASGI Server
- Recommended ASGI server (faster than Gunicorn)
- `run.py` exports `asgi_app` via `WsgiToAsgi` wrapper
- Dockerfile uses `granian --interface asgi`
- `requirements.txt` includes `granian>=1.0.0`

### Search Enhancements (`app/static/js/public/search.js`)
- Live search suggestions via API
- Debounced input with keyboard navigation (arrow keys, Enter, Escape)
- CSS styled suggestions dropdown

### Account Lockout Mechanism
- `failed_login_count` and `locked_until` columns on `User` model
- `User.is_locked()`, `record_failed_login()`, `reset_failed_login()` methods
- Config: `MAX_FAILED_ATTEMPTS` (5) and `LOCKOUT_DURATION_MINUTES` (15)
- Login checks lockout status before password verification

### APScheduler Persistence
- Uses `fcntl` file locking for newsletter job (Unix-only, single-machine)
- For multi-machine deployments, use distributed lock (Redis, etcd) instead

### Responsive Images
- Variants generated at 400w, 800w, 1200w widths on upload via `_generate_responsive_variants()` in `app/routes/admin/helpers/images.py`
- `post_image_srcset` Jinja filter provides srcset string from variants
- Templates use `srcset` with `sizes` attribute for responsive behavior

### Template Filters (`app/filters.py`)
- `markdown_safe` - renders markdown with nh3 sanitization
- `reading_time` - calculates reading time from word count
- `sanitize_css` - strips dangerous CSS properties
- `post_image_url` - returns validated image URL with request-level caching
- `post_image_srcset` - returns srcset string for responsive images

### Transaction Helpers (`app/transaction.py`)
- `@transactional` decorator handles IntegrityError/OperationalError with rollback
- `commit_with_slug_retry()` helper retries slug regeneration on collision

### JS Module Initialization
All JavaScript modules export a default initialization function:
```javascript
export default initXxx;  // e.g., export default initDarkMode;
```
`main.js` calls `module.default()` to invoke the exported function.

### Admin Enhancements
- Pages link in admin navigation dropdown
- Restore button uses distinct `btn-warning` (amber) styling
- Escape key closes modals
- Media cache invalidation on post create/edit

### Editor Preview Latency (`app/static/js/admin/editor.js`)
- Client-side markdown rendering via `app/static/js/lib/marked.min.js`
- Instant preview feedback as user types (no debounce needed)
- Server-side `/admin/preview-markdown` still called for nh3 sanitization
- Abortable fetch requests prevent race conditions

### CI/CD Workflow (`.github/workflows/test.yml`)
- GitHub Actions workflow runs on push and pull request
- Python 3.12 with pip caching
- Full test suite: `pytest tests/ --ignore=tests/e2e`

### FTS5 Atomic Sync (`app/search.py`)
- `sync_fts()` uses `INSERT OR REPLACE` for atomic upsert (no separate DELETE+INSERT)
- `sync_fts_batch()` separates published/unpublished items for correct batch handling
- `reset_fts_available()` properly resets FTS cache for testing/cache invalidation
- FTS5 table created with `prefix='2 3 4'` for prefix matching (e.g., "Py" matches "Python")
- `search()` automatically appends `*` to terms for prefix search

## Security Headers

`set_security_headers` in `app/__init__.py` applies:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-Download-Options: noopen`
- `X-Permitted-Cross-Domain-Policies: none`
- `Cross-Origin-Opener-Policy: same-origin`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy` (self-only, nonces for scripts/styles, `frame-src 'none'`)

## Security Posture

The codebase implements robust security controls:
- Session fixation prevention (`session.clear()` before `login_user()`)
- CSRF protection with sliding window (timing-safe via `hmac.compare_digest`)
- API key comparison using `hmac.compare_digest()` (timing-safe)
- Password hashing via `werkzeug.security` (pbkdf2:sha256)
- Token enumeration prevention with constant-time delay
- SQLAlchemy 2.0 parameterized queries throughout
- Magic byte detection for file uploads
- CSS sanitization blocking `url()`, `expression()`, `content`, etc.
- CSV formula injection prevention
- Comprehensive security headers (CSP with nonces, HSTS, X-Frame-Options)

## Key Operational Lessons