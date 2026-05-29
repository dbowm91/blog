# Implementation Plan - Blog CMS Documentation & Code Fixes

**Project:** Blog CMS (DevLog)
**Status:** PENDING
**Last Updated:** May 29, 2026

---

## Overview

Consolidated plan from architecture reviews of all 8 modules. Reviews conducted May 29, 2026. Previous documentation waves (A-F, 43 items) and Wave 1 implementation completed May 28, 2026.

This plan addresses remaining documentation discrepancies, code bugs discovered during review, and project polish items for public release readiness.

**Total items:** 96 (50 Wave 1, 4 Wave 2, 17 Wave 3, 19 Wave 4, 6 Wave 5)

---

## Execution Strategy

This plan is optimized for parallel sub-agent execution. Waves 1A-1E can ALL run simultaneously. Wave 2 and Wave 3 can run in parallel after Wave 1. Wave 4 runs after Wave 2. Wave 5 runs last.

### Sub-Agent Assignment Guide

When dispatching work to sub-agents, use this structure:

| Sub-Agent | Wave | Items | Context |
|-----------|------|-------|---------|
| SA-1 | 1A | A-1 through A-11 | Architecture overview edits only |
| SA-2 | 1B | C-1 through C-10, F-1 through F-5 | Core + frontend doc edits |
| SA-3 | 1C | R-1 through R-3, I-1 through I-7 | Routes + infrastructure doc edits |
| SA-4 | 1D | S-1 through S-6, T-1 through T-5 | Services + tasks doc edits |
| SA-5 | 1E | D-1 through D-10, TS-1 through TS-5 | Deployment + testing doc edits |
| SA-6 | 2A | CF-1, CF-2 | Template code fix + frontend docs |
| SA-7 | 2B | DC-1, DC-2 | Dead code cleanup |
| SA-8 | 2C | TC-1, TC-2 | Test cleanup |

Each sub-agent should:
1. Read the root `AGENTS.md` and any relevant `AGENTS.override.md` files before starting
2. Verify every claim against the actual source file before making changes
3. Use `rg` (ripgrep) to locate exact positions before editing
4. Make focused, minimal edits — do not rewrite entire files

---

## Wave 1: Critical Documentation Fixes (Parallelizable)

All items in Wave 1 are independent and can be executed in parallel by separate sub-agents. Each sub-agent handles one sub-wave.

**Verification required before each edit:** Read the target file and confirm the line/content matches what is described. Line numbers drift as code evolves.

### Wave 1A: Architecture Overview Fixes

**Sub-agent: SA-1**
**Target files:** `architecture/overview.md`
**Context:** This file is 527 lines. The edits are scattered across multiple sections.

