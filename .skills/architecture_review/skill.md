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

All architecture review waves completed. Plan items implemented and verified.

### Plan Completion (May 2026)
- Wave A-F: All 36 items implemented and verified
- Deferred: B2 (per-webhook retry) - acknowledged in architecture docs
- Plan pruned to summary status in `plans/plan.md`

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