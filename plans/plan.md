# Consolidated Architecture Review Plan

**Date:** May 31, 2026
**Source:** Module reviews from core, routes, services, tasks, infrastructure, frontend, deployment, testing, and architecture pruning.

---

## Executive Summary

| Category | Count |
|----------|-------|
| Verified Claims | 124 |
| Discrepancies | 51 |
| Missing Documentation | 30 |
| Potential Bugs | 24 |
| Action Items | 135 |

### Critical Findings

1. **CRITICAL:** Nginx `proxy_pass` uses `127.0.0.1` instead of service name `blog` (deployment)
2. **HIGH:** RSS cache invalidation incomplete (atom/json feeds not invalidated)
3. **HIGH:** Global rate limit bypass via X-Forwarded-For spoofing
4. **HIGH:** `decrypt_backup_file()` missing RuntimeError catch
5. **HIGH:** `S3StorageBackend.save()` lacks error handling
6. **HIGH:** Admin Prism CSS hardcoded to okaidia (ignores user setting)
7. **HIGH:** Prism double-loading on admin pages
8. **HIGH:** Template inheritance diagram is factually wrong
9. **HIGH:** Widespread test password inconsistency ("testpassword" vs "test-password")
10. **HIGH:** Documentation claims features that don't exist (LIKE fallback, PostgreSQL fallback, email health check, exponential backoff)

---

## Wave 1: Critical Source Code Fixes

**Goal:** Fix bugs that affect runtime behavior, security, or data integrity.
**Parallelizable:** Yes — items are independent across modules.

### 1.1 Security & Data Integrity

| # | Task | Source File | Description |
|---|------|-------------|-------------|
| 1.1.1 | Fix X-Forwarded-For spoofing | `app/routes/public/__init__.py:24-32` | `get_client_ip()` must split X-Forwarded-For by comma and use first IP only. Currently accepts full header value, bypassing rate limits. |
| 1.1.2 | Fix nginx proxy_pass | `nginx/default.conf` | Change `proxy_pass http://127.0.0.1:8000` to `proxy_pass http://blog:8000` for Docker service discovery. |
| 1.1.3 | Add backup encryption error handling | `app/backup_encryption.py:237` | Add `RuntimeError` and `InvalidTag` to `decrypt_backup_file()` exception handler. Currently unhandled exceptions break the documented `False` return contract. |
| 1.1.4 | Add webhook encryption error handling | `app/backup_encryption.py:183` | Add `InvalidTag` catch to `decrypt_backup()` — corrupted encrypted data causes unhandled exception. |
| 1.1.5 | Fix S3 save error handling | `app/storage.py` | Add try/except to `S3StorageBackend.save()` consistent with other S3 methods. Currently has no error handling. |

### 1.2 RSS Cache Invalidation

| # | Task | Source File | Description |
|---|------|-------------|-------------|
| 1.2.1 | Fix RSS cache invalidation | `app/routes/rss.py` | `invalidate_rss_cache()` must also clear `atom_feed_posts` and `json_feed_posts` cache keys. Currently only invalidates one feed type. |

### 1.3 Frontend Critical Fixes

| # | Task | Source File | Description |
|---|------|-------------|-------------|
| 1.3.1 | Fix Prism double-loading | `app/templates/admin/base.html` | `admin/base.html` loads Prism eagerly AND `loadPrismIfNeeded()` loads it dynamically again on admin pages. Remove eager load. |
| 1.3.2 | Fix Prism CSS theme | `app/templates/admin/base.html:9` | Use `syntax_theme` variable for Prism CSS instead of hardcoded `prism-okaidia.css`. |
| 1.3.3 | Load marked.min.js via Vite | `app/templates/admin/base.html` | Load `marked.min.js` via `vite_asset()` instead of `url_for('static', ...)` for content hashing and CDN support. |

### 1.4 Test Standardization

| # | Task | Source File | Description |
|---|------|-------------|-------------|
| 1.4.1 | Standardize test passwords | `tests/` | Standardize password to "test-password" in all test files (24 occurrences of "testpassword"). |
| 1.4.2 | Fix test_make_owner | `tests/` | Use correct password ("test-password"). |
| 1.4.3 | Fix test_login_success | `tests/` | Use correct password or add meaningful assertion. |

