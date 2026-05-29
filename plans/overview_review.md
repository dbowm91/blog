# Overview Architecture Review

**Reviewed:** 2026-05-29
**Architecture Docs:** architecture/overview.md
**Source Files:** Cross-cutting (all modules)

## Review Scope

Reviewed `architecture/overview.md` against all 8 module reviews:
- `plans/core_review.md` -- EXISTS
- `plans/routes_review.md` -- EXISTS
- `plans/services_review.md` -- EXISTS
- `plans/tasks_review.md` -- EXISTS
- `plans/infrastructure_review.md` -- EXISTS
- `plans/testing_review.md` -- EXISTS
- `plans/frontend_review.md` -- NOW EXISTS
- `plans/deployment_review.md` -- NOW EXISTS

Focus: cross-cutting references, module interdependencies, terminology consistency, completeness; verification of previously unverifiable claims.

---

## Findings

### Verified Claims (Correct)

| Claim in overview | Verified Against | Status |
|-------------------|------------------|--------|
| 17 models listed in Data Models table | `core_review.md` line 22 | Correct; all 17 names match |
| `User` model fields (TOTP, backup codes, lockout) | `core_review.md` line 23 | Correct |
| `AdminAuditLog` for security audit trail | `core_review.md` line 29 | Correct |
| `ApiToken` with `is_valid()` / `has_scope()` | `core_review.md` line 32 | Correct |
| App factory in `app/__init__.py`, config in `app/config.py` | `core_review.md` line 10 | Correct |
| Extensions: SQLAlchemy, LoginManager, Migrate | `core_review.md` line 9 | Correct |
| All 6 blueprints registered (public, admin, rss, errors, api, swaggerui) | `core_review.md` line 14 | Correct |
| APScheduler jobs: daily newsletter, cleanup, publish, backup | `tasks_review.md` lines 35-38 | Correct schedules and FileLock usage |
| APScheduler `send_daily_newsletter` conditional on `SMTP_HOST` | `tasks_review.md` line 35 | Correct |
| APScheduler `cleanup_expired_subscribers` every 5 min | `tasks_review.md` line 36 | Correct |
| APScheduler `publish_scheduled_posts` every 5 min | `tasks_review.md` line 37 | Correct |
| APScheduler `run_daily_backup` at 02:00 | `tasks_review.md` line 38 | Correct |
| Celery queues: images, newsletter, webhooks, email, backup | `tasks_review.md` lines 18-24 | Correct queue assignments and task parameters |
| Celery `task_serializer="json"`, `task_time_limit=300`, `task_soft_time_limit=240` | `tasks_review.md` line 14 | Correct |
| Celery `worker_prefetch_multiplier=1`, `worker_max_tasks_per_child=100` | `tasks_review.md` line 14 | Correct |
| All 5 Celery tasks use `db.session.remove()` in `finally` blocks | `tasks_review.md` line 31 | Correct |
| `backup.py` `run_daily_backup()` at `app/services/backup.py:150` | `services_review.md` line 13 | Correct |
| `run_daily_backup()` uses `sqlite3.backup()` (no compression/encryption) | `tasks_review.md` line 41 | Correct |
| `backup_encryption.py`: PBKDF2 600k iterations, 16-byte salt, 12-byte nonce, AES-256-GCM | `services_review.md` line 15 | Correct |
| `webhook_encryption.py`: AES-256-GCM, 12-byte nonce, Base64 output | `services_review.md` line 16 | Correct |
| Two-level webhook dispatch (`deliver_webhook_task` -> `deliver_single_webhook_task`) | `infrastructure_review.md` lines 46-48 | Correct |
| HMAC-SHA256 webhook signing with `sha256=` prefix | `infrastructure_review.md` line 49 | Correct |
| SSRF protection blocking private IP ranges, AWS/GCP metadata | `infrastructure_review.md` lines 56-64 | Correct |
| Search provider abstraction: `SearchProvider` ABC, SQLite FTS5, PostgreSQL stub | `infrastructure_review.md` lines 23-27 | Correct |
| FTS5 virtual table with `prefix='2 3 4'` | `infrastructure_review.md` line 12 | Correct |
| Redis used for both Celery broker and rate limiting | `overview.md` lines 51-53 | Correct |
| SQLite WAL mode | `core_review.md` line 13 | Correct |
| `get_storage()` singleton pattern | `infrastructure_review.md` line 41 | Correct |
| Directory structure matches actual layout (minor exceptions) | Cross-checked | Mostly correct |
| Template directory structure verified | `frontend_review.md` lines 11-16 | Correct; all templates present |
| Template inheritance chain verified | `frontend_review.md` lines 17-21 | Correct; base.html, admin/base.html, admin/login_base.html, email/base_email.html |
| All filters in app/filters.py verified | `frontend_review.md` lines 23-29 | Correct; markdown_safe, reading_time, sanitize_css, post_image_url, post_image_srcset, post_image_avif_url_stub |
| Context processors verified | `frontend_review.md` lines 31-36 | Correct; inject_csrf, inject_config, inject_theme, inject_footer_data, inject_show_footer_posts |
| Cache invalidation functions verified | `frontend_review.md` lines 38-40 | Correct; invalidate_settings_cache, invalidate_footer_cache |
| CSS files all present | `frontend_review.md` lines 42-44 | Correct; base.css, layout.css, public.css, forms.css, utilities.css, critical.css, admin.css, 6 Prism themes |
| JavaScript files all present | `frontend_review.md` lines 46-51 | Correct; admin, public, shared, lib files all verified |
| Vite chunk splitting verified | `frontend_review.md` lines 53-56 | Correct; vendor, admin, public chunks defined |
| Dark mode implementation verified | `frontend_review.md` lines 62-66 | Correct; localStorage, prefers-color-scheme, data-theme attribute |
| Critical CSS loading verified | `frontend_review.md` line 68 | Correct; base.html:24 with media="screen" |
| Docker Compose production profile verified | `deployment_review.md` lines 27-30 | Correct; blog, celery, redis, nginx |
| CI/CD workflow 6 jobs verified | `deployment_review.md` lines 32-38 | Correct; lint-and-type, test, security-audit, frontend-build, docker-build, e2e-tests |
| Weekly schedule cron `0 8 * * 1` | `deployment_review.md` lines 40-41 | Correct; Monday 08:00 UTC |
| Dockerfile multi-stage, Python 3.12-slim, non-root user | `deployment_review.md` lines 43-46 | Correct |
| Granian CMD with 4 workers, 60s timeout verified | `deployment_review.md` lines 47, 78-79 | Correct |
| nginx rate limiting, security headers, Brotli commented out | `deployment_review.md` lines 48-55 | Correct |
| Resource limits verified (blog 512M, celery 256M, redis 128M) | `deployment_review.md` lines 62-65 | Correct |
| All documented env vars present | `deployment_review.md` lines 67-70 | Correct |

