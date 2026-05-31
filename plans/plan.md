# Consolidated Architecture Review Plan

**Date:** May 31, 2026
**Source:** Module reviews from core, routes, services, tasks, infrastructure, frontend, deployment, and testing.

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

1. **CRITICAL:** Nginx `proxy_pass` uses `127.0.0.1` instead of service name `blog` (`nginx/conf.d/blog.conf:52,65,75,84`)
2. **HIGH:** RSS cache invalidation incomplete — only `rss_feed_posts` cleared, atom/JSON feeds stale for up to 5 min (`app/routes/rss.py:103-105`)
3. **HIGH:** Global rate limit bypass via X-Forwarded-For spoofing (`app/__init__.py:45-49`)
4. **HIGH:** `decrypt_backup_file()` missing `RuntimeError` and `InvalidTag` catch (`app/backup_encryption.py:237`)
5. **HIGH:** `S3StorageBackend.save()` lacks error handling unlike all other S3 methods (`app/storage.py:182-184`)
6. **HIGH:** Admin Prism CSS hardcoded to okaidia, ignores `syntax_theme` setting (`app/templates/admin/base.html:9`)
7. **HIGH:** Prism double-loading on admin pages — static tags + `loadPrismIfNeeded()` (`app/templates/admin/base.html:162-163`, `app/static/js/main.js:97-117`)
8. **HIGH:** Template inheritance diagram factually wrong — admin templates are standalone (`app/templates/admin/base.html:1`, `app/templates/admin/login_base.html:1`)
9. **HIGH:** Widespread test password inconsistency — 24 occurrences of `"testpassword"` vs 14 of `"test-password"` across `tests/`
10. **HIGH:** Documentation claims features that don't exist — LIKE fallback, PostgreSQL fallback, email health check, exponential backoff

---

## Wave 1: Critical Source Code Fixes

**Goal:** Fix bugs that affect runtime behavior, security, or data integrity.
**Parallelizable:** Yes — items are independent across modules.
**Verification:** Run `ruff check .`, `ruff format --check .`, `mypy app/`, and `ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/` after all items complete.

### 1.1 Security & Data Integrity

| # | Task | File | Line(s) | Exact Change |
|---|------|------|---------|--------------|
| 1.1.1 | Fix X-Forwarded-For spoofing | `app/__init__.py` | 45-49 | Split `forwarded_for` by comma, strip whitespace, return first IP. Match the pattern in `app/routes/public/comments.py:28-30` |
| 1.1.2 | Fix nginx proxy_pass | `nginx/conf.d/blog.conf` | 52,65,75,84 | Change all four `proxy_pass http://127.0.0.1:5000` to `proxy_pass http://blog:5000` |
| 1.1.3 | Add backup encryption error handling | `app/backup_encryption.py` | 237 | Add `RuntimeError` and `cryptography.hazmat.primitives.exceptions.InvalidTag` to the except clause in `decrypt_backup_file()` |
| 1.1.4 | Add webhook encryption error handling | `app/backup_encryption.py` | 183 | Add `InvalidTag` catch to `decrypt_backup()` — currently `InvalidTag` from GCM auth failure propagates unhandled |
| 1.1.5 | Fix S3 save error handling | `app/storage.py` | 182-184 | Wrap `self.client.put_object(...)` in `try/except (ClientError, BotoCoreError)` matching the pattern used by `load()`, `delete()`, `exists()`, and `list_files()` in the same class |

### 1.2 RSS Cache Invalidation

| # | Task | File | Line(s) | Exact Change |
|---|------|------|---------|--------------|
| 1.2.1 | Fix RSS cache invalidation | `app/routes/rss.py` | 103-105 | Add `flask_cache.delete("atom_feed_posts")` and `flask_cache.delete("json_feed_posts")` to `invalidate_rss_cache()`. Current function only clears `rss_feed_posts`, leaving atom and JSON feeds stale for up to 300s. |

### 1.3 Frontend Critical Fixes

| # | Task | File | Line(s) | Exact Change |
|---|------|------|---------|--------------|
| 1.3.1 | Fix Prism double-loading | `app/templates/admin/base.html` | 162-163 | Remove the two `<script defer>` tags for `prism.min.js` and `prism-languages.js`. These are loaded dynamically by `loadPrismIfNeeded()` in `main.js:97-117` when code blocks exist. The static tags cause double-loading on pages with code blocks. |
| 1.3.2 | Fix Prism CSS theme | `app/templates/admin/base.html` | 9 | Change `{{ vite_asset('css/prism-okaidia.css') }}` to `{{ vite_asset('css/' + syntax_theme + '.css') }}` to match the pattern in `base.html:30` |
| 1.3.3 | Load marked.min.js via Vite | `app/templates/admin/base.html` | 164 | Change `url_for('static', filename='js/lib/marked.min.js')` to `vite_asset('js/lib/marked.min.js')` for content hashing and CDN support. Also check `app/templates/base.html` for the same issue. |

