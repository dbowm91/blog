# Deployment Architecture Review

**Reviewed:** 2026-05-29
**Architecture Docs:** 
- `architecture/deployment/overview.md`
- `architecture/deployment/docker.md`
- `architecture/deployment/security.md`
- `architecture/deployment/cicd.md`

**Source Files:**
- `Dockerfile`
- `docker-compose.yml`
- `nginx/nginx.conf`
- `nginx/conf.d/blog.conf`
- `.github/workflows/ci.yml`
- `scripts/build_assets.py`
- `scripts/dev.sh`
- `scripts/update-assets.sh`
- `scripts/sync_backups.sh`
- `app/services/backup.py`
- `backup.py`

## Findings

### Verified Claims (Correct)

**Docker Compose Profiles:**
- Production profile correctly defined for `blog`, `celery`, `redis`, `nginx` services (docker-compose.yml:50-51, 78-79, 93-94, 110-111)
- Backup profile correctly defined for `backup` service (docker-compose.yml:130-131)
- Explicit profile requirement documented and matches implementation

**CI/CD Workflow (6 jobs):**
- `lint-and-type` job: ruff + mypy, Python 3.12 (ci.yml:11-38)
- `test` job: pytest with 80% coverage, Python 3.12/3.13 (ci.yml:40-71)
- `security-audit` job: pip-audit (ci.yml:73-97)
- `frontend-build` job: Node.js 20, npm ci + build (ci.yml:99-114)
- `docker-build` job: docker build . (ci.yml:116-122)
- `e2e-tests` job: Playwright, Docker-based with --profile production (ci.yml:124-185)

**Weekly Schedule:**
- Cron expression `0 8 * * 1` correctly set (Monday 08:00 UTC) (ci.yml:8)

**Dockerfile:**
- Multi-stage build with Python 3.12-slim (Dockerfile:1-12)
- Non-root user `blog` created (Dockerfile:23)
- Granian CMD correctly configured with 4 workers (Dockerfile:41)

**nginx Configuration:**
- Rate limiting zones defined in nginx.conf:48-49
- Security headers in blog.conf:25-32 match documentation (security.md:41-53)
- Brotli commented out (nginx.conf:26-34) matches documentation (docker.md:50-54)
- HTTP to HTTPS redirect at blog.conf:10-11
- Health check proxy at /health (blog.conf:82-87)
- client_max_body_size 16M (blog.conf:89)
- Login rate limit: 5r/m burst=5 nodelay (blog.conf:62-64)
- Admin rate limit: 20r/m burst=10 nodelay (blog.conf:72-74)

**Celery Configuration:**
- Single concurrency (--concurrency=1) (docker-compose.yml:60)
- Redis dependency with health check condition (docker-compose.yml:71-73)

**Resource Limits:**
- blog: 512M limit, 256M reservation (docker-compose.yml:46-49)
- celery: 256M limit (docker-compose.yml:76-77)
- redis: 128M limit (docker-compose.yml:91-92)

**Environment Variables (docker.md:86-106):**
- All documented env vars present in docker-compose.yml
- FLASK_ENV defaults to production (docker-compose.yml:16)
- REDIS_URL defaults to redis://redis:6379/0 (docker-compose.yml:23)

**Scripts:**
- build_assets.py: dry-run and force flags (build_assets.py:71-72)
- dev.sh: Python 3.14+ check (dev.sh:11)
- update-assets.sh: marked.js + Prism.js downloads (update-assets.sh:10-15)
- sync_backups.sh: --dry-run, --verify, --cleanup flags (sync_backups.sh:85-95)

**Granary Configuration (docker.md:188-202):**
- 4 workers, 60s timeout, asgi interface (Dockerfile:41)

### Discrepancies (Doc vs Code)

**docker.md:37 vs docker-compose.yml:113-131**
- **Doc claims:** backup service is at docker-compose.yml:111-129
- **Actual:** backup service is at lines 113-131 (2-line drift, within acceptable)
- Backup service definition confirmed correct in actual code