---

### Discrepancies (Doc vs Code)

1. **`overview.md:67` -- Dual Redis description is ambiguous but not incorrect**
   - The diagram shows two Redis boxes ("Redis (Broker + Cache)" and "Redis (Rate Limits)") but in code `RedisCache` is used for Flask-Caching and the same `REDIS_URL` is used for Celery broker, result backend, and rate limit storage. This is a presentation artifact in the diagram, not a code discrepancy. The text "Redis (Broker + Cache)" and "Redis (Rate Limits)" separation may confuse readers about whether there are one or two Redis instances.

2. **`overview.md:149-158` (API Routes table) -- Missing endpoints**
   - Overview API table lists only: posts, subscribers, stats, pages, series, tags.
   - The overview's text says: "pages, series, tags" in the table header but the table columns only show "posts, subscribers, stats, pages, series, tags". This matches what exists in `app/routes/api/`. **Actually correct** -- the table does include pages, series, tags. The routes_review.md noted that these have rate limits but docs don't mention them; the overview table correctly lists all six files.

3. **`overview.md:235` (Infrastructure -- Search source) -- Single source file is misleading**
   - Lists `app/search.py` as the source for "Search"
   - But there is also `app/services/search/` providing the `SearchProvider` abstraction. The overview shows the search provider under Services Layer (line 171) but the Infrastructure section shows only `app/search.py`. This creates an inconsistent picture: is search an infrastructure concern or a service? The `services/search/` directory is listed in the directory structure (line 392-395) but search is categorized under Infrastructure. This is a structural inconsistency.