---

## Wave 2: High Priority Documentation Corrections

**Goal:** Fix documentation that makes false claims about features or behavior.
**Parallelizable:** Yes — items are independent across doc files.
**Depends on:** Wave 1 (source code fixes must be done first to know correct behavior).

### 2.1 Core Documentation

| # | Task | Doc File | Description |
|---|------|----------|-------------|
| 2.1.1 | Fix LOGIN_FAILURE_DELAY doc | `architecture/core/app-factory.md` | Minimum is 0.1s, not "no minimum enforced". |
| 2.1.2 | Fix Storage Settings attribution | `architecture/core/app-factory.md` | Env vars are in `app/storage.py`, not `app/config.py`. |
| 2.1.3 | Add nullable constraints | `architecture/core/models.md` | Add nullable constraints to all model code blocks. |
| 2.1.4 | Add missing indexes | `architecture/core/models.md` | Add 11 missing indexes to Key Indexes section (AdminSession, Webhook, WebhookEvent, Series, ApiToken). |
| 2.1.5 | Add WebhookEvent fields | `architecture/core/models.md` | Add `successful_deliveries` and `failed_deliveries` fields to WebhookEvent model doc. |
| 2.1.6 | Fix PostSeries __repr__ | `architecture/core/models.md` | Fix to match actual code output. |
| 2.1.7 | Fix flask seed CLI doc | `architecture/core/app-factory.md` | Option is `--published/--draft`, not just `--published`. |
| 2.1.8 | Document CSRF mechanism | `architecture/core/app-factory.md` | Document CSRF sliding window mechanism (window size 5, token rotation) and global enforcement via before_request_handler(). |
| 2.1.9 | Document search fallback | `architecture/core/app-factory.md` | Document that search fallback and "Did you mean?" features do NOT exist (currently claimed but missing). |
| 2.1.10 | Add missing validations | `architecture/core/configuration.md` | Add 8 missing validations to Validation section. |

### 2.2 Route Documentation

| # | Task | Doc File | Description |
|---|------|----------|-------------|
| 2.2.1 | Fix admin routes | `architecture/routes/admin-routes.md` | Fix route paths, remove phantom revision route, relocate Markdown Preview section, add helpers/ directory. |
| 2.2.2 | Fix public routes | `architecture/routes/public-routes.md` | Rewrite route table to remove phantom routes (`/page/<page>`, `/tag/<slug>/<page>`), fix health check parameter (`?detailed=true`). |
| 2.2.3 | Fix API routes | `architecture/routes/api-routes.md` | Fix auth section: 401 not 503 when API_KEY unset; describe two-tier auth (legacy API_KEY + scoped ApiToken). Remove non-existent "API key check: 1000/hour" rate limit. |
| 2.2.4 | Document scoped API tokens | `architecture/routes/api-routes.md` | Document ApiToken, require_scope decorator, full scope list. |
| 2.2.5 | Fix RSS cache doc | `architecture/routes/rss-feeds.md` | Clarify server-side 5 min vs HTTP Cache-Control 1 hour distinction. |
| 2.2.6 | Fix password route path | `architecture/routes/admin-routes.md` | `/users/password/<user_id>` not `/users/<user_id>/password`. |

### 2.3 Infrastructure Documentation

