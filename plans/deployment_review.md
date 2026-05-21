# Deployment Module Architecture Review

**Review Date:** 2026-05-21
**Reviewer:** deployment_reviewer

---

## 1. Verified Accurate Claims

| Claim | Document | Line | Evidence |
|-------|----------|------|----------|
| Services table (blog, celery, redis, nginx) | docker.md | 7-12 | Matches docker-compose.yml:2-88 |
| Docker Compose profiles (default, production, backup) | docker.md | 14-20 | Matches docker-compose.yml:33,56,88,101 |
| Non-root user `blog` in Dockerfile | docker.md | 29 | Dockerfile:23 creates user blog |
| Multi-stage build in Dockerfile | docker.md | 24-26 | Dockerfile:1-15 (builder), 16-42 (runtime) |
| Health check configured in Dockerfile | docker.md | 40 | Dockerfile:40 `HEALTHCHECK --interval=30s...` |
| Resource limits (blog: 512M/256M, celery: 256M, redis: 128M) | docker.md | 121-125 | Matches docker-compose.yml:29-31,54,69 |
| Celery task queues (images, newsletter, webhooks, email, backup) | docker.md | 52-59 | Matches app/tasks.py:31,130,182,262,283,304 |
| APScheduler multi-worker limitation documented | docker.md | 66-76 | Correctly describes FileLock limitation |
| Brotli commented out in nginx.conf | docker.md | 47-50 | nginx.conf:26-34 shows commented LoadModule directives |
| Rate limiting (login: 5r/m, admin: 20r/m) | docker.md | 41 | nginx.conf:48-49 matches |
| Health critical checks (database, scheduler, search, disk_space, db_integrity) | docker.md | 98-106 | Matches app/routes/public/meta.py:286-288 |
| Backup encryption: AES-256-GCM + PBKDF2-HMAC-SHA256, 600,000 iterations | security.md | 55 | Matches app/backup_encryption.py:43 |
| Webhook encryption: AES-256-GCM, direct key (not PBKDF2) | security.md | 56 | Matches app/webhook_encryption.py |
| CSRF sliding window of 5 tokens, hmac.compare_digest | security.md | 26-28 | Matches app code |
| CI/CD: test.yml with lint-and-type, test, security-audit, e2e-tests jobs | cicd.md | 7-9 | Matches .github/workflows/test.yml:7-156 |
| CI/CD: Python 3.12, 3.13 test matrix | cicd.md | 19-20 | Matches test.yml:42 |
| CI/CD: Minimum 80% coverage requirement | cicd.md | 19 | Matches test.yml:68 `--cov-fail-under=80` |
| E2E tests use Playwright with Chromium | cicd.md | 28-30 | Matches test.yml:136-139 |

---

## 2. Inaccurate/Outdated Claims

| Claim | Document | Actual Behavior | Correction Needed |
|-------|----------|-----------------|-------------------|
| Health check: "Rate Limiting: Limited at nginx level" | docker.md | Line 192 applies `@limiter.limit("60 per minute")` via Flask-Limiter | Update to mention 60 req/min rate limit via Flask-Limiter |
| Health check: "Authentication: None required" | docker.md | Secret-based HMAC auth when `HEALTH_CHECK_SECRET` is set (meta.py:199-203) | Add note: "Optional HMAC authentication when HEALTH_CHECK_SECRET is configured" |
| Health check: "Returns 200 even if optional services are degraded" | docker.md | Accurate (meta.py:290-293), but optional checks not explicitly documented | Clarify: Optional checks are `backup_freshness`, `email`, `redis`, `celery` |
| CI/CD: e2e-tests uses `docker-compose up` | cicd.md | Uses `--profile production` (test.yml:119) | Document the correct command |

---

## 3. Bugs Identified

| Severity | Location | Description |
|----------|----------|-------------|
| **Medium** | docker-compose.yml:14 | `SESSION_COOKIE_SECURE=${SESSION_COOKIE_SECURE:-true}` passes string "true" not boolean. Flask handles this via truthiness but is not properly typed. Consider using `t_bool` helper or explicit string handling. |
| **Low** | nginx/conf.d/blog.conf:18-19 | SSL certificate paths use `blog.example.com` placeholder. While standard convention, no warning about replacing these exists in documentation. |
| **Low** | docker-compose.yml:46-47 | Celery service mounts `blog_data` and `blog_uploads` volumes but not `blog_logs`. Celery logs will go to container stdout only, not persist. |

---

## 4. Missing Documentation

| Item | Where Documented | Status |
|------|------------------|--------|
| `HEALTH_CHECK_SECRET` environment variable for authenticated detailed health checks | app/config.py:127, app/routes/public/meta.py:199-203 | Not in docker.md |
| SMTP_HOST determines if scheduler check runs (meta.py:220-224) | app/routes/public/meta.py | Not in docker.md |
| Optional health checks (backup_freshness, email, redis, celery) don't affect overall status | app/routes/public/meta.py:286-293 | Not in docker.md |
| `ADMIN_RATE_LIMITS` configuration (config.py:145-152) | app/config.py | Not in docker.md |
| Celery worker `--concurrency=1` flag (docker-compose.yml:38) | docker-compose.yml | Not in docker.md |
| `docker wait redis` in e2e-tests job (test.yml:120) | test.yml | Not in cicd.md |
| `STORAGE_BACKEND` environment variable (listed in docker.md but not in actual docker-compose.yml) | docker-compose.yml | Remove from docker.md or add to docker-compose.yml |
| Account lockout configuration (`MAX_FAILED_ATTEMPTS`, `LOCKOUT_DURATION_MINUTES`) | config.py:142-143 | Not in security.md |

---

## 5. Recommended Improvements

### High Priority

1. **docker.md - Add HEALTH_CHECK_SECRET documentation**
   - Document that `HEALTH_CHECK_SECRET` enables authenticated detailed health checks
   - Document the `?secret=<value>&detailed=true` query parameters
   - Location: docker.md section "Health Check Endpoint"

2. **docker.md - Add optional checks clarification**
   - Explicitly document which checks are optional and don't affect overall status
   - Add table listing all checks with "Affects overall" column

### Medium Priority

3. **docker-compose.yml - Fix SESSION_COOKIE_SECURE**
   - Change from string interpolation to proper boolean handling
   - Or document that string "true"/"false" is handled by Flask

4. **docker-compose.yml - Add blog_logs volume to celery**
   - Add `- blog_logs:/home/blog/logs` to celery volumes section
   - Ensures logs persist for celery worker

5. **docker.md - Remove STORAGE_BACKEND from Environment Variables table**
   - This variable is not used in docker-compose.yml
   - Misleading if it doesn't actually configure anything

6. **security.md - Add account lockout configuration**
   - Document `MAX_FAILED_ATTEMPTS` and `LOCKOUT_DURATION_MINUTES`

### Low Priority

7. **cicd.md - Document docker wait redis**
   - Add note about `docker-compose wait redis` in e2e-tests setup

8. **docker.md - Document celery --concurrency=1**
   - Add note that Celery worker runs with single concurrency

9. **nginx/conf.d/blog.conf - Add SSL placeholder warning**
   - Add comment about replacing blog.example.com with actual domain

---

## Summary

| Category | Count |
|----------|-------|
| Verified Accurate Claims | 19 |
| Inaccurate Claims | 4 |
| Bugs Identified | 3 |
| Missing Documentation | 8 |
| Improvements | 9 |