4. **`overview.md:239-242` (Infrastructure table) -- Source files partially incorrect**
   - Shows: `app/search.py`, `app/email.py`, `app/storage.py`, `app/webhooks.py`
   - Missing: `app/utils.py` (contains `is_safe_webhook_url` for SSRF), `app/services/search/__init__.py` (SearchProvider ABC), `app/services/search/sqlite.py`, `app/services/search/postgresql.py`
   - The SSRF protection (`is_safe_webhook_url`) is listed in the overview diagram (line 278: "SSRF Protection") but the infrastructure table source column doesn't include `app/utils.py` where it lives.

5. **`overview.md:266` (Security source) -- Missing `app/csrf.py`**
   - Lists: `app/routes/admin/auth.py`, `app/services/encryption.py`, `app/middleware/rate_limit.py`
   - Missing: `app/csrf.py` (CSRF token generation/validation), `app/extensions.py` (LoginManager config)
   - The overview mentions "CSRF: Sliding window tokens (5 valid)" but doesn't list the actual CSRF implementation file.

6. **`overview.md:266` (Security source) -- Missing `app/utils.py` for SSRF**
   - `is_safe_webhook_url()` is in `app/utils.py` but not listed as a Security source.

7. **`overview.md:318-319` (Directory structure) -- `app/utils.py` described as "Utilities (slug, UTCDateTime, SSRF)"**
   - `app/utils.py` does contain `generate_slug`, `UTCDateTime`, `is_safe_webhook_url`, and other utilities. This is accurate.

8. **`overview.md` -- No mention of `app/tag_cache.py` in module table**
   - The Discrete Modules table (lines 9-23) doesn't mention `tag_cache.py`. The directory structure (line 328) lists it. It should appear in the Core Application or Infrastructure section as a caching concern.

9. **`overview.md` -- `app/middleware/rate_limit.py` listed in directory but not in module table**
   - The directory structure shows `app/middleware/rate_limit.py` but the Core Application module table doesn't mention middleware at all. Rate limiting is mentioned under Security Architecture but `app/middleware/rate_limit.py` is not listed as a source file there.

10. **`overview.md` -- Frontend module table shows correct source files but Vite manifest requirement undocumented** (NEW from `frontend_review.md`)
    - The frontend section shows `app/templates/`, `app/static/` as source, which is correct.
    - However, `frontend_review.md` identified that `npm run build` (Vite build) must run before production deployment, and the manifest.json must be present. This build requirement is not documented in the overview.

11. **`overview.md` -- Login template asset loading not flagged as inconsistent** (NEW from `frontend_review.md`)
    - Overview doesn't mention that `admin/login_base.html` uses `url_for('static', ...)` directly instead of `vite_asset()`, unlike `admin/base.html`. This could cause cache/CDN issues on login pages.

12. **`overview.md` -- Prism theme loading inconsistency** (NEW from `frontend_review.md`)
    - `base.html:30` uses `vite_asset('css/' + syntax_theme + '.css')` but `main.js:102` loads Prism CSS via direct path `/static/css/...`. If CDN_URL is configured, JS path won't include it. Not flagged in overview.

13. **`overview.md` -- Docker profile requirements not explicitly documented** (NEW from `deployment_review.md`)
    - Overview mentions Docker/Nginx/CI/CD but does not explicitly state that all services require explicit `--profile` flag. `deployment_review.md` notes explicit profile requirement but this is not prominent in overview.

14. **`overview.md` -- Python version mismatch not documented** (NEW from `deployment_review.md`)
    - `dev.sh` requires Python >= 3.14 but `Dockerfile` uses python:3.12-slim. This dev/prod version mismatch could cause compatibility issues. Not flagged in overview.

---

### Missing Documentation

1. **APScheduler multi-worker race condition (HIGH priority -- known from `tasks_review.md`)**
   - The overview describes APScheduler as running "in-process" (correct) and shows it under Granian. It does NOT warn that FileLock with `timeout=0` only works on a single machine. Multiple container replicas will each run their own APScheduler and execute jobs concurrently. This is a critical architectural limitation completely absent from the overview. The `scheduler.py` itself documents this limitation (lines 3-8) but the overview does not.

