# Deployment Architecture Review

**Date:** May 22, 2026  
**Reviewer:** Architecture Agent  
**Documents Reviewed:** `architecture/deployment/` (docker.md, security.md, cicd.md, overview.md)  
**Implementation Files Reviewed:** docker-compose.yml, Dockerfile, nginx/*.conf, .github/workflows/test.yml, app/config.py, app/scheduler.py, app/tasks.py, app/csrf.py, app/backup_encryption.py, app/webhook_encryption.py

---

## Summary

The deployment documentation in `architecture/deployment/` is largely accurate and well-maintained. Most claims were verified against the actual implementation. A few minor discrepancies and suggestions for improvement were identified.

---

## Verified Accurate Claims

### Docker Configuration
- **Services table** (docker.md:7-12): All 4 services correctly listed with accurate images
- **Docker Compose profiles** (docker.md:14-20): Default (blog, redis) and production (blog, celery, redis, nginx) profiles match docker-compose.yml
- **Multi-stage Dockerfile**: Correctly describes builder/runtime stages
- **Non-root user**: Dockerfile correctly creates `blog` user (line 23)
- **Resource limits** (docker.md:136-143): Memory limits in docker-compose.yml match (blog: 512M, celery: 256M, redis: 128M)
- **Celery concurrency=1** (docker-compose.yml:50): Correctly set to prevent duplicate newsletter sends

### Nginx Configuration
- **Gzip compression** (nginx/nginx.conf:36-42): Enabled with correct settings
- **Brotli comments** (nginx/nginx.conf:26-34): Correctly noted as requiring custom nginx image
- **Rate limiting zones** (nginx/nginx.conf:48-49): `login: 5r/m` and `admin: 20r/m` correctly configured
- **Security headers** (nginx/conf.d/blog.conf:24-32): X-Frame-Options DENY, X-Content-Type-Options nosniff, HSTS, CSP, COOP, Referrer-Policy all correctly set
- **Health check endpoint** (nginx/conf.d/blog.conf:83-87): Proxies to `/health` with no rate limiting

### Environment Variables
- **All documented variables** (docker.md:79-92): Verified present in docker-compose.yml
- **SESSION_COOKIE_SECURE default** (docker-compose.yml:16): Correctly set to "true" as string

### Health Check Endpoint
- **Critical checks** (docker.md:104-112): database, scheduler, search, disk_space, db_integrity all correctly implemented in app/routes/public/meta.py:286-288
- **Optional checks** (docker.md:114-121): backup_freshness, email, redis, celery all correctly implemented
- **Auth HMAC** (docker.md:123-126): Correctly implemented via hmac.compare_digest in meta.py:198-202
- **Rate limit 60/min** (docker.md:101): Correctly set in meta.py:192

### CI/CD Pipeline
- **test.yml jobs** (cicd.md:11-31): lint-and-type, test, security-audit, e2e-tests all present and accurate
- **Python versions** (cicd.md:17,20): 3.12 and 3.13 correctly configured
- **Coverage minimum 80%** (cicd.md:19): Correctly configured in test.yml:69
- **pip-audit** (cicd.md:24-25): Correctly configured in security-audit job
- **docker-compose wait redis** (cicd.md:31): Correctly implemented in test.yml:121

### Security
- **Session cookies** (security.md:16-20): SESSION_COOKIE_SECURE, SESSION_COOKIE_SAMESITE, SESSION_COOKIE_HTTPONLY all correctly configured in app/__init__.py:182-186
- **CSRF sliding window** (security.md:26-28): CSRF_TOKEN_WINDOW_SIZE=5 correctly implemented in app/csrf.py:20
- **Timing-safe comparison** (security.md:28): hmac.compare_digest correctly used in app/csrf.py:56
- **Password hashing** (security.md:9): werkzeug.security (pbkdf2:sha256) in use
- **2FA TOTP** (security.md:11): pyotp in use
- **Account lockout** (security.md:12): MAX_FAILED_ATTEMPTS=5 correctly configured in app/config.py:146
- **Input sanitization** (security.md:31-37): nh3, tinycss2, SQLAlchemy 2.0, SSRF protection all confirmed
- **Backup encryption** (security.md:51-55): AES-256-GCM with PBKDF2-HMAC-SHA256 (600,000 iterations) correctly implemented in app/backup_encryption.py:43
- **Webhook encryption** (security.md:55): AES-256-GCM via app/webhook_encryption.py (direct 32-byte key, not PBKDF2) correctly implemented
- **Admin audit log** (security.md:64-71): Actor ID (not username), action type, target info, IP, timestamp - correctly implemented

### APScheduler Configuration
- **cleanup_expired_subscribers** (scheduler.py:300-306): Runs every 5 minutes (`minute="*/5"`) - correctly documented
- **run_daily_backup** (scheduler.py:314-320): Runs at 02:00 (`hour=2, minute=0`) - correctly documented
- **SMTP handling** (scheduler.py:289-299): Newsletter job disabled when SMTP_HOST not configured - correctly documented

### Celery Task Queues
- **Queue names** (docker.md:54-59): images, newsletter, webhooks, email, backup - all correctly implemented in app/tasks.py:28,127,184,263,284,305

---

## Discrepancies and Issues

