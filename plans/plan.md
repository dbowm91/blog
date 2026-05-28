# Implementation Plan - Blog CMS Architecture Documentation & Code Fixes

**Project:** Blog CMS
**Status:** IN PROGRESS
**Last Updated:** May 28, 2026

---

## Overview

Consolidated plan from architecture reviews of all 8 modules (core, routes, services, tasks, infrastructure, frontend, deployment, testing). Reviews conducted May 9, 2026. Previous documentation waves (A-F, 43 items) completed May 22, 2026.

This plan organizes items into parallelizable waves. Each wave can run subagents concurrently.

---

## Deferred Items

### Per-Webhook Retry

**Status:** Not implemented - would require significant refactoring

- **Location:** `app/tasks.py:234-246`
- **Current behavior:** Failed webhooks are logged but silently skipped
- **Documentation:** Acknowledged in `architecture/tasks/celery-tasks.md` and `architecture/infrastructure/webhooks.md`
- **Reason deferred:** `deliver_webhook_task` catches `requests.RequestException` without calling `self.retry()`, so Celery's `max_retries=3` never triggers. Per-webhook retry would require significant refactoring to track individual webhook state.

---

## Wave 1: Core + Routes (Parallel) — High Priority Documentation Fixes

These waves fix inaccurate claims in documentation and add missing route/model documentation. Run subagents in parallel.

### Wave 1A: Core Module Fixes

**Target files:** `architecture/core/app-factory.md`, `architecture/core/configuration.md`, `architecture/core/models.md`

| ID | Priority | Issue | Action |
|----|----------|-------|--------|
| C-3 | HIGH | `models.md` documents `totp_secret` as a column | Fix: `totp_secret_encrypted` is the column; `totp_secret` is a property that decrypts on access via AES-256-GCM |
| C-5 | HIGH | `configuration.md` does not document ~17 settings | Add to architecture docs: MAX_VIEWED_POSTS, TAG_CACHE_TTL_SECONDS, DASHBOARD_PER_PAGE, SUBSCRIBERS_PER_PAGE, MEDIA_PER_PAGE, MEDIA_MAX_FILES, EXPORT_BATCH_SIZE, FTS_RESULT_LIMIT, PREVIEW_TOKEN_EXPIRY_DAYS, HEALTH_CHECK_SECRET, DATA_BACKUP_DIR, WEBHOOK_TIMEOUT, WEBHOOK_ENCRYPTION_KEY, COMPRESS_ALGORITHM, SMTP_TIMEOUT, SEARCH_PROVIDER, SEARCH_CONFIG (all exist in `app/config.py`) |
| C-6 | HIGH | `configuration.md` SESSION_IP_BINDING values not explained | Document: `"warn"` (default, logs warning on IP change) vs `"enforce"` (invalidates session, implemented in `app/routes/admin/__init__.py:32`) |
| C-1 | MEDIUM | `app-factory.md` SESSION_COOKIE_SECURE documented as `True (in production)` | Fix: defaults to `"true"` string, configurable via env var |
| C-2 | MEDIUM | `app-factory.md` SQLite Pragmas shown as static commands | Fix: pragmas set via SQLAlchemy `connect` event listener |
| C-7 | MEDIUM | `models.md` Comment `author_email` documented as nullable | Fix: actual is `nullable=False` (required) |
| C-4 | MEDIUM | `models.md` missing backup codes documentation | Add: `backup_codes_hashed` column, `generate_backup_codes()` (8 codes), `verify_backup_code()` |

**Missing models to document in `models.md`:**
- AdminSession, Series, PostSeries, Webhook, WebhookEvent, PostRevision (missing `author_id`)

**Missing services to document:**
- Encryption service (`app/services/encryption.py`)
- Backup service details
- Slug service (100 try limit, UUID fallback, `exclude_id` parameter)

**Missing features to document:**
- 2FA implementation (TOTP encrypted at rest, backup codes)
- Rate limiting (ADMIN_RATE_LIMITS in `app/config.py`)
- Account lockout

### Wave 1B: Routes Module Fixes

**Target files:** `architecture/routes/admin-routes.md`, `architecture/routes/public-routes.md`, `architecture/routes/api-routes.md`