2. **`_update_delivery_status` bug (HIGH priority -- known from `tasks_review.md` and `infrastructure_review.md`)**
   - The webhook delivery status tracking sets `event.delivered = True` at the dispatcher level BEFORE individual webhook deliveries complete. The overview says "'delivered' when all webhooks succeed" but this is not what the code does. No mention of this limitation.

3. **`get_storage()` singleton not thread-safe (MEDIUM priority -- `infrastructure_review.md`)**
   - `storage.py` singleton has a race condition: multiple threads could create multiple storage instances. The overview describes S3 lazy initialization as thread-safe ("threading.Lock") but the singleton wrapper itself lacks a lock.

4. **`SESSION_IP_BINDING` not implemented (noted in `core_review.md`)**
   - Overview lists "AdminSession ... with IP binding" under models but `core_review.md` found the IP binding enforcement logic appears to be missing from `before_request_handler`. The overview should clarify the actual implementation status.

5. **Silent FTS initialization failure (noted in `core_review.md`)**
   - `__init__.py` lines 430-433 catch `OperationalError` during FTS init silently. This is not documented in the overview.

6. **Webhook SSRF DNS time-of-check limitation (noted in `infrastructure_review.md`)**
   - `is_safe_webhook_url()` resolves DNS once before the request. If DNS changes between validation and request, a previously safe URL could become unsafe. No lock or resolved IP reservation. This is a subtle but real SSRF gap.

7. **`test-suite.md` E2E password inconsistency (from `testing_review.md`)**
   - The overview mentions Playwright E2E tests under test structure but does not note the password inconsistency bug (`"testpassword"` vs `"test-password"` across fixtures). This is a latent test reliability issue.

8. **Vite manifest requirement for production** (NEW from `frontend_review.md`)
   - The overview doesn't mention that `npm run build` (Vite build) must be run before production deployment, and manifest.json must be present. If Vite build hasn't run, JS assets return hashed paths that don't exist.

9. **Login template asset loading inconsistency** (NEW from `frontend_review.md`)
   - `admin()` and `login_base.html` uses `url_for('static', ...)` directly instead of `vite_asset()`, creating inconsistency with admin/base.html and potentially breaking CDN prefix support.

10. **marked.min.js outside Vite build system** (NEW from `frontend_review.md`)
    - `marked.min.js` is loaded via `url_for('static', ...)` directly, not through Vite. This means it's not content-hashed and won't benefit from Vite's optimization. Not documented.

11. **`_post_image_cache` implementation detail** (NEW from `frontend_review.md`)
    - Uses post_id keys for post_image_url but also stores srcset cache with key `_post_srcset_cache_{post.id}`. This nested cache structure is undocumented but could cause maintenance issues if not understood.

12. **APScheduler multi-container limitation detection** (NEW from `deployment_review.md`)
    - `deployment_review.md` notes the APScheduler FileLock limitation but adds that there is no documentation on how to detect if multiple APScheduler instances are running, and no alerting mechanism for duplicate job execution. This gap was previously unnoted.

13. **Backup encryption key loading gap** (NEW from `deployment_review.md`)
    - `deployment_review.md` documents that BACKUP_ENCRYPTION_KEY can come from config.toml via app.config but this is not documented. Silent fallback to unencrypted backup if key loading fails not documented.

14. **Celery worker scaling not warned** (NEW from `deployment_review.md`)
    - Scaling celery from 1 to 3 containers with `--scale` would have 3x parallelism (since --concurrency=1 is per-container), not 1x. This is not documented anywhere in overview.

15. **Health check start_period not documented** (NEW from `deployment_review.md`)
    - Container won't be marked healthy for 10 seconds after startup (docker-compose.yml:43 start_period). Overview's health check description doesn't mention this.

16. **E2E test Docker build dependency** (NEW from `deployment_review.md`)
    - The e2e-tests job in CI depends on docker-build but NOT on frontend-build. If frontend build fails, e2e tests may still run with stale assets. Not documented in overview.

---

### Potential Bugs / Concerns

1. **APScheduler multi-container race (tasks_review.md:98-100 -- HIGH)**
   - FileLock with `timeout=0` only works on single machine. Multi-container deployments (Docker Compose with multiple blog containers) will produce duplicate newsletter sends, duplicate backups, duplicate post publishes. The overview's Docker architecture diagram does not show multiple app containers.

