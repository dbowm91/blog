# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it via:

1. **GitHub Security Advisories**: Use the "Security" tab to report privately
2. **Email**: Send details to the maintainer

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Security Features

### Authentication
- Password hashing via `werkzeug.security` (pbkdf2:sha256)
- TOTP-based 2FA for admin accounts
- Session fixation prevention
- Admin session tracking with IP binding

### API Security
- API key authentication with timing-safe comparison
- Rate limiting via `flask-limiter`

### Data Protection
- Webhook secrets encrypted at rest (AES-256-GCM)
- Database backups can be GPG-encrypted
- FTS query injection prevention via parameterized queries

### Input Sanitization
- HTML sanitization via `nh3` (allowlist approach)
- CSS sanitization via `tinycss2` (property allowlist)
- SQL injection prevention via SQLAlchemy 2.0 patterns

### Security Headers
- Content-Security-Policy (with nonces)
- Strict-Transport-Security (HSTS)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff

## Configuration Recommendations

### Production
```bash
# Strong credentials
SECRET_KEY=<32+ random characters>
ADMIN_PASSWORD=<strong password>
BACKUP_ENCRYPTION_KEY=<12+ characters>

# Security settings
SESSION_COOKIE_SECURE=true
```

### Environment Variables

| Variable | Security Note |
|----------|---------------|
| `SECRET_KEY` | Required for production; 32+ characters |
| `ADMIN_PASSWORD` | Use strong password |
| `BACKUP_ENCRYPTION_KEY` | 12+ characters for backup encryption |
| `WEBHOOK_ENCRYPTION_KEY` | 32 bytes for webhook encryption |