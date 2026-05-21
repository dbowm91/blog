# Deployment Architecture Review

**Review Date:** 2026-05-21
**Reviewed Documents:** `architecture/deployment/` (docker.md, security.md, cicd.md, overview.md)
**Verification Scope:** Docker configs, CI/CD pipelines, security implementations, app code

---

## Summary

Reviewed deployment documentation against actual implementation in Dockerfiles, docker-compose.yml, nginx configs, GitHub Actions workflows, and application code. Overall the documentation is accurate and well-maintained. Several minor discrepancies and improvement opportunities identified.

---

## Verified Claims

### docker.md

| Claim | Status | Evidence |
|-------|--------|----------|
| Multi-container setup (blog, celery, redis, nginx) | ✓ Verified | docker-compose.yml:1-109 |
| Custom blog image, redis:7-alpine, nginx:alpine | ✓ Verified | docker-compose.yml:3,59,74 |
| Profile-based service selection | ✓ Verified | docker-compose.yml:33,55,70,88,101 |
| Multi-stage Dockerfile build | ✓ Verified | Dockerfile:1-16 (builder), 16-42 (runtime) |
| Non-root user (`blog`) | ✓ Verified | Dockerfile:23 (useradd), 31 (USER blog) |
| Resource limits in docker-compose.yml | ✓ Verified | docker-compose.yml:28-31,53-54,66-69 |
| Nginx rate limiting (login: 5r/m, admin: 20r/m) | ✓ Verified | nginx/nginx.conf:48-49 |
| Gzip compression enabled | ✓ Verified | nginx/nginx.conf:36-42 |
| Brotli commented out (custom nginx required) | ✓ Verified | nginx/nginx.conf:26-34 |
| Celery queues: images, newsletter, webhooks, email, backup | ✓ Verified | app/tasks.py:31,130,182,255,297 |
| APScheduler FileLock multi-worker limitation | ✓ Verified | app/scheduler.py:3-8 |
| Health check endpoint (`/health`) | ✓ Verified | nginx/conf.d/blog.conf:81-86 |

### security.md

| Claim | Status | Evidence |
|-------|--------|----------|
| Password hashing via werkzeug.security (pbkdf2:sha256) | ✓ Verified | app/models.py:7 (import), 97,100 (usage) |
| Session IP binding | ✓ Verified | app/config.py:87 (SESSION_IP_BINDING) |
| 2FA via pyotp | ✓ Verified | requirements.txt:24 (pyotp>=2.9.0) |
| Account lockout after 5 failed attempts (configurable) | ✓ Verified | app/config.py:142-143 (MAX_FAILED_ATTEMPTS, LOCKOUT_DURATION_MINUTES) |
| SESSION_COOKIE_SECURE = True | ✓ Verified | app/__init__.py:182-184 |
| SESSION_COOKIE_SAMESITE = "Lax" | ✓ Verified | app/__init__.py:185 |
| SESSION_COOKIE_HTTPONLY = True | ✓ Verified | app/__init__.py:186 |
| CSRF sliding window of 5 tokens | ✓ Verified | app/csrf.py:20 (CSRF_TOKEN_WINDOW_SIZE = 5), 30-36, 54-62 |
| Timing-safe comparison via hmac.compare_digest | ✓ Verified | app/csrf.py:56 |
| nh3 HTML sanitization | ✓ Verified | requirements.txt:13 |
| tinycss2 CSS property allowlist | ✓ Verified | requirements.txt:26 |
| SQLAlchemy 2.0 parameterized queries | ✓ Verified | app/__init__.py uses SQLAlchemy 3.x |
| SSRF protection with IP range checking | ✓ Verified | app/tasks.py:211 (is_safe_webhook_url check) |
| Security headers (X-Frame-Options, X-Content-Type-Options, HSTS, CSP, COOP, Referrer-Policy, Permissions-Policy) | ✓ Verified | app/__init__.py:338-378, nginx/conf.d/blog.conf:25-31 |
| Backup encryption: AES-256-GCM with PBKDF2-HMAC-SHA256 (600,000 iterations) | ✓ Verified | app/backup_encryption.py:42-43 |
| Admin audit log with actor ID (never username) | ✓ Verified | app/models.py:461-481 (AdminAuditLog) |

