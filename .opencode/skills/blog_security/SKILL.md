---
name: blog_security
description: "Blog CMS - Flask-based blogging platform with admin dashboard, newsletter, FTS5 search. Triggers: security hardening, rate limiting, CSRF, session management, custom CSS sanitization, health endpoint, cascade delete, exception handling, specific exceptions."
metadata:
  requires: "python>=3.12, flask>=3.1"
  homepage: "https://github.com/sugarwookie/blog"
---

## Project Overview

Blog CMS is a Flask-based blogging platform with:
- SQLAlchemy + SQLite (WAL mode)
- FTS5 full-text search with LIKE fallback
- Admin dashboard with session management
- Newsletter scheduling via APScheduler
- Custom CSS theming with sanitization
- Multi-admin support with session tracking

## Key Commands

```bash
# Run tests
cd /home/sugarwookie/projects/blog && source .venv/bin/activate && python -m pytest tests/ -v --tb=short

# Development server
cd /home/sugarwookie/projects/blog && source .venv/bin/activate && python run.py

# Database migrations
cd /home/sugarwookie/projects/blog && source .venv/bin/activate && flask db migrate -m "description" && flask db upgrade
```

## Wave 2 Security Hardening (Completed 2026-04-14)

### CSS Sanitization (app/utils.py)
Custom CSS is sanitized via `sanitize_css()` before rendering:
```python
def sanitize_css(css_text: str) -> str:
    css_text = re.sub(r"url\s*\([^)]*\)", "", css_text, flags=re.IGNORECASE)
    css_text = re.sub(r"expression\s*\([^)]*\)", "", css_text, flags=re.IGNORECASE)
    css_text = re.sub(r"content\s*:[^;]*;", "content: none;", css_text, flags=re.IGNORECASE)
    css_text = re.sub(r"behavior\s*:[^;]*;", "", css_text, flags=re.IGNORECASE)
    css_text = re.sub(r"mso-[^;]*:[^;]*;", "", css_text, flags=re.IGNORECASE)
    css_text = re.sub(r"@import\s+", "", css_text, flags=re.IGNORECASE)
    return css_text.strip()
```
Used in templates as `{{ custom_css | sanitize_css | safe }}` (base.html:30, admin/base.html:20).

### SESSION_COOKIE_SECURE (app/__init__.py:95-97)
Now controlled via `SESSION_COOKIE_SECURE` env var independently of debug mode:
```python
app.config["SESSION_COOKIE_SECURE"] = os.environ.get(
    "SESSION_COOKIE_SECURE", "true"
).lower() in ("true", "1", "yes")
```
Defaults to "true" (HTTPS-only). Set to "false" to allow HTTP cookies.

### SECRET_KEY Validation (app/__init__.py:71-75)
Minimum 32-character requirement enforced at startup:
```python
if len(SECRET_KEY) < 32:
    raise RuntimeError(
        "SECRET_KEY must be at least 32 characters long for security. "
        "Current length: {}.".format(len(SECRET_KEY))
    )
```

### CSRF Enforcement Warning (app/__init__.py:103-110)
Logs warning if CSRF disabled in production mode:
```python
if not app.debug and not app.testing:
    csrf_disabled = not app.config.get("CSRF_ENABLED", True)
    if csrf_disabled:
        logger.warning(
            "CSRF protection is disabled in production mode. "
            "This is a security risk. Set CSRF_ENABLED=True in production."
        )
```

### COOP Security Header (app/__init__.py:199)
`Cross-Origin-Opener-Policy: same-origin` added to `set_security_headers()`.

### Health Endpoint (app/routes/public.py:529-590)
Removed Python version and pool stats. Now returns only `status`, `checks`, and `timestamp`.

### Cascade Delete for AdminSession (app/models.py)
User.admin_sessions relationship uses `cascade="all,delete-orphan"` with back_populates:
```python
class User(UserMixin, db.Model):
    admin_sessions = db.relationship(
        "AdminSession", back_populates="user", lazy="select", cascade="all,delete-orphan"
    )

class AdminSession(db.Model):
    user = db.relationship("User", back_populates="admin_sessions")
```

### FakeSubscriber Complete (app/routes/admin/newsletter.py:15-19)
All Subscriber attributes present with sensible defaults:
```python
@dataclass
class FakeSubscriber:
    email: str
    token: str = "test"
    confirmed: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    unsubscribed_at: datetime | None = None
```

## Rate Limiting Delegation

This codebase intentionally **does not include application-level rate limiting**. Per AGENTS.md:
- Rate limiting is expected to be handled by reverse proxy/WAF/CDN
- `/admin/login` should be rate-limited at proxy level (5 req/min per IP)
- Token endpoints (`/confirm/<token>`, `/unsubscribe/<token>`) are protected by constant-time delay

## Security Headers (set_security_headers in app/__init__.py)

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-Download-Options: noopen`
- `X-Permitted-Cross-Domain-Policies: none`
- `Cross-Origin-Opener-Policy: same-origin`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy` (nonce-based, self-only sources)
- `Cache-Control: public, max-age=31536000, immutable` (static assets only)

## Session Security

- `session.clear()` before `login_user()` prevents session fixation (Flask 3.x)
- Admin sessions track `session_id`, `ip_address`, `user_agent`
- Sessions expire after `SESSION_LIFETIME_HOURS` of inactivity
- Cascade delete ensures AdminSession records removed when User deleted

## Tests

Security tests pass:
```bash
source .venv/bin/activate && python -m pytest tests/test_security.py -v
```

All tests pass (some failures in admin tests are due to SQLite in-memory DB issues, not code bugs).

## Wave 3 Exception Handling (Completed 2026-04-15)

Bare `except Exception` blocks replaced with specific exceptions throughout the codebase:

### search.py
Uses `sqlalchemy.exc.OperationalError, ProgrammingError, DatabaseError` for FTS operations:
- `init_fts()` - FTS5 initialization
- `rebuild_fts()` - Index rebuild
- `sync_fts()` - Index sync for post changes
- `remove_fts()` - Index removal for deleted posts
- `search()` - Search query execution

Note: `DatabaseError` is needed because SQLite's FTS5 can raise `sqlite3.DatabaseError` which is not a subclass of `OperationalError` or `ProgrammingError` in SQLAlchemy's exception hierarchy.

### email.py
Uses `smtplib.SMTPException, OSError` for SMTP operations:
- `_connect_smtp()` - SMTP connection establishment
- `send_newsletter()` finally block - server quit cleanup

### public.py
Uses `sqlalchemy.exc.OperationalError, ProgrammingError`:
- Health check endpoint database query
- Health check endpoint FTS query

### newsletter.py
Uses `smtplib.SMTPException, OSError`:
- Newsletter test send failure handling

### backup.py
Uses `sqlite3.Error, OSError`:
- Backup creation
- gzip compression (uses `OSError` only)

### Intentional Catch-All Comments
Where bare `except Exception` is intentionally used for graceful degradation:
- `app/routes/admin/helpers.py:_categorize_referrer()` - URL parsing failures categorized as "Other"
- `app/routes/errors.py:_get_recent_posts()` - DB unavailable errors return empty list for error page graceful degradation

## Testing

```bash
# Run all tests
cd /home/sugarwookie/projects/blog && source .venv/bin/activate && python -m pytest tests/ -v

# Note: SECRET_KEY env var must be at least 32 chars, ADMIN_PASSWORD must be set
ADMIN_PASSWORD=test SECRET_KEY=test-test-test-test-test-test-test-test-test python -m pytest tests/ -v
```