| # | Task | Doc File | Description |
|---|------|----------|-------------|
| 2.3.1 | Fix email backoff claim | `architecture/infrastructure/email.md` | `_send_email_with_retry()` has no sleep/delay between retries — either implement backoff or remove "Exponential backoff" claim. |
| 2.3.2 | Fix search fallback claim | `architecture/infrastructure/search.md` | `search()` returns empty list when FTS unavailable, not LIKE-based fallback — either implement fallback or remove claim. |
| 2.3.3 | Fix PostgreSQL fallback claim | `architecture/infrastructure/search.md` | `PostgreSQLSearchProvider` raises `ConfigurationError`, does NOT fall back to SQLite — either implement fallback or correct docs. |
| 2.3.4 | Remove email health check | `architecture/infrastructure/overview.md` | `email` health check does not exist in `app/routes/public/meta.py` — remove from docs or implement. |
| 2.3.5 | Fix webhook URL snippet | `architecture/infrastructure/overview.md` | Replace simplified `is_safe_webhook_url()` code snippet (10 lines vs ~100 actual) with accurate version or remove. |
| 2.3.6 | Fix S3 error handling claim | `architecture/infrastructure/storage.md` | `save()` raises exceptions, does NOT return False — update docs. |
| 2.3.7 | Add missing webhook fields | `architecture/infrastructure/webhooks.md` | Add `successful_deliveries` and `failed_deliveries` fields to WebhookEvent model docs. |

### 2.4 Services Documentation

| # | Task | Doc File | Description |
|---|------|----------|-------------|
| 2.4.1 | Fix backup silent fallback | `architecture/services/backup.md` | "Silent fallback" section contradicts code (warnings ARE logged) — fix self-contradictory documentation. |
| 2.4.2 | Remove config.toml encryption claim | `architecture/services/backup.md` | Key is only loaded from environment variable, not config.toml — remove false claim. |
| 2.4.3 | Fix search line reference | `architecture/services/search.md` | Case Preservation line reference should be `342-344`, not `349-351`. |
| 2.4.4 | Fix tag line numbers | `architecture/services/tag.md` | Update line numbers for 4 functions (get_tag_by_slug, get_all_tags, delete_tag_if_unused, get_tag_post_count). |
| 2.4.5 | Fix tag_cache line numbers | `architecture/services/tag_cache.md` | Update line numbers for 4 functions. |
| 2.4.6 | Fix duplicate encryption entries | `architecture/services/overview.md` | Remove duplicate "Encryption" table entries. |

### 2.5 Deployment Documentation

| # | Task | Doc File | Description |
|---|------|----------|-------------|
| 2.5.1 | Fix docker e2e wait | `architecture/deployment/cicd.md` | e2e wait command is `docker compose wait blog`, not `redis`. |
| 2.5.2 | Fix security headers | `architecture/deployment/security.md` | X-Download-Options and X-Permitted-Cross-Domain-Policies ARE set by Flask — update docs. |
| 2.5.3 | Fix backup profile description | `architecture/deployment/docker.md` | Should list `backup` service, not `blog`. |
| 2.5.4 | Fix "no warning logged" claim | `architecture/deployment/docker.md` | backup.py:69-70 does log a warning — update docs. |
| 2.5.5 | Document CSP differences | `architecture/deployment/security.md` | Document CSP policy difference between Flask (nonce-based) and nginx (unsafe-inline). |

### 2.6 Tasks Documentation

| # | Task | Doc File | Description |
|---|------|----------|-------------|
| 2.6.1 | Fix newsletter error handling | `architecture/tasks/celery-tasks.md` | `send_newsletter_task` does NOT call `self.retry()` — document actual behavior (returns False on failure, Celery auto-retry on uncaught exceptions only). |
| 2.6.2 | Remove duplicate webhook section | `architecture/tasks/celery-tasks.md` | Remove duplicate `deliver_single_webhook_task` section (lines 79-100). |
| 2.6.3 | Document newsletter retry gap | `architecture/tasks/celery-tasks.md` | Document that `send_newsletter_task` does NOT check `NEWSLETTER_MAX_RETRY_ATTEMPTS` (unlike scheduler path) and explain why. |
| 2.6.4 | Fix scheduler log message | `architecture/tasks/scheduler.md` | Fix log message template to match actual code (`"Could not acquire lock %s, skipping run"`). |
| 2.6.5 | Document delivery status race | `architecture/tasks/scheduler.md` | Document that `_update_delivery_status` correctness depends on `--concurrency=1` and the race condition risk if concurrency is increased. |

### 2.7 Overview Documentation

