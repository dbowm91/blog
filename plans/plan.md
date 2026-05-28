# Implementation Plan - Blog CMS Architecture Documentation Fixes

**Project:** Blog CMS
**Status:** IN PROGRESS
**Last Updated:** May 28, 2026

---

## Overview

Consolidated plan from architecture reviews of all 8 modules. Reviews conducted May 9, 2026. Previous documentation waves (A-F, 43 items) completed May 22, 2026. Plan updated May 28, 2026 with codebase verification.

This plan organizes items into **parallelizable waves**. Each wave can run subagents concurrently. All items are documentation-only — no code changes required (except one fixed inaccuracy in search.md, addressed separately).

---

## Deferred Items

### Per-Webhook Retry

**Status:** Not implemented - would require significant refactoring

- **Location:** `app/tasks.py:234-246`
- **Current behavior:** Failed webhooks are logged but silently skipped
- **Documentation:** Acknowledged in `architecture/tasks/celery-tasks.md` and `architecture/infrastructure/webhooks.md`
- **Reason deferred:** `deliver_webhook_task` catches `requests.RequestException` without calling `self.retry()`, so Celery's `max_retries=3` never triggers. Per-webhook retry would require significant refactoring to track individual webhook state.

---

## Wave 1: All Documentation Fixes (Parallel) — Run All Subagents Concurrently

**Strategy:** Launch all subagents in parallel since documentation edits target different files with no dependencies between them. Each subagent works on its own module's documentation files.

### Wave 1A: Core Module Fixes

**Target files:** `architecture/core/models.md`

**Subagent instructions:** Read each target file, read the actual source code, fix inaccuracies, add missing documentation. Verify all claims before writing.

| ID | Priority | Issue | Action |
|----|----------|-------|--------|
| C-3 | HIGH | `models.md` overview table line 9 documents `totp_secret` as column | Fix: change `totp_secret` to `totp_secret_encrypted` in overview table. The `totp_secret` is a `@property` that decrypts on access (see `app/models.py:33,43-52`) |
| C-4 | MEDIUM | `models.md` User Model Details missing backup code methods | Add `generate_backup_codes()` and `verify_backup_code()` methods to User model methods list (actual code at `app/models.py:74-94`). Column `backup_codes_hashed` already documented |

**Newly discovered issues (from verification):**

| ID | Priority | Issue | Action |
|----|----------|-------|--------|
| C-8 | HIGH | `models.md` Webhook section shows `secret` as plain-text column | Fix: actual column is `webhook_secret_encrypted` (LargeBinary), with `secret` as `@property` that decrypts via AES-256-GCM. See `app/models.py:490-517`. Document similar to TOTP pattern |
| C-9 | MEDIUM | `models.md` WebhookEvent section missing `delivery_status` field | Add: `delivery_status = db.Column(db.String(32), nullable=True)` with values `'delivered'`, `'partial_failure'`, `'failed'`. See `app/models.py:533` |

**Note:** C-1, C-2, C-5, C-6, C-7 from original plan are **already correct** in documentation — no changes needed.

---

### Wave 1B: Routes Module Fixes

**Target files:** `architecture/routes/admin-routes.md`, `architecture/routes/public-routes.md`, `architecture/routes/api-routes.md`

**Subagent instructions:** For each route correction, read the actual handler file to verify the HTTP method, path, and parameters before editing. Route handler files are in `app/routes/admin/`, `app/routes/public/`, and `app/routes/api/`.