| ID | Priority | Description | File:Line | Verification |
|----|----------|-------------|-----------|--------------|
| A-1 | high | Fix model count: "20 models" and "19 models" → "17 models" | `architecture/overview.md:99,312` | Count model classes in `app/models.py` — there are exactly 17: User, Post, Tag, Subscriber, Page, PageView, ShareEvent, AdminSession, SiteSettings, Webhook, WebhookEvent, Series, PostSeries, Comment, PostRevision, AdminAuditLog, ApiToken |
| A-2 | high | Remove stale `app/services/tag_cache.py` from directory structure | `architecture/overview.md:389` | File does NOT exist at `app/services/tag_cache.py`. It IS at `app/tag_cache.py` (line 326 already has the correct entry). Remove the duplicate stale line at 389. |
| A-3 | high | Replace `post.created` with `post.unpublished` in event types table | `architecture/infrastructure/webhooks.md:119` | The event `post.created` does NOT exist in the codebase. Actual events are `post.published`, `post.unpublished`, `subscriber.confirmed`. Verify by searching `app/webhooks.py` and `app/routes/` for event type strings. |
| A-4 | high | Add `deliver_single_webhook_task` documentation and update dispatch pattern | `architecture/tasks/celery-tasks.md` | The task is at `app/tasks.py:233-308`. It handles per-webhook SSRF protection, HMAC signing, retry logic, delivery status. `deliver_webhook_task` (line 194) dispatches TO this task. Update doc to reflect two-level architecture. |
| A-5 | med | Add missing API endpoints (pages, series, tags) to api-routes.md | `architecture/routes/api-routes.md` | Three API packages exist but are undocumented: `app/routes/api/pages.py`, `app/routes/api/series.py`, `app/routes/api/tags.py`. Each provides full CRUD. Read each file to document exact routes and scopes. |
| A-6 | med | Add `encryption.py` to services overview table | `architecture/services/overview.md` | `app/services/encryption.py` exists and handles TOTP secret encryption via AES-256-GCM. Add to the services table. |
| A-7 | med | Add `ApiToken` to models overview table | `architecture/core/models.md` | `app/models.py:623-655` defines ApiToken with fields: id, name, token_hash, scopes, created_at, last_used_at, expires_at, revoked_at. Methods: is_valid(), has_scope(). |
| A-8 | med | Add `app/cli.py` to directory structure and Core section component table | `architecture/overview.md:86-91,306-333` | `app/cli.py` exists. It registers CLI commands via `register_cli_commands()` at `app/__init__.py:464-466`. Add to both the directory tree and the Core component table. |
| A-9 | med | Add `app/validators.py` to Core section component table | `architecture/overview.md:86-91` | `app/validators.py` exists (189 lines). Contains validate_string, validate_post_input, validate_subscriber_input, etc. Listed in directory structure but missing from Core component table. |
| A-10 | low | Fix broken `routes/overview.md` link in See Also | `architecture/core/app-factory.md:141` | `architecture/routes/overview.md` does NOT exist. The routes directory has individual files (admin-routes.md, api-routes.md, etc.) but no overview.md. Replace with a valid link or remove. |
| A-11 | low | Clarify `.gpg` extension is AES-256-GCM, not GPG | `architecture/services/backup.md:97` | The backup system uses AES-256-GCM via `app/backup_encryption.py`, not GPG. The `.gpg` extension is misleading. Add a note clarifying the actual encryption mechanism. |

### Wave 1B: Core & Frontend Documentation Fixes

**Sub-agent: SA-2**
**Target files:** `architecture/core/models.md`, `architecture/core/app-factory.md`, `architecture/core/configuration.md`, `architecture/frontend/templates.md`, `architecture/frontend/static-assets.md`