### cicd.md

| Claim | Status | Evidence |
|-------|--------|----------|
| test.yml workflow on push/PR | ✓ Verified | .github/workflows/test.yml:3-5 |
| lint-and-type: ruff and mypy | ✓ Verified | .github/workflows/test.yml:31-35 |
| test job: pytest with 80% coverage | ✓ Verified | .github/workflows/test.yml:64-68 |
| Python 3.12, 3.13 matrix | ✓ Verified | .github/workflows/test.yml:42 |
| security-audit: pip-audit | ✓ Verified | .github/workflows/test.yml:70-94 |
| e2e-tests: Playwright, Docker, Chromium | ✓ Verified | .github/workflows/test.yml:96-156, requirements.txt:18-19 |
| pytest.ini: test discovery, 80% threshold | ✓ Verified | pytest.ini:1-22 |

---

## Discrepancies

### 1. STORAGE_BACKEND not explicitly configured in docker-compose.yml

**File:** docker-compose.yml:1-109

**Issue:** docker.md documents `STORAGE_BACKEND` as an environment variable with options `local` or `s3`. However, docker-compose.yml does not set this variable, relying on the application default of `local`.

**Impact:** Low - works as designed, but documentation could be clearer about the default.

**Recommendation:** Add comment in docker-compose.yml noting that STORAGE_BACKEND defaults to "local".

---

### 2. Security header implementation differs between Flask and nginx

**Files:**
- app/__init__.py:338-378 (Flask after_request)
- nginx/conf.d/blog.conf:25-31 (nginx add_header)

**Issue:** Both Flask and nginx set `X-Frame-Options: DENY`, but the mechanisms differ:
- Flask only sets it in `set_security_headers()` which runs on every request
- nginx uses `add_header` which is applied once per server block

**Impact:** Low - functionality is correct, this is an implementation consistency note.

---

### 3. CSRF token rotation on privilege changes not implemented

**File:** app/csrf.py:1-64

**Issue:** security.md line 27 states "Token rotation on privilege changes" but the actual implementation only rotates tokens on successful validation. There's no mechanism to detect privilege changes and rotate tokens.

**Impact:** Low - the sliding window provides protection; privilege change rotation would be a secondary defense.

---

### 4. HSTS header not set in debug mode

**File:** app/__init__.py:352-355

**Issue:** `Strict-Transport-Security` header is only set when `not current_app.debug`. This is correct security practice but not explicitly documented in security.md.

**Impact:** Low - expected behavior, not a bug.

---

## Bugs Identified

### BUG-1: Celery worker concurrency not configured (MEDIUM)

**File:** docker-compose.yml:38

**Current:**
```yaml
command: celery -A app.celery_app worker --loglevel=info
```

**Issue:** No `--concurrency` flag specified. Celery defaults to using multiple processes/threads, which may cause issues in memory-constrained environments (celery is limited to 256M).

**Recommendation:** Add `--concurrency=1` to prevent memory issues:
```yaml
command: celery -A app.celery_app worker --loglevel=info --concurrency=1
```

---

### BUG-2: `pip-audit` failure is silently ignored (MEDIUM)

**File:** .github/workflows/test.yml:94

**Current:**
```yaml
- name: Run pip-audit
  run: pip-audit || true
```

**Issue:** The `|| true` means pip-audit failures don't fail the CI job. This defeats the purpose of security auditing in CI.

**Recommendation:** Remove `|| true` or make it conditional based on severity:
```yaml
- name: Run pip-audit
  run: pip-audit --fail-on=all
```

---

### BUG-3: Webhook secret encryption documented incorrectly (LOW)

**File:** architecture/deployment/security.md:56

**Current:**
> Webhook secrets: AES-256-GCM via `app/backup_encryption.py` (same scheme)

**Issue:** Webhook secrets are encrypted via `app/webhook_encryption.py`, not `app/backup_encryption.py`. Both use AES-256-GCM but with different key derivation approaches:
- `backup_encryption.py`: PBKDF2-HMAC-SHA256 with 600,000 iterations
- `webhook_encryption.py`: Direct AES-256-GCM with 32-byte key from `WEBHOOK_ENCRYPTION_KEY`

