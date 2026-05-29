# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it via:

1. **GitHub Security Advisories** (preferred): Use the "Security" tab on GitHub to report privately. This keeps the discussion confidential until a fix is available.
2. **Email**: Send details to security@devlog.example.com for issues that cannot be reported through GitHub.

Please include:
- Description of the vulnerability and its potential impact
- Steps to reproduce or a proof-of-concept
- Affected version(s)
- Any suggested fix (if known)

### Response Window

We aim to acknowledge receipt within **48 hours** and provide an initial assessment within **7 days**. Critical vulnerabilities will be prioritized for immediate patching. We request that reporters give us reasonable time to address issues before public disclosure.

## Security Boundaries

DevLog is a **self-hosted** application. Security depends on proper deployment configuration.

### What the Application Covers

- CSRF protection on all POST requests (enabled by default)
- Rate limiting via `flask-limiter` (login: 5/min, API writes: 100/min, API reads: 500/min)
- SSRF protection on webhook delivery targets
- HTML/CSS/SQL injection prevention via parameterized queries and input sanitization
- Session fixation prevention and secure cookie attributes (HttpOnly, SameSite=Lax)
- Password hashing via `werkzeug.security` (pbkdf2:sha256)
- Encrypted webhooks and backups at rest (AES-256-GCM)
- Security headers: CSP (with nonces), HSTS, X-Frame-Options, X-Content-Type-Options
- Login failure delay and account lockout after failed attempts

### What the Application Does NOT Cover

- **TLS/HTTPS**: The application does not terminate TLS. Use a reverse proxy (nginx, Caddy) for SSL termination and HTTP-to-HTTPS redirects.
- **WAF (Web Application Firewall)**: No WAF is included. For public-facing deployments, consider a WAF layer (Cloudflare, ModSecurity).
- **DDoS protection**: Rate limiting is per-IP only. The application does not provide volumetric DDoS mitigation.
- **Network segmentation**: Firewall rules, VPC configuration, and network access control are the operator's responsibility.
- **OS hardening**: Server-level security (kernel updates, SSH hardening, unnecessary services) is out of scope.
- **Database backups encryption**: Backup encryption requires `BACKUP_ENCRYPTION_KEY` to be set; unencrypted backups may exist if not configured.
- **Dependency auditing**: No automated dependency vulnerability scanning is built in. Operators should use tools like `pip-audit` or GitHub Dependabot.
- **Container image scanning**: Docker images are not scanned for CVEs in the build process. Use `docker scan` or Trivy in CI.

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