| ID | Priority | Description | File | Verification |
|----|----------|-------------|------|--------------|
| C-1 | high | Add `ApiToken` model to models.md details section | `architecture/core/models.md` | Full model at `app/models.py:623-655`. Fields: id (Integer, PK), name (String(100)), token_hash (String(64), unique), scopes (Text, JSON-encoded list), created_at, last_used_at, expires_at, revoked_at. Methods: is_valid(), has_scope(scope). |
| C-2 | high | Add `is_spam`, `spam_score`, `created_at` fields to Comment model docs | `architecture/core/models.md` | Comment model at `app/models.py:594`. is_spam: Boolean, default=False, nullable=False (line 604). spam_score: Float, nullable=True (line 605). created_at: UTCDateTime, default=utc_now (line 606). |
| C-3 | high | Add `ix_comments_is_spam` index to Comment index table | `architecture/core/models.md` | Index at `app/models.py:616`: `db.Index("ix_comments_is_spam", "is_spam")`. Part of Comment.__table_args__ (lines 612-617). |
| C-4 | high | Add `canonical_url` to context processors list | `architecture/core/app-factory.md` | `app/context_processors.py:151` provides `canonical_url`. Listed context processors: inject_csrf, inject_config, inject_theme, inject_footer_data, inject_show_footer_posts. canonical_url is missing from the docs. |
| C-5 | med | Document `created_at`/`updated_at` on Post, Page, Comment, PostRevision, SiteSettings | `architecture/core/models.md` | Post: created_at (190), updated_at (191). Page: created_at (160), updated_at (165). Comment: created_at (606). PostRevision: created_at (250). SiteSettings: updated_at (351). Verify each in `app/models.py`. |
| C-6 | med | Fix rss blueprint prefix description | `architecture/core/app-factory.md` | The rss blueprint is defined WITHOUT url_prefix at `app/routes/rss.py:18`. Routes are registered at top-level: /rss, /atom, /json. The doc implies they're under a prefix. Fix to say routes are at root level. |
| C-7 | med | Add `ADMIN_RATE_LIMITS` to configuration.md | `architecture/core/configuration.md` | `app/config.py:164-171` defines admin rate limit tuples. Not documented. Read the config to get exact values and add to the security settings table. |
| C-8 | med | Add comment settings to configuration.md | `architecture/core/configuration.md` | `app/config.py:137-142`: COMMENT_MIN_LENGTH, COMMENT_MAX_LENGTH, COMMENT_RATE_LIMIT_PER_IP, COMMENT_RATE_LIMIT_PER_POST, COMMENT_NOTIFY_PENDING, COMMENT_SPAM_WORDS. Add these to config documentation. |
| C-9 | med | Add `ANALYTICS_DAYS_MIN/MAX`, `PAGE_VIEW_BUFFER_SIZE` to configuration.md | `architecture/core/configuration.md` | `app/config.py:129-133`. ANALYTICS_DAYS_MIN (default?), ANALYTICS_DAYS_MAX (default?), PAGE_VIEW_BUFFER_SIZE (default?). Read the file for exact defaults. |
| C-10 | med | Document `ix_admin_sessions_user_id` index in AdminSession section | `architecture/core/models.md` | Index at `app/models.py:336`: `db.Index("ix_admin_sessions_user_id", "user_id")`. Part of AdminSession.__table_args__. |
| F-1 | high | Fix template inheritance diagram to show four base templates | `architecture/frontend/templates.md` | Four base templates: `base.html` (public), `admin/base.html` (admin), `admin/login_base.html` (auth pages), `email/base_email.html` (emails). Read each to understand inheritance. |
| F-2 | high | Fix line number references for critical CSS, font preload, syntax theme, vite functions | `architecture/frontend/static-assets.md` | Critical CSS: `base.html:25` (not 22). Font preload: `base.html:40-41` (not 37-38). Syntax theme: `base.html:31` (not 28). `vite_asset()`: `app/vite.py:48` (not 47). `init_vite()`: `app/vite.py:81-83` (not 80-82). Verify by reading each file. |
| F-3 | med | Rewrite lazy loading tier 1 description | `architecture/frontend/static-assets.md` | Tier 1: JS returns early (does nothing) — the browser handles `loading="lazy"` natively. The HTML templates already include `loading="lazy"` on `<img>` tags. Don't say JS "uses" the attribute; say it defers to native browser handling. |
| F-4 | med | Fix dark mode default description | `architecture/frontend/static-assets.md` | Default follows OS preference via `prefers-color-scheme: dark` in `dark-mode.js:13-14`. If OS is light, `data-theme="light"` is set immediately. "No attribute = dark" is only true after user has toggled to dark. |
| F-5 | med | Add `post_image_srcset` filter implementation details | `architecture/frontend/templates.md` | Filter at `app/filters.py:57-76`. Generates srcset for 400, 800, 1200 widths. Handles CDN_URL. Uses `_post_srcset_cache_` cache key pattern. |

### Wave 1C: Routes & Infrastructure Documentation Fixes

**Sub-agent: SA-3**
**Target files:** `architecture/routes/admin-routes.md`, `architecture/infrastructure/overview.md`, `architecture/infrastructure/webhooks.md`

