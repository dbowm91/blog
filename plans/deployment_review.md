# Deployment Architecture Review

**Reviewed:** 2026-06-02
**Architecture Docs:** architecture/deployment/overview.md, architecture/deployment/docker.md, architecture/deployment/security.md, architecture/deployment/cicd.md
**Source Files:** Dockerfile, docker-compose.yml, nginx/nginx.conf, nginx/conf.d/blog.conf, .github/workflows/ci.yml, scripts/dev.sh, app/celery_app.py

## Findings

### Verified Claims (Correct)

#### Docker Services (docker-compose.yml)
- All 5 services present: `blog`, `celery`, `redis`, `nginx`, `backup`
- Service images match documentation: blog/celery/backup custom, redis:7-alpine, nginx:alpine
- Profile assignments: `production` (blog, celery, redis, nginx), `backup` (backup)
- Resource limits: blog 512M limit/256M reservation, celery 256M limit, redis 128M limit
- Health check: `curl -f http://localhost:5000/health`, 30s interval, 10s timeout, 3 retries, 10s start_period
- `blog` depends_on `redis` with `condition: service_healthy`
- `nginx` depends_on `blog` with `condition: service_healthy`
- Celery command: `--concurrency=1` (docker-compose.yml:66)
- APScheduler warning comment at docker-compose.yml:56-58

#### Dockerfile
- Multi-stage build with python:3.12-slim
- Builder stage installs dependencies with venv
- Non-root user `blog` created (line 23) and used (line 30)
- Granian ASGI server: `--workers 4 --timeout 60 --host 0.0.0.0 --port 5000` (line 41)
- HEALTHCHECK instruction present (line 39)
- EXPOSE 5000 (line 37)

#### Nginx Configuration
- `proxy_pass http://blog:5000` at nginx/conf.d/blog.conf:52
- Rate limiting zones at nginx/nginx.conf:48-49:
  - `login`: 5r/m burst=5 nodelay
  - `admin`: 20r/m burst=10 nodelay
- Security headers at nginx/conf.d/blog.conf:25-32:
  - X-Frame-Options: DENY
  - X-Content-Type-Options: nosniff
  - X-XSS-Protection: 1; mode=block
  - Referrer-Policy: strict-origin-when-cross-origin
  - Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; ...
  - Strict-Transport-Security: max-age=31536000; includeSubDomains
  - Cross-Origin-Opener-Policy: same-origin
  - Permissions-Policy: camera=(), microphone=(), geolocation=()
- Brotli compression commented out at nginx.conf:26-34
- client_max_body_size 16M at blog.conf:89
- Gzip compression enabled at nginx.conf:36-42

#### CI/CD Workflow (.github/workflows/ci.yml)
- Exactly 6 jobs: `lint-and-type`, `test`, `security-audit`, `frontend-build`, `docker-build`, `e2e-tests`
- Job dependencies: `lint-and-type` → `test` → `e2e-tests`; `docker-build` → `e2e-tests`
- Schedule: Monday 08:00 UTC (cron: "0 8 * * 1")
- Python 3.12 for lint-and-type, security-audit, frontend-build, docker-build, e2e-tests
- Python 3.12, 3.13 for test job (matrix)
- frontend-build uses Node.js 20
- e2e-tests uses `docker compose up -d --profile production` and `docker compose wait blog`
- pip-audit runs with `--fail-on=all`
- Minimum 80% coverage with `--cov-fail-under=80`

#### Celery Configuration (app/celery_app.py)
- `task_time_limit=300` (line 27)
- `task_soft_time_limit=240` (line 28)
- `worker_prefetch_multiplier=1` (line 29)
- `worker_max_tasks_per_child=100` (line 30)
- `task_acks_late=True` and `task_reject_on_worker_lost=True` when app context available (lines 35-36)

#### Scripts
- `dev.sh` checks Python >= 3.12 (line 11)
- `dev.sh` creates venv, installs deps, runs `flask db upgrade`, prints env var instructions

### Discrepancies (Doc vs Code)

1. **docker.md:37** - Backup service line range
   - **Doc claims:** `docker-compose.yml:119-137`
   - **Actual:** `docker-compose.yml:120-140` (start is line 120, end is line 140)
   - **Impact:** Minor - off by 1 for start, off by 3 for end