| ID | Priority | Issue | Action |
|----|----------|-------|--------|
| R-1 | HIGH | Preview route path wrong | Fix: actual is `GET /preview/<int:post_id>?token=<token>&expires=<timestamp>` (HMAC-based). Handler: `app/routes/public/posts.py:94-140` |
| R-2 | HIGH | Logout method wrong | Fix: actual is `POST /admin/logout` with CSRF validation. Handler: `app/routes/admin/auth.py:99` |
| R-9 | HIGH | API publish route doesn't exist | Fix: no `POST /api/posts/<id>/publish`. Publish via `PUT /api/posts/<id>` with `{"published": true}` body. Handler: `app/routes/api/posts.py:207` |
| R-10 | HIGH | Rate limits wrong | Fix: actual limits are `DEFAULT_LIMIT = "20 per minute"` (reads), `WRITE_LIMIT = "10 per minute"` (writes). Constants at `app/routes/api/posts.py:18-19` |
| R-4 | MEDIUM | Subscriber export method wrong | Fix: actual is `GET /admin/subscribers/export`. Handler: `app/routes/admin/subscribers.py:83` |
| R-5 | MEDIUM | Tag create path wrong + missing rename | Fix: actual is `POST /admin/tags/create` (line 115) + `POST /admin/tags/rename/<int:tag_id>` (line 40). Handler: `app/routes/admin/tags.py` |
| R-6 | MEDIUM | Media delete method and path wrong | Fix: actual is `POST /admin/media/delete/<filename>`. Handler: `app/routes/admin/media.py:160` |
| R-7 | MEDIUM | Newsletter routes wrong | Fix: actual is `POST /admin/newsletter-test` + `GET /admin/newsletter/preview`. Handlers: `app/routes/admin/newsletter.py:24,70` |
| R-8 | MEDIUM | Settings routes wrong | Fix: actual is `GET /admin/settings` + `POST /admin/settings/theme`. Handlers: `app/routes/admin/settings.py:14,41` |
| R-3 | LOW | Post list path wrong | Fix: actual is `GET /admin/` (dashboard). Handler: `app/routes/admin/posts/__init__.py:51` |

**Missing routes to add to documentation (19 confirmed):**

| ID | Route | Handler Location |
|----|-------|-----------------|
| M-1 | `GET /series/<slug>` | `app/routes/public/browse.py:314` |
| M-2 | `GET /archive` (cursor-based pagination) | `app/routes/public/browse.py:121` |
| M-3 | `GET /s/<code>` (short URL redirect + share tracking) | `app/routes/public/posts.py:142` |
| M-4 | `POST /api/track-share` | `app/routes/public/posts.py:165` |
| M-5 | `POST /admin/bulk` (bulk post operations) | `app/routes/admin/posts/__init__.py:118` |
| M-6 | `POST /admin/delete/<int:post_id>` | `app/routes/admin/posts/manage.py:72` |
| M-7 | `GET /admin/preview/<int:post_id>` + shareable preview | `app/routes/admin/posts/manage.py:97` |
| M-8 | `POST /admin/posts/<int:post_id>/revisions/<int:revision_id>/restore` | `app/routes/admin/posts/revisions.py:75` |
| M-9 | `POST /admin/users/<int:user_id>/make-owner` | `app/routes/admin/users.py:192` |
| M-10 | `POST /admin/users/password/<int:user_id>` | `app/routes/admin/users.py:242` |
| M-11 | `POST /admin/subscribers/bulk` | `app/routes/admin/subscribers.py:121` |
| M-12 | `POST /admin/subscribers/delete/<int:sub_id>` | `app/routes/admin/subscribers.py:56` |
| M-13 | `POST /admin/sessions/revoke/<int:sess_id>` | `app/routes/admin/sessions.py:43` |
| M-14 | `POST /admin/newsletter-reset/<int:post_id>` | `app/routes/admin/auth.py:125` |
| M-15 | `GET/POST /admin/forgot-password` + `GET/POST /admin/reset/<token>` | `app/routes/admin/auth.py:155,198` |
| M-16 | 2FA routes: `/admin/login-2fa`, `/admin/2fa/setup`, `/admin/2fa/verify`, `/admin/2fa/backup-codes`, `/admin/2fa/disable` | `app/routes/admin/auth.py:263,312,349,420,436` |
| M-17 | `GET /metrics` (Prometheus) | `app/routes/public/meta.py:315` |
| M-18 | `GET /favicon.ico` | `app/routes/public/meta.py:183` |
| M-19 | `GET /api/stats` | `app/routes/api/stats.py:17` |

**Removed from plan (verified non-existent):**
- ~~M-20: `POST /api/auth`~~ — `app/routes/api/auth.py` contains only `require_api_key` decorator, no route
- ~~M-21: `POST /api/subscribers/export`~~ — No export endpoint in API; only admin export at `GET /admin/subscribers/export`

---

### Wave 1C: Services Module Fixes

**Target files:** `architecture/services/backup.md`, `architecture/services/serialization.md`, new `architecture/services/tag_cache.md`

**Subagent instructions:** Read actual source files before documenting. For tag cache, create new file `architecture/services/tag_cache.md`.

