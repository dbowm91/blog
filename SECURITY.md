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

- CSRF protection on all browser POST requests (enabled by default). API-key authenticated requests on the `api` blueprint are exempt — they are protected by token secrecy, HTTPS, scopes, rate limits, and audit logging instead of browser CSRF tokens
- Rate limiting via `flask-limiter` on the API (writes: 10/min, reads: 20/min), comments and public browse routes
- SSRF protection on webhook delivery targets
- HTML/CSS/SQL injection prevention via parameterized queries and input sanitization
- Session fixation prevention and secure cookie attributes (HttpOnly, SameSite=Lax)
- Password hashing via `werkzeug.security` (pbkdf2:sha256)
- Encrypted webhooks and backups at rest (AES-256-GCM)
- Security headers: CSP (with nonces), HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
- Login failure delay and account lockout after failed attempts

### What the Application Does NOT Cover

- **Rate limiting on the login routes**: the application deliberately does not rate limit `/login` or `/admin/login`, so the proxy can do it without the application paying for a storage round trip on every attempt. The per-account lockout stays, because it is a column on the user row and a distributed attempt against one account is not stopped by a per-IP limit. **A deployment without a reverse proxy or WAF in front of it has no per-IP limit on the login routes.**
- **TLS/HTTPS**: The application does not terminate TLS. Use a reverse proxy (nginx, Caddy) for SSL termination and HTTP-to-HTTPS redirects.
- **WAF (Web Application Firewall)**: No WAF is included. For public-facing deployments, consider a WAF layer (Cloudflare, ModSecurity).
- **DDoS protection**: Rate limiting is per-IP only. The application does not provide volumetric DDoS mitigation.
- **Network segmentation**: Firewall rules, VPC configuration, and network access control are the operator's responsibility.
- **OS hardening**: Server-level security (kernel updates, SSH hardening, unnecessary services) is out of scope.
- **Database backups encryption**: Backup encryption requires `BACKUP_ENCRYPTION_KEY` to be set; unencrypted backups may exist if not configured.
- **Dependency auditing**: No automated dependency vulnerability scanning is built in. Operators should use tools like `pip-audit` or GitHub Dependabot.
- **Container image scanning**: Docker images are not scanned for CVEs in the build process. Use `docker scan` or Trivy in CI.

### Proxy and Reverse Proxy Assumptions

- The application expects `X-Forwarded-For` and `X-Forwarded-Proto` headers from a trusted reverse proxy
- `PROXY_COUNT` must match the number of proxies in front of the app (default: `1`)
- `request.remote_addr` (normalized by `ProxyFix`) is used for rate limiting and session IP binding
- TLS termination must be handled by the reverse proxy — the application does not terminate TLS

## Security Features

### Authentication
- Password hashing via `werkzeug.security` (pbkdf2:sha256)
- TOTP-based 2FA for admin accounts, with single-use backup codes
- Session fixation prevention
- Admin session tracking with IP binding (`SESSION_IP_BINDING`: `off`, `warn` or `enforce`; default `warn` logs the change but keeps the session)

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
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: camera, microphone and geolocation disabled
- Cross-Origin-Opener-Policy: same-origin

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
| `HEALTH_CHECK_SECRET` | Gates detailed `/health?detailed=true` endpoint |
| `METRICS_SECRET` | Gates `/metrics` endpoint. Required when `ENABLE_METRICS=true`; no fallback |

## Production Security Checklist

- [ ] `SECRET_KEY` is a random 64-character hex string
- [ ] `ADMIN_PASSWORD` is strong (12+ chars, mixed case, numbers, symbols)
- [ ] `config.toml` is NOT tracked in git (only `config.toml.example` is committed)
- [ ] `config.toml [server] debug = false`
- [ ] `config.toml [site] base_url` uses `https://`
- [ ] HTTPS enforced at reverse proxy (redirect from HTTP, HSTS header)
- [ ] `SESSION_COOKIE_SECURE = True`
- [ ] `PROXY_COUNT` set correctly for proxy setup
- [ ] `HEALTH_CHECK_SECRET` set to gate detailed health endpoint
- [ ] `METRICS_SECRET` set and `ENABLE_METRICS=true` to gate `/metrics` endpoint
- [ ] Static files served by nginx/Caddy, not proxied
- [ ] Rate limiting configured for `/admin/login` (5 req/min)
- [ ] `data/devlog.sqlite3` not in a web-accessible directory
- [ ] `app/static/uploads/` permissions restricted
- [ ] SMTP credentials via environment variables (not in config.toml)
- [ ] Regular backups configured and tested
