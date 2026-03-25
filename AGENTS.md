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
app/config.py           # All config loaded from `config.toml` + env vars
app/models.py           # SQLAlchemy models (User, Post, Tag, Subscriber, PageView, ShareEvent)
app/extensions.py       # Flask extensions (db, login_manager, migrate)
app/routes/public.py    # Public-facing routes
app/routes/admin.py     # Admin routes (requires login)
app/routes/rss.py       # RSS feed
app/csrf.py             # CSRF token handling
app/rate_limit.py       # In-memory rate limiting
app/utils.py            # Slug generation, XML escaping
app/base62.py           # Short URL encoding (base62)
app/scheduler.py        # APScheduler newsletter job
app/email.py            # SMTP email sending
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

### CSRF
- All POST routes require CSRF token unless decorated with `@csrf_exempt`
- Tests disable CSRF via `CSRF_ENABLED=False` in config
- Token injected into templates via `context_processor`

### Rate Limiting
- In-memory dicts—state lost on restart
- `check_rate_limit()` for login, `api_rate_limit()` for API endpoints

### Configuration
- `config.toml` for site settings (title, author, email, etc.)
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
- **Newsletter scheduler**—runs in-process via APScheduler, not suitable for multi-worker setups

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
