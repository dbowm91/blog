# Improvement Plan 5: Tech Stack Review & Deployment Fixes

**Date:** 2026-04-28  
**Scope:** Docker configuration, Granian integration, deployment scripts, documentation accuracy

---

## Executive Summary

A deep-dive review of the blog CMS tech stack and deployment infrastructure revealed **3 critical issues** and **3 minor issues**. The most significant problem is that despite documentation promoting Granian (Rust-based ASGI server), the Docker setup actually uses Gunicorn. Additionally, a circular dependency in `docker-compose.yml` will prevent successful deployment, and health endpoint documentation doesn't match the actual implementation.

All issues are documented with specific file locations, current state, and required changes.

---

## Critical Issues (High Priority)

### Issue 1: Granian Not Actually Used in Docker Deployment

**Severity:** High  
**Status:** Documentation says Granian, Dockerfile uses Gunicorn

#### Current State
| File | Line | Current Content | Problem |
|------|------|-----------------|---------|
| `requirements.txt` | All | No `granian` entry | Granian not installed |
| `Dockerfile` | 12 | `RUN pip install --user --no-cache-dir -r requirements.txt gunicorn` | Installs Gunicorn |
| `Dockerfile` | 27 | `CMD ["gunicorn", "--bind", "0.0.0.0:5000", ...]` | Runs Gunicorn |

#### What Works
- `run.py` correctly exports `asgi_app = WsgiToAsgi(app)` (line 9)
- `asgiref>=3.8,<4.0` is already in requirements.txt
- Documentation (README.md, DEPLOY.md) correctly describes Granian usage

#### Required Changes

**File: `requirements.txt`**
```diff
+ granian>=2.7.0,<3.0
```

**File: `Dockerfile`**
```dockerfile
# Line 12 - Change from:
- RUN pip install --user --no-cache-dir -r requirements.txt gunicorn
# To:
+ RUN pip install --user --no-cache-dir -r requirements.txt

# Line 27 - Change from:
- CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-", "run:app"]
# To:
+ CMD ["granian", "--interface", "asgi", "--workers", "2", "--host", "0.0.0.0", "--port", "5000", "run:asgi_app"]
```

**Notes:**
- Granian 2.7.0+ has pre-built wheels for Python 3.14 (no Rust toolchain needed)
- Use `--interface asgi` with `run:asgi_app` (WsgiToAsgi wrapper)
- Adjust workers based on container resources (2 is safe default for 512MB RAM)

---

### Issue 2: Docker-Compose Circular Dependency

**Severity:** High  
**Status:** Services cannot start due to circular `depends_on`

#### Current State
**File:** `docker-compose.yml` lines 24-26 and 41-43

```yaml
services:
  blog:
    # ...
    depends_on:
      nginx:
        condition: service_healthy  # Blog waits for nginx

  nginx:
    # ...
    depends_on:
      blog:
        condition: service_healthy  # Nginx waits for blog
```

**Problem:** Neither service can start first → deadlock during `docker-compose up`

#### Required Changes

**File:** `docker-compose.yml`

Remove `depends_on` from `blog` service (lines 24-26):

```yaml
  blog:
    build: .
    restart: unless-stopped
    expose:
      - "5000"
    environment:
      - SECRET_KEY=${SECRET_KEY:?SECRET_KEY is required}
      - ADMIN_PASSWORD=${ADMIN_PASSWORD:?ADMIN_PASSWORD is required}
      - ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
      - SMTP_USER=${SMTP_USER:-}
      - SMTP_PASSWORD=${SMTP_PASSWORD:-}
      - SESSION_COOKIE_SECURE=${SESSION_COOKIE_SECURE:-true}
    volumes:
      - blog_data:/home/blog/instance
      - blog_logs:/home/blog/logs
      - blog_uploads:/home/blog/app/static/uploads
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    # REMOVED: depends_on nginx (circular dependency)
    profiles:
      - production
```

**Keep** `nginx` depends_on `blog` (optional, but helps avoid immediate 502 errors):

```yaml
  nginx:
    image: nginx:alpine
    # ...
    depends_on:
      blog:
        condition: service_healthy
```

---

### Issue 3: Health Endpoint Documentation Mismatch & Status Detection

