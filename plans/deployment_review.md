# Deployment Module Architecture Review

**Reviewed:** May 29, 2026
**Architecture Docs:** overview.md, docker.md, security.md, cicd.md
**Source Files:** Dockerfile, docker-compose.yml, nginx/, .github/workflows/, scripts/

## Findings

### Verified Claims (Correct)

- **Docker service names** (docker.md:7-12): `blog`, `celery`, `redis`, `nginx` all exist in docker-compose.yml
- **Docker images** (docker.md:11-12): `redis:7-alpine` (docker-compose.yml:74), `nginx:alpine` (docker-compose.yml:89)
- **Dockerfile multi-stage build** (docker.md:24-26): Builder + Runtime stages confirmed (Dockerfile:1,12)
- **Non-root user** (docker.md:29): `blog` user created (Dockerfile:23) and used (Dockerfile:30)
- **Backup service volumes** (docker.md:37): `blog_data:/home/blog/instance:ro` confirmed (docker-compose.yml:109), `./backups:/backups` confirmed (docker-compose.yml:110)
- **Backup working_dir** (docker.md:37): `/home/blog` confirmed (docker-compose.yml:111)
- **Celery concurrency=1** (docker.md:65): Confirmed (docker-compose.yml:52)
- **Celery task queues** (docker.md:58-63): All 5 queues confirmed in app/tasks.py: `images` (line 30), `newsletter` (line 135), `webhooks` (line 194), `email` (line 333), `backup` (line 375)
- **Resource limits** (docker.md:148-155): blog 512M/256M (docker-compose.yml:42-44), celery 256M (line 69), redis 128M (line 84)
- **Brotli commented out** (docker.md:52-54): Lines 26-34 of nginx.conf confirmed
- **Rate limiting zones** (security.md:58): `login` 5r/m, `admin` 20r/m confirmed (nginx.conf:48-49)
- **Security headers** (security.md:41-52): All 8 headers present at blog.conf:25-32
- **SSL certificate paths** (security.md:69-71): Lines 18-19 of blog.conf confirmed
- **nginx user directive** (security.md:77): `user nginx;` at nginx.conf:1
- **Session cookie config** (security.md:16-20): `SESSION_COOKIE_SECURE`, `SameSite=Lax`, `HTTPONLY=True` confirmed (app/__init__.py:180-184)
- **Sliding session expiration** (security.md:22): `last_activity` in session confirmed (app/__init__.py:301-330)
- **CSRF sliding window** (security.md:26-27): 5-token window confirmed (app/csrf.py:8,20), timing-safe comparison via `hmac.compare_digest` confirmed (app/csrf.py:54)
- **pytest min coverage 80%** (cicd.md:19): `--cov-fail-under=80` confirmed (ci.yml:97)
- **CI Python versions** (cicd.md:20): 3.12, 3.13 matrix confirmed (ci.yml:71)
- **e2e Docker-based** (cicd.md:29): `--profile production` confirmed (ci.yml:174)
- **e2e Playwright/Chromium** (cicd.md:30): Confirmed (ci.yml:193-194)

### Discrepancies (Doc vs Code)

1. **CI workflow filename** (cicd.md:1): Doc references `test.yml` but actual file is `.github/workflows/ci.yml`
   - **File:** `architecture/deployment/cicd.md:1`

2. **Missing default profile** (docker.md:18): Doc claims `(default)` profile has `blog, redis`, but ALL services in docker-compose.yml have explicit profiles (`production` or `backup`). A bare `docker compose up` starts zero services.
   - **File:** `architecture/deployment/docker.md:18`, `docker-compose.yml:45-46,70-71,85-86,102-103,119-120`

3. **Missing backup service from Services table** (docker.md:7-12): Services table lists 4 services but `backup` service (docker-compose.yml:105-120) is omitted. It should be listed.
   - **File:** `architecture/deployment/docker.md:7-12`

4. **Line number drift - backup.py** (docker.md:37): Doc claims `backup.py:24` for relative path. Actual line is `backup.py:23`. Off by 1.
   - **File:** `architecture/deployment/docker.md:37`, `backup.py:23`

5. **Line number drift - docker-compose.yml backup service** (docker.md:37): Doc claims backup service at `docker-compose.yml:103-118`. Actual range is `docker-compose.yml:105-120`. Off by 2.
   - **File:** `architecture/deployment/docker.md:37`, `docker-compose.yml:105-120`

