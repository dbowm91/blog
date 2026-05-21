# Architecture Module Agent Override

## Purpose
Architecture documentation for the blog CMS application.

## Key Files
- `architecture/review_plan.md` - Architecture review plan and status
- `architecture/overview.md` - High-level architecture overview
- `architecture/core/` - App factory, configuration, models
- `architecture/routes/` - API, admin, public routes, RSS feeds
- `architecture/services/` - Backup, serialization, tag, slug services
- `architecture/tasks/` - Celery tasks, APScheduler, task overview
- `architecture/infrastructure/` - Webhooks, search, email, storage, health
- `architecture/frontend/` - Static assets, templates
- `architecture/deployment/` - Docker, CI/CD, security
- `architecture/testing/` - Test suite documentation

## Review Status (May 2026)
All 8 modules reviewed:
- ✅ Core - Verified with minor fixes
- ✅ Services - Critical backup retention bug fixed
- ✅ Routes - Verified
- ✅ Tasks - Verified
- ✅ Infrastructure - Redis/celery health checks added
- ✅ Frontend - Verified
- ✅ Deployment - Verified
- ✅ Testing - Verified

## Architecture Review Skill
See `.skills/architecture_review/skill.md` for detailed architecture review workflow.