| ID | Priority | Description | File:Line | Verification |
|----|----------|-------------|-----------|--------------|
| R-1 | high | Fix post list route path | `architecture/routes/admin-routes.md:96` | Doc says `GET /admin/<int:page>`. Actual route is `GET /admin/` with `page` as a query parameter (`app/routes/admin/posts/__init__.py:51`). The `<int:page>` path parameter does not exist. |
| R-2 | high | Fix backup route URLs: add `<filename>` path parameters | `architecture/routes/admin-routes.md:160-163` | Doc shows trailing slashes: `/admin/backup/restore/`, etc. Actual routes have `<filename>` params: `/backup/restore/<filename>`, `/backup/download/<filename>`, `/backup/delete/<filename>`, `/backup/verify/<filename>`. Verify in `app/routes/admin/backup.py`. |
| R-3 | high | Fix post delete/preview file reference | `architecture/routes/admin-routes.md:85,89` | Doc says `manage.py`. Actual file is `posts/manage.py`. Functions registered via `register_manage_routes()` in `app/routes/admin/posts/__init__.py:47`. |
| I-1 | high | Fix `is_safe_url` → `is_safe_webhook_url` name and code block | `architecture/infrastructure/overview.md:89` | Actual function is `is_safe_webhook_url(url: str) -> tuple[bool, str]` at `app/utils.py:383`. NOT `is_safe_url`. The return type is a tuple (bool, str), not just bool. The doc's simplified code block using `socket.gethostbyname` is misleading — actual uses `socket.getaddrinfo` with AF_UNSPEC. |
| I-2 | high | Fix `?detailed=1` → `?detailed=true` and document `?secret=` requirement | `architecture/infrastructure/overview.md:17` | Actual code at `app/routes/public/meta.py:194`: `request.args.get("detailed", "").lower() == "true"`. Also requires `?secret=<HEALTH_CHECK_SECRET>` for HMAC comparison (line 197). |
| I-3 | high | Fix `disk_space` check description | `architecture/infrastructure/overview.md:26` | Doc says "Available space > 100MB". Actual at `app/routes/public/meta.py:234-235`: checks `free_percent >= 10` (10% free), not an absolute 100MB. |
| I-4 | med | Document `app/webhook_encryption.py` in webhooks.md | `architecture/infrastructure/webhooks.md` | Module at `app/webhook_encryption.py` provides AES-256-GCM encryption for webhook secrets. Uses `WEBHOOK_ENCRYPTION_KEY` env var (32 bytes or 64 hex chars). Read the file to document the functions. |
| I-5 | med | Document `is_safe_webhook_url()` full validation logic | `architecture/infrastructure/webhooks.md` | Function at `app/utils.py:383-485`. Checks: scheme, userinfo, loopback, private, link-local, reserved, multicast, IPv4-mapped IPv6, cloud metadata (169.254.169.254, metadata.google.internal), and `is_global`. Returns tuple[bool, str]. |
| I-6 | med | Update queue line numbers in webhooks.md | `architecture/infrastructure/webhooks.md` | Current line numbers: images=30, newsletter=135, webhooks=194,233, email=333,354, backup=375. Verify by reading `app/tasks.py` — line numbers drift as code evolves. |
| I-7 | med | Document two-level webhook delivery architecture | `architecture/infrastructure/webhooks.md` | `deliver_webhook_task` (line 194) dispatches TO `deliver_single_webhook_task` (line 233). The subtask handles per-webhook SSRF, HMAC, retry, status. The parent just iterates and dispatches. |

### Wave 1D: Services & Tasks Documentation Fixes

**Sub-agent: SA-4**
**Target files:** `architecture/services/search.md`, `architecture/services/tag_cache.md`, `architecture/services/overview.md`, `architecture/tasks/celery-tasks.md`, `architecture/tasks/scheduler.md`