| ID | Priority | Issue | Action |
|----|----------|-------|--------|
| -- | HIGH | Tag Cache Module undocumented | Create `architecture/services/tag_cache.md` documenting `app/tag_cache.py`: `_get_tag_counts()`, `invalidate_tag_cache()`, TTL config via `TAG_CACHE_TTL_SECONDS`, invalidation triggers. Functions: `_build_tag_counts_query()` (line 16), `_get_tag_counts_cached()` (line 30), `_get_tag_counts()` (line 37), `_get_tag_counts_uncached()` (line 44), `invalidate_tag_cache()` (line 50) |
| -- | MEDIUM | Encryption Module undocumented | Document `app/backup_encryption.py`: PBKDF2-HMAC-SHA256 key derivation (600,000 iterations), 16-byte salt, 32-byte key, 12-byte nonce, AES-256-GCM cipher, min password 12 chars, file format: salt(16) + nonce(12) + ciphertext + tag(16). Also document `app/services/encryption.py` (direct AES-256-GCM, no PBKDF2, uses SECRET_KEY) and `app/webhook_encryption.py` (AES-256-GCM, direct 32-byte key from WEBHOOK_ENCRYPTION_KEY) |
| -- | MEDIUM | Slug Service incomplete | Document: 100 try limit, UUID format (`uuid.uuid4().hex[:8]`), `exclude_id` parameter for collision avoidance. Source: `app/services/slug.py` |
| S-3 | MEDIUM | Decryption output path behavior | Document: for non-`.gpg` files, appends `.decrypted` instead of removing extension. This is the actual behavior at `app/services/backup.py:107-127` |
| S-4 | LOW | Serialization import handling | Document: no `deserialize_*` functions exist; import handled inline in CLI `import-data` command (`app/cli.py:140`). Serialization functions: `serialize_post`, `serialize_subscriber`, `serialize_page`, `serialize_tag`, `export_data_to_dict` |

**Note:** S-2 (naming conventions) already correct in docs — both use `blog_*.db` naming consistently.

---

### Wave 1D: Tasks Module Fixes

**Target files:** `architecture/tasks/celery-tasks.md`, `architecture/tasks/scheduler.md`

**Subagent instructions:** Read actual task implementations before documenting. Key file: `app/tasks.py` for Celery tasks, `app/scheduler.py` for APScheduler jobs.

| ID | Priority | Issue | Action |
|----|----------|-------|--------|
| T-4 | HIGH | `send_daily_newsletter` behavior wrong | Fix: `app/scheduler.py:70-162` calls `send_newsletter()` synchronously from `app.email`, NOT via Celery. Celery `send_newsletter_task` is for manual/ad-hoc sends only. Update scheduler.md to clarify this distinction |
| T-3 | MEDIUM | APScheduler "Queue Routing" section misleading | Fix: APScheduler jobs are in-process direct function calls, not Celery queues. Remove or rename any section suggesting queue routing. See `app/scheduler.py` module docstring for multi-worker limitation docs |
| T-2 | MEDIUM | `run_backup_task` parameters not documented | Add: hardcoded params `compress=True, keep=7, encrypt=False` passed to `create_backup()`. Task takes no arguments beyond `self`. Creates `blog_*.db` files. See `app/tasks.py:305-321` |
| -- | MEDIUM | Missing backup implementation comparison | Add table comparing APScheduler backup (`app/scheduler.py:run_daily_backup`, calls `app.services.backup.run_daily_backup`, uses FileLock with `backup.lock`) vs Celery backup (`app/tasks.py:run_backup_task`, calls `app.services.backup.create_backup`, AES-256-GCM encryption). Both use `blog_*.db` naming |
| -- | MEDIUM | Missing FileLock documentation | Document FileLock usage in scheduler: `newsletter.lock`, `cleanup.lock`, `scheduled.lock`, `backup.lock`. `timeout=0` means non-blocking (fail immediately if locked). See `app/scheduler.py` |

**Note:** TM-1 (missing NEWSLETTER_MAX_RETRY_ATTEMPTS) and TM-2 (missing FTS sync in publish_scheduled_posts) from original plan are **incorrect claims** — both features already exist. Removed from plan.

---

### Wave 1E: Deployment Fixes

**Target files:** `architecture/deployment/docker.md`, `architecture/deployment/security.md`, `architecture/deployment/cicd.md`

