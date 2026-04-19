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
- IP binding warning logged on address change (does NOT invalidate session for mobile user experience)

## CSRF Protection

- All POST routes require CSRF token via `validate_csrf_token()` in `app/csrf.py`
- Token injected into templates via `context_processor` as `csrf_token`
- Hidden form field: `<input type="hidden" name="csrf_token" value="{{ csrf_token }}">`
- `main.js` sends `X-CSRF-Token` header for JSON endpoints
- Production warning logged if CSRF disabled

## CSS Sanitization (app/utils.py)

Custom CSS is sanitized via `sanitize_css()` before rendering to strip dangerous properties:

```python
def sanitize_css(css_text: str) -> str:
    css_text = re.sub(r"url\s*\([^)]*\)", "", css_text, flags=re.IGNORECASE)
    css_text = re.sub(r"url\s*\(\s*\)", "", css_text, flags=re.IGNORECASE)
    css_text = re.sub(r"expression\s*\([^)]*\)", "", css_text, flags=re.IGNORECASE)
    css_text = re.sub(r"content\s*:\s*[^;]*;", "content: none;", css_text, flags=re.IGNORECASE)
    css_text = re.sub(r"behavior\s*:\s*[^;]*;", "", css_text, flags=re.IGNORECASE)
    css_text = re.sub(r"mso-[^\s:;]*\s*:\s*[^\s;]*;", "", css_text, flags=re.IGNORECASE)
    css_text = re.sub(r"@import\s+", "", css_text, flags=re.IGNORECASE)
    css_text = re.sub(r"-webkit-text-security\s*:\s*[^\s;]+", "", css_text, flags=re.IGNORECASE)
    css_text = re.sub(r"unicode-bidi\s*:\s*(?:isolate|embed|bidi-override)", "", css_text, flags=re.IGNORECASE)
    css_text = re.sub(r"direction\s*:\s*[^\s;]+", "", css_text, flags=re.IGNORECASE)
    return css_text.strip()
```

Used in templates as `{{ custom_css | sanitize_css | safe }}` (base.html, admin/base.html).

Additional dangerous properties blocked:
- `-webkit-text-security` (can hide content)
- `unicode-bidi: isolate|embed|bidi-override` (can override text direction)
- `direction` property

## Rate Limiting Delegation

This codebase intentionally **does not include application-level rate limiting**. Configure at reverse proxy/WAF/CDN level:

- `/admin/login`: 5 requests/minute per IP
- `/admin/*`: 20 requests/minute per IP
- Public routes: 100 requests/minute per IP

Token endpoints (`/confirm/<token>`, `/unsubscribe/<token>`) are protected by constant-time delay.

## Exception Handling Patterns

Specific exceptions used throughout (no bare `except Exception`):

- **FTS/Search** (`app/search.py`): `sqlalchemy.exc.OperationalError, ProgrammingError, DatabaseError`
- **SMTP/Email** (`app/email.py`): `smtplib.SMTPException, OSError`
- **Database** (`app/routes/public.py`): `sqlalchemy.exc.OperationalError, ProgrammingError`

Intentional catch-all for graceful degradation (with comment):
- `app/routes/admin/helpers.py:_categorize_referrer()` - URL parsing failures
- `app/routes/errors.py:_get_recent_posts()` - DB unavailable for error page

## Token Enumeration Prevention

`/confirm/<token>` and `/unsubscribe/<token>` use constant-time patterns:
- `scalar_one_or_none()` + `time.sleep(0.1)` before DB query
- Invalid tokens return success (not 404) to avoid revealing valid tokens
- Already-confirmed subscribers get "Already confirmed." flash and redirect

## Configuration Security

- `SECRET_KEY`: minimum 32 characters enforced at startup
- `SESSION_COOKIE_SECURE`: controlled via env var (defaults to "true")
- `ADMIN_PASSWORD`: RuntimeError if missing
- `CSRF_ENABLED`: warning logged in production if disabled

## Tests

```bash
# Run all tests
cd /home/sugarwookie/projects/blog && source .venv/bin/activate
ADMIN_PASSWORD=test SECRET_KEY=test-test-test-test-test-test-test-test-test python -m pytest tests/ -v
```