| # | Task | Doc File | Description |
|---|------|----------|-------------|
| 2.7.1 | Add ApiToken to schema | `architecture/overview.md` | Add `api_tokens` to database tables list and ApiToken to ER diagram. |
| 2.7.2 | Expand API Auth | `architecture/overview.md` | Expand API Auth description to cover two-tier system (legacy API_KEY + scoped ApiToken). |
| 2.7.3 | Fix Three-Way Path | `architecture/overview.md` | Fix heading to match two described paths. |
| 2.7.4 | Document CSRF | `architecture/overview.md` | Document CSRF global enforcement mechanism via before_request_handler(). |
| 2.7.5 | Add encryption modules | `architecture/overview.md` | Add backup_encryption.py and webhook_encryption.py to services table. |
| 2.7.6 | Complete source list | `architecture/overview.md` | Add cli.py and validators.py to Core Application source list. |
| 2.7.7 | Add Docker profiles | `architecture/overview.md` | Add Docker Compose profiles requirement to Deployment section. |
| 2.7.8 | Add APScheduler warning | `architecture/overview.md` | Add multi-container limitation warning to Task Processing section. |
| 2.7.9 | Document newsletter retry | `architecture/overview.md` | Document retry count (5) and path differences between Celery and scheduler. |

---

## Wave 3: Medium Priority Improvements

**Goal:** Improve documentation completeness, fix minor bugs, and clean up code.
**Parallelizable:** Yes — items are independent.
**Depends on:** Wave 2 (documentation corrections must be done first).

### 3.1 Source Code Improvements

| # | Task | Source File | Description |
|---|------|-------------|-------------|
| 3.1.1 | Add rate limit to metrics | `app/routes/public/meta.py` | Add `@limiter.limit("60 per minute")` to `GET /metrics` route. |
| 3.1.2 | Consolidate _save_revision | `app/routes/admin/` | Consolidate three duplicate `_save_revision()` functions into single definition. |
| 3.1.3 | Remove dead RSS code | `app/routes/rss.py` | Remove dead code `_get_cached_feed_posts()` (misleading, delegates to atom cache). |
| 3.1.4 | Add error handling to delete_post | `app/routes/admin/manage.py:88` | Add `try/except` around `db.session.commit()`. |
| 3.1.5 | Fix newsletter retry count | `app/tasks.py` | Document that `_send_email_with_retry` default `max_retries=3` vs. newsletter override to 5. |
| 3.1.6 | Fix backup timezone | `app/services/backup.py:49` | Use `datetime.now(timezone.utc)` in `create_backup()` for consistency with `run_daily_backup`. |
| 3.1.7 | Remove ENABLE_SCHEDULER | `app/config.py` | Remove or implement dead `ENABLE_SCHEDULER` config key. |
| 3.1.8 | Add FTS locking | `app/search.py` | Add locking to `_check_fts_enabled()` module-level globals for thread safety. |
| 3.1.9 | Fix FTS init destructive behavior | `app/search.py` | Make `init_fts()` less destructive on transient failures (currently drops FTS table). |
| 3.1.10 | Fix highlight_query escaping | `app/search.py` | Review `highlight_query()` for double-escaping of already-escaped HTML. |
| 3.1.11 | Add Celery concurrency docs | `architecture/tasks/scheduler.md` | Document that Celery worker runs with `--concurrency=1` and `worker_prefetch_multiplier=1` as production requirements. |
| 3.1.12 | Remove e2e dead code | `tests/e2e/conftest.py` | Remove dead code in e2e/app_server (redundant tmp_path and env var override). |
| 3.1.13 | Replace e2e sleep | `tests/e2e/conftest.py` | Replace time.sleep(1) with readiness polling. |
| 3.1.14 | Fix mock_email description | `tests/conftest.py` | Remove "autouse" claim about mock_render and mock_smtp. |
| 3.1.15 | Fix cleanup_uploads | `tests/conftest.py` | Handle subdirectories in cleanup_uploads. |

### 3.2 Documentation Additions