**Subagent instructions:** Read actual Docker and nginx configs before documenting. Key files: `Dockerfile`, `docker-compose.yml`, `nginx/nginx.conf`, `nginx/conf.d/blog.conf`.

| ID | Priority | Issue | Action |
|----|----------|-------|--------|
| DEP-1 | HIGH | backup.py working directory | Document: backup service uses `working_dir: /home/blog` in docker-compose.yml (line 109) with volume mount `blog_data:/home/blog/instance:ro`. The relative path `instance/blog.db` resolves from working_dir. See `backup.py:24` |
| -- | HIGH | Missing nginx security headers | Document present headers: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, `Content-Security-Policy`, `Strict-Transport-Security`, `Cross-Origin-Opener-Policy: same-origin`, `Permissions-Policy`. Document MISSING: `X-Download-Options`, `X-Permitted-Cross-Domain-Policies`. Source: `nginx/conf.d/blog.conf:25-32` |
| -- | MEDIUM | Missing rate limiting zones | Document nginx zones: `login` at `rate=5r/m burst=5 nodelay`, `admin` at `rate=20r/m burst=10 nodelay`. Source: `nginx/nginx.conf:48-49` |
| -- | MEDIUM | Missing SSL certificate documentation | Add: Let's Encrypt paths referenced in nginx config (`/etc/letsencrypt/live/blog.example.com/`) but no setup/renewal docs exist. Document gap |
| -- | LOW | Brotli configuration status | Document: Brotli settings present but commented out in `nginx/nginx.conf:26-34`. Requires custom nginx image with `--with-http_brotli_module` |
| DEP-2 | LOW | nginx master process root | Document: nginx master process runs as root (standard nginx:alpine behavior), worker processes run as `nginx` user per `nginx.conf:1`. App container runs as `blog` user |

**Note:** DEP-5 (Celery production docs) already exist in docker.md lines 52-68. DEP-6 (Redis image tag) no discrepancy — both use `redis:7-alpine`. Removed from plan.

---

### Wave 1F: Infrastructure Fixes

**Target files:** `architecture/infrastructure/search.md`, `architecture/infrastructure/webhooks.md`, `architecture/infrastructure/overview.md`

**Subagent instructions:** Read actual implementation files. Key files: `app/services/search/`, `app/search.py`, `app/utils.py:312-414`, `app/webhook_encryption.py`.

| ID | Priority | Issue | Action |
|----|----------|-------|--------|
| INF-1 | HIGH | Search abstraction description wrong | Fix: `architecture/infrastructure/search.md:12` says `SQLiteSearchProvider` "Wraps `app/search.py` FTS5 implementation." This is INCORRECT. The two are SEPARATE implementations. `app/search.py` has standalone FTS5 functions. `SQLiteSearchProvider` in `app/services/search/sqlite.py` has its own implementation. They are NOT a wrapping relationship. Update description to say `SQLiteSearchProvider` provides its own FTS5 implementation through the `SearchProvider` interface |
| INF-2 | MEDIUM | SSRF protection not documented in webhooks | Add: `is_safe_webhook_url()` in `app/utils.py:312-414` performs: scheme validation (http/https only), userinfo blocking, hostname resolution via `socket.getaddrinfo`, loopback/private/link-local/reserved/multicast IP blocking, AWS/GCP metadata endpoint blocking, IPv4-mapped IPv6 checking, `ip.is_global` verification. Called from `app/tasks.py:213-218` and `app/webhooks.py:64-68`. Also: `allow_redirects=False` in task prevents redirect-based SSRF |
| INF-3 | MEDIUM | Health check critical checks | Already documented in `overview.md`. Verify: critical checks are `database`, `scheduler`, `search`, `disk_space`, `db_integrity`. Optional checks (`backup_freshness`, `email`, `redis`, `celery`) don't affect overall status. Source: `app/routes/public/meta.py:286-294` |
| -- | LOW | S3 Storage Backend | Document: `app/storage.py` has `StorageBackend(ABC)`, `LocalStorageBackend`, `S3StorageBackend`. S3 config from env vars (`S3_BUCKET`, `S3_REGION`, `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_PUBLIC_URL`). Lazy client init with `threading.Lock`. `get_storage()` returns module-level singleton. Error handling: methods return `False` or empty lists on failure |

---

### Wave 1G: Testing Fixes

**Target files:** `architecture/testing/test-suite.md`

**Subagent instructions:** Read actual test directory structure and fixture files before documenting.

