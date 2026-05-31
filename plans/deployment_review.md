# Deployment Module Architecture Review

**Reviewed:** 2026-05-31
**Architecture Docs:** overview.md, docker.md, security.md, cicd.md
**Source Files:** Dockerfile, docker-compose.yml, nginx/, .github/workflows/ci.yml, scripts/

## Findings

### Verified Claims (Correct)

- **Docker services**: blog, celery, redis, nginx, backup all exist in docker-compose.yml
- **Dockerfile multi-stage build**: Builder stage (python:3.12-slim) + runtime stage with non-root `blog` user
- **Docker Compose profiles**: All services require explicit profiles (`production`, `backup`); no default profile
- **Blog service health check**: `interval: 30s`, `timeout: 10s`, `retries: 3`, `start_period: 10s` (docker-compose.yml:38-43)
- **Redis health check**: `interval: 10s`, `timeout: 3s`, `retries: 3` (docker-compose.yml:90-94)
- **Resource limits**: blog 512M/256M, celery 256M, redis 128M (docker-compose.yml:44-98)
- **Nginx rate limiting zones**: login 5r/m, admin 20r/m (nginx.conf:48-49)
- **Security headers in nginx**: All 8 documented headers confirmed at blog.conf:25-32
- **SSL certificate paths**: blog.conf:18-19 reference Let's Encrypt paths
- **APScheduler FileLock**: `timeout=0` confirmed at scheduler.py:76
- **APScheduler jobs**: send_daily_newsletter, cleanup_expired_subscribers, publish_scheduled_posts, run_daily_backup (scheduler.py:292-321)
- **Celery concurrency**: `--concurrency=1` confirmed at docker-compose.yml:66
- **All 5 Celery queues**: images, newsletter, webhooks, email, backup (tasks.py:30,135,194,344,386)
- **CI workflow 6 jobs**: lint-and-type, test, security-audit, frontend-build, docker-build, e2e-tests (ci.yml:11-173)
- **Weekly schedule**: Monday 08:00 UTC cron `0 8 * * 1` (ci.yml:8)
- **Coverage fail_under**: 80 confirmed in pyproject.toml:33
- **Test matrix**: Python 3.12, 3.13 (ci.yml:45)
- **Node.js 20**: frontend-build (ci.yml:107)
- **Session cookie settings**: SECURE, SAMESITE=Lax, HTTPONLY=True (__init__.py:180-184)
- **CSRF sliding window**: 5 tokens per session, token rotation on validation (csrf.py:20,56)
- **Account lockout**: MAX_FAILED_ATTEMPTS=5, configurable (config.py:162)
- **Backup encryption**: AES-256-GCM with PBKDF2-HMAC-SHA256, 600,000 iterations (backup_encryption.py:43,76)
- **Webhook encryption**: AES-256-GCM with direct key, no PBKDF2 (webhook_encryption.py:75)
- **Brotli commented out**: nginx.conf:26-34
- **client_max_body_size**: 16M (blog.conf:89)
- **Non-root user**: `blog` user created in Dockerfile:23, `USER blog` at Dockerfile:30
- **dev.sh Python check**: Requires >= 3.12 (dev.sh:11)
- **Granian CMD**: `--workers 4 --timeout 60 --port 5000` (Dockerfile:41)
- **Backup service**: working_dir `/home/blog`, entrypoint `python3 backup.py` (docker-compose.yml:128-129)
- **pyproject.toml test config**: testpaths=["tests"], addopts="--cov=app --cov-report=term-missing" (pyproject.toml:21-22)
- **Health endpoint rate limit**: 60 per minute via Flask-Limiter (meta.py:189)

### Discrepancies (Doc vs Code)

1. **docker.md:20 — Backup profile description**
   - Doc claims: `backup` profile includes `blog` (backup only)
   - Code: backup profile contains only the `backup` service (docker-compose.yml:136-137). The `blog` service is exclusively in the `production` profile.

2. **docker.md:65 — Celery concurrency line reference**
   - Doc claims: docker-compose.yml:58
   - Code: The `--concurrency=1` flag is at docker-compose.yml:66 (line 58 is a comment about APScheduler)

3. **docker.md:37 — Backup service line reference**
   - Doc claims: docker-compose.yml:111-129
   - Code: The backup service definition spans docker-compose.yml:119-137

4. **cicd.md:39 — E2E wait command**
   - Doc claims: `docker compose wait redis`
   - Code: ci.yml:150 uses `docker compose wait blog` (waits for the blog service, not redis)

