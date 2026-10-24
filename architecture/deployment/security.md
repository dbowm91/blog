# Security

Security architecture and features.

## Authentication

| Feature | Implementation |
|---------|---------------|
| Password Hashing | `werkzeug.security` (pbkdf2:sha256) |
| Session Management | Flask-Login with IP binding |
| 2FA | TOTP via `pyotp` |
| Account Lockout | After 5 failed attempts (configurable) |

## Session Security

```python
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
```

Sliding expiration via `last_activity` in session.

## CSRF Protection

- Global `before_request` hook in `app/__init__.py` validates CSRF on all POST requests
- API blueprint (`/api/*`) is exempt via `should_skip_csrf()` in `app/csrf.py`
- Sliding window of 5 valid tokens per session
- A token stays valid until it ages out of the window; it is not consumed on use, so a single rendered page can issue more than one request (e.g. the theme preview endpoint and the form below it)
- Timing-safe comparison via `hmac.compare_digest`
- Browser form POSTs (admin, public, comments, subscribe, logout) require valid CSRF tokens
- API POST/PUT/DELETE use API key authentication, not CSRF

## Input Sanitization

| Input | Method |
|-------|--------|
| HTML | `nh3` allowlist sanitization |
| CSS | `tinycss2` property allowlist |
| SQL | SQLAlchemy 2.0 parameterized queries |
| URLs (webhooks) | SSRF protection with IP range checking |

## Security Headers

Both Flask and nginx set these headers. nginx headers are defined in `nginx/conf.d/blog.conf:25-32`:

| Header | Value |
|--------|-------|
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `default-src 'self'; ...` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `Cross-Origin-Opener-Policy` | `same-origin` |
| `Content-Security-Policy` | nonce-based (Flask) or `unsafe-inline` (nginx) — see below |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |
| `X-Download-Options` | `noopen` |
| `X-Permitted-Cross-Domain-Policies` | `none` |

### CSP Differences

Nginx and Flask set different `Content-Security-Policy` values for `script-src`:
- **Flask** (`app/__init__.py`): `script-src 'self' 'nonce-{nonce}'` — nonce-based, more secure
- **Nginx** (`nginx/conf.d/blog.conf`): `script-src 'self' 'unsafe-inline'` — overrides Flask's CSP

When behind nginx, the nginx CSP header takes precedence, replacing Flask's nonce-based policy with `unsafe-inline`. This weakens XSS protection since `unsafe-inline` allows arbitrary inline scripts.

## Nginx Rate Limiting

Rate limiting zones defined in `nginx/nginx.conf:48-49`:

| Zone | Rate | Burst | Scope | Applied To |
|------|------|-------|-------|------------|
| `login` | 5 req/min | 5 nodelay | Per IP | `/login`, `/admin/login` |
| `admin` | 20 req/min | 10 nodelay | Per IP | `/admin/` |

Rate limit violations return HTTP 429.

The login routes are **not** rate limited by the application. The deployment
is expected to sit behind this proxy or a WAF, so the per-IP limit lives here
rather than costing the application a storage round trip on every attempt.
Flask-Limiter still provides application-level rate limiting for the API,
comments and the public browse routes.

The generated native deployment config (`app/deployment/proxy.py`) emits the
same zones and the same two login locations. It must be included from the
**http** context, because `limit_req_zone` is only valid there.

## SSL/TLS Certificates

nginx references Let's Encrypt certificate paths in `nginx/conf.d/blog.conf:18-19`:
- Certificate: `/etc/letsencrypt/live/blog.example.com/fullchain.pem`
- Key: `/etc/letsencrypt/live/blog.example.com/privkey.pem`

**Note**: No automated certificate setup or renewal documentation exists. Certificates must be provisioned externally (e.g., certbot, traefik, or manual mounting).

## Nginx Process Model

The nginx container runs the master process as `root` (default `nginx:alpine` behavior). Worker processes run as the `nginx` user per `nginx.conf:1`. The app and celery containers run as the `blog` user (non-root).

## Encryption

| Data | Method |
|------|--------|
| Backups | AES-256-GCM encryption with PBKDF2-HMAC-SHA256 key derivation (600,000 iterations) |
| Webhook secrets | AES-256-GCM via `app/webhook_encryption.py` (direct key, not PBKDF2) |

### Key Requirements

| Key | Minimum Length | Generation |
|-----|---------------|------------|
| `BACKUP_ENCRYPTION_KEY` | 12 characters | `python -c "import secrets; print(secrets.token_urlsafe(12))"` |
| `WEBHOOK_ENCRYPTION_KEY` | 32 bytes / 64 hex chars | `python -c "import secrets; print(secrets.token_hex(32))"` |

## Admin Audit Log

All admin actions logged to `AdminAuditLog`:
- Actor ID (never username)
- Action type
- Target ID and type
- IP address
- Timestamp

## See Also
- [App Factory](../core/app-factory.md) - Security middleware
- [Models](../core/models.md) - User model
- [Webhooks](../infrastructure/webhooks.md) - Webhook SSRF protection