| ID | Priority | Issue | Action |
|----|----------|-------|--------|
| -- | HIGH | Non-existent directories documented | Fix: `tests/unit/` and `tests/integration/` do NOT exist. Tests are in flat structure at `tests/` root. Note: `tests/test_integration.py` exists as a single file, not a directory |
| -- | HIGH | E2E file structure wrong | Fix: single file `tests/e2e/test_e2e.py` with 4 classes (`TestAdminLogin`, `TestPostCreation`, `TestNewsletterSubscription`, `TestMobileResponsiveness`), NOT separate files |
| -- | HIGH | Missing fixtures documentation | Add: `sample_post`, `sample_tag`, `sample_subscriber`, `mock_render`, `mock_smtp`, `mock_email`, `clean_analytics_cache`, `cleanup_uploads`, `ensure_buffer_disabled`. Sources: `tests/conftest.py`, `tests/shared_fixtures.py` |
| -- | MEDIUM | Missing E2E configuration section | Document: `pytest-playwright` requirement (not in committed requirements — must be installed separately via `pip install pytest-playwright && playwright install chromium`). E2E conftest uses `page` fixture (pytest-playwright convention). CI runs on port 5010 |
| -- | MEDIUM | Missing test patterns | Document: SQLAlchemy 2.0 patterns (`select(Model).filter()`, `db.paginate()`). `db.session.refresh()` fails if object not in session — re-query instead |
| -- | LOW | Missing command reference | Add: `ADMIN_PASSWORD=test SECRET_KEY=test .venv/bin/python3 -m pytest tests/` with `--ignore=tests/e2e` to exclude E2E. `--collect-only` for test count |

---

### Wave 1H: Frontend Fixes

**Target files:** `architecture/frontend/templates.md`, `architecture/frontend/static-assets.md`, `architecture/frontend/overview.md`

**Subagent instructions:** Read actual template and JS files before documenting.

| ID | Priority | Issue | Action |
|----|----------|-------|--------|
| -- | HIGH | Missing `post_image_avif_url_stub` filter | Add to filter list in `templates.md`. Filter at `app/filters.py:75-85`, registered as `post_image_avif_url_stub`, DEPRECATED — always returns `None`. No templates currently use it |
| -- | HIGH | Incorrect context processor variable names | Fix: `site_name` → `site_title`, `site_tagline` → `site_description` in `templates.md`. Source: `app/context_processors.py:151-161`. Templates use `{{ site_title }}` and `{{ site_description }}` |
| -- | MEDIUM | CSS architecture undocumented | Add: file aggregation via Vite, dark mode as default with `data-theme` attribute toggle + `localStorage` persistence + `prefers-color-scheme` media query, `critical.css` for above-the-fold CSS (loaded in `base.html:22` with `media="screen"`), font self-hosting (Inter, JetBrains Mono). 6 Prism.js themes available via `SiteSettings.syntax_theme` |
| -- | MEDIUM | JavaScript module system undocumented | Add: ES modules with Vite, `export default initXxx` convention, `import.meta.glob()` for dynamic loading (`main.js:6`), route-based code splitting via `ROUTE_MODULES` map (`main.js:30`), `mobile-menu.jsx` as JSX (Vite esbuild handles it) |
| -- | MEDIUM | Vite asset helper undocumented | Document `vite_asset()` in `app/vite.py:47`, content hashing, manifest file, CDN_URL prefix support. Registered as Jinja2 global. Used in `base.html` for all CSS/JS/font references |
| -- | MEDIUM | Lazy image progressive enhancement undocumented | Document CSS pattern: `app/static/js/shared/lazy-load.js` checks native `loading` support first (line 3), falls back to `IntersectionObserver` polyfill (line 8), ultimate fallback loads all lazy images immediately (line 10). Uses `data-src` attribute |
| -- | LOW | Vite chunk split | Document actual chunks: vendor (vue/lodash), admin, public splits via `manualChunks` in `vite.config.js` |

---

## Wave 2: Verification & Cleanup

After Wave 1 completes:

1. **Verify all documentation changes** — spot-check that fixes match actual code
2. **Run any available documentation linting** — check for broken links, formatting
3. **Update this plan** — mark completed items with ✅
4. **Archive or prune** — remove completed items, keep only deferred items

---

## Notes for Future Agents

