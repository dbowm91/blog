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

## Wave K Completion (May 2026)
Architecture reviews completed for all 8 modules:
- Core, Services (K1)
- Routes, Tasks (K2)
- Frontend, Testing, Infrastructure, Deployment (K3)

Each module review documented verified claims, discrepancies, bugs, and improvements in `plans/<module>_review.md`.

## Wave L Completion (May 2026)
Implementation of architecture review findings:
- Critical bug fixes (webhooks logger, mobile-menu syntax, search.html srcset)
- High priority fixes (celery concurrency, pip-audit silencing, scheduler SMTP handling)
- Documentation corrections (TAG_CACHE_TTL, backup naming, slug signature, preview security, etc.)

See `architecture/review_plan.md` for full summary of issues found and fixed.

## Wave M Completion (May 2026)
Continued architecture review findings implementation:
- **email.py** - Added SMTPException and SMTPServerDisconnected to exception handling
- **storage.py** - Removed _clear_credentials() that broke S3 client recreation
- **webhooks.md** - Fixed Webhook model with secret encryption and delivery_status field
- **docker.md/cicd.md** - Fixed health check docs, e2e-tests docs
- **services/search.md** - Created new SearchProvider documentation

## Architecture Review Skill
See `.skills/architecture_review/skill.md` for detailed architecture review workflow.
