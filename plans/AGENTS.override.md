# Plans Module Override

## Overview

This module contains the consolidated implementation plan in `plans/plan.md`.

## Plan File

The main plan file `plans/plan.md` serves as the single source of truth for documentation fixes and deferred items.

## Plan Maintenance

When implementing plan items:
1. Mark items as ✅ DONE when completed
2. Update status in plan header
3. Document any issues or clarifications discovered during implementation
4. When a plan is fully completed, prune it to keep only deferred items and essential context

## Deferred Items

See `plans/plan.md` for current deferred items.

## Executing This Plan

### Parallel Execution
All Wave 1 subagents can run concurrently since they target different files. Launch subagents for each wave section (1A through 1H) in parallel.

### Subagent Instructions
Each subagent should:
1. Read the target architecture file(s) first
2. Read the actual source code referenced in the plan
3. Verify claims against the code before making edits
4. Make minimal, focused changes — fix only what's documented as inaccurate
5. Preserve existing accurate content in each file

### Key Source Files Reference
| Module | Source Files |
|--------|-------------|
| Core | `app/__init__.py`, `app/config.py`, `app/models.py` |
| Routes | `app/routes/admin/`, `app/routes/public/`, `app/routes/api/` |
| Services | `app/services/backup.py`, `app/services/serialization.py`, `app/services/slug.py`, `app/tag_cache.py`, `app/backup_encryption.py` |
| Tasks | `app/tasks.py`, `app/scheduler.py` |
| Deployment | `Dockerfile`, `docker-compose.yml`, `nginx/nginx.conf`, `nginx/conf.d/blog.conf` |
| Infrastructure | `app/services/search/`, `app/search.py`, `app/utils.py`, `app/webhook_encryption.py`, `app/storage.py` |
| Testing | `tests/conftest.py`, `tests/shared_fixtures.py`, `tests/e2e/test_e2e.py` |
| Frontend | `app/filters.py`, `app/context_processors.py`, `app/vite.py`, `app/static/js/`, `app/templates/` |
