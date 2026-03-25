# Agent Guidelines

Quick reference for AI agents working on this codebase.

## Running Tests

```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

Both `ADMIN_PASSWORD` and `SECRET_KEY` environment variables are **required**—the app raises `RuntimeError` at import time without them.

## Project Structure

```
run.py                  # Entry point—exports `app` (WSGI) and `asgi_app` (ASGI)
app/__init__.py         # App factory (`create_app()`), middleware, logging setup
app/config.py           # All config loaded from `config.toml` + env vars (+ validation)
app/models.py           # SQLAlchemy models (User, Post, Tag, Subscriber, PageView, ShareEvent)
app/extensions.py       # Flask extensions (db, login_manager, migrate)
app/routes/public.py    # Public-facing routes
app/routes/admin.py     # Admin routes (requires login)
app/routes/rss.py       # RSS feed
app/csrf.py             # CSRF token handling
app/rate_limit.py       # In-memory rate limiting
app/utils.py            # Slug generation, email validation, XML escaping
app/base62.py           # Short URL encoding (base62)
app/scheduler.py        # APScheduler newsletter job (with file locking)
app/email.py            # SMTP email sending (with TLS via ssl.create_default_context)
```

## Key Patterns

### Database
- SQLite stored in `instance/blog.db` (auto-created)
- Uses Flask-SQLAlchemy + Flask-Migrate (Alembic)
- Use `db.session.get(Model, id)` instead of `Model.query.get(id)` (avoids LegacyAPIWarning)

### Models
- `Post.slug` must be unique—use `_generate_unique_slug()` in admin.py
- `Post.updated_at` has automatic `onupdate` trigger in the model
- Tags use a many-to-many relationship via `post_tags` table
- `Post.short_code()` encodes the post ID to base62 for short URLs (`/s/<code>`)
- `Subscriber.token` is a UUID hex used for confirm/unsubscribe links
- `Subscriber.expires_at` defaults to 365 days; checked in the unsubscribe route
- All models have `__repr__` methods for debugging
- Database indexes: `ix_posts_published_created` on `(published, created_at)`, `ix_posts_slug` on `slug`

### Slugs
- `generate_slug()` in `app/utils.py` handles unicode normalization, lowercasing, and special char removal
- Both `Post.generate_slug()` and `Tag.generate_slug()` delegate to this utility

### Session
- `session["viewed_posts"]` tracks viewed post IDs to avoid double-counting page views—capped at 100 entries (keeps most recent)
- Admin session expires after 24 hours of inactivity (`check_session_timeout` in `__init__.py`)

### CSRF
- All POST routes require CSRF token unless decorated with `@csrf_exempt`
- Tests disable CSRF via `CSRF_ENABLED=False` in config
- Token injected into templates via `context_processor`

### Rate Limiting
- In-memory dicts—state lost on restart, **not shared across workers**
- `check_rate_limit()` for login, `api_rate_limit()` for API endpoints
- Uses `request.remote_addr` for IP identification—proxy setups need `ProxyFix` middleware

### Configuration
- `config.toml` for site settings (title, author, email, etc.)
- Config is validated at import time (`_validate_config` in `config.py`)
- Environment variables override config values:
  - `SECRET_KEY` (required)
  - `ADMIN_PASSWORD` (required)
  - `ADMIN_USERNAME` (optional, default: admin)
  - `SMTP_USER`, `SMTP_PASSWORD` (optional)

## Common Tasks

### Add a new route
1. Add handler to `app/routes/public.py` or `app/routes/admin.py`
2. Create template in `app/templates/`
3. Admin routes need `@login_required` decorator

### Add a new model
1. Define in `app/models.py`
2. Run `flask db migrate -m "description"`
3. Run `flask db upgrade`

### Modify templates
- Base template: `app/templates/base.html`
- Sidebar: `app/templates/_sidebar.html`
- Admin templates: `app/templates/admin/`

## Known Limitations

- **SQLite only**—no PostgreSQL/MySQL support configured
- **In-memory rate limiting**—resets on restart, doesn't share across workers
- **File uploads**—stored locally in `static/uploads/`, no S3 support
- **Newsletter scheduler**—runs in-process via APScheduler with `fcntl` file locking to prevent duplicate sends across workers (Unix only)

## Assets

- **No external assets**—all fonts (Inter, JetBrains Mono) are self-hosted in `app/static/fonts/`
- **Prism.js** is self-hosted (`app/static/js/prism.min.js` and `app/static/js/prism-languages.js`) with extended language definitions (Python, Bash, JSON, Markdown, SQL, TypeScript, Go, Rust, C/C++, YAML, TOML, Docker, PHP, Ruby, Swift)
- Do not add external CDN links (Google Fonts, CDNs, etc.)

## Dependencies (Python 3.14 compatible)

See `requirements.txt`. Key packages:
- Flask 3.1+
- SQLAlchemy 2.0+ (via Flask-SQLAlchemy)
- Werkzeug 3.1+ (password hashing, security)
- asgiref 3.8+ (ASGI adapter for Granian)
- nh3 0.2+ (HTML sanitization—**not** `bleach`, which is deprecated since 2023)

## Email

- Uses `smtplib` directly (no Celery/Redis dependency)
- SMTP connection uses `starttls()` with `ssl.create_default_context()` for TLS certificate verification
- Newsletter sending has per-subscriber exception handling; failures are logged but don't stop the batch

## Templates

- `{{ post.body | markdown_safe | safe }}` renders markdown with HTML sanitization via `nh3`
- The `markdown_safe` filter allows: `p, br, strong, em, u, s, code, pre, blockquote, h1-h6, ul, ol, li, a, img, table, thead, tbody, tr, th, td, hr, span, div`
- Allowed attributes: `a[href,title]`, `img[src,alt,title,width,height]`, `span/div[*][class]`
- **nh3 note**: The `rel` attribute for `<a>` tags is managed automatically by nh3—do not include it in allowed attributes (causes a panic)
- OG image meta tag is already implemented in `post.html:8`
- CSP header: `'self'` only for styles and fonts (fonts are self-hosted)

## CSRF

- `csrf_exempt` decorator is defined in `app/csrf.py` but not used on any routes
- The `before_request` handler in `__init__.py` checks for `_csrf_exempt` attribute on view functions
- Tests disable CSRF via `CSRF_ENABLED=False` + `TESTING=True` in config

## Security Headers

The `set_security_headers` after-request handler sets:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy` (self-only sources)
- `Cache-Control: public, max-age=31536000, immutable` (static assets only)
