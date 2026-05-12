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

- Sliding window of 5 valid tokens per session
- Token rotation on privilege changes
- Timing-safe comparison via `hmac.compare_digest`

## Input Sanitization

| Input | Method |
|-------|--------|
| HTML | `nh3` allowlist sanitization |
| CSS | `tinycss2` property allowlist |
| SQL | SQLAlchemy 2.0 parameterized queries |
| URLs (webhooks) | SSRF protection with IP range checking |

## Security Headers

```python
X-Content-Type-Options: nosniff
X-Frame-Options: DENY  # Both Flask and nginx set DENY
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; ...
Cross-Origin-Opener-Policy: same-origin  # Both Flask and nginx set same-origin
Referrer-Policy: strict-origin-when-cross-origin (Flask) / no-referrer-when-downgrade (nginx)  # Mismatch - verify alignment
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

**Note:** There is a Referrer-Policy mismatch between Flask (`strict-origin-when-cross-origin`) and nginx (`no-referrer-when-downgrade`). Consider aligning these for consistent behavior.

## Encryption

| Data | Method |
|------|--------|
| Backups | AES-256-GCM encryption with PBKDF2-HMAC-SHA256 key derivation |
| Webhook secrets | AES-256-GCM via `app/webhook_encryption.py` |

## Admin Audit Log

All admin actions logged to `AdminAuditLog`:
- Actor ID (never username)
- Action type
- Target ID and type
- IP address
- Timestamp

## See Also
- [App Factory](core/app-factory.md) - Security middleware
- [Models](core/models.md) - User model
- [Webhooks](../infrastructure/webhooks.md) - Webhook SSRF protection