6. **Line number drift - celery concurrency** (docker.md:65): Doc references `docker-compose.yml:50`. The `--concurrency=1` flag is in the command at `docker-compose.yml:52`. Off by 2.
   - **File:** `architecture/deployment/docker.md:65`, `docker-compose.yml:52`

7. **CI missing schedule trigger** (cicd.md:9): Doc says triggers are `push, pull_request` only. Actual ci.yml also has `schedule` (weekly cron at Monday 08:00, line 7-8).
   - **File:** `architecture/deployment/cicd.md:9`, `.github/workflows/ci.yml:7-8`

8. **CI missing 3 jobs** (cicd.md:11-31): Doc documents only 4 jobs. Actual ci.yml has 7 jobs: `openapi-validation`, `frontend-build`, `docker-build` are undocumented.
   - **File:** `architecture/deployment/cicd.md:11-31`, `.github/workflows/ci.yml:40-148`

9. **pytest.ini inaccurate** (cicd.md:35-38): Doc claims pytest.ini defines test discovery, coverage HTML, and min coverage. Actual pytest.ini (3 lines) only defines markers. Coverage settings are passed via CLI args in ci.yml:97.
   - **File:** `architecture/deployment/cicd.md:35-38`, `pytest.ini:1-3`

10. **Docker compose v2 syntax** (cicd.md:31): Doc uses `docker-compose wait` (hyphenated v1 syntax). Actual ci.yml uses `docker compose wait` (spaced v2 syntax, line 175).
    - **File:** `architecture/deployment/cicd.md:31`, `.github/workflows/ci.yml:175`

### Missing Documentation

1. **Dockerfile base image**: `python:3.12-slim` is not mentioned in docker.md. The specific base image matters for security and compatibility.
   - **File:** `Dockerfile:1,12`

2. **Granian worker config**: Dockerfile runs `granian --workers 4 --timeout 60` (line 41). Worker count and timeout not documented.
   - **File:** `Dockerfile:41`

3. **scripts/ directory**: Four scripts exist but are not documented in any deployment doc:
   - `scripts/build_assets.py` - CSS/JS minification
   - `scripts/dev.sh` - Development setup
   - `scripts/update-assets.sh` - CDN asset updates
   - `scripts/sync_backups.sh` - Off-site backup sync
   - **Files:** `scripts/`

4. **Celery worker configuration** (docker.md:56-72): Missing `worker_prefetch_multiplier=1`, `worker_max_tasks_per_child=100`, `task_time_limit=300`, `task_soft_time_limit=240` from celery_app.py:27-30.
   - **File:** `app/celery_app.py:20-31`

5. **Missing `SQLALCHEMY_DATABASE_URI` env var** (docker.md:86-103): `docker-compose.yml:11` passes `SQLALCHEMY_DATABASE_URI` but it's not listed in the Environment Variables table.
   - **File:** `architecture/deployment/docker.md:86-103`, `docker-compose.yml:11`

6. **Missing `API_KEY` env var** (docker.md:86-103): `docker-compose.yml:26` passes `API_KEY` but it's not in the Environment Variables table.
   - **File:** `architecture/deployment/docker.md:86-103`, `docker-compose.yml:26`

7. **Missing `SESSION_COOKIE_SECURE` env var** (docker.md:86-103): `docker-compose.yml:16` passes this but it's not in the Environment Variables table.
   - **File:** `architecture/deployment/docker.md:86-103`, `docker-compose.yml:16`

8. **Missing `FLASK_ENV` verification** (docker.md:90): Doc lists `FLASK_ENV` but it doesn't appear in docker-compose.yml or Dockerfile. May be vestigial documentation.
   - **File:** `architecture/deployment/docker.md:90`

9. **Backup encryption key source** (docker.md:117-118, docker-compose.yml:117): Backup service env comments say keys are "loaded from config.toml in app" but no mechanism for config.toml loading exists in the backup container. The backup.py entrypoint imports from `app.services.backup` but doesn't set up Flask config loading.
   - **File:** `docker-compose.yml:117-118`, `backup.py:27`

### Potential Bugs / Concerns

1. **Missing validate_openapi.py script**: ci.yml:64 references `python scripts/validate_openapi.py` but this file does not exist. CI will fail on the `openapi-validation` job.
   - **File:** `.github/workflows/ci.yml:64`, `scripts/` (missing)