| ID | Priority | Issue | Action |
|----|----------|-------|--------|
| R-1 | HIGH | Preview route documented as `GET /post/<slug>/preview/<token>` | Fix: actual is `GET /preview/<int:post_id>?token=<token>&expires=<timestamp>` (HMAC-based) |
| R-2 | HIGH | Logout documented as `GET /admin/logout` | Fix: actual is `POST /admin/logout` with CSRF validation |
| R-9 | HIGH | API publish documented as `POST /api/posts/<id>/publish` | Fix: does not exist; publish via `PUT /api/posts/<id>` with `{"published": true}` |
| R-10 | HIGH | Rate limits documented as 500/min reads, 100/min writes | Fix: actual route-level limits are `DEFAULT_LIMIT = "20 per minute"` (reads), `WRITE_LIMIT = "10 per minute"` (writes) in `app/routes/api/posts.py:18-19` |
| R-4 | MEDIUM | Subscriber export documented as `POST` | Fix: actual is `GET /admin/subscribers/export` |
| R-5 | MEDIUM | Tag create documented as `POST /admin/tags` | Fix: actual is `POST /admin/tags/create`; also missing rename route `POST /admin/tags/rename/<int:tag_id>` |
| R-6 | MEDIUM | Media delete documented as `DELETE /admin/media/<filename>` | Fix: actual is `POST /admin/media/delete/<filename>` |
| R-7 | MEDIUM | Newsletter routes documented as `GET/POST /admin/newsletter` | Fix: actual is `POST /admin/newsletter-test` + `GET /admin/newsletter/preview` |
| R-8 | MEDIUM | Settings documented as `GET/POST /admin/settings` | Fix: actual is `GET /admin/settings` + `POST /admin/settings/theme` |
| R-3 | LOW | Post list documented as `GET /admin/posts` | Fix: actual is `GET /admin/` (dashboard) |

**Missing routes to add (21 routes):**

| ID | Route | Location |
|----|-------|----------|
| M-1 | `GET /series/<slug>` | browse.py |
| M-2 | `GET /archive` (cursor-based pagination) | browse.py |
| M-3 | `GET /s/<code>` (short URL redirect + share tracking) | posts.py |
| M-4 | `POST /api/track-share` | posts.py |
| M-5 | `POST /admin/bulk` (bulk post operations) | posts/__init__.py |
| M-6 | `POST /admin/delete/<int:post_id>` | posts/manage.py |
| M-7 | `GET /admin/preview/<int:post_id>` + shareable preview | posts/manage.py |
| M-8 | `POST /admin/posts/<int:post_id>/revisions/<int:revision_id>/restore` | revisions.py |
| M-9 | `POST /admin/users/<int:user_id>/make-owner` | users.py |
| M-10 | `POST /admin/users/password/<int:user_id>` | users.py |
| M-11 | `POST /admin/subscribers/bulk` | subscribers.py |
| M-12 | `POST /admin/subscribers/delete/<int:sub_id>` | subscribers.py |
| M-13 | `POST /admin/sessions/revoke/<int:sess_id>` | sessions.py |
| M-14 | `POST /admin/newsletter-reset/<int:post_id>` | auth.py |
| M-15 | `GET/POST /admin/forgot-password` + `GET/POST /admin/reset/<token>` | auth.py |
| M-16 | 2FA routes: `/admin/login-2fa`, `/admin/2fa/backup-codes`, `/admin/2fa/disable` | auth.py |
| M-17 | `GET /metrics` (Prometheus) | meta.py |
| M-18 | `GET /favicon.ico` | meta.py |
| M-19 | `GET /api/stats` | api/stats.py |
| M-20 | `POST /api/auth` | api/auth.py |
| M-21 | `POST /api/subscribers/export` | api/subscribers.py |

**Note:** Route documentation must be cross-referenced against actual handlers in `app/routes/` before writing. Always verify HTTP methods and parameters.

---

## Wave 2: Services + Tasks (Parallel) — Documentation & Code Fixes

### Wave 2A: Services Module Fixes

**Target files:** `architecture/services/backup.md`, `architecture/services/serialization.md`, new `architecture/services/tag_cache.md`

| ID | Priority | Issue | Action |
|----|----------|-------|--------|
| S-2 | HIGH | Naming conventions not clearly distinguished | Document: both `create_backup()` and `run_daily_backup()` use `blog_*.db` naming (verify against actual code before documenting) |
| -- | HIGH | Tag Cache Module undocumented | Create `architecture/services/tag_cache.md` documenting `app/tag_cache.py`: `_get_tag_counts()`, `invalidate_tag_cache()`, TTL config, invalidation triggers |
| -- | MEDIUM | Encryption Module undocumented | Document `app/backup_encryption.py`: PBKDF2 key derivation, encrypted file format (salt + nonce + ciphertext + tag) |
| -- | MEDIUM | Slug Service incomplete | Document: 100 try limit, UUID format (`uuid.uuid4().hex[:8]`), `exclude_id` parameter |
| S-3 | MEDIUM | Decryption output path default incorrect | Fix: for non-`.gpg` files, appends `.decrypted` instead of removing extension |
| S-4 | LOW | Serialization import handling incomplete | Document: no `deserialize_*` functions exist; import handled via CLI only |
| -- | LOW | FileLock in `run_daily_backup` | Document: lock file location (`{instance_path}/backup.lock`), timeout=0 behavior |