**Severity:** High  
**Status:** DEPLOY.md shows incorrect JSON structure; docker healthcheck doesn't detect degraded status

#### Current State

**Actual implementation** (`app/routes/public.py` lines 828-914):
```json
{
  "status": "ok" | "degraded",
  "checks": {
    "database": "ok" | "error",
    "scheduler": "running" | "stopped" | "disabled",
    "search": "ok" | "unavailable" | "error"
  },
  "timestamp": "2026-04-28T15:41:33.414966+00:00"
}
```

**Documentation** (DEPLOY.md lines 946-952):
```json
{
  "status": "ok",
  "database": "connected",  ← WRONG: should be "ok" and nested under "checks"
  "scheduler": "running",
  "timestamp": "2026-04-01T12:00:00+00:00"
}
```

**Docker healthcheck issue:**
```yaml
test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
```
This checks HTTP status codes:
- Returns non-zero exit for 503 (database failure) → unhealthy ✓
- Returns 0 exit for 200 (including "degraded" status) → healthy ✗ (should detect degraded)

**Note:** The code correctly returns 503 when database check fails (line 868). The issue is that "degraded" status still returns HTTP 200.

#### Required Changes

**Option A: Fix Documentation (Recommended)**
Update DEPLOY.md lines 946-952 to match actual JSON structure from `app/routes/public.py`.

**Option B: Fix Code + Documentation**
1. Simplify `/health` response to flat structure
2. Return 503 when any check fails (not just database)
3. Update DEPLOY.md accordingly

**Recommended: Option A** (preserve current nested structure, fix docs)

**Correct JSON structure (from actual code lines 897-901):**
```python
{
    "status": "ok" | "degraded",
    "checks": {
        "database": "ok" | "error",
        "scheduler": "running" | "stopped" | "disabled",
        "search": "ok" | "unavailable" | "error"
    },
    "timestamp": "2026-04-28T15:41:33.414966+00:00"
}
```

**File:** `DEPLOY.md` (lines 946-952) - update to show correct structure:
```markdown
```json
{
  "status": "ok",
  "checks": {
    "database": "ok",
    "scheduler": "running",
    "search": "ok"
  },
  "timestamp": "2026-04-01T12:00:00+00:00"
}
```
```

**File:** `docker-compose.yml` healthcheck (line 19):
```yaml
# Better healthcheck that detects degraded status
test: ["CMD", "bash", "-c", "curl -sf http://localhost:5000/health | grep -q '\"status\": \"ok\"'"]
```

---

## Minor Issues (Medium/Low Priority)

### Issue 4: README.md Logout Route Documentation Error

**File:** `README.md` line 239  
**Problem:** Documents `GET /admin/logout`, actual route is `POST /admin/logout`

**Fix:**
```markdown
| `POST /admin/logout` | Logout |
```

**Location:** `/home/sugarwookie/projects/blog/app/routes/admin/auth.py` line 61

---

### Issue 5: Missing Route Documentation in README.md

The following routes exist in code but are not documented in README.md:

| Route | Location | Purpose |
|-------|----------|---------|
| `GET /page/<slug>` | `app/routes/public.py:222` | Static pages |
| `GET /s/<code>` | `app/routes/public.py:388` | Short URLs |
| `GET /preview/<id>` | `app/routes/public.py:411` | Post preview |
| `POST /api/track-share` | `app/routes/public.py:469` | Share tracking |
| `GET /archive` | `app/routes/public.py:123` | Post archive |
| `GET /admin/pages` | `app/routes/admin/pages.py` | Page management |

**Fix:** Add these to the Routes section in README.md

---

### Issue 6: Docker-Compose Backup Service Minor Issue

**File:** `docker-compose.yml` lines 47-57  
**Problem:** Sets `BACKUP_DIR` environment variable, but `backup.py` uses `--dir` argument

**Current:**
```yaml
backup:
  # ...
  environment:
    - BACKUP_DIR=/backups
```

**Fix (choose one):**

**Option A:** Update `backup.py` to check `BACKUP_DIR` env var
```python
import os
backup_dir = os.environ.get('BACKUP_DIR', 'backups')
```

**Option B:** Change entrypoint to use `--dir` argument:
```yaml
entrypoint: ["python3", "backup.py", "--dir", "/backups"]
```

**Recommended:** Option B (simpler, no code change needed)