**Recommendation:** Update security.md:
> Webhook secrets: AES-256-GCM via `app/webhook_encryption.py` (direct key, not PBKDF2)

---

### BUG-4: Health check endpoint accessible without authentication (LOW)

**Files:**
- app/__init__.py: no auth required for /health
- nginx/conf.d/blog.conf:81-86

**Issue:** The `/health` endpoint has no authentication and is rate-limited at nginx level but not protected. This is by design for load balancer health checks, but could be documented better.

**Recommendation:** Add explicit documentation that /health is intended for internal use and should be network-restricted in production.

---

## Improvement Recommendations

### REC-1: Add explicit health check documentation

**Files:** architecture/deployment/docker.md

**Recommendation:** Add section documenting:
- `/health` endpoint returns JSON with component status
- Does not require authentication (network-level access only)
- Rate limited at nginx level
- Returns 200 even if optional services are degraded (only critical checks affect overall status)

### REC-2: Document Celery queue behavior more thoroughly

**Files:** architecture/deployment/docker.md

**Recommendation:** Add:
- Default queue priorities (backup runs on 'backup' queue)
- How to monitor queue depths
- Memory considerations for image processing (PIL can be memory-intensive)

### REC-3: Add nginx.conf security header verification

**Files:** architecture/deployment/security.md

**Recommendation:** Note that nginx security headers are additive to Flask headers, not replacements. Flask headers are set per-request, nginx headers are set per-server-block.

### REC-4: Document backup encryption key requirements

**Files:** architecture/deployment/docker.md, architecture/deployment/security.md

**Recommendation:** Add clarity on:
- `BACKUP_ENCRYPTION_KEY` must be at least 12 characters
- `WEBHOOK_ENCRYPTION_KEY` must be exactly 32 bytes
- These can be generated with: `python -c "import secrets; print(secrets.token_hex(32))"`

### REC-5: Add resource limit documentation

**Files:** architecture/deployment/docker.md

**Recommendation:** Document actual memory limits:
- blog: 512M limit, 256M reservation
- celery: 256M limit
- redis: 128M limit

### REC-6: Document expected APScheduler behavior in multi-container

**Files:** architecture/deployment/docker.md

**Recommendation:** Add more specific guidance:
- Daily backup (`run_daily_backup`) runs at 02:00 UTC
- Newsletter runs at configured `NEWSLETTER_SEND_TIME`
- Subscriber cleanup runs every 5 minutes
- All APScheduler jobs use FileLock and will skip if another instance holds the lock

---

## Cross-Reference Notes

### Security Implementation Locations

| Feature | Location |
|---------|----------|
| CSRF token generation/validation | app/csrf.py |
| Session security | app/__init__.py:182-200 |
| Security headers | app/__init__.py:338-378 |
| Account lockout | app/models.py:108-112, app/routes/admin/auth.py:61 |
| Backup encryption | app/backup_encryption.py |
| Webhook encryption | app/webhook_encryption.py |
| Rate limiting | app/middleware/rate_limit.py, nginx/nginx.conf |
| SSRF protection | app/tasks.py:211, app/utils.py (is_safe_webhook_url) |

### Celery Task Queues

| Queue | Tasks |
|-------|-------|
| images | generate_image_variants (app/tasks.py:31) |
| newsletter | send_newsletter_task (app/tasks.py:130) |
| webhooks | deliver_webhook_task (app/tasks.py:182) |
| email | send_confirmation_task (app/tasks.py:255), send_password_reset_task (app/tasks.py:276) |
| backup | run_backup_task (app/tasks.py:297) |

---

## Conclusion

The deployment documentation is well-maintained and accurately reflects the implementation. The identified bugs are minor and primarily relate to CI/CD configuration (pip-audit silencing) and Docker defaults (celery concurrency). The discrepancies are informational rather than functional issues.

**Priority fixes:**
1. BUG-1: Add `--concurrency=1` to celery worker command
2. BUG-2: Remove `|| true` from pip-audit step in CI
3. BUG-3: Fix webhook encryption documentation path