### 1.4 Test Standardization

| # | Task | File(s) | Exact Change |
|---|------|---------|--------------|
| 1.4.1 | Standardize test passwords | `tests/test_security.py` (9), `tests/test_2fa.py` (6), `tests/test_context_processors.py` (2), `tests/benchmarks/conftest.py` (2), `tests/test_search.py` (1), `tests/test_api.py` (1), `tests/test_phase3b.py` (1), `tests/test_admin_users.py` (1), `tests/test_admin.py` (1) | Replace all 24 occurrences of `"testpassword"` with `"test-password"` to match `ADMIN_PASSWORD` env var set in `tests/conftest.py:9` |
| 1.4.2 | Fix test_make_owner | `tests/test_admin_users.py` | Line 113: change `"testpassword"` to `"test-password"` — currently the password confirmation fails silently, meaning the test does not actually validate ownership transfer |
| 1.4.3 | Fix test_login_success | `tests/test_admin.py` | Line 17: change `"testpassword"` to `"test-password"` — currently the test passes because both login failure and success return 200 with `follow_redirects=True` |

---

## Wave 2: High Priority Documentation Corrections

**Goal:** Fix documentation that makes false claims about features or behavior.
**Parallelizable:** Yes — items are independent across doc files.
**Depends on:** Wave 1 (source code fixes must be done first to know correct behavior).
**Verification:** Ensure all doc changes are internally consistent, no phantom claims remain, and line references are accurate.

### 2.1 Core Documentation

| # | Task | File | Description |
|---|------|------|-------------|
| 2.1.1 | Fix LOGIN_FAILURE_DELAY doc | `architecture/core/app-factory.md` | Minimum is 0.1s (enforced at `app/config.py:148` via `max(LOGIN_FAILURE_DELAY, 0.1)`), not "no minimum enforced" |
| 2.1.2 | Fix Storage Settings attribution | `architecture/core/app-factory.md` | Env vars (STORAGE_BACKEND, S3_BUCKET, etc.) are defined in `app/storage.py:53-60`, not `app/config.py` |
| 2.1.3 | Add nullable constraints | `architecture/core/models.md` | Add `nullable=` constraints to all model code blocks (Post, Comment, Page, SiteSettings models all have missing constraints) |
| 2.1.4 | Add missing indexes | `architecture/core/models.md` | Add 11 missing indexes: AdminSession `ix_admin_sessions_user_id`, Webhook `ix_webhooks_event_type_enabled`, WebhookEvent `ix_webhook_events_event_type_delivered` + `ix_webhook_events_webhook_id`, Series `ix_series_slug`, ApiToken `ix_api_tokens_token_hash` + `ix_api_tokens_revoked_at` |
| 2.1.5 | Add WebhookEvent fields | `architecture/core/models.md` | Add `successful_deliveries` and `failed_deliveries` fields (both `Integer, default=0, nullable=False`) to WebhookEvent model doc |
| 2.1.6 | Fix PostSeries __repr__ | `architecture/core/models.md` | Actual code at `app/models.py:593` returns `<PostSeries series_id={self.series_id} post_id={self.post_id} order={self.order_index}>` — doc has wrong field names and omits order_index |
| 2.1.7 | Fix flask seed CLI doc | `architecture/core/app-factory.md` | Option is `--published/--draft` (boolean flag pair), not just `--published` (`app/cli.py:264-268`) |
| 2.1.8 | Document CSRF mechanism | `architecture/core/app-factory.md` | Document sliding window of 5 valid tokens per session (`app/csrf.py:20`), token rotation on validation (`app/csrf.py:53-60`), and global enforcement via `before_request_handler()` (`app/__init__.py:296-298`) |
| 2.1.9 | Remove search fallback claim | `architecture/core/app-factory.md` | `search()` returns empty list when FTS unavailable (`app/search.py:199-200`), does NOT implement LIKE-based fallback. Module docstring at `app/search.py:1` is misleading — remove or correct |
| 2.1.10 | Add missing validations | `architecture/core/configuration.md` | Add 8 missing validations: dashboard_per_page, subscribers_per_page, media_per_page, media_max_files, max_upload_size, export_batch_size, fts_result_limit (`app/config.py:214-230`), token_enumeration_delay (`app/config.py:232-241`), smtp_timeout (`app/config.py:243-250`) |

### 2.2 Route Documentation