| ID | Priority | Description | File | Verification |
|----|----------|-------------|------|--------------|
| S-1 | high | Update `search.md` line number references | `architecture/services/search.md` | 11 functions have line drift (-1 to -7). Current actual lines: reset_fts_available=36, rebuild_fts=101, sync_fts=111, sync_fts_batch=133, remove_fts=174, search=196, get_indexed_terms=219, extract_snippet=246, get_search_snippets=275, get_did_you_mean=320, highlight_query=349. Verify each by reading `app/search.py`. |
| S-2 | high | Update `tag_cache.md` invalidation call line numbers | `architecture/services/tag_cache.md` | 15 references with drift. Actual lines (verify by reading each file): `admin/__init__.py`=68 (call), 103 (import, NOT call); `editor.py`=89, 204; `revisions.py`=97; `manage.py`=82; `tags.py`=76, 104, 142; `posts/__init__.py`=158, 179, 198, 216; `scheduler.py`=224, 256. |
| S-3 | high | Remove `_SQLITE_MAX_VARS` from config keys; add `FTS_RESULT_LIMIT` | `architecture/services/search.md` | `_SQLITE_MAX_VARS` at `app/search.py:291` is a hardcoded LOCAL variable, not a config key. `FTS_RESULT_LIMIT` at `app/config.py:128` (default: 100) is the actual configurable parameter. |
| S-4 | med | Correct `tag_cache.md:30` — line 100 is import, not call | `architecture/services/tag_cache.md` | `app/routes/admin/__init__.py:103` is an import statement (`from app.tag_cache import invalidate_tag_cache`), not a call. The actual call is at line 68 inside `_invalidate_all_caches()`. |
| S-5 | med | Add encryption modules to overview.md services table | `architecture/services/overview.md` | Three encryption modules missing: `app/services/encryption.py` (TOTP), `app/backup_encryption.py` (backup AES-256-GCM), `app/webhook_encryption.py` (webhook AES-256-GCM). |
| S-6 | med | Add `app/search.py` standalone functions to overview.md | `architecture/services/overview.md` | `app/search.py` provides standalone FTS5 functions (search, sync_fts, rebuild_fts, etc.) separate from the SearchProvider abstraction. Add as a separate entry in the services overview. |
| T-1 | high | Document `deliver_single_webhook_task` and update dispatch pattern | `architecture/tasks/celery-tasks.md` | Task at `app/tasks.py:233-308`. Handles per-webhook: SSRF check via `is_safe_webhook_url()`, HMAC signing, requests.post with timeout, `_update_delivery_status()`. |
| T-2 | high | Fix error handling table and Note paragraph for webhook retry behavior | `architecture/tasks/celery-tasks.md` | Current doc says webhook task NEVER retries. This is WRONG for `deliver_single_webhook_task` which has its own retry logic via `self.retry()` at lines 294, 298. |
| T-3 | med | Add conditional note for `send_daily_newsletter` in jobs table | `architecture/tasks/scheduler.md` | `app/scheduler.py:290` only adds the newsletter job when `SMTP_HOST` is configured. Add a "Conditional" column or note to the jobs table. |
| T-4 | low | Fix `init_scheduler` return type to `Optional["BackgroundScheduler"]` | `architecture/tasks/scheduler.md` | `app/scheduler.py:281` returns `Optional["BackgroundScheduler"]`. Doc says `None`. |
| T-5 | low | Fix `images` queue line number (30, not 28) | `architecture/tasks/scheduler.md` | `app/tasks.py:30` defines the images queue. Doc says line 28. |

### Wave 1E: Deployment & Testing Documentation Fixes

**Sub-agent: SA-5**
**Target files:** `architecture/deployment/cicd.md`, `architecture/deployment/docker.md`, `architecture/testing/test-suite.md`, `tests/AGENTS.override.md`, `tests/conftest.py`

