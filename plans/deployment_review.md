# Deployment Documentation Review - Improvement Plan

## Overview

Reviewed `architecture/deployment/` documents (overview.md, security.md, cicd.md, docker.md) against actual implementation (docker-compose.yml, nginx configs, app code, CI/CD workflows).

---

## Discrepancies & Issues

### 1. Docker Compose - Missing Critical Environment Variables

**Files:** `docker-compose.yml`, `app/config.py`

docker-compose.yml is missing several environment variables required for full production functionality:

| Missing Variable | Impact |
|-----------------|--------|
| `SMTP_HOST` | Newsletter and email tasks disabled without this |
| `SMTP_PORT` | Defaults to 587 if missing |
| `FROM_ADDRESS` | Email functionality requires this |
| `BACKUP_ENCRYPTION_KEY` | Cannot encrypt backups |
| `WEBHOOK_ENCRYPTION_KEY` | Webhook secrets cannot be encrypted |
| `HEALTH_CHECK_SECRET` | Detailed health checks unavailable |
| `CACHE_REDIS_URL` | Flask-Caching uses this in production |
| `CELERY_BROKER_URL` | Not set, defaults to REDIS_URL |

**Recommendation:** Add these environment variables to docker-compose.yml blog and celery services, with comments explaining their purpose.

---

### 2. Backup Service Configuration Issues

**File:** `docker-compose.yml:92-103`

Issues:
- `entrypoint: ["python3", "backup.py"]` - backup.py is at project root, working_dir is `/home/blog`
- backup.py imports `from app.services.backup import create_backup` - requires PYTHONPATH=/home/blog which is set for celery but NOT for backup service
- Backup service lacks `SECRET_KEY`, `DATABASE_URL` environment variables

**Code evidence:** `backup.py:28` imports from `app.services.backup`

**Recommendation:** Add PYTHONPATH, SECRET_KEY, and DATABASE_URL to backup service environment.

---

### 3. SSL Certificate Placeholder Paths

**File:** `nginx/conf.d/blog.conf:18-19`

```nginx
ssl_certificate /etc/letsencrypt/live/blog.example.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/blog.example.com/privkey.pem;
```

These are placeholder paths. Documentation should clarify that operators must replace with actual certificate paths or use certbot's `--deploy-hook` to link certificates.

**Recommendation:** Add a comment in nginx/conf.d/blog.conf explaining certificate setup.

---

### 4. SMTP Configuration Inconsistency

**Files:** `docker-compose.yml:12-13`, `app/config.py:104-108`

docker-compose.yml has `SMTP_USER` and `SMTP_PASSWORD` but NOT `SMTP_HOST`. The `SMTP_HOST` config value determines whether SMTP features are enabled.

**Code evidence:** `meta.py:220` - `if SMTP_HOST:` controls scheduler health check

**Recommendation:** Add `SMTP_HOST` to docker-compose.yml environment section.

---

### 5. Redis Rate Limiting Storage Not Exposed

**Files:** `docker-compose.yml`, `app/config.py:129-132`

```python
RATE_LIMIT_STORAGE_URI = _env(
    "RATE_LIMIT_STORAGE_URI",
    "redis://localhost:6379/1" if os.environ.get("FLASK_ENV") == "production" else "memory://"
)
```

In production (FLASK_ENV=production), rate limits use Redis DB 1, but this is not configurable via docker-compose.yml. When REDIS_URL is set to `redis://redis:6379/0`, rate limiting still works but uses the default memory:// storage unless explicitly configured.

**Code evidence:** `app/__init__.py:220` sets `app.config["RATELIMIT_STORAGE_URI"] = RATE_LIMIT_STORAGE_URI`

**Recommendation:** Add `RATE_LIMIT_STORAGE_URI` to docker-compose.yml to ensure Redis is used for rate limiting in production.

---

### 6. Login Rate Limit Mismatch

**Files:** `nginx/conf.d/blog.conf:63`, `app/config.py:145-146`

| Source | Value |
|--------|-------|
| nginx `limit_req_zone=login` | `rate=5r/m` (1 per 12 sec burst 5) |
| Flask `ADMIN_RATE_LIMITS["login"]` | `(5, 60)` (5 per 60 sec) |