### Verification Steps
When updating line numbers in documentation, verify against actual source:
- Use `grep -n` or read the file directly to confirm current line numbers
- Line numbers change with code modifications; use functional descriptions when possible

### Context for Implementation
- **Search Provider Architecture**: `app/search.py` module-level functions are SEPARATE from the `SearchProvider` abstraction. `SQLiteSearchProvider` in `app/services/search/sqlite.py` is NOT a wrapper — it has its own implementation. See `app/services/search/__init__.py` for the abstraction.
- **Celery Tasks**: Verify task behavior in `app/tasks.py` before documenting error handling
- **Frontend Templates**: Check `app/templates/` directory for actual template files
- **Routes**: Cross-reference route handlers in `app/routes/` with documentation
- **Lazy Load JS**: See `app/static/js/shared/lazy-load.js` for full fallback behavior

### Key Line Numbers (Verified May 2026)
- `app/tasks.py`: generate_image_variants(28), send_newsletter_task(127), deliver_webhook_task(184), send_confirmation_task(263), send_password_reset_task(284), run_backup_task(305)
- `app/search.py`: reset_fts_available(36), search(201), sync_fts(112), sync_fts_batch(136), remove_fts(177), rebuild_fts(102), get_search_snippets(282), get_did_you_mean(327), highlight_query(356), extract_snippet(253), get_indexed_terms(224)

### Exception Handling in Search
All module-level functions in `app/search.py` catch `OperationalError`, `ProgrammingError`, and `DatabaseError` exceptions from SQLAlchemy. When these exceptions occur during search operations, functions return empty results or `False` rather than propagating.

### Celery Concurrency
The Celery worker runs with `--concurrency=1` (see `docker-compose.yml:50`). This single-concurrency setting ensures newsletter emails are sent in order without duplication and webhook delivery is serialized.

### APScheduler Newsletter Behavior
The APScheduler `send_daily_newsletter` function calls `send_newsletter()` synchronously from `app.email`, NOT via Celery. The Celery `send_newsletter_task` is used for manual/ad-hoc newsletter sends only.

### Backup Exception Handling
`run_backup_task` in `app/tasks.py:305-321` catches `(SQLAlchemyError, OSError, ImportError)` — NOT a bare `except Exception`.

### Backup Implementations
Two separate backup implementations exist:
- `app/services/backup.py:create_backup()` — Used by Celery task, supports AES-256-GCM encryption with PBKDF2/compression, uses `blog_*.db` naming
- `app/scheduler.py:run_daily_backup()` — Used by APScheduler, no encryption/compression, uses `blog_*.db` naming, wrapped with FileLock

Both use `blog_*.db` naming, so `cleanup_old_backups()` correctly cleans both.

### Backup Encryption Distinction
Three separate encryption modules:
- `app/backup_encryption.py` — PBKDF2-HMAC-SHA256 key derivation (600K iterations) for backup files
- `app/webhook_encryption.py` — Direct 32-byte key (no PBKDF2) for webhook secrets
- `app/services/encryption.py` — Direct AES-256-GCM using SECRET_KEY for TOTP secrets

### Verified FALSE Claims (Do NOT Include)
These claims from review files were verified against the codebase and found to be inaccurate:
- ~~GPG encryption in backup.md~~ — Both architecture docs and code docstring already correctly say AES-256-GCM
- ~~Bare `except Exception` in `run_backup_task`~~ — Actually catches `(SQLAlchemyError, OSError, ImportError)` at line 319
- ~~Referrer-Policy mismatch between Flask and nginx~~ — Both use `strict-origin-when-cross-origin`
- ~~`POST /api/auth` route~~ — `app/routes/api/auth.py` contains only `require_api_key` decorator, no route
- ~~`POST /api/subscribers/export` route~~ — No export endpoint in API; only admin export
- ~~`NEWSLETTER_MAX_RETRY_ATTEMPTS` missing~~ — Exists at `app/config.py:116`
- ~~FTS sync missing in `publish_scheduled_posts`~~ — Both `sync_fts_batch` and `invalidate_tag_cache` are present
- ~~Celery production docs missing~~ — Already documented in `architecture/deployment/docker.md` lines 52-68
- ~~Redis image tag discrepancy~~ — Both docker-compose.yml and docker.md use `redis:7-alpine`

---

*Last updated: May 28, 2026 — Consolidated and verified against codebase*