| # | Task | Doc File | Description |
|---|------|----------|-------------|
| 3.2.1 | Document marked.min.js pattern | `architecture/frontend/static-assets.md` | Document loading pattern (outside Vite pipeline) and its limitations. |
| 3.2.2 | Document template partials | `architecture/frontend/templates.md` | Document `prefetch.js`, `macros.html`, `_post_content.html`, `_error.html`, `_sidebar.html`, `_breadcrumbs.html`. |
| 3.2.3 | Fix static-assets file names | `architecture/frontend/static-assets.md` | Fix Public JS / Admin JS sections — actual file names differ from doc descriptions. |
| 3.2.4 | Update static-assets line ref | `architecture/frontend/static-assets.md` | Update vite.config.js JSX line reference from 31-39 to 36-44. |
| 3.2.5 | Document Page View Buffer | `architecture/core/app-factory.md` | Document flush size, interval, and shutdown behavior. |
| 3.2.6 | Document tag cache | `architecture/core/app-factory.md` | Document tag cache mechanism and TTL. |
| 3.2.7 | Document footer exclusion | `architecture/core/app-factory.md` | Document path-based footer exclusion logic (/admin, /api, /rss). |
| 3.2.8 | Document admin helpers | `architecture/routes/admin-routes.md` | Document the `helpers/` directory. |
| 3.2.9 | Document comment spam | `architecture/routes/public-routes.md` | Document comment spam scoring system (thresholds, heuristics, auto-quarantine). |
| 3.2.10 | Document archive pagination | `architecture/routes/public-routes.md` | Document cursor-based pagination parameters. |
| 3.2.11 | Document newsletter test vs preview | `architecture/routes/admin-routes.md` | Clarify test vs preview distinction. |
| 3.2.12 | Document Celery configuration | `architecture/deployment/docker.md` | Document Celery task configuration (time limits, max tasks per child). |
| 3.2.13 | Document CI pipeline | `architecture/deployment/cicd.md` | Document dependency chain (lint-and-type -> test -> e2e-tests). |
| 3.2.14 | Add FakeSubscriber docs | `architecture/testing/test-suite.md` | Document FakeSubscriber dataclass. |
| 3.2.15 | Document search functions | `architecture/infrastructure/search.md` | Add `init_fts()`, `_check_fts_enabled()`, `extract_snippet()`, `get_indexed_terms()` to module-level functions table. |
| 3.2.16 | Document exception classes | `architecture/services/*.md` | Document `EncryptionError`, `WebhookEncryptionError`, and `ConfigurationError` exception classes. |
| 3.2.17 | Document backup params | `architecture/services/backup.md` | Document mutual exclusivity of `compress` and `encrypt` parameters. |
| 3.2.18 | Document highlight_query | `architecture/infrastructure/search.md` | Document HTML escaping behavior. |

---

## Wave 4: Low Priority Cleanup

**Goal:** Remove dead code, fix style issues, and address minor concerns.
**Parallelizable:** Yes — items are independent.
**Depends on:** Wave 3.

### 4.1 Dead Code Removal

| # | Task | Source File | Description |
|---|------|-------------|-------------|
| 4.1.1 | Remove init_storage dead code | `app/storage.py` | `init_storage()` is defined and documented but never called anywhere. |
| 4.1.2 | Remove legacy _has_gnupg | `app/backup_encryption.py` | Remove legacy `_has_gnupg()` function or rename it. |
| 4.1.3 | Remove unnecessary SQLAlchemyError | `app/backup_encryption.py` | Remove unnecessary `SQLAlchemyError` from exception handlers in standalone encryption functions. |
| 4.1.4 | Remove _get_cached_feed_posts | `app/routes/rss.py` | Dead code that delegates to atom cache. |
| 4.1.5 | Remove unused vite-plugin-beasties | `vite.config.js` | Remove or configure unused plugin. |
| 4.1.6 | Remove redundant env var declarations | `tests/` | Remove redundant env var declarations from individual test files. |
| 4.1.7 | Remove redundant fixture overrides | `tests/` | Remove from test_context_processors.py and test_search.py. |

### 4.2 Style & Documentation Cleanup