| ID | Priority | Description | File | Verification |
|----|----------|-------------|------|--------------|
| D-1 | high | Create missing `scripts/validate_openapi.py` or remove the CI job | `.github/workflows/ci.yml:64` | `scripts/validate_openapi.py` does NOT exist. CI job `openapi-validation` will fail. Either create the script or comment out/remove the job. This requires a decision — default to removing the job if the script is complex. |
| D-2 | high | Fix CI workflow filename | `architecture/deployment/cicd.md:1` | Doc says `test.yml`. Actual file is `.github/workflows/ci.yml`. |
| D-3 | high | Add `openapi-validation`, `frontend-build`, `docker-build` jobs and `schedule` trigger to CI docs | `architecture/deployment/cicd.md:11-31` | `.github/workflows/ci.yml` has 7 jobs: lint, typecheck, test, openapi-validation, frontend-build, docker-build, e2e. Also has `schedule` trigger (weekly cron Monday 08:00). Read the CI file to document all jobs. |
| D-4 | high | Fix docker-compose profiles | `architecture/deployment/docker.md:18` | ALL services require explicit profiles. `docker compose up` with no profile starts ZERO services. `--profile production`: blog, celery, redis, nginx. `--profile backup`: backup. |
| D-5 | med | Add `backup` service to Docker Services table | `architecture/deployment/docker.md:7-12` | Backup service at `docker-compose.yml:105-120`. Uses `python:3.12-slim`, runs `python3 backup.py`. Volumes: blog_data (read-only), backups, config.toml. |
| D-6 | med | Fix line number references | `architecture/deployment/docker.md` | backup.py:24→23, docker-compose.yml:103→105, docker-compose.yml:50→52. Verify by reading each file. |
| D-7 | med | Add missing env vars | `architecture/deployment/docker.md:86-103` | Missing: `SQLALCHEMY_DATABASE_URI` (docker-compose.yml:11), `API_KEY` (docker-compose.yml:26), `SESSION_COOKIE_SECURE` (docker-compose.yml:16). |
| D-8 | med | Remove `FLASK_ENV` if unused | `architecture/deployment/docker.md:90` | `FLASK_ENV` does not appear in docker-compose.yml or Dockerfile. May be vestigial. Verify by searching the codebase. |
| D-9 | med | Fix `docker-compose` → `docker compose` (v2 syntax) | `architecture/deployment/cicd.md` | ci.yml:175 uses `docker compose wait` (spaced v2). Doc should match. |
| D-10 | med | Fix `pytest.ini` documentation | `architecture/deployment/cicd.md:35-38` | Actual `pytest.ini` is 3 lines: just `[pytest]` with `e2e` marker. Coverage settings are in `pyproject.toml:20-22,33`. |
| TS-1 | high | Fix pytest.ini reference → pyproject.toml | `architecture/testing/test-suite.md:79-84` | Real pytest config is in `pyproject.toml:20-22` (testpaths, addopts). `pytest.ini` only defines markers. |
| TS-2 | high | Remove phantom `regular_user` and `post` fixtures | `tests/AGENTS.override.md:68-69` | Neither fixture exists. `def regular_user` — no matches. `def post` — no matches. Remove these lines. |
| TS-3 | med | Remove duplicate `clean_analytics_cache` from conftest.py | `tests/conftest.py:179-186` | Duplicate of `tests/shared_fixtures.py:17-24`. Both are identical. Remove from conftest.py (shared_fixtures.py is imported via `*`). |
| TS-4 | med | Document Celery eager configuration in tests | `architecture/testing/test-suite.md` | `tests/conftest.py:49-55` configures Celery to run tasks eagerly in tests. Add a note to test-suite.md. |
| TS-5 | med | Document `slow` marker from pytest_configure | `architecture/testing/test-suite.md` | `tests/conftest.py:19-22` registers a `slow` marker. Document how to skip: `-m "not slow"`. |

---

## Wave 2: Code-Level Fixes (Can start after Wave 1 begins)

These are actual code changes, not documentation. Each can be done independently.

### Wave 2A: Template & Frontend Code Fixes

**Sub-agent: SA-6**

| ID | Priority | Description | File | Verification |
|----|----------|-------------|------|--------------|
| CF-1 | high | Fix duplicate Atom feed link in `base.html:24` | `app/templates/base.html:24` | Line 19 outputs Atom inside `{% block feed_links %}`. Line 24 outputs an identical hardcoded Atom link OUTSIDE the block. Line 24 is unconditional — every page gets two feed links. Remove line 24. |
| CF-2 | low | Add `admin/login_base.html` and `email/base_email.html` to template directory structure listing | `architecture/frontend/templates.md` | These are base templates not currently listed in the template directory structure. Add them. |

### Wave 2B: Dead Code Cleanup

**Sub-agent: SA-7**