The nginx rate limiting is stricter (1 per minute vs 5 per minute in Flask). This isn't necessarily wrong but represents an inconsistency.

**Recommendation:** Align nginx limit_req_zone with Flask rate limits or document why nginx is stricter.

---

### 7. Security.md - CSRF Token Rotation on Privilege Changes

**File:** `app/csrf.py`

security.md claims "Token rotation on privilege changes" but `csrf.py` implements no such mechanism. The sliding window of 5 tokens is maintained, but there's no code to rotate on privilege changes (e.g., when user promotes another user).

**Code evidence:** `csrf.py:23-36` - `generate_csrf_token()` only maintains the sliding window, no privilege change detection

**Recommendation:** Either implement the feature or remove the claim from security.md.

---

### 8. Security.md - Password Hashing Ambiguity

**File:** `app/models.py`

security.md says "werkzeug.security (pbkdf2:sha256)" but werkzeug's `generate_password_hash` uses pbkdf2:sha256:iterations format (e.g., `pbkdf2:sha256:600000`).

**Code evidence:** `werkzeug.security.generate_password_hash` default is `pbkdf2:sha256:600000`

**Recommendation:** Clarify that iterations are used (600,000 default in werkzeug).

---

### 9. Docker Multi-Worker Limitation - Missing celery concurrency flag

**File:** `docker-compose.yml:39`

```yaml
command: celery -A app.celery_app worker --loglevel=info --concurrency=1
```

The `--concurrency=1` flag IS present in docker-compose.yml, contradicting the documentation that says the limitation exists but doesn't mention this mitigation.

**Code evidence:** `docker-compose.yml:39`

**Recommendation:** Update docker.md:66-76 to clarify that `--concurrency=1` mitigates the duplicate task risk on single machine.

---

### 10. Health Check Rate Limit Documentation Discrepancy

**Files:** `nginx/conf.d/blog.conf:83-87`, `app/routes/public/meta.py:192`

| Component | Rate Limit |
|-----------|------------|
| Flask `/health` route | 60 per minute |
| nginx location /health | No rate limiting (access_log off) |

docker.md:94 says "60 requests/minute via Flask-Limiter" - this applies to Flask, not nginx. The nginx config has no limit_req on `/health`.

**Recommendation:** Clarify in docs that rate limiting is at Flask level.

---

### 11. Dockerfile Base Image vs CI/CD Python Versions

**Files:** `Dockerfile:1`, `.github/workflows/test.yml:43`

- Dockerfile uses `python:3.12-slim`
- CI/CD tests on both 3.12 and 3.13

**Recommendation:** Either update Dockerfile to test 3.13 or document that production uses 3.12.

---

### 12. docker-compose.yml - Missing Flask-Caching Config

**File:** `app/__init__.py:225-230`

When `FLASK_ENV=production`, cache uses Redis but `CACHE_REDIS_URL` is not set in docker-compose.yml:

```python
"CACHE_TYPE": "RedisCache",
"CACHE_REDIS_URL": os.environ.get("CACHE_REDIS_URL", "redis://localhost:6379/0"),
```

Default redis://localhost:6379/0 will not work inside Docker network where service is named `redis`.

**Recommendation:** Add `CACHE_REDIS_URL` to docker-compose.yml, or explicitly pass `REDIS_URL` as `CACHE_REDIS_URL`.

---

### 13. backup.conf Command Documentation Inconsistency

**Files:** `docker-compose.yml:99`, `docs/deployment/docker.md`

docker-compose.yml uses `entrypoint: ["python3", "backup.py"]` which references the standalone CLI tool at project root. But `app/scheduler.py:run_daily_backup()` is the APScheduler task that runs the backup.

The `backup` profile runs the backup.py CLI, not the APScheduler task. This may be intentional but is not documented.

**Recommendation:** Clarify in docs that `backup` profile runs CLI backup, while APScheduler handles scheduled backups.

---

### 14. Missing Documentation - PROXY_COUNT

**File:** `app/__init__.py:187-188`

