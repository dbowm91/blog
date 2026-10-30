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
- `architecture/core/` - app-factory.md, configuration.md, models.md, filesystem.md, onboarding.md, themes.md
- `architecture/routes/` - public-routes.md, admin-routes.md, api-routes.md, rss-feeds.md
- `architecture/services/` - overview.md, operations.md, doctor.md, backup.md, encryption.md, search.md, serialization.md, slug.md, tag.md, tag_cache.md
- `architecture/tasks/` - overview.md, scheduler.md, celery-tasks.md
- `architecture/infrastructure/` - overview.md, search.md, email.md, storage.md, webhooks.md
- `architecture/frontend/` - overview.md, static-assets.md, templates.md, appearance.md
- `architecture/deployment/` - overview.md, cli.md, managed-deployment.md, installation.md, docker.md, cicd.md, security.md
- `architecture/testing/` - test-suite.md

`architecture/overview.md` is the index: it names every discrete module and links
to its deep-dive document. Adding a module means adding the deep-dive file and
then adding the row to the overview's module map.

## Status

**October 2026 review — complete.** Every module was reviewed against the
source and six new deep dives were written for the modules that had none:
`core/filesystem.md`, `core/onboarding.md`, `core/themes.md`,
`services/operations.md`, `deployment/cli.md` and `deployment/managed-deployment.md`.
`architecture/overview.md` was rewritten as the module map and index.

The review surfaced real defects, recorded in a `## Notes and Gotchas` section
in each document — including a colour-conversion bug in `shift_lightness()`, a
missing `app.config["DEVLOG_CONFIG"]` key that breaks the `devlog deploy`
group outside the test suite, and a `deploy render` default target that renders
nothing.

**June 2026 review — complete.** All 9 module reviews completed (June 1-2,
2026). All architecture fixes implemented and verified.

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

**October 2026 variant.** For a module with no deep dive, the subagent reads
the source and writes the deep-dive document directly, including a
`## Notes and Gotchas` section for defects and surprises. Defects are
**documented, not fixed** — fixing them is a separate, deliberate change. Each
subagent owns exactly one output file so they can run in parallel.

## Key Counts to Verify
- Models: exactly 18 (User, Post, Tag, Subscriber, Page, Project, PageView, ShareEvent, AdminSession, SiteSettings, Webhook, WebhookEvent, Series, PostSeries, Comment, PostRevision, AdminAuditLog, ApiToken)
- Queues: 5 (images, newsletter, webhooks, email, backup)
- Scheduled jobs: 4 (send_daily_newsletter, cleanup_expired_subscribers, publish_scheduled_posts, run_daily_backup)
- Newsletter retry count: 5 (not 3)
- CI jobs: 11 (lint-and-type, test, theme-policy, migration-chain, theme-package-verification, frontend-build, security-audit, docker-build, e2e-tests, dependency-consistency, release1-package-smoke)
- Template filters: 6 (markdown_safe, reading_time, sanitize_css, post_image_url, post_image_srcset, post_image_avif_url_stub [deprecated])
- Doctor checks: 76 across 20 categories
- BlogTheme fields: 52 (43 RGB + 9 RGBA); CSS_VARS: 52 entries; ALIASES: 40 entries
- Bundled themes: 50 in `app/themes/bundled/`
- Appearance layer: 10 font families (4 sans, 6 mono), 3 backdrops
- Onboarding steps: 17
- Configuration dataclasses: 24 (`DevLogConfig` + 23 section classes)

## Maintenance

Project architecture documentation is current. Run reviews after major code changes to ensure documentation stays accurate.