### Wave 2B: Tasks Module Fixes

**Target files:** `architecture/tasks/celery-tasks.md`, `architecture/tasks/scheduler.md`

| ID | Priority | Issue | Action |
|----|----------|-------|--------|
| T-4 | HIGH | `send_daily_newsletter` claimed to trigger Celery task | Fix: `app/scheduler.py` calls `send_newsletter()` synchronously, NOT via Celery. Celery `send_newsletter_task` is for manual/ad-hoc sends only |
| T-3 | MEDIUM | APScheduler "Queue Routing" section is misleading | Fix: APScheduler jobs are in-process, not Celery queues. Remove/rename section |
| T-2 | MEDIUM | `run_backup_task` parameters not documented | Add: `compress=True, keep=7, encrypt=False`, creates `blog_*.db` files |
| -- | MEDIUM | Missing backup implementation comparison | Add table: APScheduler (`backup_*.db`, no encryption) vs Celery (`blog_*.db`, AES-256-GCM encryption) |
| -- | MEDIUM | Missing FileLock documentation | Document: lock file paths, `timeout=0` behavior as intentional design |
| TM-1 | LOW | Missing `NEWSLETTER_MAX_RETRY_ATTEMPTS` config | Document in scheduler.md |
| TM-2 | LOW | Missing FTS sync + tag cache invalidation in `publish_scheduled_posts` | Document side effects |

**Verified FALSE (do NOT include):**
- ~~Bare `except Exception` in `run_backup_task`~~ — Actually catches `(SQLAlchemyError, OSError, ImportError)` at line 319
- ~~GPG in backup.md~~ — Documentation already correctly says AES-256-GCM

---

## Wave 3: Deployment + Infrastructure + Testing (Parallel) — Mixed Priority

### Wave 3A: Deployment Fixes

**Target files:** `architecture/deployment/docker.md`, `architecture/deployment/security.md`, `architecture/deployment/cicd.md`

| ID | Priority | Issue | Action |
|----|----------|-------|--------|
| DEP-5 | CRITICAL | No Celery production documentation | Add: task registration, worker scaling, queue configuration, monitoring |
| DEP-2 | SECURITY | nginx runs as root in Docker | Document as known limitation; recommend non-root nginx image |
| DEP-1 | HIGH | backup.py working directory confusion | Document: `working_dir: /home/blog` + volume mount relationship |
| -- | HIGH | Missing nginx security headers | Document: `X-XSS-Protection`, `X-Download-Options`, `X-Permitted-Cross-Domain-Policies` |
| -- | MEDIUM | CI/CD workflow details incomplete | Document all jobs in `.github/workflows/test.yml`: lint-and-type, test, security-audit, e2e-tests |
| -- | MEDIUM | Missing rate limiting zones | Document nginx zones: `login` (5r/m), `admin` (20r/m) |
| -- | MEDIUM | Missing SSL certificate documentation | Add setup/renewal docs for Let's Encrypt |
| -- | LOW | Brotli configuration status | Document: commented out in nginx.conf, requires custom nginx image |
| DEP-6 | LOW | Redis image tag discrepancy | Fix: document `redis:7-alpine` (not `redis:alpine`) |

### Wave 3B: Infrastructure Fixes

**Target files:** `architecture/infrastructure/search.md`, `architecture/infrastructure/webhooks.md`, `architecture/infrastructure/overview.md`

| ID | Priority | Issue | Action |
|----|----------|-------|--------|
| INF-1 | HIGH | Search abstraction layer undocumented | Document entire `app/services/search/` provider abstraction: SearchProvider ABC, SQLiteSearchProvider, PostgreSQLSearchProvider stub, `get_search_provider()` factory |
| INF-2 | MEDIUM | SSRF protection not documented in webhooks overview | Add: scheme checking, URL format validation, userinfo blocking, loopback hostname blocking, IP resolution and validation, IPv4-mapped IPv6 checking, AWS/GCP metadata endpoint blocking, global routability check |
| INF-3 | MEDIUM | Health check critical checks not documented | Add health check section to `overview.md` |
| -- | MEDIUM | `remove_fts` function undocumented | Document `app/search.py:177-190` |
| -- | MEDIUM | `sync_fts_batch` signature mismatch | Fix: actual signature takes `items: list[tuple]` |
| INF-4 | LOW | Webhook Secret Encryption undocumented | Document `app/webhook_encryption.py` |
| -- | LOW | S3 Storage Backend error handling undocumented | Document: methods return `False` or empty lists on failure |
| -- | LOW | Storage Singleton Pattern undocumented | Document `get_storage()` returns module-level singleton |

