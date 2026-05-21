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

## Wave J Completion (May 2026)
Documentation fixes applied to all 8 modules via architecture review.

## Wave K Status (May 2026)
Wave K architecture reviews IN PROGRESS for all 8 modules:
- Core, Services (K1)
- Routes, Tasks (K2)
- Frontend, Testing, Infrastructure, Deployment (K3)

Each module review follows: Read docs → Cross-reference code → Document verification → Identify issues → Write improvements.

## Architecture Review Skill
See `.skills/architecture_review/skill.md` for detailed architecture review workflow.
