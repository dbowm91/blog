# Deployment Architecture Review

Reviewed: `cicd.md`, `docker.md`, `overview.md`, `security.md` against actual code/config.

---

## Verified Claims

### docker.md
- Services (blog, celery, redis, nginx) - all present in docker-compose.yml
- Docker Compose Profiles - correct (default/production/backup)
- Multi-stage Dockerfile build - present (builder + runtime stages)
- Non-root user (`blog`) - Dockerfile line 31
- Health checks - present in both Dockerfile and docker-compose.yml
- Gzip compression - nginx.conf lines 36-42
- Brotli commented out - nginx.conf lines 26-34
- Rate limiting (login: 5r/m, admin: 20r/m) - nginx.conf lines 48-49
- Celery task queues - tasks.py uses correct queues (images, newsletter, webhooks, email, backup)
- APScheduler multi-worker limitation - documented correctly
- Resource limits match (512M blog, 256M celery, 128M redis)

### cicd.md
- test.yml workflow exists and runs on push/PR
- lint-and-type (ruff, mypy) - correct
- test job with pytest, 80% coverage, Python 3.12/3.13 - correct
- security-audit (pip-audit) - correct
- e2e-tests with Playwright/Chromium - correct
- docker-compose wait redis - line 120
- pytest.ini configuration matches

### security.md
- Session cookie settings (__init__.py:182-186) - all correct
- CSRF sliding window of 5 tokens - csrf.py:20 with hmac.compare_digest
- Input sanitization (nh3, tinycss2, SQLAlchemy 2.0) - present
- Password hashing via werkzeug.security - present
- 2FA via pyotp - requirements.txt:24
- Account lockout (5 attempts) - config.py:142
- Security headers in nginx (DENY, nosniff, HSTS, CSP, COOP, Referrer-Policy) - conf.d/blog.conf:25-31
- AES-256-GCM encryption for backups and webhooks - verified
- Admin audit log logs user ID, not username - verified

---

## Discrepancies

### cicd.md
1. **lint-and-type Python version** - Doc says 3.12, 3.13 but test.yml only tests 3.12 (line 16)
2. **Docker compose command** - Doc says `docker-compose wait redis` but modern Docker v2+ uses `docker compose`

### security.md
1. **Permissions-Policy header missing** - Doc claims `Permissions-Policy: camera=(), microphone=(), geolocation=()` but this header is NOT in nginx/conf.d/blog.conf. Only Referrer-Policy is present.

### docker.md
1. **SESSION_COOKIE_SECURE string handling** - Doc doesn't mention that docker-compose passes this as string "true" which Flask converts to boolean (docker-compose.yml:14 comment acknowledges this)

---

## Bugs Found

### docker-compose.yml / CI
1. **Docker Compose v1 syntax** - `docker-compose` (with hyphen) used at test.yml:119-120. GitHub Actions now includes Docker Compose v2 as `docker compose` (space). The old syntax may fail on newer runners.

### Missing Security Header
2. **Permissions-Policy not set** - Neither nginx nor Flask sets this header despite documentation claiming it exists. This is a documentation bug.

---

## Improvement Opportunities

### Priority: Low

1. **Update Docker compose command in CI** - Change `docker-compose up` to `docker compose up` in test.yml to use Docker Compose v2 syntax
2. **Add missing Permissions-Policy header** - Add to nginx/conf.d/blog.conf:
   ```
   add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
   ```
3. **Update cicd.md lint-and-type matrix** - Either update doc to say Python 3.12 only, or update test.yml to matrix over 3.12, 3.13

---

## Summary

| Document | Status |
|----------|--------|
| docker.md | Mostly accurate, minor missing detail |
| cicd.md | Inaccurate Python version for lint job |
| security.md | Missing Permissions-Policy header |
| overview.md | Reference document, no issues |