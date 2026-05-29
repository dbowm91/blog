# Plans Module Override

## Overview

This module contains the consolidated implementation plan in `plans/plan.md`.

## Plan Status

The implementation plan (`plans/plan.md`) is **IN PROGRESS** with new items from architecture reviews conducted May 29, 2026. The previous 96-item plan was marked complete May 29, 2026.

## Plan Structure

The NEW plan is organized into 6 waves:
- **Wave 1**: Critical code bugs (6 items: APScheduler race, webhook status, E2E fixtures, backup encryption, Python version, thread-safe singleton)
- **Wave 2**: Documentation corrections (3 items: test-suite.md false claims, module boundaries, stale line refs)
- **Wave 3**: Missing documentation (13 items: APScheduler detection, Vite build, backup key, RSS feeds, API errors, rate limits, etc.)
- **Wave 4**: Frontend code fixes (3 items: login template assets, Prism CSS CDN, CSS hash caching)
- **Wave 5**: Source code cleanup (5 items: dead imports, export decrypt_backup_file, /metrics auth, session remove, S3 errors)
- **Wave 6**: Security hardening (2 items: LOGIN_FAILURE_DELAY, comment rate limit IP header)

## Plan File

The main plan file `plans/plan.md` serves as the single source of truth for all implementation items.

## Implementation Notes

**Parallelization:** All Wave 1 items are independent and can run in parallel. Same for Wave 2 and Wave 3 items.

**Verification commands:**
```bash
ruff check . && ruff format --check .  # lint
mypy app/  # type check
ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/  # tests
npm run build  # frontend build
docker compose config  # docker validation
```

## Key Source Files Reference

| Module | Source Files |
|--------|-------------|
| Core | `app/__init__.py`, `app/config.py`, `app/models.py`, `app/storage.py`, `app/tag_cache.py` |
| Routes | `app/routes/admin/`, `app/routes/public/`, `app/routes/api/` |
| Services | `app/services/backup.py`, `app/services/serialization.py`, `app/services/slug.py`, `app/backup_encryption.py` |
| Tasks | `app/tasks.py`, `app/scheduler.py` |
| Deployment | `Dockerfile`, `docker-compose.yml`, `nginx/nginx.conf`, `nginx/conf.d/blog.conf`, `scripts/dev.sh` |
| Infrastructure | `app/services/search/`, `app/search.py`, `app/utils.py`, `app/webhook_encryption.py` |
| Testing | `tests/conftest.py`, `tests/shared_fixtures.py`, `tests/e2e/conftest.py`, `tests/e2e/test_e2e.py` |
| Frontend | `app/filters.py`, `app/context_processors.py`, `app/vite.py`, `app/static/js/main.js`, `app/templates/` |