| # | Task | File | Description |
|---|------|------|-------------|
| 2.2.1 | Fix admin routes | `architecture/routes/admin-routes.md` | Fix route path `/users/<id>/password` to `/users/password/<id>` (`app/routes/admin/users.py:229`); remove phantom `GET /posts/<id>/revisions/<rev_id>` route (only list GET and POST restore exist); relocate "Markdown Preview" section from under "Session Monitoring" to "Post Management" (it's in `posts/editor.py:319`, not `sessions.py`) |
| 2.2.2 | Fix public routes | `architecture/routes/public-routes.md` | Remove phantom routes `/page/<page>` and `/tag/<slug>/<page>` (pagination uses `?page=N` query param, not path segments); fix health check parameter from `?detailed=1` to `?detailed=true` (`app/routes/public/meta.py:194`); relocate short URL doc from "Comment Routes" to "Post Routes" |
| 2.2.3 | Fix API routes | `architecture/routes/api-routes.md` | Fix auth section: returns 401 not 503 when API_KEY unset (`app/routes/api/auth.py:82-83`); describe two-tier auth (legacy `API_KEY` + scoped `ApiToken` with `require_scope` decorator); remove non-existent "API key check: 1000/hour" rate limit (default is "100 per minute") |
| 2.2.4 | Document scoped API tokens | `architecture/routes/api-routes.md` | Document `ApiToken` model (`app/models.py:625-657`), `require_scope()` decorator, full scope list: `posts:read`, `posts:write`, `media:read`, `media:write`, `subscribers:read`, `subscribers:write`, `newsletter:send`, `analytics:read`, `tags:read`, `tags:write`, `pages:read`, `pages:write`, `series:read`, `series:write`, `admin:*` |
| 2.2.5 | Fix RSS cache doc | `architecture/routes/rss-feeds.md` | Clarify server-side cache TTL (5 min via Flask-Caching) vs HTTP Cache-Control header (1 hour via `max-age=3600` at `app/routes/rss.py:98`) |
| 2.2.6 | Fix password route path | `architecture/routes/admin-routes.md` | `/users/password/<user_id>` not `/users/<user_id>/password` (`app/routes/admin/users.py:229`) |
| 2.2.7 | Document helpers/ directory | `architecture/routes/admin-routes.md` | Add `app/routes/admin/helpers/` to module structure — contains 9 submodules: `__init__.py`, `analytics.py`, `dashboard.py`, `images.py`, `posts.py`, `shared.py`, `slug.py`, `tags.py` |

### 2.3 Infrastructure Documentation

| # | Task | File | Description |
|---|------|------|-------------|
| 2.3.1 | Fix email backoff claim | `architecture/infrastructure/email.md` | `_send_email_with_retry()` has NO sleep/delay between retries (`app/email.py:106-149`) — docstring and docs both claim "exponential backoff" but it does not exist. Either implement backoff or remove claim. |
| 2.3.2 | Fix search fallback claim | `architecture/infrastructure/search.md` | `search()` returns empty list when FTS unavailable (`app/search.py:199-200`), NOT LIKE-based fallback. Remove "Fallback: LIKE-based search" claim. |
| 2.3.3 | Fix PostgreSQL fallback claim | `architecture/infrastructure/search.md` | `PostgreSQLSearchProvider` raises `ConfigurationError` on all methods (`app/services/search/postgresql.py:17-76`), does NOT fall back to SQLite |
| 2.3.4 | Remove email health check | `architecture/infrastructure/overview.md` | `email` health check does not exist in `app/routes/public/meta.py:188-321` — actual optional checks are redis, celery, backup_freshness |
| 2.3.5 | Fix webhook URL snippet | `architecture/infrastructure/overview.md` | Replace simplified `is_safe_webhook_url()` code snippet (~10 lines) with reference to full implementation in `app/utils.py:383-485` (~100 lines) |
| 2.3.6 | Fix S3 error handling claim | `architecture/infrastructure/storage.md` | `save()` raises exceptions, does NOT return False — unlike other S3 methods which have try/except |
| 2.3.7 | Add missing webhook fields | `architecture/infrastructure/webhooks.md` | Add `successful_deliveries` and `failed_deliveries` fields to WebhookEvent model docs |

### 2.4 Services Documentation

| # | Task | File | Description |
|---|------|------|-------------|
| 2.4.1 | Fix backup silent fallback | `architecture/services/backup.md` | "Silent fallback" section contradicts code — TWO warnings ARE logged: `_encrypt_backup_file` at `backup.py:107-110` and `create_backup` at `backup.py:69-71`. Fix self-contradictory documentation. |
| 2.4.2 | Remove config.toml encryption claim | `architecture/services/backup.md` | Key is loaded ONLY from `BACKUP_ENCRYPTION_KEY` env var (`app/backup_encryption.py:40`), NOT from config.toml `[backup]` section. Remove false claim at lines 96, 104. |
| 2.4.3 | Fix search line reference | `architecture/services/search.md` | Case Preservation line reference should be `app/search.py:342-344` (in `get_did_you_mean()`), not `349-351` (which is `highlight_query()`) |
| 2.4.4 | Fix tag line numbers | `architecture/services/tag.md` | `get_tag_by_slug`: 32 not 34; `get_all_tags`: 37 not 41; `delete_tag_if_unused`: 55 not 58; `get_tag_post_count`: 42 not 48 |
| 2.4.5 | Fix tag_cache line numbers | `architecture/services/tag_cache.md` | `_get_tag_counts_cached`: 32 not 30; `_get_tag_counts`: 39 not 37; `_get_tag_counts_uncached`: 46 not 44; `invalidate_tag_cache`: 52 not 50 |
| 2.4.6 | Fix duplicate encryption entries | `architecture/services/overview.md` | Merge duplicate "Encryption" and "Encryption (TOTP)" rows (both point to `app/services/encryption.py`) |

### 2.5 Deployment Documentation

| # | Task | File | Description |
|---|------|------|-------------|
| 2.5.1 | Fix docker e2e wait | `architecture/deployment/cicd.md` | e2e wait command is `docker compose wait blog` (`.github/workflows/ci.yml:150`), not `redis` |
| 2.5.2 | Fix security headers | `architecture/deployment/security.md` | `X-Download-Options: noopen` and `X-Permitted-Cross-Domain-Policies: none` ARE set by Flask (`app/__init__.py:340-341`) — update docs to reflect this |
| 2.5.3 | Fix backup profile description | `architecture/deployment/docker.md` | Backup profile contains only the `backup` service (`docker-compose.yml:136-137`), not `blog` |
| 2.5.4 | Fix "no warning logged" claim | `architecture/deployment/docker.md` | `backup.py:69-70` DOES log WARNING: `"Backup encryption failed, proceeding without encryption"` |
| 2.5.5 | Document CSP differences | `architecture/deployment/security.md` | Nginx CSP uses `script-src 'self' 'unsafe-inline'` while Flask CSP uses `script-src 'self' 'nonce-{nonce}'` — nginx overrides the more secure nonce-based policy |

### 2.6 Tasks Documentation

| # | Task | File | Description |
|---|------|------|-------------|
| 2.6.1 | Fix newsletter error handling | `architecture/tasks/celery-tasks.md` | `send_newsletter_task` does NOT call `self.retry()` (`app/tasks.py:144-191`) — it has a bare `try/finally` with no `except` block. On `send_newsletter()` returning False, it increments `newsletter_attempts` and returns False. Celery auto-retry only on uncaught exceptions. |
| 2.6.2 | Remove duplicate webhook section | `architecture/tasks/celery-tasks.md` | Remove duplicate `deliver_single_webhook_task` section (lines 79-100 duplicate lines 64-100) |
| 2.6.3 | Document newsletter retry gap | `architecture/tasks/celery-tasks.md` | `send_newsletter_task` does NOT check `NEWSLETTER_MAX_RETRY_ATTEMPTS` (unlike scheduler path at `app/scheduler.py:118`). Document why — Celery task sends for all posts, scheduler filters by attempts. |
| 2.6.4 | Fix scheduler log message | `architecture/tasks/scheduler.md` | Fix log message template to match actual code: `"Could not acquire lock %s, skipping run"` (`app/scheduler.py:80`) |
| 2.6.5 | Document delivery status race | `architecture/tasks/scheduler.md` | Document that `_update_delivery_status` correctness depends on `--concurrency=1` (`docker-compose.yml:66`) and the race condition risk if concurrency is increased |

### 2.7 Overview Documentation

| # | Task | File | Description |
|---|------|------|-------------|
| 2.7.1 | Add ApiToken to schema | `architecture/overview.md` | Add `api_tokens` to database tables list and ApiToken to ER diagram (`app/models.py:625-657`) |
| 2.7.2 | Expand API Auth | `architecture/overview.md` | Expand API Auth to cover two-tier system: legacy `API_KEY` env var + scoped `ApiToken` model with `require_scope()` decorator |
| 2.7.3 | Fix Three-Way Path | `architecture/overview.md` | Fix heading "Newsletter Three-Way Path" to "Newsletter Delivery Paths" — only two paths are described |
| 2.7.4 | Document CSRF | `architecture/overview.md` | Document CSRF global enforcement via `before_request_handler()` (`app/__init__.py:296-298`) |
| 2.7.5 | Add encryption modules | `architecture/overview.md` | Add `app/backup_encryption.py` and `app/webhook_encryption.py` to services table |
| 2.7.6 | Complete source list | `architecture/overview.md` | Add `cli.py` and `validators.py` to Core Application source list |
| 2.7.7 | Add Docker profiles | `architecture/overview.md` | Add Docker Compose profiles requirement (`--profile production`, `--profile backup`) to Deployment section |
| 2.7.8 | Add APScheduler warning | `architecture/overview.md` | Add multi-container limitation warning (FileLock `timeout=0` only works on single machine) to Task Processing section |
| 2.7.9 | Document newsletter retry | `architecture/overview.md` | Document retry count (5) and path differences between Celery (no attempt check) and scheduler (checks `NEWSLETTER_MAX_RETRY_ATTEMPTS`) |

---

## Wave 3: Medium Priority Improvements

**Goal:** Improve documentation completeness, fix minor bugs, and clean up code.
**Parallelizable:** Yes — items are independent.
**Depends on:** Wave 2 (documentation corrections must be done first).
**Verification:** Same as Wave 1.

### 3.1 Source Code Improvements

| # | Task | File | Line(s) | Description |
|---|------|------|---------|-------------|
| 3.1.1 | Add rate limit to metrics | `app/routes/public/meta.py` | — | Add `@limiter.limit("60 per minute")` to `GET /metrics` route to match other meta routes |
| 3.1.2 | Consolidate _save_revision | `app/routes/admin/posts/` | — | Remove duplicate `_save_revision()` from `editor.py:36-46` and `manage.py:34-44`. Keep only the one in `revisions.py:32-42`. Update imports. |
| 3.1.3 | Remove dead RSS code | `app/routes/rss.py` | 52-57 | Remove `_get_cached_feed_posts()` — never called, delegates to atom cache, misleading |
| 3.1.4 | Add error handling to delete_post | `app/routes/admin/manage.py` | 88 | Add `try/except (IntegrityError, OperationalError)` around `db.session.commit()` after `db.session.delete(post)` |
| 3.1.5 | Fix newsletter retry count doc | `app/tasks.py` | — | Document that `_send_email_with_retry` default `max_retries=3` (`app/email.py:111`) vs newsletter override to 5 (`app/config.py:119`) |
| 3.1.6 | Fix backup timezone | `app/services/backup.py` | 49 | Change `datetime.now()` to `datetime.now(timezone.utc)` to match `run_daily_backup` at line 181 |
| 3.1.7 | Remove ENABLE_SCHEDULER | `app/config.py` | 55 | Remove `ENABLE_SCHEDULER` from `__all__` — it is never assigned or read anywhere in the codebase |
| 3.1.8 | Add FTS locking | `app/search.py` | 43-55 | Add `threading.Lock()` to `_check_fts_enabled()` module-level globals for thread safety in multi-threaded WSGI servers |
| 3.1.9 | Fix FTS init destructive behavior | `app/search.py` | 88-98 | Make `init_fts()` less destructive on transient failures — currently drops FTS table on any error, destroying working index |
| 3.1.10 | Fix highlight_query escaping | `app/search.py` | 349-364 | Review `highlight_query()` for double-escaping of already-escaped HTML (calls `html.escape()` then applies regex) |
| 3.1.11 | Document Celery concurrency | `architecture/tasks/scheduler.md` | — | Document that Celery worker runs with `--concurrency=1` and `worker_prefetch_multiplier=1` as production requirements |
| 3.1.12 | Remove e2e dead code | `tests/e2e/conftest.py` | 64-66 | Remove dead `tmp_path_factory.mktemp` and env var override — has no effect because Flask app is already configured by `app` fixture |
| 3.1.13 | Replace e2e sleep | `tests/e2e/conftest.py` | 97 | Replace `time.sleep(1)` with readiness polling (attempt connection in loop with timeout) |
| 3.1.14 | Fix mock_email description | `tests/conftest.py` | — | Remove "autouse" claim about mock_render and mock_smtp — they are function-scoped and explicitly requested |
| 3.1.15 | Fix cleanup_uploads | `tests/conftest.py` | 186-189 | Handle subdirectories in `cleanup_uploads` — currently only removes files at top level, leaking subdirectories |

### 3.2 Documentation Additions

| # | Task | File | Description |
|---|------|------|-------------|
| 3.2.1 | Document marked.min.js pattern | `architecture/frontend/static-assets.md` | Document loading pattern (outside Vite pipeline via `url_for`) and its limitations (no content hashing, no CDN) |
| 3.2.2 | Document template partials | `architecture/frontend/templates.md` | Document `prefetch.js` (intelligent link prefetching), `macros.html` (pagination, field_error macros), `_post_content.html` (post hero, share bar, TL;DR, markdown body), `_error.html` (error pages), `_sidebar.html` (recent posts/tags), `_breadcrumbs.html` (admin navigation) |
| 3.2.3 | Fix static-assets file names | `architecture/frontend/static-assets.md` | Fix Public JS / Admin JS sections — actual public JS files: `anchor-links.js`, `code-copy.js`, `lightbox.js`, `media-copy.js`, `search.js`, `share.js`, `toc.js` (no `comments.js` or `newsletter.js`) |
| 3.2.4 | Update static-assets line ref | `architecture/frontend/static-assets.md` | Update vite.config.js JSX line reference from 31-39 to 36-44 |
| 3.2.5 | Document Page View Buffer | `architecture/core/app-factory.md` | Document flush size (`PAGE_VIEW_BUFFER_SIZE`), interval (5s default at `app/page_view_buffer.py:30`), and shutdown behavior (final flush on `stop()`) |
| 3.2.6 | Document tag cache | `architecture/core/app-factory.md` | Document tag cache mechanism via `app/tag_cache.py` with configurable TTL |
| 3.2.7 | Document footer exclusion | `architecture/core/app-factory.md` | Document path-based footer exclusion logic: `/admin`, `/api`, `/rss` paths get empty footer data |
| 3.2.8 | Document admin helpers | `architecture/routes/admin-routes.md` | Document the `helpers/` directory with 9 submodules |
| 3.2.9 | Document comment spam | `architecture/routes/public-routes.md` | Document comment spam scoring system (`compute_spam_score`), thresholds, heuristics, auto-quarantine at 0.7 |
| 3.2.10 | Document archive pagination | `architecture/routes/public-routes.md` | Document cursor-based pagination parameters (cursor, direction, year query params) |
| 3.2.11 | Document newsletter test vs preview | `architecture/routes/admin-routes.md` | Clarify: preview renders HTML in-browser, test sends actual email |
| 3.2.12 | Document Celery configuration | `architecture/deployment/docker.md` | Document task_time_limit=300, task_soft_time_limit=240, worker_max_tasks_per_child=100 (`app/celery_app.py:27-30`) |
| 3.2.13 | Document CI pipeline | `architecture/deployment/cicd.md` | Document dependency chain: lint-and-type -> test -> e2e-tests; docker-build -> e2e-tests |
| 3.2.14 | Add FakeSubscriber docs | `architecture/testing/test-suite.md` | Document `FakeSubscriber` dataclass (`tests/conftest.py:60-69`) |
| 3.2.15 | Document search functions | `architecture/infrastructure/search.md` | Add `init_fts()`, `_check_fts_enabled()`, `extract_snippet()`, `get_indexed_terms()` to module-level functions table |
| 3.2.16 | Document exception classes | `architecture/services/*.md` | Document `EncryptionError` (`app/services/encryption.py:16-19`), `WebhookEncryptionError` (`app/webhook_encryption.py:16-19`), and `ConfigurationError` (`app/services/search/__init__.py:7-10`) |
| 3.2.17 | Document backup params | `architecture/services/backup.md` | Document mutual exclusivity of `compress` and `encrypt` parameters (code uses `elif` at `backup.py:72`) |
| 3.2.18 | Document highlight_query | `architecture/infrastructure/search.md` | Document HTML escaping behavior — `highlight_query()` calls `html.escape()` before applying `<mark>` tags |

---

## Wave 4: Low Priority Cleanup

**Goal:** Remove dead code, fix style issues, and address minor concerns.
**Parallelizable:** Yes — items are independent.
**Depends on:** Wave 3.
**Verification:** Same as Wave 1.

### 4.1 Dead Code Removal

| # | Task | File | Line(s) | Description |
|---|------|------|---------|-------------|
| 4.1.1 | Remove init_storage dead code | `app/storage.py` | 280-284 | `init_storage()` is defined and documented but never called — storage always accessed via `get_storage()` singleton |
| 4.1.2 | Remove legacy _has_gnupg | `app/backup_encryption.py` | 86-88 | Remove or rename misleading `_has_gnupg()` function (just returns `CRYPTOGRAPHY_AVAILABLE`) |
| 4.1.3 | Remove unnecessary SQLAlchemyError | `app/backup_encryption.py` | — | Remove `SQLAlchemyError` from exception handlers in standalone encryption functions (no SQLAlchemy dependency needed) |
| 4.1.4 | Remove _get_cached_feed_posts | `app/routes/rss.py` | 52-57 | Dead code that delegates to atom cache, never called |
| 4.1.5 | Remove unused vite-plugin-beasties | `vite.config.js` | — | Listed in `package.json` but `plugins: []` is empty |
| 4.1.6 | Remove redundant env var declarations | `tests/` | — | Remove redundant SECRET_KEY/ADMIN_PASSWORD from `test_context_processors.py:3-4`, `test_search.py:3-4`, `test_api.py:6-9` (already set in `conftest.py:8-11`) |
| 4.1.7 | Remove redundant fixture overrides | `tests/` | — | Remove from `test_context_processors.py` and `test_search.py` unless documented as intentional |

### 4.2 Style & Documentation Cleanup

| # | Task | File | Description |
|---|------|------|-------------|
| 4.2.1 | Add .svg loader to docs | `architecture/frontend/static-assets.md` | Add `.svg: 'text'` loader to vite.config.js code example (actual code at `vite.config.js:41`) |
| 4.2.2 | Fix Prism data attribute doc | `architecture/frontend/templates.md` | Document `data-prism-css-url` attribute on `<html>` element and its role in Prism lazy loading |
| 4.2.3 | Add loadPrismIfNeeded guard | `app/static/js/admin.js` | Add guard to check `window.Prism` existence before creating script elements (prevents double-loading) |
| 4.2.4 | Consider search sanitization | `app/search.py` | Add nh3 clean on FTS5 snippets before rendering with `| safe` in `search.html:52` |
| 4.2.5 | Document CI pip-audit | `architecture/deployment/cicd.md` | Note pip-audit uses `--fail-on=all` (strict mode) at `.github/workflows/ci.yml:97` |
| 4.2.6 | Document nginx XSS header | `architecture/deployment/docker.md` | Note nginx `X-XSS-Protection` only present when proxied through nginx (Flask does not set it) |
| 4.2.7 | Note healthcheck timeout diff | `architecture/deployment/docker.md` | Dockerfile healthcheck timeout (3s) differs from docker-compose override (10s) |
| 4.2.8 | Add start_period | `Dockerfile` | Add `--start-period=10s` to HEALTHCHECK or document the omission |
| 4.2.9 | Add SECRET_KEY to backup | `docker-compose.yml` | Add SECRET_KEY to backup service environment if needed by app imports |
| 4.2.10 | Document email retry arch | `architecture/infrastructure/email.md` | Document retry architecture (3 default at `app/email.py:111` vs 5 for newsletter at `app/config.py:119`) |
| 4.2.11 | Document search fallback | `architecture/infrastructure/search.md` | Document `get_indexed_terms()` fallback path (`app/search.py:230-243`) |
| 4.2.12 | Move _SQLITE_MAX_VARS | `architecture/infrastructure/search.md` | Move out of module-level constants code block — it is local to `get_search_snippets()` at `app/search.py:291` |
| 4.2.13 | Document init_fts error | `architecture/infrastructure/search.md` | Document `init_fts()` destructive error handling (drops FTS table on failure at `app/search.py:91`) |
| 4.2.14 | Document silent webhook fail | `architecture/infrastructure/webhooks.md` | Document that `create_webhook_event()` silently swallows Celery queue failures (`app/webhooks.py:112`) — event exists but never delivered |
| 4.2.15 | Move api_client | `tests/` | Move `api_client` from `test_api.py:17` to conftest.py (or clarify it is test-local) |
| 4.2.16 | Add Celery eager config | `tests/conftest.py` | Add Celery eager config to `test_context_processors.py` app fixture (latent risk) |
| 4.2.17 | Apply pytest markers | `tests/` | Apply `@pytest.mark.e2e` and `@pytest.mark.slow` to appropriate tests (markers registered but never used) |
| 4.2.18 | Remove username from log | `app/routes/admin/auth.py` | Line 247: remove `username=%s` from log line for PII compliance (codebase rule: log ID, not username) |
| 4.2.19 | Add try/except to subscribe | `app/routes/public/subscribe.py` | Lines 74,82,114,143: add `try/except` guard on `db.session.commit()` where not already wrapped |

---

## Wave 5: Architecture Pruning

**Goal:** Delete, rewrite, or merge stale architecture documentation.
**Parallelizable:** Partially — rewrites can be parallelized, merges must be sequential.
**Depends on:** Waves 2-4 (source code fixes and doc corrections must be done first to know correct state).
**Verification:** Read modified files end-to-end to ensure internal consistency.

### 5.1 Full Rewrites

| # | Task | File | Description |
|---|------|------|-------------|
| 5.1.1 | Rewrite E2E testing docs | `architecture/testing/test-suite.md` | Full rewrite of E2E section: fix false claims about app fixture (it DOES exist in e2e/conftest.py:11-43), fix playwright claim (IS in requirements.txt:18-19), fix mock_email description (not autouse), add FakeSubscriber docs, update marker usage status |
| 5.1.2 | Rewrite public routes | `architecture/routes/public-routes.md` | Remove phantom routes `/page/<page>` and `/tag/<slug>/<page>`, fix health check `?detailed=true`, relocate short URL doc |
| 5.1.3 | Rewrite admin routes | `architecture/routes/admin-routes.md` | Fix route paths, remove phantom revision route, relocate Markdown Preview section, add helpers/ directory |

### 5.2 Merges

| # | Task | File(s) | Description |
|---|------|---------|-------------|
| 5.2.1 | Merge infrastructure overview | `architecture/infrastructure/overview.md` -> `architecture/overview.md` | Merge unique content (health check details, search provider architecture) into main overview, delete sub-module file |
| 5.2.2 | Fix services overview duplicates | `architecture/services/overview.md` | Deduplicate "Encryption" entries |

### 5.3 Stale Line References

Fix line number references that have drifted in:
- `architecture/infrastructure/search.md` — search.py:349-351 should be 342-344
- `architecture/services/tag.md` — 4 functions with wrong line numbers
- `architecture/services/tag_cache.md` — 4 functions with wrong line numbers
- `architecture/infrastructure/webhooks.md` — tasks.py:333,354 should be 344,365
- `architecture/deployment/docker.md` — docker-compose.yml:58 should be 66; 111-129 should be 119-137
- `architecture/core/configuration.md` — config.py:164-171 should be 165-172
- `architecture/frontend/static-assets.md` — vite.config.js:31-39 should be 36-44

---

## Wave 6: AGENTS.md Cleanup

**Goal:** Update agent documentation to reflect current state.
**Parallelizable:** No — must be done after all other waves.
**Depends on:** All previous waves.

### 6.1 AGENTS.md Updates

| # | Task | Description |
|---|------|-------------|
| 6.1.1 | Remove outdated e2e claim | Remove outdated claim about e2e/conftest.py not defining app fixture |
| 6.1.2 | Add template context vars | Add `site_title` and `site_description` as context variables (NOT `site_name` or `site_tagline`) |
| 6.1.3 | Add template filters | Add actual filters: `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`, `post_image_avif_url_stub` |
| 6.1.4 | Add Critical CSS note | Document `critical.css` file and its loading in `base.html:24` |
| 6.1.5 | Add Docker profiles | Document that all services require explicit profiles (no default profile) |
| 6.1.6 | Add CI workflow location | Document CI workflow is at `.github/workflows/ci.yml` with 6 jobs |
| 6.1.7 | Add Webhook delivery arch | Document two-level dispatch pattern |
| 6.1.8 | Add model count | Document exactly 17 model classes in `app/models.py` |
| 6.1.9 | Add thread-safe storage | Document `get_storage()` double-checked locking pattern |
| 6.1.10 | Add E2E test isolation | Document session-scoped `app` fixture and dead code in E2E `app_server` fixture |
| 6.1.11 | Add Login template assets | Document `admin/login_base.html` uses `vite_asset()` for CSS/JS assets |
| 6.1.12 | Add Prism CSS loading | Document Prism CSS loaded via `data-prism-css-url` attribute |
| 6.1.13 | Add Session IP Binding | Document enforcement via `admin_required` decorator, not global handler |
| 6.1.14 | Add Silent FTS init | Document `OperationalError` catch during FTS init silently |
| 6.1.15 | Add LOGIN_FAILURE_DELAY | Document minimum 0.1s enforced in `app/config.py` |
| 6.1.16 | Add Comment Rate Limit | Document X-Forwarded-For header bypass limitation |
| 6.1.17 | Add APScheduler limitation | Document FileLock with `timeout=0` only works on single machine |
| 6.1.18 | Add Vite build required | Document `npm run build` must be run before production deployment |
| 6.1.19 | Add SMTP handling | Document that only daily newsletter job is disabled when SMTP_HOST not configured |
| 6.1.20 | Add Email retry count | Document newsletter retry count default is 5 (not 3) |

### 6.2 AGENTS.override.md Updates

| # | Task | File | Description |
|---|------|------|-------------|
| 6.2.1 | Update plans override | `plans/AGENTS.override.md` | Update to reflect consolidated plan status |

---

## Implementation Strategy

### Parallel Execution Plan

```
Wave 1 (Critical) ─────────────────────────────────────────────────────────┐
  ├─ Sub-Agent 1: Security fixes (1.1.1-1.1.5)                          │
  ├─ Sub-Agent 2: RSS + Frontend fixes (1.2.1, 1.3.1-1.3.3)             │
  └─ Sub-Agent 3: Test standardization (1.4.1-1.4.3)                     │
                                                                           │
Wave 2 (High Priority Docs) ──────────────────────────────────────────────┤
  ├─ Sub-Agent 1: Core + Route docs (2.1, 2.2)                           │
  ├─ Sub-Agent 2: Infrastructure + Services docs (2.3, 2.4)              │
  └─ Sub-Agent 3: Deployment + Tasks + Overview docs (2.5, 2.6, 2.7)     │
                                                                           │
Wave 3 (Medium Priority) ─────────────────────────────────────────────────┤
  ├─ Sub-Agent 1: Source code improvements (3.1)                          │
  └─ Sub-Agent 2: Documentation additions (3.2)                           │
                                                                           │
Wave 4 (Low Priority) ────────────────────────────────────────────────────┤
  ├─ Sub-Agent 1: Dead code removal (4.1)                                 │
  └─ Sub-Agent 2: Style cleanup (4.2)                                     │
                                                                           │
Wave 5 (Architecture Pruning) ────────────────────────────────────────────┤
  ├─ Sub-Agent 1: Full rewrites (5.1)                                     │
  └─ Sub-Agent 2: Merges + stale refs (5.2, 5.3)                         │
                                                                           │
Wave 6 (AGENTS.md Cleanup) ───────────────────────────────────────────────┘
  └─ Sub-Agent 1: AGENTS.md + AGENTS.override.md updates (6.1, 6.2)
```

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
- 2.1.1-2.1.10, 2.2.1-2.2.7, 2.3.1-2.3.7, 2.4.1-2.4.6, 2.5.1-2.5.5, 2.6.1-2.6.5, 2.7.1-2.7.9

### Wave 3: 33 tasks
- 3.1.1-3.1.15, 3.2.1-3.2.18

### Wave 4: 26 tasks
- 4.1.1-4.1.7, 4.2.1-4.2.19

### Wave 5: 12 tasks
- 5.1.1-5.1.3, 5.2.1-5.2.2, 5.3 (7 files)

### Wave 6: 21 tasks
- 6.1.1-6.1.20, 6.2.1

**Total: 152 tasks**
