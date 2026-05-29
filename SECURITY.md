# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it via:

1. **GitHub Security Advisories**: Use the "Security" tab to report privately
2. **Email**: Send details to security@devlog.example.com

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Window

We aim to acknowledge receipt within **48 hours** and provide an initial assessment within **7 days**. Critical vulnerabilities will be prioritized for immediate patching.

## Security Boundaries

DevLog is a **self-hosted** application. Security depends on proper deployment:

- The server operator is responsible for HTTPS, network security, and OS hardening
- The application does not manage TLS certificates — use a reverse proxy (nginx, Caddy)
- Rate limiting is configured at the reverse proxy level, not in the application
- Database security depends on file system permissions and access controls

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
- Database backups encrypted with AES-256-GCM and PBKDF2 key derivation
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

## Production Security Checklist

- [ ] `SECRET_KEY` is a random 64-character hex string
- [ ] `ADMIN_PASSWORD` is strong (12+ chars, mixed case, numbers, symbols)
- [ ] `config.toml [server] debug = false`
- [ ] `config.toml [site] base_url` uses `https://`
- [ ] HTTPS enforced at reverse proxy (redirect from HTTP, HSTS header)
- [ ] `SESSION_COOKIE_SECURE = True`
- [ ] `PROXY_COUNT` set correctly for proxy setup
- [ ] Static files served by nginx/Caddy, not proxied
- [ ] Rate limiting configured for `/admin/login` (5 req/min)
- [ ] `instance/blog.db` not in web-accessible directory
- [ ] `static/uploads/` permissions restricted
- [ ] SMTP credentials via environment variables (not in config.toml)
- [ ] Regular backups configured and tested
