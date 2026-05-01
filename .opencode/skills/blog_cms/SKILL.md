---
name: blog_cms
description: "Blog CMS - Flask-based blogging platform with admin dashboard, newsletter scheduling, FTS5 search, multi-admin sessions, custom CSS theming, syntax highlighting themes, post series, Atom feed. Triggers: Flask app, SQLAlchemy, session management, CSRF, newsletter, APScheduler, FTS5, REST API, password reset, post revisions, preview links, toasts, dashboard charts, graceful shutdown, Docker deployment, Vite bundler."
metadata:
  requires: "python>=3.12, flask>=3.1"
  homepage: "https://github.com/sugarwookie/blog"
---

## Project Overview

Flask-based blogging platform with:
- SQLAlchemy + SQLite (WAL mode) with PostgreSQL migration path
- FTS5 full-text search with LIKE fallback, snippet extraction, and prefix matching
- Admin dashboard with session management, multi-admin support, and related posts (tag intersection scoring)
- Newsletter scheduling via APScheduler with file locking
- Custom CSS theming with sanitization and 6 syntax highlighting theme options (Prism)
- REST API for post/subscriber management with input validation and error handling
- Post revisions, scheduled publishing, shareable preview links
- Post series/collections feature
- Async task processing via Celery (image variants, newsletter, webhooks, email)
- RSS 2.0, Atom 1.0, and JSON Feed 1.1 support with caching
- OpenAPI/Swagger UI documentation at `/api/docs`
- Vite bundler for modern JavaScript/CSS with content hashing (item 5A.5 COMPLETED)

## Quick Reference

### Running Tests
```bash
# All tests (requires Playwright browsers installed)
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v

# Without E2E tests (if Playwright not installed):
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ --ignore=tests/e2e

# Install Playwright: pip install playwright && playwright install chromium
# Current test count: 524 (514 unit + 10 E2E)
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
- `/admin/` - Dashboard with widgets (traffic chart, top shares, trending, scheduled posts)
- `/admin/posts` - Post CRUD with bulk operations
- `/admin/posts/<id>/revisions` - Post revision history
- `/admin/subscribers` - Subscriber management with bulk resend
- `/admin/users` - User management with promote/demote/make-owner
- `/admin/sessions` - Active session viewing/revocation
- `/admin/media` - Media library with upload/delete
- `/admin/backup` - Database backup/restore with encryption
- `/admin/settings` - Theme presets, custom CSS, logo, syntax highlighting theme
- `/admin/pages` - Static pages CRUD
- `/admin/series` - Post series/collections management
- `/admin/newsletter` - Newsletter with preview feature

### Public Routes (`app/routes/public.py`)
- `/` - Home page with post listing
- `/post/<slug>` - Individual post with lightbox, TOC, series badge
- `/archive` - Archive by year/month (cached)
- `/tag/<tag>` - Posts by tag
- `/search` - Full-text search with suggestions
- `/page/<slug>` - Static pages
- `/subscribe` - Newsletter subscription
- `/confirm/<token>` - Email confirmation
- `/unsubscribe/<token>` - Unsubscribe
- `/preview/<post_id>?token=&expires=` - Shareable preview links
- `/series/<slug>` - Post series/collections view
- `/rss` - RSS 2.0 feed (cached)
- `/atom` - Atom 1.0 feed
- `/json` - JSON Feed 1.1
- `/sitemap.xml` - Sitemap including archive page
- `/api/docs` - Swagger UI for API documentation
- `/health` - Health check endpoint

### Post Features
- Markdown rendering with HTML sanitization via nh3
- Table of contents from h2/h3 headings
- Image lightbox with swipe/zoom/keyboard nav
- Share tracking (Twitter, LinkedIn, Hacker News, Reddit, Facebook)
- Schema.org JSON-LD structured data
- Twitter card and Open Graph meta tags
- Canonical URLs
- Draft autosave to localStorage
- Scheduled publishing (scheduler checks every 5 minutes)
- Post revisions tracked on each publish
- Related posts via tag intersection scoring (`_get_related_posts()` in `public.py`)
- Configurable `RELATED_POSTS_COUNT` in `config.toml` (default: 3, hard limit: 6)

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
- `/subscribe`: 10 req/min
- Public routes (index, post, page, tag, series): 60 req/min
- Archive and preview: 30 req/min
- Search and share tracking: 20 req/min
- Confirm/unsubscribe: 5 req/min
- Storage: configurable via `RATE_LIMIT_STORAGE_URI` env var (Redis for production, memory for dev/test)

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
- When using `joinedload()` with `scalar_one_or_none()`, must call `.unique()` first to avoid SQLAlchemy error "The unique() method must be invoked on this Result"
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

### Verified Completion
All plan items (plans/plan.md) have been verified as complete:
- 514 tests passing
- All 37 actionable items implemented and tested
- Features verified: syntax highlighting themes, Atom feed, related posts scoring, reading time in dashboard, rate limiting on all routes, proper API error handling

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

## Dependencies (Python 3.14 compatible)

See `requirements.txt`. Key packages:
- Flask 3.1+
- SQLAlchemy 2.0+ (via Flask-SQLAlchemy)
- Werkzeug 3.1+ (password hashing, security)
- asgiref 3.8+ (ASGI adapter for Granian)
- nh3 0.2+ (HTML sanitization—**not** `bleach`, which is deprecated since 2023)
- pillow 10.0+ (image processing for responsive variants)

## Frontend Build System (Content Hashing - Item 5A.5 COMPLETED)

Uses **Vite** for modern JavaScript/CSS bundling with content hashing:

```bash
# Install dependencies
npm install --registry https://registry.npmjs.org/

