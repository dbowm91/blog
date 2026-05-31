# Architecture Review Skill

## Description
Architecture documentation review and improvement workflow. Reviews architecture documents against actual source code and generates improvement plans.

## Triggers
architecture, review, documentation, verify, cross-reference

## Module Directories
- `architecture/core/` - app-factory.md, configuration.md, models.md
- `architecture/routes/` - public-routes.md, admin-routes.md, api-routes.md, rss-feeds.md
- `architecture/services/` - overview.md, backup.md, serialization.md, slug.md, tag.md, tag_cache.md
- `architecture/tasks/` - overview.md, scheduler.md, celery-tasks.md
- `architecture/infrastructure/` - overview.md, search.md, email.md, storage.md, webhooks.md
- `architecture/frontend/` - overview.md, static-assets.md, templates.md
- `architecture/deployment/` - overview.md, docker.md, cicd.md, security.md
- `architecture/testing/` - test-suite.md

## Status

**COMPLETED** - All architecture review items implemented (May 30, 2026).

### Key Findings Fixed (May 29-30, 2026)
- **APScheduler FileLock** documented in docker-compose.yml with warning comment
- **Backup encryption** now logs WARNING when encryption fails
- **E2E test password** - both conftest files use "test-password"
- **Webhook delivery** - per-webhook counters track success/failure with "partial_failure" status
- **Python version** - dev.sh aligns with Dockerfile (3.12)
- **Thread-safe storage** - double-checked locking in storage.py
- **LOGIN_FAILURE_DELAY** - minimum 0.1s enforced in config
- **Vite build** - documented in overview.md and static-assets.md
- **Stale line references** - corrected in webhooks.md and scheduler.md

## Architecture Review Notes

When reviewing documentation:
- Line numbers become stale quickly - prefer functional descriptions over specific line references
- Queue routing table in scheduler.md: images:30, newsletter:129, webhooks:194, email:345, backup:387
- Rate limit values should be verified against actual code
- Error handling table documents actual retry behavior for Celery tasks
- E2E tests use pytest-playwright, not @playwright/test

## Maintenance

All items from architecture review (90+ across 6 waves) have been implemented and verified.
Project in maintenance mode - no active review planned.