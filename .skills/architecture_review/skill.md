---
name: architecture_review
description: "Architecture documentation review and improvement workflow. Reviews architecture documents against actual source code and generates improvement plans. Use when reviewing, verifying, or cross-referencing architecture documentation."
---

# Architecture Review Skill

## Description
Architecture documentation review and improvement workflow. Reviews architecture documents against actual source code and generates improvement plans.

## Triggers
architecture, review, documentation, verify, cross-reference

## Module Directories
- `architecture/core/` - app-factory.md, configuration.md, models.md
- `architecture/routes/` - public-routes.md, admin-routes.md, api-routes.md, rss-feeds.md
- `architecture/services/` - overview.md, backup.md, encryption.md, search.md, serialization.md, slug.md, tag.md, tag_cache.md
- `architecture/tasks/` - overview.md, scheduler.md, celery-tasks.md
- `architecture/infrastructure/` - overview.md, search.md, email.md, storage.md, webhooks.md
- `architecture/frontend/` - overview.md, static-assets.md, templates.md
- `architecture/deployment/` - overview.md, docker.md, cicd.md, security.md
- `architecture/testing/` - test-suite.md

## Status

**REVIEW COMPLETE, ALL FIXES COMPLETED** — All 9 module reviews completed (June 1-2, 2026). All architecture fixes implemented and verified.

### Previous Fixes (May 29-30, 2026)
- APScheduler FileLock documented in docker-compose.yml with warning comment
- Backup encryption now logs WARNING when encryption fails
- Webhook delivery per-webhook counters track success/failure with "partial_failure" status
- Thread-safe storage double-checked locking in storage.py
- LOGIN_FAILURE_DELAY minimum 0.1s enforced in config
- Vite build documented in overview.md and static-assets.md

### June 2026 Fixes
- Template inheritance corrected — admin/base.html and login_base.html are standalone
- marked.min.js uses vite_asset(), not url_for()
- SSRF protection correctly documented at app/utils.py
- Encryption function names corrected to encrypt()/decrypt()
- Nginx proxy_pass corrected to http://blog:5000
- Dead code _invalidate_all_caches() removed
- Celery missing SMTP_HOST in docker-compose.yml fixed

## Review Process

Use `explore` subagent type for module reviews. Each subagent:
1. Reads architecture docs in the module directory
2. Reads referenced source files
3. Cross-references every factual claim against code
4. Writes findings to `plans/{module}_review.md`

After all module reviews, run:
- Phase 2: Overview cross-reference (reviews overview.md against all module findings)
- Phase 3: Stale item pruning (creates `plans/architecture_prune.md`)

## Key Counts to Verify
- Models: exactly 17 (User, Post, Tag, Subscriber, Page, PageView, ShareEvent, AdminSession, SiteSettings, Webhook, WebhookEvent, Series, PostSeries, Comment, PostRevision, AdminAuditLog, ApiToken)
- Queues: 5 (images, newsletter, webhooks, email, backup)
- Scheduled jobs: 4 (send_daily_newsletter, cleanup_expired_subscribers, publish_scheduled_posts, run_daily_backup)
- Newsletter retry count: 5 (not 3)
- CI jobs: 6 (lint-and-type, test, security-audit, frontend-build, docker-build, e2e-tests)
- Template filters: 6 (markdown_safe, reading_time, sanitize_css, post_image_url, post_image_srcset, post_image_avif_url_stub [deprecated])

## Maintenance

Project architecture documentation is current. Run reviews after major code changes to ensure documentation stays accurate.