```python
proxy_count = int(os.environ.get("PROXY_COUNT", 1))
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_count, x_proto=1, x_host=1)
```

`PROXY_COUNT` is not documented anywhere in deployment docs but is essential for proper IP detection behind nginx reverse proxy.

**Recommendation:** Add `PROXY_COUNT` to docker.md environment variables table.

---

### 15. Test Workflow Uses `docker-compose` vs `docker compose`

**File:** `.github/workflows/test.yml:121`

Uses `docker compose` (Docker Compose V2). docs/deployment/docker.md and other docs use `docker-compose` (V1 syntax).

**Code evidence:** `test.yml:121` - `docker compose up -d`

Both commands work but consistency should be maintained. V2 `docker compose` is now standard.

---

## Potential Bugs

### 1. APScheduler Multi-Worker Issue With Celery Concurrency=1

**File:** `app/scheduler.py:70-77`

The APScheduler runs `send_daily_newsletter()` which acquires a FileLock. This prevents duplicate newsletter sends on a single machine. However:

- Celery worker has `--concurrency=1` preventing parallel newsletter sends via Celery
- But APScheduler and Celery are separate - APScheduler newsletter runs in the blog container, Celery handles other tasks

If the blog container is scaled (`docker-compose up -d --scale blog=2`), APScheduler runs on both containers simultaneously without coordination (FileLock is local to each container's filesystem).

**Bug:** Scaling blog containers can cause duplicate newsletter sends because APScheduler uses local FileLock only.

**Recommendation:** Document this limitation or use a Redis-based lock for APScheduler.

---

### 2. Health Check Celery Detection When Celery Uses Different Broker

**File:** `app/routes/public/meta.py:262-269`

```python
from app.celery_app import celery_app
inspector = celery_app.control.inspect(timeout=3)
```

The celery_app uses the broker configured in Celery config. If `CELERY_BROKER_URL` is different from `REDIS_URL`, the health check might ping the wrong broker. Currently REDIS_URL is used for both cache and Celery, but if split, health check would fail silently.

**Recommendation:** Add explicit `CELERY_BROKER_URL` to health check logic or document that Celery and Redis must share a broker.

---

## Improvements to Documentation Structure

### 1. Consolidate Environment Variables

Current docs are scattered:
- `docker-compose.yml` environment section
- `docker.md` Environment Variables table
- `security.md` Key Requirements table
- `app/config.py` for actual defaults

**Recommendation:** Create a single source of truth for all environment variables.

### 2. Add Troubleshooting Section

Missing content:
- How to view logs in production
- Common failure modes (Redis connection, database permissions)
- Backup restore procedure

### 3. Add Backup Encryption Workflow

security.md mentions backup encryption but doesn't explain:
- How to generate BACKUP_ENCRYPTION_KEY
- How to use encrypted backups
- How to rotate encryption keys

---

## Summary of Recommendations

| Priority | Issue | Recommendation |
|----------|-------|----------------|
| High | Missing SMTP_HOST in docker-compose.yml | Add SMTP_HOST |
| High | Missing BACKUP_ENCRYPTION_KEY, WEBHOOK_ENCRYPTION_KEY | Add encryption keys |
| High | Backup service PYTHONPATH missing | Add PYTHONPATH env var |
| Medium | PROXY_COUNT not documented | Document in docker.md |
| Medium | Login rate limit mismatch | Align or document discrepancy |
| Medium | CSRF privilege rotation claim | Implement or remove |
| Medium | CACHE_REDIS_URL not in docker-compose | Add for production |
| Low | docker-compose vs docker compose inconsistency | Standardize |
| Low | SSL placeholder paths | Add explanatory comment |

---

## Verification Checklist

- [ ] docker-compose.yml includes all required env vars (SMTP_HOST, BACKUP_ENCRYPTION_KEY, etc.)
- [ ] Backup service has PYTHONPATH set correctly
- [ ] nginx SSL paths are documented as placeholders
- [ ] PROXY_COUNT is documented
- [ ] CSRF privilege rotation is either implemented or documentation updated
- [ ] Rate limit settings are aligned between Flask and nginx