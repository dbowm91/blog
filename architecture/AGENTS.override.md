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

## Wave N Completion (May 2026)
All Wave N implementation items completed and verified:
- Fixed email task retry logic with `max_retries=3` and `self.retry()` in `app/tasks.py`
- Fixed mobile-menu.jsx import in `app/static/js/main.js`
- All documentation fixes completed (see `plans/plan.md` for details)
- Plan file pruned - only important context for future agents remains

## Wave O Completion (May 2026)
Implementation of review findings from `plans/<module>_review.md`:

| Module | Fixes Applied |
|--------|---------------|
| **deployment** | docker.md: ADMIN_USERNAME/FLASK_ENV env vars, Celery concurrency=1, BACKUP_ENCRYPTION_KEY clarification, PYTHONPATH for backup |
| **frontend** | static-assets.md: Added critical.css; templates.md: Clarified editor.html/page_editor.html |
| **infrastructure** | webhooks.md: Fixed queue routing line numbers; overview.md: Email check via scheduler status; storage.md: S3 variant cleanup |
| **routes** | api-routes.md: Rate limit fix (10/min), 'pages' field; public-routes.md: Duplicate section removed, sitemap cache; rss-feeds.md: authors field |
| **services** | tag_cache.md: Removed stale line numbers; backup.md: run_daily_backup() line number |
| **tasks** | celery-tasks.md: Line numbers fixed, error handling table added |
| **testing** | test-suite.md: pytest-playwright instructions, api_client fixture |

See `architecture/review_plan.md` for full details.

## Architecture Review Skill
See `.skills/architecture_review/skill.md` for detailed architecture review workflow.