5. **docker.md:205-208 — "email" health check does not exist**
   - Doc lists `email` as an optional health check
   - Code: The health endpoint (meta.py:200-287) has NO `checks["email"]` assignment. Actual optional checks are: `redis`, `celery`, `backup_freshness`. There is no SMTP connectivity check.

6. **docker.md:169 — Health check status code behavior**
   - Doc claims: "Returns 200 even if optional services are degraded"
   - Code: Returns 503 when the `database` check fails (meta.py:212). Returns 200 even when OTHER critical checks (scheduler, search, disk_space, db_integrity) are in error/degraded state. The doc wording is misleading; it should clarify the 503 behavior for database failures.

7. **docker.md:301 — Silent fallback behavior**
   - Doc claims: "no warning is logged" when encryption fails
   - Code: backup.py:69-70 logs a WARNING: `logger.warning("Backup encryption failed, proceeding without encryption")`

8. **Dockerfile:39 vs docker-compose.yml:41 — Healthcheck timeout mismatch**
   - Dockerfile HEALTHCHECK: `--timeout=3s`
   - docker-compose.yml override: `timeout: 10s`
   - Doc only documents the docker-compose value (10s). Running the image directly without docker-compose uses the 3s timeout.

9. **security.md:41 — Headers claim "Both Flask and nginx set these headers"**
   - Doc claims: Both layers set identical headers
   - Code: Flask CSP uses nonce-based policy (`script-src 'self' 'nonce-{nonce}'`, __init__.py:347-357). Nginx CSP uses `script-src 'self' 'unsafe-inline'` (blog.conf:29). These are different and potentially conflicting. Additionally, both layers set headers, which may produce duplicate headers on responses.

10. **security.md:54 — "Not set" headers claim**
    - Doc claims: `X-Download-Options`, `X-Permitted-Cross-Domain-Policies` are not set
    - Code: Flask sets both at __init__.py:340-341: `X-Download-Options: noopen` and `X-Permitted-Cross-Domain-Policies: none`

11. **security.md:47 — X-XSS-Protection**
    - Doc implies both Flask and nginx set this header
    - Code: Only nginx sets `X-XSS-Protection` (blog.conf:27). Flask does NOT set it (not found in __init__.py security headers). When accessed through nginx, it is present; if Flask is accessed directly, it is absent.

12. **docker.md:279-283 — Nginx proxy networking explanation**
    - Doc claims: "containers on the same user-defined network share a network namespace"
    - Code/Fact: Docker Compose containers on the same bridge network have SEPARATE network namespaces, each with their own IP. Containers communicate via DNS-resolvable service names (e.g., `blog`), not via `127.0.0.1`. Using `proxy_pass http://127.0.0.1:5000` from nginx would reach nginx's own loopback, not the blog service. The correct configuration should be `proxy_pass http://blog:5000`.

### Missing Documentation

1. **Nginx service has no health check** in docker-compose.yml — not documented as a gap
2. **Backup service has no health check** in docker-compose.yml — not documented as a gap
3. **Nginx service has no resource limits** in docker-compose.yml — not documented
4. **Backup service has no resource limits** in docker-compose.yml — not documented
5. **CI pipeline dependency chain**: e2e-tests depends on [test, docker-build]; test depends on lint-and-type — not documented
6. **Dockerfile HEALTHCHECK lacks start_period** — only docker-compose adds start_period:10s; running image directly has no grace period
7. **Celery task config**: `task_time_limit=300`, `task_soft_time_limit=240`, `worker_max_tasks_per_child=100` (celery_app.py:27-30) — not documented
8. **pip-audit strictness**: CI runs `pip-audit --fail-on=all` (ci.yml:97), more strict than documented "pip-audit"
9. **No automated SSL certificate renewal** documentation — certificates must be provisioned externally (only briefly noted in security.md:73)
10. **Backup service missing SECRET_KEY** in its environment variables — backup.py imports from app.services which may need app config; not documented whether SECRET_KEY is required for backup

### Potential Bugs / Concerns

1. **CRITICAL: Nginx proxy_pass uses 127.0.0.1** (blog.conf:52,65,75,84) — All four `proxy_pass` directives use `http://127.0.0.1:5000`. In standard Docker Compose networking, each container has its own network namespace. `127.0.0.1` from nginx refers to nginx itself, not the blog service. This configuration would fail unless Docker is configured with shared network namespaces. Should be `http://blog:5000`.

2. **Dockerfile healthcheck timeout too aggressive** — The 3-second timeout (Dockerfile:39) may cause false unhealthy status when the app is under load or starting up slowly. The docker-compose override to 10s mitigates this for compose-based deployments, but direct image usage suffers.