### Wave 3C: Testing Fixes

**Target files:** `architecture/testing/test-suite.md`

| ID | Priority | Issue | Action |
|----|----------|-------|--------|
| -- | HIGH | Non-existent directories documented | Fix: `tests/unit/` and `tests/integration/` do NOT exist; tests are in flat structure at `tests/` root |
| -- | HIGH | E2E file structure wrong | Fix: single file `tests/e2e/test_e2e.py` with 4 classes, NOT separate files |
| -- | HIGH | Missing fixtures documentation | Add: `sample_post`, `sample_tag`, `sample_subscriber`, `mock_render`, `mock_smtp`, `mock_email`, `clean_analytics_cache`, `cleanup_uploads` |
| -- | MEDIUM | Missing E2E configuration section | Document: `pytest-playwright` requirement (note: not in committed requirements files, must be installed separately), `playwright install chromium`, `app_server` fixture on port 5010 |
| -- | MEDIUM | Missing SQLAlchemy 2.0 query patterns | Document modern patterns: `select(Model).filter()`, `db.paginate()` |
| -- | MEDIUM | Test database session issues undocumented | Document: `db.session.refresh()` fails if object not in session; re-query instead |
| -- | LOW | Missing command reference | Add: `.venv/bin/python3 -m pytest` with `ADMIN_PASSWORD=test SECRET_KEY=test` prefix |

---

## Wave 4: Frontend (After Wave 1-3) — Documentation Fixes

**Target files:** `architecture/frontend/templates.md`, `architecture/frontend/static-assets.md`, `architecture/frontend/overview.md`

| ID | Priority | Issue | Action |
|----|----------|-------|--------|
| -- | HIGH | Missing `post_image_avif_url_stub` filter | Add to filter list in `templates.md` (filter at `app/filters.py:75-83`, registered as `post_image_avif_url_stub`, DEPRECATED — always returns `None`) |
| -- | HIGH | Incorrect context processor variable names | Fix: `site_name` → `site_title`, `site_tagline` → `site_description` in `templates.md` |
| -- | MEDIUM | CSS architecture undocumented | Add: file aggregation, dark mode as default with `data-theme`, `critical.css` for above-the-fold, font self-hosting (Inter, JetBrains Mono) |
| -- | MEDIUM | JavaScript module system undocumented | Add: `export default initXxx` requirement, `import.meta.glob()` for dynamic loading, mobile menu creation, admin body class detection |
| -- | MEDIUM | Vite asset helper undocumented | Document `vite_asset()` helper in `app/vite.py`, content hashing, manifest file |
| -- | MEDIUM | Lazy image progressive enhancement undocumented | Document CSS pattern (`opacity: 0` default + `.loaded` class) |
| -- | LOW | Prism.js syntax highlighting themes | Document: 6 themes available, selection via `SiteSettings.syntax_theme` |
| -- | LOW | Vite chunk split inconsistency | Document actual chunks or update `vite.config.js` manualChunks |

---

## Wave 5: Verification & Cleanup

After all waves complete:

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
- **Search Provider Architecture**: `app/search.py` and `SQLiteSearchProvider` in `app/services/search/sqlite.py` are SEPARATE implementations. The SearchProvider abstraction is a wrapper/interface pattern, but the actual functions in app/search.py are standalone FTS5 functions. See `app/services/search/__init__.py` for the abstraction.
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

### Verified FALSE Claims (Do NOT Include)
These claims from review files were verified against the codebase and found to be inaccurate:
- ~~GPG encryption in backup.md~~ — Both architecture docs and code docstring already correctly say AES-256-GCM
- ~~Bare `except Exception` in `run_backup_task`~~ — Actually catches `(SQLAlchemyError, OSError, ImportError)` at line 319
- ~~Referrer-Policy mismatch between Flask and nginx~~ — Both use `strict-origin-when-cross-origin`

---

*Last updated: May 28, 2026 - Consolidated from 8 architecture review files*