| ID | Priority | Description | File | Verification |
|----|----------|-------------|------|--------------|
| DC-1 | low | Remove dead state variables from `SQLiteSearchProvider.__init__()` | `app/services/search/sqlite.py:10-12` | Three unused vars: `_fts_enabled`, `_fts_check_time`, `_FTS_CHECK_TTL`. Never read anywhere in the file. All methods delegate to `app.search` functions. |
| DC-2 | low | Investigate dead code in RSS feed functions | `app/routes/rss.py:201,204,306,309,354,357,459,462,640,643` | 10 standalone expressions like `utc_now().isoformat() + "Z"` that compute but never assign or return. Leftover from `feed_updated` refactoring. Remove each unused expression line. |

### Wave 2C: Test Cleanup

**Sub-agent: SA-8**

| ID | Priority | Description | File | Verification |
|----|----------|-------------|------|--------------|
| TC-1 | med | Remove duplicate `clean_analytics_cache` definition from conftest.py | `tests/conftest.py:179-186` | Already defined in `tests/shared_fixtures.py:17-24` and imported via `*`. Remove from conftest.py. |
| TC-2 | low | Add server teardown to `app_server` fixture | `tests/e2e/conftest.py:26-60` | Starts Flask server thread but has no shutdown. Thread is daemon so dies with process, but could cause port conflicts. Add teardown that sets a shutdown event or calls server.shutdown(). |

---

## Wave 3: Documentation Improvements (Can run in parallel with Wave 2)

New documentation to add for completeness. Can be assigned to the same sub-agents as Wave 2.

### Wave 3A: Missing Model & Config Documentation

**Sub-agent: SA-6 (or SA-2 after Wave 1B)**

| ID | Priority | Description | File |
|----|----------|-------------|------|
| MD-1 | med | Document Vite integration and CLI commands in app-factory.md | `architecture/core/app-factory.md` |
| MD-2 | low | Add `nullable` constraints to User model field docs (email nullable=True) | `architecture/core/models.md` |
| MD-3 | low | Document structured logging, ProxyFix, and cache configuration | `architecture/core/app-factory.md` |
| MD-4 | low | Document `get_indexed_terms_fallback()` and `_escape_fts_term()` in search.md | `architecture/services/search.md` |
| MD-5 | low | Document service-level `run_daily_backup()` in backup.md | `architecture/services/backup.md` |
| MD-6 | low | Document `_invalidate_all_caches()` coordination in tag.md | `architecture/services/tag.md` |
| MD-7 | low | Document `extract_snippet()`, `init_storage()`, `storage_delete_file()` | `architecture/services/search.md`, `architecture/infrastructure/storage.md` |
| MD-8 | low | Add `base_email.html` to email templates list | `architecture/infrastructure/email.md` |
| MD-9 | low | Clarify `_send_email_with_retry` default (3) vs newsletter override (5) in email.md | `architecture/infrastructure/email.md` |
| MD-10 | low | Document `img-skeleton` shimmer animation in the lazy loading section | `architecture/frontend/static-assets.md` |
| MD-11 | low | Add `admin/login_base.html` and `email/base_email.html` to template directory structure listing | `architecture/frontend/templates.md` |

### Wave 3B: Missing Infrastructure Documentation

**Sub-agent: SA-7 (or SA-5 after Wave 1E)**

| ID | Priority | Description | File |
|----|----------|-------------|------|
| ID-1 | low | Document scripts/ directory (build_assets, dev.sh, update-assets, sync_backups) | `architecture/deployment/docker.md` or new doc |
| ID-2 | low | Document Granian worker count (4) and timeout (60s) | `architecture/deployment/docker.md` |
| ID-3 | low | Address backup container config.toml / encryption key loading | `docker-compose.yml` |
| ID-4 | low | Verify nginx proxy_pass 127.0.0.1 works with Docker networking | `nginx/conf.d/blog.conf` |
| ID-5 | low | Document Celery global config (`task_time_limit`, `worker_prefetch_multiplier`, etc.) | `architecture/tasks/celery-tasks.md` |
| ID-6 | low | Document `publish_scheduled_posts` rollback on FTS sync failure | `architecture/tasks/scheduler.md` |