3. **No health checks for nginx and backup services** — If these containers crash or become unresponsive, Docker's restart policy alone may not detect the issue quickly. Health checks would enable automatic detection and restart.

4. **No resource limits for nginx and backup** — These services could consume unbounded memory/CPU, potentially impacting the blog service. nginx especially could be affected by slow client connections (slowloris).

5. **Duplicate security headers** — Flask (after_request) and nginx (add_header) both set the same security headers. Responses passing through nginx get double headers. While browsers typically use the first or last value, this is non-standard behavior and could cause confusion. CSP is particularly problematic as Flask uses nonces while nginx uses unsafe-inline.

6. **CSP policy inconsistency** — Flask CSP uses `script-src 'self' 'nonce-{nonce}'` (secure). Nginx CSP uses `script-src 'self' 'unsafe-inline'` (weaker). When nginx overwrites the Flask CSP header, the weaker policy applies. This defeats the nonce-based XSS protection.

7. **Backup service lacks SECRET_KEY** — The backup container (docker-compose.yml:130-136) does not include SECRET_KEY in its environment. If backup.py imports modules that require SECRET_KEY (e.g., app config loading), the service could fail at runtime.

8. **APScheduler always runs** — init_scheduler() is called unconditionally in __init__.py:457. Even in multi-container deployments, every blog replica starts its own APScheduler, which could cause duplicate jobs (documented in docker.md but still a deployment risk).

### Improvement Suggestions

1. **Fix nginx proxy_pass** — Change `proxy_pass http://127.0.0.1:5000` to `proxy_pass http://blog:5000` in all four location blocks in blog.conf.

2. **Add health checks for nginx and backup** — Add healthcheck sections in docker-compose.yml for these services.

3. **Add resource limits for nginx and backup** — Add `deploy.resources.limits` for both services.

4. **Remove "email" from health check docs** or implement an SMTP connectivity check in the health endpoint.

5. **Fix all line number references** in docker.md to match actual code positions.

6. **Clarify the backup profile description** — It contains only the `backup` service, not `blog`.

7. **Add Dockerfile HEALTHCHECK start_period** — Add `--start-period=10s` or document the discrepancy.

8. **Document CSP differences** — Explicitly note that nginx overrides Flask's nonce-based CSP with a weaker unsafe-inline policy, and recommend aligning them.

9. **Add SECRET_KEY to backup service** environment variables if required.

10. **Document CI dependency chain** — Show that lint-and-type -> test -> e2e-tests and docker-build -> e2e-tests.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | high | Fix nginx proxy_pass to use service name `blog` instead of `127.0.0.1` | source |
| 2 | high | Add health checks for nginx and backup services in docker-compose.yml | source |
| 3 | high | Add resource limits for nginx and backup services in docker-compose.yml | source |
| 4 | high | Align nginx CSP with Flask nonce-based CSP or document the security downgrade | source |
| 5 | med | Remove phantom "email" health check from docker.md or implement it in code | docs/source |
| 6 | med | Fix all line number references in docker.md (backup service, celery concurrency) | docs |
| 7 | med | Fix backup profile description in docker.md (should list `backup` service, not `blog`) | docs |
| 8 | med | Clarify health check HTTP status behavior: 503 for database errors, 200 for other critical failures | docs |
| 9 | med | Fix "no warning logged" claim in docker.md (backup.py:69-70 does log a warning) | docs |
| 10 | med | Fix cicd.md: e2e wait command is `docker compose wait blog`, not `redis` | docs |
| 11 | med | Fix security.md: X-Download-Options and X-Permitted-Cross-Domain-Policies ARE set by Flask | docs |
| 12 | med | Document CSP differences between Flask (nonce-based) and nginx (unsafe-inline) | docs |
| 13 | med | Add `start_period` to Dockerfile HEALTHCHECK or document the omission | source/docs |
| 14 | low | Document CI pipeline dependency chain (lint-and-type -> test -> e2e-tests) | docs |
| 15 | low | Document Celery task configuration (time limits, max tasks per child) | docs |
| 16 | low | Add SECRET_KEY to backup service environment if needed by app imports | source |
| 17 | low | Note pip-audit uses `--fail-on=all` (strict mode) in cicd.md | docs |
| 18 | low | Document that nginx X-XSS-Protection is only present when proxied through nginx | docs |
| 19 | low | Note Dockerfile healthcheck timeout (3s) differs from docker-compose override (10s) | docs |