| # | Task | Doc File | Description |
|---|------|----------|-------------|
| 4.2.1 | Add .svg loader to docs | `architecture/frontend/static-assets.md` | Add `.svg: 'text'` loader to vite.config.js code example. |
| 4.2.2 | Fix Prism data attribute doc | `architecture/frontend/templates.md` | Document `data-prism-css-url` attribute on `<html>` element. |
| 4.2.3 | Add loadPrismIfNeeded guard | `app/static/js/admin.js` | Add guard to check `window.Prism` existence before creating script elements. |
| 4.2.4 | Consider search sanitization | `app/search.py` | Add nh3 clean on FTS5 snippets before rendering with `| safe`. |
| 4.2.5 | Document CI pip-audit | `architecture/deployment/cicd.md` | Note pip-audit uses `--fail-on=all` (strict mode). |
| 4.2.6 | Document nginx XSS header | `architecture/deployment/docker.md` | Note nginx X-XSS-Protection only present when proxied through nginx. |
| 4.2.7 | Note healthcheck timeout diff | `architecture/deployment/docker.md` | Dockerfile healthcheck timeout (3s) differs from docker-compose override (10s). |
| 4.2.8 | Add start_period | `Dockerfile` | Add `start_period` to HEALTHCHECK or document the omission. |
| 4.2.9 | Add SECRET_KEY to backup | `docker-compose.yml` | Add SECRET_KEY to backup service environment if needed by app imports. |
| 4.2.10 | Document email retry arch | `architecture/infrastructure/email.md` | Document retry architecture (3 default vs 5 for newsletter). |
| 4.2.11 | Document search fallback | `architecture/infrastructure/search.md` | Document `get_indexed_terms()` fallback path. |
| 4.2.12 | Move _SQLITE_MAX_VARS | `architecture/infrastructure/search.md` | Move out of module-level constants code block or clarify it is local to `get_search_snippets()`. |
| 4.2.13 | Document init_fts error | `architecture/infrastructure/search.md` | Document `init_fts()` destructive error handling behavior. |
| 4.2.14 | Document silent webhook fail | `architecture/infrastructure/webhooks.md` | Document silent webhook queue failure. |
| 4.2.15 | Move api_client | `tests/` | Move api_client from test_api.py to conftest.py (or clarify it is test-local). |
| 4.2.16 | Add Celery eager config | `tests/conftest.py` | Add Celery eager config to test_context_processors.py app fixture (latent risk). |
| 4.2.17 | Apply pytest markers | `tests/` | Apply @pytest.mark.e2e and @pytest.mark.slow to appropriate tests. |
| 4.2.18 | Document newsletter test vs preview | `architecture/routes/admin-routes.md` | Clarify distinction. |
| 4.2.19 | Remove username from log | `app/routes/admin/auth.py:247` | Remove username from password reset log line for PII compliance. |
| 4.2.20 | Add try/except to subscribe | `app/routes/public/subscribe.py:74,82,114,143` | Add `try/except` guard on `db.session.commit()` where not already wrapped. |

---

## Wave 5: Architecture Pruning

**Goal:** Delete, rewrite, or merge stale architecture documentation.
**Parallelizable:** Partially — rewrites can be parallelized, merges must be sequential.
**Depends on:** Waves 2-4 (source code fixes and doc corrections must be done first to know correct state).

### 5.1 Full Rewrites

| # | Task | Doc File | Description |
|---|------|----------|-------------|
| 5.1.1 | Rewrite E2E testing docs | `architecture/testing/test-suite.md` | Full rewrite of E2E section, fix playwright claim, fix mock_email description, add FakeSubscriber docs, update marker usage status. |
| 5.1.2 | Rewrite public routes | `architecture/routes/public-routes.md` | Rewrite route table to remove phantom routes, fix health check parameter, relocate short URL documentation. |
| 5.1.3 | Rewrite admin routes | `architecture/routes/admin-routes.md` | Fix route paths, remove phantom revision route, relocate Markdown Preview section, add helpers/ directory. |

### 5.2 Merges