---

## Wave 4: Project Polish for Public Release (Sequential, lower priority)

These items are from the improvements plan and should be done after documentation fixes.

### Wave 4A: Public Project Identity

| ID | Priority | Description |
|----|----------|-------------|
| P-1 | med | Establish consistent project name (DevLog) across repository |
| P-2 | med | Add positioning section and badges to README.md |
| P-3 | med | Align Python version documentation (3.12/3.13) across docs |

### Wave 4B: Environment & Security Polish

| ID | Priority | Description |
|----|----------|-------------|
| P-4 | med | Expand `.env.example` with all supported env vars |
| P-5 | med | Replace unsafe placeholders with generation commands |
| P-6 | med | Add concrete vulnerability reporting path to SECURITY.md |
| P-7 | med | Add "Security Boundaries" section to SECURITY.md |
| P-8 | med | Add production checklist to deployment docs |

### Wave 4C: Docker & CI Polish

| ID | Priority | Description |
|----|----------|-------------|
| P-9 | med | Add or improve `.dockerignore` |
| P-10 | med | Add Docker labels if useful |
| P-11 | med | Add frontend build check to CI |
| P-12 | med | Add Docker build check to CI |
| P-13 | low | Add Dependabot configuration |

### Wave 4D: Contribution & Release Hygiene

| ID | Priority | Description |
|----|----------|-------------|
| P-14 | low | Clean CONTRIBUTING.md (remove internal branch naming) |
| P-15 | low | Add issue templates (bug report, feature request) |
| P-16 | low | Add PR template |
| P-17 | low | Add CHANGELOG.md |
| P-18 | low | Update license year if appropriate |
| P-19 | low | Add repository About metadata and topics |

---

## Wave 5: Final Verification (After all other waves)

| ID | Priority | Description |
|----|----------|-------------|
| V-1 | high | Run repository-wide drift marker search (`rg -n "NOT |not exist|does NOT|actual|Actual|deprecated|TODO|FIXME|placeholder|<repo-url>"`) |
| V-2 | high | Run backend checks: `ruff check . && mypy app/ && ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/ --ignore=tests/e2e` |
| V-3 | high | Run frontend checks: `npm run build` (if npm available) |
| V-4 | high | Run Docker build check: `docker build .` |
| V-5 | med | Validate docs links (check for broken markdown links) |
| V-6 | med | Verify no secrets or private data in repo |

---

## Dependency Graph

```
Wave 1A ──┐
Wave 1B ──┤
Wave 1C ──┼──→ Wave 2 (Code Fixes) ──→ Wave 5 (Verification)
Wave 1D ──┤         │
Wave 1E ──┘         └──→ Wave 3 (New Docs) ──┘
                                        │
                                        └──→ Wave 4 (Project Polish) ──→ Wave 5
```

**Parallelization Notes:**
- All Wave 1 sub-waves (A-E) can run simultaneously as 5 separate sub-agents
- Wave 2 and Wave 3 can run in parallel after Wave 1 completes
- Wave 4 can start after Wave 2 completes (some items need code fixes)
- Wave 5 must run after all other waves complete

---

## Estimated Item Count

| Wave | Items | Estimated Effort |
|------|-------|------------------|
| Wave 1 | 50 | Medium (documentation edits) |
| Wave 2 | 4 | Low (small code changes) |
| Wave 3 | 17 | Medium (new documentation) |
| Wave 4 | 19 | Medium (project polish) |
| Wave 5 | 6 | Low (verification) |
| **Total** | **96** | |

---

## Do Not Do

- Do not rewrite the Flask app
- Do not replace SQLite/PostgreSQL abstractions
- Do not remove working security features
- Do not introduce a new frontend framework
- Do not add hosted/SaaS assumptions
- Do not remove AGENTS guidance entirely; split and stabilize it
- Do not claim production scalability beyond what the scheduler, SQLite, and background-job architecture actually support
- Do not publish real secrets, private analytics, private posts, or subscriber information

---

*Last updated: May 29, 2026 — Plan created from consolidated architecture reviews*