2. **`_update_delivery_status` always reports "delivered" (tasks_review.md:87-91 -- MEDIUM; infrastructure_review.md:110-113 -- HIGH)**
   - `event.delivered` is set to `True` by `deliver_webhook_task` (dispatcher) BEFORE `deliver_single_webhook_task` calls are dispatched. The per-webhook status is never checked. Webhook delivery status in DB will be misleading.

3. **`get_storage()` singleton not thread-safe (infrastructure_review.md:115-117 -- MEDIUM)**
   - `_storage is None` check has no lock. Double-checked locking pattern recommended.

4. **E2E test isolation bug (testing_review.md:93 -- HIGH latent)**
   - `e2e/conftest.py` does not define its own `app` fixture. Running `pytest tests/e2e/` alone fails because it relies on the import chain. The overview's directory structure correctly shows `tests/e2e/` but doesn't flag isolation concern.

5. **Admin password inconsistency across test fixtures (testing_review.md:99 -- HIGH)**
   - `tests/conftest.py` uses `"testpassword"` (no hyphen); `tests/e2e/conftest.py` uses `"test-password"` (with hyphen). Tests may fail inconsistently depending on which fixture set is used.

6. **Webhook task dispatch marks event delivered before completion (infrastructure_review.md:128-135 -- MEDIUM)**
   - `deliver_webhook_task` sets `event.delivered = True` at line 226 before Celery tasks complete. If Celery is unavailable, webhooks are silently undelivered but the event is marked delivered.

7. **`session.clear()` placement (routes_review.md:142 -- noted but not a bug)**
   - Session fixation protection via `session.clear()` before `login_user()` is correctly implemented. Not a bug, just undocumented in overview.

8. **S3 `list_files()` and `exists()` swallow all exceptions (infrastructure_review.md:119-126,142-144 -- MEDIUM)**
   - Cannot distinguish "file not found" from S3 errors. Silent failure mode could mask permission or connectivity issues.

9. **Prism CSS loaded via JS bypasses vite_asset (frontend_review.md:113 -- MEDIUM)** (NEW)
   - If CDN_URL is configured, Prism CSS loaded by main.js:102 via direct path `/static/css/...` won't include CDN prefix. Inconsistency between vite-based CSS loading for admin and JS-based loading for public.

10. **Login pages missing CDN prefix support (frontend_review.md:111 -- MEDIUM)** (NEW)
    - `admin/login_base.html` uses `url_for('static', ...)` directly while `admin/base.html` uses `vite_asset()`. Login pages won't benefit from content-hashed URLs or CDN prefix.

11. **No error handling for missing Vite manifest (frontend_review.md:117 -- LOW)** (NEW)
    - `vite.py:26-30` silently returns empty dict if manifest doesn't exist. In production, if Vite build hasn't run, JS assets will return hashed paths that don't exist.

12. **CSS hash caching process-level (frontend_review.md:119 -- LOW)** (NEW)
    - `_css_hash_cache` dict in vite.py is process-level caching that won't update if files change without process restart. Not documented.

13. **E2E test race condition in CI (deployment_review.md:163-168 -- MEDIUM)** (NEW)
    - `docker compose wait redis` only waits for redis to be ready. Blog service may not be healthy yet when tests start. Works but fragile.

14. **APScheduler FileLock not enforced against scaling (deployment_review.md:170-175 -- HIGH)** (NEW)
    - No mechanism prevents user from running `docker-compose up -d --scale celery=3`. APScheduler jobs would run on all 3 replicas simultaneously. No warning in docker-compose.yml.

15. **Backup encryption silently disabled (deployment_review.md:177-183 -- HIGH)** (NEW)
    - If BACKUP_ENCRYPTION_KEY environment variable is set but cannot be loaded, backup.py silently falls back to unencrypted. No error raised. Encryption may be disabled without indication to operator.

16. **Python version mismatch dev vs prod (deployment_review.md:185-189 -- MEDIUM)** (NEW)
    - dev.sh requires Python >= 3.14 but Dockerfile uses python:3.12-slim. Could cause compatibility issues if code uses 3.14 features.

