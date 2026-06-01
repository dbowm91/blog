# Deployment Architecture Review

**Reviewed:** 2026-05-31  
**Architecture Docs:** overview.md, docker.md, security.md, cicd.md  
**Source Files:** Dockerfile, docker-compose.yml, nginx/, .github/workflows/ci.yml, scripts/

## Findings

### Verified Claims (Correct)

- **Docker Compose Profiles**: All services require explicit profiles, no default profile. `blog`, `celery`, `redis`, `nginx` use `production`; `backup` uses `backup` (`docker-compose.yml:50-51,84-85,99-100,116-117,138-139`).
- **Nginx proxy_pass**: `proxy_pass http://blog:5000` (`nginx/conf.d/blog.conf:52`).
- **CI Workflow Jobs**: Exactly 6 jobs: lint-and-type, test, security-audit, frontend-build, docker-build, e2e-tests (`.github/workflows/ci.yml:11,40,73,99,116,124`).
- **Weekly Schedule**: Cron `0 8 * * 1` (Monday 08:00 UTC) (`.github/workflows/ci.yml:8`).
- **Security Headers**: All listed in `nginx/conf.d/blog.conf:25-32` match docs (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy, CSP, HSTS, COOP, Permissions-Policy).
- **Rate Limiting Zones**: login 5r/m, admin 20r/m (`nginx/nginx.conf:48-49`).
- **Resource Limits**: blog 512M/256M, celery 256M, redis 128M (`docker-compose.yml:46-49,83,98`).
- **Health Check Parameters**: interval 30s, timeout 10s, retries 3, start_period 10s (`docker-compose.yml:39-43`).
- **Python Version Consistency**: `dev.sh` requires Python ≥ 3.12 (`scripts/dev.sh:11`); Dockerfile uses `python:3.12-slim` (`Dockerfile:1,12`).
- **APScheduler Multi-Container Limitation**: FileLock with timeout=0, scaling warning documented (`docker.md:103-150`).
- **Celery Concurrency**: `--concurrency=1` (`docker-compose.yml:66`).
- **Security-Audit Mode**: `pip-audit --fail-on=all` (`.github/workflows/ci.yml:97`).
- **E2E Test Setup**: `docker compose wait blog` (`.github/workflows/ci.yml:150`).
- **Nginx client_max_body_size**: 16M (`nginx/conf.d/blog.conf:89`).
- **Backup Service Working Directory**: `/home/blog` (`docker-compose.yml:128`).
- **Backup Encryption Key Loading**: Environment variable or config.toml (`docker.md:316-320`).

### Discrepancies (Doc vs Code)

1. **Nginx proxy_pass Address**:  
   - **Doc**: `docker.md:298` claims `proxy_pass http://127.0.0.1:5000`.  
   - **Code**: `nginx/conf.d/blog.conf:52` uses `proxy_pass http://blog:5000`.  
   - **Impact**: Misleading documentation; service name is correct for Docker networking.

2. **Backup Service Line Range**:  
   - **Doc**: `docker.md:37` references `docker-compose.yml:119-137`.  
   - **Code**: Backup service spans lines 119-139 (includes `profiles:` section).  
   - **Impact**: Minor, but line range inaccurate.

3. **Celery Service Missing SMTP_HOST**:  
   - **Doc**: `docker.md:167` lists `SMTP_HOST` as environment variable for blog service; not explicitly mentioned for celery.  
   - **Code**: `docker-compose.yml:67-71` includes `SMTP_USER` and `SMTP_PASSWORD` but omits `SMTP_HOST`.  
   - **Impact**: Celery worker may lack SMTP host for newsletter tasks; could cause failures.

4. **Missing Security Headers in Nginx**:  
   - **Doc**: `security.md:54-55` lists `X-Download-Options: noopen` and `X-Permitted-Cross-Domain-Policies: none`.  
   - **Code**: Not present in `nginx/conf.d/blog.conf:25-32`.  
   - **Impact**: Headers likely set by Flask, but doc implies nginx sets them; ambiguous.