# Development with HMR
npm run dev

# Build for production (with content hashing)
npm run build
```

Configuration: `vite.config.js` with `build.manifest: true` for content-hashed filenames.

### Content Hashing Implementation
- Vite generates content-hashed JS filenames (e.g., `main-BVtPp-ke.js`)
- Manifest file generated at `app/static/dist/.vite/manifest.json`
- Flask helper `vite_asset()` in `app/vite.py`:
  - JS files: Looks up hashed filename from manifest
  - CSS/other: Appends MD5 content hash as query string (e.g., `base.css?v=3544ab62`)
- Templates use `{{ vite_asset('path/to/file') }}` instead of `{{ url_for('static', ...) }}`
- Enables aggressive caching: `Cache-Control: max-age=31536000, immutable`

Key files:
- `vite.config.js` - Vite configuration with manifest generation
- `app/vite.py` - Flask helper for content-hashed asset URLs
- `app/__init__.py` - Initializes Vite integration via `init_vite(app)`

## Storage Abstraction Layer (`app/storage.py`)

Supports local filesystem and S3-compatible storage backends:

```bash
# Local storage (default)
export STORAGE_BACKEND=local

# S3 storage
export STORAGE_BACKEND=s3
export S3_BUCKET=my-bucket
export S3_REGION=us-east-1
export S3_ACCESS_KEY=...
export S3_SECRET_KEY=...
export S3_ENDPOINT=https://s3.amazonaws.com  # optional, for S3-compatible services
export S3_PUBLIC_URL=https://cdn.example.com   # optional, for custom CDN URLs
```

**Key classes:**
- `StorageBackend` — Abstract base class defining the interface
- `LocalStorageBackend` — Local filesystem storage
- `S3StorageBackend` — S3-compatible storage via boto3

**Key functions:**
- `get_storage()` — Returns the singleton storage instance
- `upload_with_processing()` — Saves an image with responsive variant generation

**Note:** Image processing (responsive variants) requires local file access. For S3, files are saved to a temp directory, processed locally, then uploaded to S3.

## Page View Buffer (`app/page_view_buffer.py`)

For high-traffic sites, page views can be buffered and batch-written to reduce database load:

```bash
# Enable buffer (flush when buffer reaches 100 views)
export PAGE_VIEW_BUFFER_SIZE=100

# Flush interval in seconds (default: 5)
export PAGE_VIEW_FLUSH_INTERVAL=10
```

**Key classes:**
- `PageViewBuffer` — Thread-safe buffer with background flush thread

**Key functions:**
- `record_page_view(post_id, referrer)` — Record a page view (uses buffer if enabled, else immediate)
- `shutdown_page_view_buffer()` — Graceful shutdown with buffer flush

**Note:** Buffer is disabled by default (`PAGE_VIEW_BUFFER_SIZE=0`). Enable for high-traffic deployments.

## Backup Encryption (`app/backup_encryption.py`)

GPG symmetric encryption for database backups:

```bash
# Set encryption passphrase (min 8 characters)
export BACKUP_ENCRYPTION_KEY=your-secure-passphrase

# Optional: specify cipher (default: AES256)
export BACKUP_GPG_CIPHER=AES256
```

**Key functions:**
- `encrypt_backup(data)` — Encrypt bytes using GPG symmetric encryption
- `decrypt_backup(data)` — Decrypt GPG-encrypted bytes
- `encrypt_backup_file(input_path, output_path)` — Encrypt a file
- `decrypt_backup_file(input_path, output_path)` — Decrypt a file
- `is_encryption_available()` — Check if GPG and key are configured

**CLI support via `backup.py`:**
```bash
python backup.py --encrypt              # Create encrypted backup
python backup.py --compress --encrypt # Compressed and encrypted
python backup.py --decrypt backup.db.gpg  # Decrypt a backup file
```

**Admin UI:** The backup/restore route handles `.gpg` encrypted files transparently.

## Key Operational Lessons