2. **security.md:54-55** - Missing nginx security headers
   - **Doc claims:** `X-Download-Options: noopen` and `X-Permitted-Cross-Domain-Policies: none` are set at `nginx/conf.d/blog.conf:25-32`
   - **Actual:** nginx/conf.d/blog.conf:25-32 does NOT include these headers. Only the 8 headers listed in "Verified Claims" above are present
   - **Impact:** Documentation claims headers that don't exist in nginx config

3. **docker.md:52** - Brotli line reference
   - **Doc claims:** Brotli configuration commented out at `nginx/nginx.conf:26-34`
   - **Actual:** Correct - lines 26-34 contain commented Brotli configuration
   - **Impact:** None - this one is accurate

4. **docker.md:67** - Celery config line reference
   - **Doc claims:** Celery configuration in `app/celery_app.py:20-31`
   - **Actual:** task_time_limit=300 at line 27, task_soft_time_limit=240 at line 28, worker_prefetch_multiplier=1 at line 29, worker_max_tasks_per_child=100 at line 30. Lines 20-31 contain the `celery_app.conf.update()` call containing these settings
   - **Impact:** Minor - the settings are within the range, just not at the exact lines claimed

### Missing Documentation

1. **Nginx X-Download-Options and X-Permitted-Cross-Domain-Policies headers** - security.md claims these are set in nginx but they are not

2. **Docker health check timeout override** - docker.md:206 correctly notes that docker-compose overrides Dockerfile HEALTHCHECK timeout (3s → 10s), but this cascading configuration could be clearer

3. **Nginx process model user** - security.md:86 mentions nginx worker processes run as `nginx` user, which is correct at nginx.conf:1

4. **Redis health check** - docker-compose.yml:91-95 defines redis health check but docker.md doesn't document it

5. **Backup service entrypoint** - docker.md:37 correctly notes `working_dir: /home/blog` and `entrypoint: ["python3", "backup.py"]` at docker-compose.yml:130

### Potential Bugs / Concerns

1. **Nginx CSP overrides Flask CSP** (security.md:61-63 documents this correctly as a concern)
   - nginx CSP `script-src 'self' 'unsafe-inline'` replaces Flask's nonce-based CSP
   - This weakens XSS protection - documented correctly but worth highlighting

2. **APScheduler multi-container limitation** (docker-compose.yml:56-58, docker.md:103-151)
   - APScheduler with FileLock only works on single machine
   - Multiple container replicas will each run their own scheduler
   - Warning comment present in docker-compose.yml but could be more prominent

3. **E2E test Redis URL mismatch** (.github/workflows/ci.yml:162)
   - e2e-tests sets `REDIS_URL: redis://localhost:6379/0`
   - But services are started with `docker compose up -d --profile production`
   - Redis is accessed via Docker networking, not localhost
   - This could cause issues if Redis URL is used in tests

### Improvement Suggestions

1. **Add missing nginx security headers** - Add `X-Download-Options` and `X-Permitted-Cross-Domain-Policies` to nginx/conf.d/blog.conf:25-32, or remove from security.md if not intended

2. **Fix backup service line reference** - Update docker.md:37 from `docker-compose.yml:119-137` to `docker-compose.yml:120-140`

3. **Clarify Redis URL in E2E tests** - The REDIS_URL in e2e-tests job may not be needed since Docker Compose handles networking

4. **Document Redis health check** - Add redis health check configuration to docker.md

5. **Standardize line number references** - Consider using function names or ranges instead of exact line numbers to reduce drift

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | high | Add missing `X-Download-Options` and `X-Permitted-Cross-Domain-Policies` headers to nginx/conf.d/blog.conf, OR remove from security.md | docs/source |
| 2 | medium | Fix backup service line reference in docker.md:37 (should be 120-140, not 119-137) | docs |
| 3 | low | Investigate REDIS_URL usage in e2e-tests job (.github/workflows/ci.yml:162) | source |
| 4 | low | Document Redis health check in docker.md | docs |
| 5 | low | Consider using symbolic references (function names) instead of line numbers in docs | docs |