**docker.md:60 vs docker-compose.yml:53-79**
- **Doc claims:** Celery command: `celery -A app.celery_app worker --loglevel=info --concurrency=1`
- **Actual:** `celery -A app.celery_app worker --loglevel=info --concurrency=1` (docker-compose.yml:60)
- Correct - no drift

**docker.md:188-200 vs Dockerfile:41**
- **Doc claims:** CMD uses `--workers 4 --timeout 60 --host 0.0.0.0 --port 5000`
- **Actual:** `CMD ["granian", "--interface", "asgi", "--workers", "4", "--timeout", "60", "--host", "0.0.0.0", "--port", "5000", "run:asgi_app"]`
- Correct - matches exactly

**docker.md:162-169 vs scripts/build_assets.py**
- **Doc claims:** build_assets.py minifies CSS/JS with .orig backups, --dry-run, --force
- **Actual:** Matches (build_assets.py:58-61, 71-72)
- Correct

**docker.md:174-176 vs scripts/dev.sh**
- **Doc claims:** dev.sh checks Python >= 3.14, creates venv, installs deps, runs migrations
- **Actual:** Matches (dev.sh:11, 24-27, 40-42, 59-61)
- Correct

**docker.md:178-180 vs scripts/update-assets.sh**
- **Doc claims:** update-assets.sh fetches marked.js and Prism.js from jsDelivr
- **Actual:** Matches (update-assets.sh:10-15)
- Correct

**docker.md:182-184 vs scripts/sync_backups.sh**
- **Doc claims:** sync_backups.sh supports --dry-run, --verify, --cleanup, REMOTE_TYPE
- **Actual:** Matches (sync_backups.sh:85-95, 120)
- Correct

**security.md:59 vs nginx/nginx.conf:48-49**
- **Doc claims:** Rate limiting zones at nginx.conf:48-49
- **Actual:** `limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;` and `zone=admin:10m rate=20r/m;`
- Correct - but documentation refers to blog.conf while actual config is in nginx.conf main file (minor doc clarification issue)

**security.md:69-71 vs nginx/conf.d/blog.conf:18-19**
- **Doc claims:** SSL certificate paths at blog.conf:18-19
- **Actual:** Correct - `/etc/letsencrypt/live/blog.example.com/fullchain.pem` and `privkey.pem`
- Correct

### Missing Documentation

**APScheduler Multi-Container Limitation:**
- docker.md:76-84 describes APScheduler FileLock limitation for multi-container deployments
- However, no documentation on how to detect if multiple APScheduler instances are running
- No alerting mechanism documented for duplicate job execution

**Backup Encryption Key Loading:**
- docker.md:212-220 describes backup encryption key loading
- Documents that BACKUP_ENCRYPTION_KEY is expected from host environment
- docker-compose.yml:126 confirms environment variable reference
- However, does not document that encryption keys can also come from config.toml via app.config

**Celery Worker Scaling Warning:**
- docker.md:69-72 shows how to scale celery with --scale
- Does not warn that scaling celery with --concurrency=1 increases total concurrency
- A user scaling celery from 1 to 3 containers would have 3x parallelism, not 1x

**Health Check Details:**
- docker.md:108-140 documents /health endpoint
- Does not mention that optional checks (backup_freshness, email, redis, celery) are only shown in detailed output, not basic output
- Missing documentation on what triggers a "degraded" status

**Nginx Process Model:**
- security.md:77 mentions nginx runs as root with worker as nginx user
- nginx.conf:1 confirms `user nginx;`
- Does not document that the app and celery containers run as `blog` user (non-root)

**Backup Service Entry Point:**
- docker-compose.yml:123 shows `entrypoint: ["python3", "backup.py"]`
- docker.md:37 correctly identifies working_dir: /home/blog
- However, docker.md does not document that the backup service uses `entrypoint` (not `command`) which overrides any CMD in Dockerfile

### Potential Bugs / Concerns