| # | Task | Doc Files | Description |
|---|------|-----------|-------------|
| 5.2.1 | Merge infrastructure overview | `architecture/infrastructure/overview.md` → `architecture/overview.md` | Merge infrastructure overview into main overview. |
| 5.2.2 | Fix services overview duplicates | `architecture/services/overview.md` | Deduplicate "Encryption" entries. |

### 5.3 Stale Line References

Fix line number references that have drifted in:
- `architecture/infrastructure/search.md`
- `architecture/services/tag.md`
- `architecture/services/tag_cache.md`
- `architecture/infrastructure/webhooks.md`
- `architecture/deployment/docker.md`
- `architecture/core/configuration.md`
- `architecture/frontend/static-assets.md`

---

## Wave 6: AGENTS.md Cleanup

**Goal:** Update agent documentation to reflect current state.
**Parallelizable:** No — must be done after all other waves.
**Depends on:** All previous waves.

### 6.1 AGENTS.md Updates

| # | Task | Description |
|---|------|-------------|
| 6.1.1 | Remove outdated e2e claim | Remove outdated claim about e2e/conftest.py not defining app fixture. |
| 6.1.2 | Add template context vars | Add `site_title` and `site_description` as context variables (NOT `site_name` or `site_tagline`). |
| 6.1.3 | Add template filters | Add actual filters: `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`, `post_image_avif_url_stub`. |
| 6.1.4 | Add Critical CSS note | Document `critical.css` file and its loading in `base.html:24`. |
| 6.1.5 | Add Docker profiles | Document that all services require explicit profiles (no default profile). |
| 6.1.6 | Add CI workflow location | Document CI workflow is at `.github/workflows/ci.yml` with 6 jobs. |
| 6.1.7 | Add Webhook delivery arch | Document two-level dispatch pattern. |
| 6.1.8 | Add model count | Document exactly 17 model classes in `app/models.py`. |
| 6.1.9 | Add thread-safe storage | Document `get_storage()` double-checked locking pattern. |
| 6.1.10 | Add E2E test isolation | Document session-scoped `app` fixture and dead code in E2E `app_server` fixture. |
| 6.1.11 | Add Login template assets | Document `admin/login_base.html` uses `vite_asset()` for CSS/JS assets. |
| 6.1.12 | Add Prism CSS loading | Document Prism CSS loaded via `data-prism-css-url` attribute. |
| 6.1.13 | Add Session IP Binding | Document enforcement via `admin_required` decorator, not global handler. |
| 6.1.14 | Add Silent FTS init | Document `OperationalError` catch during FTS init silently. |
| 6.1.15 | Add LOGIN_FAILURE_DELAY | Document minimum 0.1s enforced in `app/config.py`. |
| 6.1.16 | Add Comment Rate Limit | Document X-Forwarded-For header bypass limitation. |
| 6.1.17 | Add APScheduler limitation | Document FileLock with `timeout=0` only works on single machine. |
| 6.1.18 | Add Vite build required | Document `npm run build` must be run before production deployment. |
| 6.1.19 | Add SMTP handling | Document that only daily newsletter job is disabled when SMTP_HOST not configured. |
| 6.1.20 | Add Email retry count | Document newsletter retry count default is 5 (not 3). |

### 6.2 AGENTS.override.md Updates

| # | Task | File | Description |
|---|------|------|-------------|
| 6.2.1 | Update plans override | `plans/AGENTS.override.md` | Update to reflect consolidated plan status. |

---

## Implementation Strategy

### Parallel Execution Plan