---

## Implementation Plan

### Phase 1: Critical Fixes (Do First)

| Step | Action | Files | Verification |
|------|--------|-------|---------------|
| 1.1 | Add `granian>=2.7.0,<3.0` to requirements.txt | `requirements.txt` | `pip check` |
| 1.2 | Update Dockerfile to use Granian | `Dockerfile` | `docker build .` succeeds |
| 1.3 | Remove circular dependency in docker-compose.yml | `docker-compose.yml` | `docker-compose config` validates |
| 1.4 | Update DEPLOY.md to match actual health JSON structure | `DEPLOY.md` | Diff review |
| 1.5 | Update docker-compose healthcheck to detect degraded | `docker-compose.yml` | `docker-compose config` |

### Phase 2: Minor Fixes (Do Second)

| Step | Action | Files | Verification |
|------|--------|-------|---------------|
| 2.1 | Fix README logout method (GET → POST) | `README.md` | Diff review |
| 2.2 | Add missing routes to README | `README.md` | Diff review |
| 2.3 | Fix backup service entrypoint | `docker-compose.yml` | `docker-compose run backup` |
| 2.4 | Verify setup.sh and dev.sh completeness | `setup.sh`, `dev.sh` | Manual review |

### Phase 3: Testing & Validation

| Step | Action | Command |
|------|--------|---------|
| 3.1 | Run unit tests | `ADMIN_PASSWORD=test SECRET_KEY=test python -m pytest tests/ -v` |
| 3.2 | Build Docker image | `docker build -t blog-test .` |
| 3.3 | Test Granian startup | `docker run --rm -e SECRET_KEY=test -e ADMIN_PASSWORD=test blog-test` |
| 3.4 | Validate docker-compose config | `docker-compose config` |
| 3.5 | Verify health endpoint | `curl http://localhost:5000/health` |
| 3.6 | Test health endpoint degraded detection | Stop scheduler, verify status |

---

## Granian Performance Context

Based on research, Granian WSGI mode delivers:
- **19.5x faster** than Gunicorn Gthread (123,487 vs 6,345 RPS)
- **13.1x faster** than Gunicorn Gevent
- Pre-built wheels available for Python 3.14 (no Rust needed in Docker)

**Recommended Granian configuration for Flask:**
```bash
granian --interface asgi \
    --workers 2 \
    --host 0.0.0.0 \
    --port 5000 \
    --http auto \
    run:asgi_app
```

**Worker tuning:**
| Workers | CPU Cores | RAM |
|---------|-----------|-----|
| 1-2 | 1-2 | 512 MB+ |
| 3-4 | 2-4 | 1 GB+ |
| 5-8 | 4+ | 2 GB+ |

---

## References

| Topic | Location |
|-------|----------|
| Granian GitHub | https://github.com/emmett-framework/granian |
| Granian PyPI | https://pypi.org/project/granian/ |
| Flask ASGI Docs | https://flask.palletsprojects.com/en/stable/deploying/asgi/ |
| WsgiToAsgi Docs | https://docs.djangoproject.com/en/dev/howto/deployment/wsgi/granian/ |
| Benchmarks | https://github.com/emmett-framework/granian/tree/master/benchmarks |

---

## Summary of Changes

| Priority | Issue | Files to Modify | Est. Time |
|----------|-------|-----------------|-----------|
| **High** | Granian not in Docker | `requirements.txt`, `Dockerfile` | 15 min |
| **High** | Circular dependency | `docker-compose.yml` | 5 min |
| **High** | Health endpoint docs mismatch & healthcheck | `DEPLOY.md`, `docker-compose.yml` | 15 min |
| Medium | README logout route | `README.md` | 5 min |
| Medium | Missing routes doc | `README.md` | 15 min |
| Medium | Backup entrypoint | `docker-compose.yml` | 5 min |

**Total estimated time:** ~50 minutes

## Verification Notes

- `backup.py` exists at project root (not `scripts/backup.py`) - docker-compose backup service works correctly
- `setup.sh` and `dev.sh` are complete - no changes needed
- Granian 2.7.0+ has pre-built Python 3.14 wheels (no Rust toolchain required)
- WsgiToAsgi wrapper in `run.py` is correctly implemented for Granian ASGI mode