2. **Backup container config.toml gap**: The backup service (docker-compose.yml:112) runs `python3 backup.py` with `PYTHONPATH=/home/blog`. The backup.py imports `app.services.backup` which may need config.toml for encryption keys, but no volume mounts or env vars provide it. The `BACKUP_ENCRYPTION_KEY` is only mentioned in comments (docker-compose.yml:117), not passed as an env var.
   - **File:** `docker-compose.yml:105-120`

3. **WORKDIR mismatch**: Dockerfile sets `WORKDIR /app` (line 14) but volumes mount to `/home/blog/instance`, `/home/blog/logs`, `/home/blog/app/static/uploads`. Blog and celery services run from `/app` while data directories live under `/home/blog`. Works because volumes are absolute mounts, but confusing.
   - **File:** `Dockerfile:14,28`, `docker-compose.yml:30-32`

4. **nginx proxy to 127.0.0.1** (blog.conf:52): `proxy_pass http://127.0.0.1:5000` - nginx and blog run in separate containers, so this would only work if they share a network namespace. With default docker-compose networking, this should be `http://blog:5000`. However, since nginx depends on blog being healthy and they're on the same compose network, this may work via Docker's embedded DNS if the blog service name resolves. This is a common anti-pattern that may silently break in some Docker networking configurations.
   - **File:** `nginx/conf.d/blog.conf:52,65,75,84`

5. **Dockerfile HEALTHCHECK vs compose healthcheck**: Dockerfile:39 defines `HEALTHCHECK` with 3s timeout and no retries. docker-compose.yml:33-38 overrides with 10s timeout, 3 retries, and 10s start_period. The Dockerfile HEALTHCHECK is effectively dead code in compose deployments.
   - **File:** `Dockerfile:39`, `docker-compose.yml:33-38`

### Improvement Suggestions

1. Add `(no profile)` or clarify that all services require explicit `--profile production` in docker.md
2. Document the `backup` service in the Docker Services table
3. Add missing CI jobs (`openapi-validation`, `frontend-build`, `docker-build`) and `schedule` trigger to cicd.md
4. Document the scripts/ directory in a new or existing deployment doc
5. Add `SQLALCHEMY_DATABASE_URI`, `API_KEY`, `SESSION_COOKIE_SECURE` to the environment variables table
6. Remove or verify `FLASK_ENV` - it's not used in docker-compose.yml
7. Fix all line number references (backup.py:24→23, docker-compose.yml:103→105, docker-compose.yml:50→52)
8. Rename `test.yml` reference to `ci.yml` in cicd.md
9. Update `pytest.ini` documentation to reflect actual content (markers only)
10. Fix `docker-compose` to `docker compose` in cicd.md for v2 syntax consistency
11. Consider adding encryption key env vars to backup service if config.toml isn't loaded
12. Resolve the nginx 127.0.0.1 proxy_pass if Docker networking requires service name resolution

## Action Items

| # | Priority | Description | Docs Affected |
|---|----------|-------------|---------------|
| 1 | high | Create missing `scripts/validate_openapi.py` or remove the CI job referencing it | cicd.md |
| 2 | high | Fix CI workflow filename: `test.yml` → `ci.yml` | cicd.md |
| 3 | high | Add `openapi-validation`, `frontend-build`, `docker-build` jobs and `schedule` trigger to CI docs | cicd.md |
| 4 | high | Fix docker-compose profiles: clarify all services require `--profile production` | docker.md |
| 5 | med | Add `backup` service to Docker Services table | docker.md |
| 6 | med | Fix line number references: backup.py:24→23, docker-compose.yml:103→105, docker-compose.yml:50→52 | docker.md |
| 7 | med | Add missing env vars: `SQLALCHEMY_DATABASE_URI`, `API_KEY`, `SESSION_COOKIE_SECURE` | docker.md |
| 8 | med | Remove `FLASK_ENV` if unused or document its actual purpose | docker.md |
| 9 | med | Fix `docker-compose` → `docker compose` (v2 syntax) | cicd.md |
| 10 | med | Fix `pytest.ini` documentation to reflect actual content | cicd.md |
| 11 | low | Document scripts/ directory (build_assets, dev.sh, update-assets, sync_backups) | docker.md or new doc |
| 12 | low | Document Granian worker count (4) and timeout (60s) | docker.md |
| 13 | low | Address backup container config.toml / encryption key loading | docker-compose.yml |
| 14 | low | Verify nginx proxy_pass 127.0.0.1 works with Docker networking | blog.conf |