```
Wave 1 (Critical) ─────────────────────────────────────────────────────────┐
  ├─ 1.1 Security & Data Integrity (5 tasks)                              │
  ├─ 1.2 RSS Cache Invalidation (1 task)                                  │
  ├─ 1.3 Frontend Critical Fixes (3 tasks)                                │
  └─ 1.4 Test Standardization (3 tasks)                                   │
                                                                           │
Wave 2 (High Priority Docs) ───────────────────────────────────────────────┤
  ├─ 2.1 Core Documentation (10 tasks)                                    │
  ├─ 2.2 Route Documentation (6 tasks)                                    │
  ├─ 2.3 Infrastructure Documentation (7 tasks)                           │
  ├─ 2.4 Services Documentation (6 tasks)                                 │
  ├─ 2.5 Deployment Documentation (5 tasks)                               │
  ├─ 2.6 Tasks Documentation (5 tasks)                                    │
  └─ 2.7 Overview Documentation (9 tasks)                                 │
                                                                           │
Wave 3 (Medium Priority) ──────────────────────────────────────────────────┤
  ├─ 3.1 Source Code Improvements (15 tasks)                              │
  └─ 3.2 Documentation Additions (18 tasks)                               │
                                                                           │
Wave 4 (Low Priority) ─────────────────────────────────────────────────────┤
  ├─ 4.1 Dead Code Removal (7 tasks)                                      │
  └─ 4.2 Style & Documentation Cleanup (20 tasks)                         │
                                                                           │
Wave 5 (Architecture Pruning) ─────────────────────────────────────────────┤
  ├─ 5.1 Full Rewrites (3 tasks)                                          │
  ├─ 5.2 Merges (2 tasks)                                                 │
  └─ 5.3 Stale Line References (7 files)                                  │
                                                                           │
Wave 6 (AGENTS.md Cleanup) ────────────────────────────────────────────────┘
  ├─ 6.1 AGENTS.md Updates (20 tasks)
  └─ 6.2 AGENTS.override.md Updates (1 task)
```

### Sub-Agent Assignment Strategy

Each wave can use multiple sub-agents working in parallel:

**Wave 1 Sub-Agents:**
- Sub-Agent 1: Security fixes (1.1.1-1.1.5)
- Sub-Agent 2: RSS + Frontend fixes (1.2.1, 1.3.1-1.3.3)
- Sub-Agent 3: Test standardization (1.4.1-1.4.3)

**Wave 2 Sub-Agents:**
- Sub-Agent 1: Core + Route docs (2.1, 2.2)
- Sub-Agent 2: Infrastructure + Services docs (2.3, 2.4)
- Sub-Agent 3: Deployment + Tasks + Overview docs (2.5, 2.6, 2.7)

**Wave 3 Sub-Agents:**
- Sub-Agent 1: Source code improvements (3.1)
- Sub-Agent 2: Documentation additions (3.2)

**Wave 4 Sub-Agents:**
- Sub-Agent 1: Dead code removal (4.1)
- Sub-Agent 2: Style cleanup (4.2)

**Wave 5 Sub-Agents:**
- Sub-Agent 1: Full rewrites (5.1)
- Sub-Agent 2: Merges + stale refs (5.2, 5.3)

**Wave 6 Sub-Agents:**
- Sub-Agent 1: AGENTS.md updates (6.1)
- Sub-Agent 2: AGENTS.override.md updates (6.2)

### Verification Checklist

After each wave, verify:
- [ ] All source code changes pass `ruff check .` and `ruff format --check .`
- [ ] All source code changes pass `mypy app/`
- [ ] All tests pass: `ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/`
- [ ] Documentation changes are internally consistent
- [ ] Line number references are accurate
- [ ] No phantom claims remain

---

## Appendix: Complete Task Index

### Wave 1: 12 tasks
- 1.1.1, 1.1.2, 1.1.3, 1.1.4, 1.1.5, 1.2.1, 1.3.1, 1.3.2, 1.3.3, 1.4.1, 1.4.2, 1.4.3

### Wave 2: 48 tasks
- 2.1.1-2.1.10, 2.2.1-2.2.6, 2.3.1-2.3.7, 2.4.1-2.4.6, 2.5.1-2.5.5, 2.6.1-2.6.5, 2.7.1-2.7.9

### Wave 3: 33 tasks
- 3.1.1-3.1.15, 3.2.1-3.2.18

### Wave 4: 27 tasks
- 4.1.1-4.1.7, 4.2.1-4.2.20

### Wave 5: 12 tasks
- 5.1.1-5.1.3, 5.2.1-5.2.2, 5.3 (7 files)

### Wave 6: 21 tasks
- 6.1.1-6.1.20, 6.2.1

**Total: 153 tasks**
