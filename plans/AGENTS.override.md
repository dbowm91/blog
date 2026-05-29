# Plans Module Override

## Overview

This module contains the consolidated implementation plan in `plans/plan.md`.

## Plan Status

The implementation plan (`plans/plan.md`) is **FULLY COMPLETED**. All documentation fixes and the per-webhook retry feature have been implemented and verified.

The architecture review (`architecture/review_plan.md`) is **FULLY COMPLETED**. All 3 phases done. Findings in `plans/*_review.md` and `plans/architecture_prune.md`.

## Plan File

The main plan file `plans/plan.md` serves as the single source of truth for documentation fixes.

## Plan Maintenance

When implementing plan items:
1. Mark items as ✅ DONE when completed
2. Update status in plan header
3. Document any issues or clarifications discovered during implementation

## Key Source Files Reference

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