---

### Cross-Cutting References Analysis

**Terminology consistency:**
- "SSRF Protection" appears in overview Security (line 278) and is implemented in `app/utils.py`. The overview's infrastructure table source doesn't list `utils.py`.
- "HMAC timing-safe comparison" for API auth (overview line 276) matches `routes_review.md` finding on `require_api_key` decorator.
- "Sliding window tokens (5 valid)" for CSRF (overview line 275) is not directly verifiable from review files but CSRF implementation is in `app/csrf.py` which is not listed as a source.
- "Critical CSS" mentioned in overview (line 24) and verified correct by `frontend_review.md:68` - loads at base.html:24 with `media="screen"`.

**Module interdependencies correctly shown:**
- Overview diagram correctly shows Granian -> app -> Redis (broker/cache) -> Celery Worker and SQLite
- `app/search.py` (Infrastructure) depends on `app/extensions.py` (Core) for `db`. Correct.
- `app/services/search/` (Services) wraps `app/search.py` (Infrastructure). Correct layering.
- `app/tasks.py` (Task Processing) imports from `app/webhooks.py`, `app/email.py`, `app/storage.py` (all Infrastructure). Correct.

**New cross-cutting findings from frontend/deployment reviews:**
- Vite build system (frontend) feeds into nginx static file serving (deployment)
- Docker Compose production profile must include nginx (deployment) which serves Vite-built assets (frontend)
- CI/CD pipeline has frontend-build job (deployment) that feeds into docker-build which tests Playwright E2E tests (testing)
- APScheduler in Docker (deployment) runs tasks that use services from multiple layers
- SSL/TLS termination at nginx (deployment) wraps all routes (routes) including API auth (security)

**Gaps in module interdependency documentation:**
- APScheduler -> `app/email.send_newsletter()` -> `app/tasks.send_newsletter_task` (three-way relationship noted in `tasks_review.md:76`) is not shown anywhere in overview.
- The `app/services/search/` abstraction layer over `app/search.py` creates confusion in the Infrastructure vs Services boundary.
- Frontend templates use filters (from `app/filters.py`) which may call `storage.exists()` (infrastructure), creating an indirect dependency not shown.
- Newsletter workflow spans: scheduler (tasks) -> email module (infrastructure) -> Celery task (tasks) -> backup service (services) -> storage (infrastructure). This circular-ish flow not documented.

---

### Improvement Suggestions

1. **Add multi-container warning to APScheduler description** in overview. The `scheduler.py` already documents this limitation. The overview should prominently flag: "FileLock-based; not safe for multi-container deployments without external coordination."

2. **Fix Infrastructure / Services boundary for search** in overview. Either move `app/services/search/` to Infrastructure (and list it in the Infrastructure table source column), or clarify that the Services layer wraps the Infrastructure layer.

3. **Add `app/csrf.py` to Security Architecture source files** in overview.

4. **Add `app/utils.py` to Infrastructure source files** since it contains `is_safe_webhook_url`.

5. **Add `app/tag_cache.py` to Core Application module table** or note it under Infrastructure as a caching concern.

6. **Add `app/middleware/rate_limit.py` to Security Architecture source** or note it under Core Application module table.

7. **Fix `SESSION_IP_BINDING` description** to either confirm it's implemented or note it's not yet enforced.

8. **Clarify Redis representation in diagram** -- show one Redis instance with multiple purposes rather than two separate boxes to avoid confusion about how many Redis instances are required.

9. **Add webhook delivery status limitation** to the overview's webhook description: current implementation sets 'delivered' at dispatch time, not per-webhook completion.

10. **Note E2E test password inconsistency** as a known test setup issue in the Testing section.

11. **Document Vite build requirement** -- add note that `npm run build` must be run before production deployment and manifest.json must be present. (NEW from `frontend_review.md`)

12. **Standardize login template asset loading** -- use `vite_asset()` consistently in `admin/login_base.html` for CDN support. (NEW from `frontend_review.md`)

13. **Add multi-container APScheduler scaling warning** to Docker architecture section. Note that scaling celery beyond 1 container without external job coordination will cause duplicate job execution. (NEW from `deployment_review.md`)