### 1. CSRF Token Rotation Documentation (Minor)
**Location:** security.md:27  
**Claim:** "Token rotation on every successful validation (not specifically on privilege changes)"  
**Verification:** Correct - the code in app/csrf.py:56-61 rotates token on successful validation. The note that it does NOT rotate on privilege changes is accurate.  
**Status:** Correct as documented.

### 2. APScheduler Multi-Worker Limitation (Minor - Already Documented)
**Location:** docker.md:66-76  
**Finding:** The documentation correctly acknowledges the FileLock limitation for multi-container deployments. This is by design and documented.
**Status:** Already correctly documented.

### 3. Admin Rate Limits Alignment
**Location:** security.md:44, docker.md:41, nginx/conf.d/blog.conf:62-79  
**Finding:** The documentation states:
- nginx `limit_req_zone=login` is at `rate=5r/m` (correct - nginx/nginx.conf:48)
- Flask `ADMIN_RATE_LIMITS["login"]` is `(5, 60)` (correct - app/config.py:150)
- Both are aligned at 5/minute

The nginx config uses `burst=5` which doesn't change the effective rate - documentation correctly notes this.
**Status:** Correct as documented.

---

## Recommended Improvements

### 1. Add Missing Environment Variables to Documentation

**File:** architecture/deployment/docker.md  
**Issue:** Some environment variables used in docker-compose.yml are not documented in the Environment Variables table.

**Missing variables:**
- `ADMIN_USERNAME` - documented in docker-compose.yml:10
- `FLASK_ENV` - used in app/config.py:133-136 for RATE_LIMIT_STORAGE_URI

**Recommendation:** Add these to the Environment Variables table (docker.md:78-92).

### 2. Document Celery Concurrency Setting

**File:** architecture/deployment/docker.md  
**Issue:** The docker-compose.yml:50 sets `--concurrency=1` for celery worker, but this is not documented.

**Recommendation:** Add a note in the Celery Task Queues section explaining that concurrency is set to 1 to prevent duplicate newsletter sends and webhook deliveries.

### 3. Clarify Backup Encryption Key Requirements

**File:** architecture/deployment/docker.md:128-133, security.md:57-62  
**Issue:** The key generation commands are documented but could be clearer.

**Current:**
```
BACKUP_ENCRYPTION_KEY: 12 characters - python -c "import secrets; print(secrets.token_hex(32))"
```

**Recommendation:** Note that the command generates 64 hex characters (32 bytes), not 12 characters. The 12-character minimum is for human-typed passwords, but hex tokens are the recommended method.

### 4. Document `PYTHONPATH` Requirement for Backup Service

**File:** architecture/deployment/docker.md  
**Finding:** docker-compose.yml:114 correctly sets `PYTHONPATH=/home/blog` for the backup service, but this is not documented.

**Recommendation:** Add a note in the Backup section explaining that PYTHONPATH is required for the backup service to import app.services.

---

## Bugs or Security Concerns

### No Critical Bugs or Security Issues Found

The codebase is well-maintained with proper security practices:
- CSRF protection with sliding window and timing-safe comparison
- Session cookies properly configured with Secure, HttpOnly, SameSite
- Backup encryption using PBKDF2 with 600,000 iterations
- Webhook secrets encrypted with AES-256-GCM
- SSRF protection for webhooks
- Input sanitization for HTML, CSS, and SQL
- Proper rate limiting at both nginx and Flask level
- Security headers properly configured

---

## Summary Table

| Category | Status | Notes |
|----------|--------|-------|
| Docker services | VERIFIED | All 4 services correct |
| Docker profiles | VERIFIED | Default and production profiles correct |
| Dockerfile multi-stage | VERIFIED | Builder/runtime stages correctly described |
| Resource limits | VERIFIED | Memory limits match |
| Nginx gzip | VERIFIED | Compression correctly configured |
| Nginx Brotli | VERIFIED | Correctly noted as requiring custom image |
| Nginx rate limiting | VERIFIED | login: 5r/m, admin: 20r/m |
| Nginx security headers | VERIFIED | All headers correctly set |
| Environment variables | MOSTLY VERIFIED | 2 missing (ADMIN_USERNAME, FLASK_ENV) |
| Health check endpoint | VERIFIED | Critical and optional checks correct |
| CI/CD pipeline | VERIFIED | All 4 jobs correct |
| Security features | VERIFIED | All confirmed |
| APScheduler jobs | VERIFIED | Schedules correct |
| Celery queues | VERIFIED | All 5 queues correct |
| Backup encryption | VERIFIED | PBKDF2 600k iterations correct |
| Webhook encryption | VERIFIED | Direct 32-byte key correct |

---

## Files Reviewed

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Container orchestration |
| `Dockerfile` | Container image build |
| `nginx/nginx.conf` | Main nginx configuration |
| `nginx/conf.d/blog.conf` | Blog-specific nginx config |
| `.github/workflows/test.yml` | CI/CD pipeline |
| `app/config.py` | Application configuration |
| `app/scheduler.py` | APScheduler jobs |
| `app/tasks.py` | Celery tasks |
| `app/csrf.py` | CSRF protection |
| `app/backup_encryption.py` | Backup encryption |
| `app/webhook_encryption.py` | Webhook secret encryption |
| `app/routes/public/meta.py` | Health check endpoint |
| `app/middleware/rate_limit.py` | Rate limiting middleware |

---

*Review completed: May 22, 2026*