**1. E2E Test Race Condition (ci.yml:147-149)**
- `docker compose up -d --profile production` starts services
- `docker compose wait redis` only waits for redis to be ready
- The blog service may not be healthy yet when tests start (blog has start_period: 10s per docker-compose.yml:43)
- Tests then poll /health up to 30 times with 2-second intervals (ci.yml:153-162)
- This works but the wait loop could be simplified by waiting for blog directly

**2. APScheduler FileLock Limitation Not Enforced**
- docker-compose.yml shows single celery container with --concurrency=1
- No mechanism prevents user from running `docker-compose up -d --scale celery=3`
- This would cause APScheduler jobs to run on all 3 replicas simultaneously
- May cause duplicate newsletter sends, duplicate backups
- No warning in docker-compose.yml or documentation about this consequence

**3. Backup Service Encryption Key Dependency Chain**
- docker-compose.yml:125-129 sets BACKUP_ENCRYPTION_KEY in environment
- But backup.py:27 imports `from app.services.backup import create_backup`
- app.services.backup imports from `app.backup_encryption` (backup.py:101)
- If `app.backup_encryption` fails to load the key, backup silently falls back to unencrypted (backup.py:103-106)
- No error raised if BACKUP_ENCRYPTION_KEY is missing - backup just proceeds without encryption
- This is a security concern - encryption may be silently disabled

**4. Python 3.14 Requirement in dev.sh vs Actual Dependencies**
- dev.sh:11 requires Python >= 3.14
- But Dockerfile:1 uses python:3.12-slim
- This means development environment requires Python 3.14 but production uses 3.12
- Could cause compatibility issues if features used in code require 3.14

### Improvement Suggestions

**1. Clarify Profile Requirements in Documentation**
Add explicit note that docker-compose requires `--profile` flag for all commands, e.g.:
```bash
docker compose up -d --profile production
docker compose --profile backup up
```
This is already mentioned in AGENTS.md but could be more prominent in deployment docs.

**2. Add Warning About Celery Scaling with APScheduler**
The docker-compose.yml:60 comment only says "Single concurrency to prevent duplicate newsletter sends" but does not warn that scaling containers changes this. Consider adding:
```yaml
# WARNING: APScheduler runs on all replicas. Scaling celery beyond 1 container
# without external job coordination (Redis, etcd) may cause duplicate job execution.
```

**3. Document Encryption Key Validation**
Add explicit check in backup.py or docker-compose.yml to fail fast if BACKUP_ENCRYPTION_KEY is set but cannot be loaded. Current behavior silently proceeds without encryption.

**4. Align Python Version Requirements**
Either:
- Update dev.sh to accept Python 3.12 (matching production), or
- Update Dockerfile to use python:3.14-slim (aligning dev with prod)

**5. Add Health Check Timeout Documentation**
Document that the health check has a start_period of 10s (docker-compose.yml:43) meaning the container won't be marked healthy for 10 seconds after startup.

**6. Document E2E Test Dependency on Docker Build**
The e2e-tests job (ci.yml:124-185) depends on docker-build completing first (ci.yml:126), but the frontend-build job is not a dependency. If frontend build fails, e2e tests may still run with stale assets.

**7. Add Redis Health Check Dependency for Celery**
docker-compose.yml:71-73 correctly shows celery depends on redis being healthy, but the backup service does not have this dependency (docker-compose.yml:113-131). If redis is not ready when backup runs, backup may fail silently.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | high | Add APScheduler scaling warning to docker-compose.yml celery service comment | source |
| 2 | high | Clarify Python version alignment (3.12 vs 3.14) between dev.sh and Dockerfile | docs/source |
| 3 | med | Add explicit profile usage examples to deployment docs | docs |
| 4 | med | Document backup encryption key validation behavior | docs/source |
| 5 | med | Clarify that rate limiting config is in nginx.conf (not blog.conf) | docs |
| 6 | low | Add health check start_period documentation | docs |
| 7 | low | Consider adding redis health dependency to backup service | source |