14. **Document backup encryption key validation behavior** -- clarify that BACKUP_ENCRYPTION_KEY from either environment or config.toml may silently fall back to unencrypted if key loading fails. (NEW from `deployment_review.md`)

15. **Align Python version requirements** -- either update dev.sh to accept Python 3.12 (matching production), or update Dockerfile to use python:3.14-slim. (NEW from `deployment_review.md`)

16. **Document health check start_period** -- note that containers won't be marked healthy for 10 seconds after startup. (NEW from `deployment_review.md`)

17. **Clarify explicit profile requirement** -- make prominent that `docker compose --profile production up` is required for all commands, not just up. (NEW from `deployment_review.md`)

18. **Document E2E test dependency chain** -- clarify that e2e-tests job depends on docker-build but NOT frontend-build, so frontend failures won't block e2e tests. (NEW from `deployment_review.md`)

---

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | high | APScheduler multi-container race condition: document that FileLock only works on single machine; add warning to overview architecture diagram | overview.md |
| 2 | high | `_update_delivery_status` bug: overview claims "'delivered' when all webhooks succeed" but code sets delivered at dispatch time. Update overview to reflect actual behavior | overview.md |
| 3 | high | E2E test isolation bug: `e2e/conftest.py` has no own `app` fixture; flag in overview's test structure notes | overview.md + tests/e2e/conftest.py |
| 4 | high | Admin password inconsistency: `testpassword` vs `test-password` across conftest files; fix or document | tests/conftest.py + tests/e2e/conftest.py |
| 5 | high | APScheduler scaling warning missing: scaling celery beyond 1 container without external coordination causes duplicate jobs. Add warning to overview Docker section | overview.md + docker-compose.yml |
| 6 | high | Backup encryption silently disabled: if BACKUP_ENCRYPTION_KEY set but cannot be loaded, backup proceeds unencrypted. Add key validation or documentation | source (backup.py) + docs |
| 7 | high | Python version mismatch: dev.sh requires 3.14+, Dockerfile uses 3.12-slim. Align versions | dev.sh + Dockerfile |
| 8 | med | `get_storage()` singleton not thread-safe: add double-checked locking or document as known limitation | source (app/storage.py) |
| 9 | med | `SESSION_IP_BINDING` not confirmed implemented: either document the implementation or remove "IP binding" from AdminSession description | overview.md + source |
| 10 | med | Infrastructure/Services boundary for search: list `app/services/search/` in Infrastructure source column or clarify service wrapping infrastructure | overview.md |
| 11 | med | Add `app/csrf.py` to Security Architecture source files | overview.md |
| 12 | med | Add `app/utils.py` to Infrastructure source files (contains SSRF protection) | overview.md |
| 13 | med | Add `app/middleware/rate_limit.py` to module documentation | overview.md |
| 14 | med | Add `app/tag_cache.py` to module table (tag count caching with Flask-Caching) | overview.md |
| 15 | med | Vite build requirement undocumented: production deployment requires `npm run build` and manifest.json presence. Add to overview | overview.md |
| 16 | med | Login template asset loading inconsistent: login_base.html uses url_for instead of vite_asset, missing CDN support | source (admin/login_base.html) |
| 17 | med | Prism CSS loaded via JS bypasses vite_asset: main.js:102 path doesn't include CDN prefix if configured | source (main.js) + vite_asset |
| 18 | med | E2E test CI race condition: docker compose wait only waits for redis, not blog health. Add health wait for blog | ci.yml + docker-compose.yml |
| 19 | low | Webhook SSRF DNS time-of-check gap: add to overview's SSRF protection description | overview.md |
| 20 | low | S3 silent error handling: document that `exists()` and `list_files()` return false/empty on any error | docs/infrastructure/storage.md |
| 21 | low | Newsletter three-way path (scheduler -> email.py -> Celery task) not shown in overview; add architecture note | overview.md |
| 22 | low | Marked.min.js outside Vite build: not content-hashed, won't benefit from Vite optimization. Document or fix | source + docs |
| 23 | low | Health check start_period undocumented: containers not healthy for 10s after startup. Document | docs/deployment/docker.md |
| 24 | low | Align E2E test to frontend build dependency: e2e-tests should depend on frontend-build or document stale asset risk | ci.yml |