5. **Dockerfile Healthcheck Timeout**:  
   - **Doc**: `docker.md:206` notes Dockerfile `--timeout=3s` vs docker-compose `timeout: 10s`.  
   - **Code**: Confirmed (`Dockerfile:39` vs `docker-compose.yml:41`).  
   - **Impact**: Doc correct, but not explicitly stated that docker-compose overrides.

### Missing Documentation

1. **Celery SMTP_HOST Requirement**: No documentation that celery service requires `SMTP_HOST` for newsletter/email tasks.  
2. **Docker Compose Version Feature**: `docker compose wait` requires Docker Compose v2.20+; not mentioned.  
3. **Nginx conf.d Directory**: Only `blog.conf` exists; no mention of default.conf or other configs.  
4. **CI Workflow Action Versions**: Uses `@v6` for checkout/setup-python/setup-node, `@v5` for cache; not documented.  
5. **Backup Service Environment Variables**: `BACKUP_DIR` set to `/backups` (`docker-compose.yml:131`) but not listed in `docker.md` environment variables table.  
6. **Flask Security Headers**: Which headers are set by Flask vs nginx; unclear.  
7. **SSL Certificate Paths**: Hardcoded to `blog.example.com`; no guidance on customization.

### Potential Bugs / Concerns

1. **Celery Missing SMTP_HOST**: Newsletter tasks may fail if `SMTP_HOST` not set in celery environment.  
2. **Nginx CSP Weakness**: nginx overrides Flask's nonce-based CSP with `unsafe-inline` (`nginx/conf.d/blog.conf:29`).  
3. **Backup Service Read-Only Database**: `blog_data:/home/blog/instance:ro` prevents writes but backup.py may need temp writes.  
4. **APScheduler Race Condition**: Scaling `blog` container beyond 1 causes duplicate jobs; documented but no runtime detection.  
5. **SSL Certificate Hardcoded**: `blog.example.com` in nginx config; must be changed per deployment.  
6. **CI E2E Test Environment**: Uses `REDIS_URL: redis://localhost:6379/0` but redis runs in container; may cause connection issues.  
7. **Backup Service Volume Mount**: `blog_data` mounted read-only but backup.py may need to write temp files.

### Improvement Suggestions

1. **Add SMTP_HOST to celery service** in docker-compose.yml.  
2. **Clarify nginx proxy_pass** uses service name `blog` (not `127.0.0.1`).  
3. **Document which security headers are set by Flask vs nginx**.  
4. **Add BACKUP_DIR to environment variables table** in docker.md.  
5. **Note Docker Compose v2.20+ requirement** for `docker compose wait`.  
6. **Add SSL certificate customization guidance** (e.g., volume mounts or env vars).  
7. **Consider adding health check for celery service**.  
8. **Add resource limits for nginx service** (currently none).  
9. **Document backup service encryption key fallback behavior** (unencrypted if key fails).  
10. **Add CI workflow caching strategy** (pip, npm) for faster builds.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|---------|
| 1 | High | Add `SMTP_HOST` to celery service environment variables | `docker-compose.yml` |
| 2 | High | Correct nginx proxy_pass documentation from `127.0.0.1` to `blog` | `architecture/deployment/docker.md` |
| 3 | Medium | Clarify security header ownership (Flask vs nginx) | `architecture/deployment/security.md` |
| 4 | Medium | Add `BACKUP_DIR` to environment variables table | `architecture/deployment/docker.md` |
| 5 | Medium | Document Docker Compose v2.20+ requirement | `architecture/deployment/docker.md` |
| 6 | Low | Add SSL certificate customization guidance | `architecture/deployment/security.md` |
| 7 | Low | Add health check for celery service | `docker-compose.yml` |
| 8 | Low | Add resource limits for nginx service | `docker-compose.yml` |
| 9 | Low | Document backup service encryption fallback | `architecture/deployment/docker.md` |
| 10 | Low | Add CI workflow caching documentation | `architecture/deployment/cicd.md` |