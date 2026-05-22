# Architecture Review Skill

## Description
Architecture documentation review and improvement workflow. Reviews architecture documents against actual source code and generates improvement plans.

## Triggers
architecture, review, documentation, verify, cross-reference

## Module Directories
- `architecture/core/` - app-factory.md, configuration.md, models.md
- `architecture/routes/` - public-routes.md, admin-routes.md, api-routes.md, rss-feeds.md
- `architecture/services/` - overview.md, backup.md, serialization.md, slug.md, tag.md
- `architecture/tasks/` - overview.md, scheduler.md, celery-tasks.md
- `architecture/infrastructure/` - overview.md, search.md, email.md, storage.md, webhooks.md
- `architecture/frontend/` - overview.md, static-assets.md, templates.md
- `architecture/deployment/` - overview.md, docker.md, cicd.md, security.md
- `architecture/testing/` - test-suite.md

## Status

Wave O completed (May 2026). Additional fixes documented in `plans/<module>_review.md` implemented across all modules.

### Wave O Fixes Applied
- **deployment**: Env vars (ADMIN_USERNAME, FLASK_ENV), Celery concurrency, BACKUP_ENCRYPTION_KEY clarification, PYTHONPATH
- **frontend**: critical.css added, editor.html/page_editor.html clarified
- **infrastructure**: Queue routing line numbers fixed, email check via scheduler, S3 variant cleanup
- **routes**: Rate limit (10/min), pages field, duplicate section removed, sitemap cache, authors field
- **services**: Stale line numbers removed, run_daily_backup() line number added
- **tasks**: Line numbers fixed, error handling table added
- **testing**: pytest-playwright instructions, api_client fixture added

### Plan Completion (May 2026)
- Wave A-F: All 36 items implemented and verified
- Wave J-N: All review findings implemented
- Wave O: Documentation fixes from module reviews implemented

### Critical Bugs Fixed
1. `app/webhooks.py:111` - Missing logger (NameError at runtime)
2. `app/static/js/shared/mobile-menu.jsx:42` - Extra `});` caused parse failure
3. `app/templates/search.html:31` - Missing srcset variable
4. `app/scheduler.py:269-271` - SMTP disable logic disabled all jobs, not just newsletter

### Verified Behavior
- All routes match documented paths
- All function signatures match documentation
- All configuration values verified
- All Celery queue names and line numbers correct
- All APScheduler schedules correct

### Architecture Review Notes
When reviewing documentation:
- Line numbers become stale quickly - prefer functional descriptions over specific line references
- Queue routing table line numbers updated to actual: images:28, newsletter:127, webhooks:184, email:263,284, backup:305
- Rate limit values should be verified against actual code (e.g., public comments is 10/min, not 20/min)
- Error handling table documents actual retry behavior for Celery tasks
- E2E tests use pytest-playwright, not @playwright/test