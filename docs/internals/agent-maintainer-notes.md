# Agent Maintainer Notes

Historical implementation caveats, known gotchas, and maintainer context for AI agents. This is a living record of things that aren't obvious from the code alone.

## Table of Contents

- [High-Risk Files](#high-risk-files)
- [Test Interference](#test-interference)
- [Implemented Features](#implemented-features)
- [Future-Agent Reminders](#future-agent-reminders)
- [Deprecated Implementations](#deprecated-implementations)
- [Actual Routes vs. Assumed](#actual-routes)
- [Context Processors](#context-processors)
- [Template Filters](#template-filters)
- [Encryption Modules](#encryption-modules)
- [S3 Storage Gotchas](#s3-storage-gotchas)
- [Task Names](#task-names)
- [Test Structure](#test-structure)
- [Misc Implementation Notes](#misc-implementation-notes)
- [Verifying Frontend Visual Defects](#verifying-frontend-visual-defects)
- [Second Frontend Review Pass (2026-10-23)](#second-frontend-review-pass-2026-10-23)
- [Code Block Line Numbers (2026-10-23)](#code-block-line-numbers-2026-10-23)
- [Admin Theme Preview Placement (2026-10-24)](#admin-theme-preview-placement-2026-10-24)
- [Site Identity, Authorship and Page Navigation (2026-10-24)](#site-identity-authorship-and-page-navigation-2026-10-24)
- [Editor Layout, Markdown Toolbar and Footer Subscribe (2026-10-24)](#editor-layout-markdown-toolbar-and-footer-subscribe-2026-10-24)
- [Themed SVG Art (2026-10-27)](#themed-svg-art-2026-10-27)
- [Index Layout and Article Furniture (2026-10-27)](#index-layout-and-article-furniture-2026-10-27)
- [See Also](#see-also)

---

## High-Risk Files

These files have been flagged for exception handling issues (all now fixed):

| File | Issue | Status |
|------|-------|--------|
| `app/routes/public/meta.py` | Previously broad exception | FIXED |
| `app/email.py` | SMTP exception too broad | FIXED |
| `app/backup_integrity.py` | Previously broad exception | FIXED |
| `app/webhooks.py` | Silent failure with `pass` | FIXED |
| `app/tasks.py` | Email task retry logic | FIXED |
| `app/page_view_buffer.py` | Previously broad exception | FIXED |

---

## Test Interference

### Page View Buffer

- The page view buffer (`app/page_view_buffer.py`) can cause test interference when running full suite
- Buffer is started during `create_app()` if `PAGE_VIEW_BUFFER_SIZE > 0`
- In tests: disable via `app.config.PAGE_VIEW_BUFFER_SIZE = 0` and call `shutdown_page_view_buffer()`
- The `ensure_buffer_disabled` fixture is in `tests/shared_fixtures.py`

### Test Database Session Issues

- `db.session.refresh()` fails if object isn't in current session
- Fix: Re-query object from database instead of using `refresh()`

### The Backup Tests Share One Directory

`tests/test_phase8.py::TestBackupRestore::test_download_backup` downloads
`backups[0]` — the first entry of an **unsorted** `os.listdir()` of
`app.instance_path/backups`. The admin route validates the name against
`BACKUP_FILENAME_RE` (`^blog_\d{8}_\d{6}\.db(\.gz)?(\.gpg)?$`) and answers
400 for anything else.

`tests/services/test_operations_backup.py::TestVerifyBackup::test_verify_backup_valid`
writes `blog_verify_<uuid>.db` into that same directory — its `backup_dir`
fixture is `app.instance_path/backups`, not a tmp path. That name starts with
`blog_`, so the other test's filter keeps it, and it does not match the
regex, so the download is refused.

The two tests therefore pass or fail depending on the directory's listing
order, which depends on the random uuid. Measured on 2026-10-27: with
`tests/services/test_operations_backup.py` running earlier in the same
session, `test_download_backup` failed **10 runs out of 10** on an unmodified
checkout. It fails intermittently in a full-suite run, and the failure set of
a full-suite run is not reproducible run to run.

Nothing about the backup code is wrong — `app/routes/admin/backup.py` and
`app/services/backup.py` behave correctly. The defect is in the tests: one
writes an invalidly named file into a shared directory, and the other assumes
the first entry of an unsorted listing is downloadable. Comparing a
before-and-after failure set needs this in mind: a single differing test in
this area is not a regression. Fixing it means sorting the listing and
filtering it to the names the route accepts, and giving the verify test a
tmp directory of its own.

### The Test Suite Used to Overwrite the Developer's `.env`

Fixed on 2026-10-24. Running `pytest tests/` replaced the repository root's
`.env` with the onboarding test's own secrets, leaving the developer with
`ADMIN_PASSWORD=SecurePass1!` and a rewritten `SECRET_KEY`. It happened 28
times before it was caught, and every stale copy was left behind as
`.env.backup.<timestamp>`.

Three causes, three fixes:

- `tests/onboarding/test_e2e_onboarding.py` replaced the path-resolution step
  with a stub that set `ctx.config_dir` and `ctx.data_dir` but left
  `ctx.env_file` at its default of `Path(".env")` - the repository root. The
  stub now sets `ctx.env_file = ctx.config_dir / ".env"`, so the test writes
  into its own tmp directory.
- `app/onboarding/steps.py::step_resolve_paths` overwrote `ctx.config_dir`,
  `ctx.data_dir` and `ctx.env_file` with the install-mode paths, discarding
  whatever the caller had passed to `run_steps`. That is how
  `tests/onboarding/test_failure_and_resume.py` ended up writing
  `failed = true` over the repository's `config.toml`. `StepContext` now
  carries a `paths_explicit` flag, set by `run_steps` when the caller gives
  paths, and `step_resolve_paths` leaves those paths alone. Both production
  callers of `run_steps` pass no paths, so the install-mode resolution is
  unchanged for them.
- `app/onboarding/state.py::_find_database` appended the working-directory
  candidates (`data/devlog.sqlite3`, `blog.db`, ...) to the list even when
  `data_path` was given explicitly, so detection reported the developer's own
  working copy as the installation being detected. An explicit `data_path` is
  now authoritative, matching what `_find_config` already did.
  `detect_installation` also takes an `env_path` argument so the env file can
  be scoped the same way.

A fourth bug came out of the same investigation: the admin check in
`detect_installation` queried a table called `user`, but the table is
`users`, so the query always raised, `admin_exists` was always false, and
`devlog onboard detect` reported every installation as `partial`. It now
reports `complete` for an installation that is complete.

**If the `.env` looks wrong after running the tests, restore it from
`.env.backup.*` - and note that the backup is the *pre-test* copy.**

---

## Implemented Features

### Halloy Theme Parser (Phase 02)

Phase 02 of the Halloy theme migration is complete. The `app/themes/` package provides a typed TOML parser (`app/themes/halloy.py`) and color primitives (`app/themes/colors.py`). All 50 catalog themes parse successfully. The parser uses Python stdlib `tomllib` with zero Flask/SQLAlchemy/templates/registry coupling. Errors carry `.source` and `.field_path` attributes for structured context. No raw color string reaches CSS without validation — all colors pass through `from_hex` → RGBA. See `plans/halloy_theme_system_roadmap.md` for the full migration plan.

### 2FA Implementation

- TOTP secrets are encrypted at rest using AES-256-GCM (`app/services/encryption.py`)
- `User.totp_secret` is now a property that decrypts on access
- Backup codes are SHA-256 hashed and single-use (8 codes generated, not 10)
- Routes: `/admin/2fa/setup`, `/admin/2fa/verify`, `/admin/2fa/backup-codes`, `/admin/2fa/disable`

### Rate Limiting

- `ADMIN_RATE_LIMITS` defined in `app/config_legacy.py`
- `app/middleware/rate_limit.py` provides `AdminRateLimiter` class
- Flask-Limiter already integrated with `key_func=get_client_ip`

### Session IP Binding

- `SESSION_IP_BINDING` config in `app/config_legacy.py` (default: `"warn"`)
- `"warn"`: logs warning on IP change during session
- `"enforce"`: invalidates session and requires re-login (implemented in `app/routes/admin/__init__.py`)

### Search Abstraction

- `SearchProvider` abstract class in `app/services/search/__init__.py`
- `SQLiteSearchProvider` wraps existing FTS5 functionality
- `PostgreSQLSearchProvider` is a stub for future implementation (falls back to SQLite silently)
- `get_search_provider()` factory function selects provider by `SEARCH_PROVIDER` config

### Frontend

- Vite configured for code splitting with `manualChunks`
- `post_image_avif_url_stub` filter is DEPRECATED - always returns None (no conditional AVIF check)

### Brotli

- Nginx configuration includes commented Brotli settings
- Requires custom nginx image with `--with-http_brotli_module`

---

## Future-Agent Reminders

### Backup Implementations

There are two separate backup implementations:

- `app/services/backup.py:create_backup()` - Used by Celery task, supports AES-256-GCM encryption with PBKDF2/compression, uses `blog_*.db` naming
- `app/scheduler.py:run_daily_backup()` - Used by APScheduler, no encryption/compression, uses `blog_*.db` naming

Both now use `blog_*.db` naming, so `cleanup_old_backups()` correctly cleans both.

### Backup Encryption

Backup encryption uses AES-256-GCM with PBKDF2-HMAC-SHA256 key derivation (600,000 iterations) via `app/backup_encryption.py`, NOT GPG. Webhook encryption uses `app/webhook_encryption.py` with a direct 32-byte key (not PBKDF2).

`InvalidTag` is imported from `cryptography.exceptions`, not from `cryptography.hazmat.primitives.exceptions` — the latter module does not exist in any cryptography release this project supports. The import sits inside a `try: ... except ImportError:` block that sets `CRYPTOGRAPHY_AVAILABLE = False`, so a wrong import path disables backup encryption silently instead of raising. `tests/test_backup_encryption.py` asserts the availability flag and the round trip so this cannot regress unnoticed.

### Slug Generation

Slug collision limit is hardcoded to 100 tries before falling back to UUID suffix (`app/services/slug.py`).

### APScheduler Job Schedules

- `cleanup_expired_subscribers` runs every 5 minutes (`minute="*/5"`), NOT hourly
- `run_daily_backup` runs at 02:00 (`hour=2, minute=0`), NOT midnight

### APScheduler SMTP Handling

When `SMTP_HOST` is not configured, only the daily newsletter job is disabled. Other scheduler jobs (cleanup_expired_subscribers, publish_scheduled_posts, run_daily_backup) continue to run.

### APScheduler Multi-Worker Limitation

APScheduler jobs use FileLock which only works on a single machine. In multi-container deployments, each container runs its own APScheduler. Without external coordination (Redis, etcd), jobs may run on all replicas simultaneously. Set `ENABLE_SCHEDULER=true` on exactly ONE container. This is documented in `architecture/tasks/scheduler.md` and `architecture/deployment/docker.md`.

### Health Check Critical Checks

The health check endpoint (`GET /health`) determines overall status using only critical checks:

- `database`, `scheduler`, `search`, `disk_space`, `db_integrity`
- Optional checks (`backup_freshness`, `email`, `redis`, `celery`) do not affect overall status
- Redis and celery checks are included in detailed health output but don't affect degraded status
- See `architecture/infrastructure/overview.md` for details

### Health Endpoint Split

`/health` has two modes:
- **Basic** (`/health`): Returns only database + scheduler status. Fast, no auth required. Used for Docker healthchecks and uptime monitoring.
- **Detailed** (`/health?detailed=true&secret=...`): Returns all 8 checks with details. Requires `HEALTH_CHECK_SECRET` when set.

### METRICS_SECRET

`METRICS_SECRET` gates the `/metrics` endpoint. When `ENABLE_METRICS=true`, `METRICS_SECRET` must be set; in production without it, `/metrics` returns 403. No fallback to `HEALTH_CHECK_SECRET`.

### python-dotenv Auto-Loading

`python-dotenv` is included in `requirements.txt` and called via `load_dotenv()` in both `run.py` and `app/config_legacy.py`. The app auto-loads `.env` without requiring manual `source` commands.

### Email Retry Count

Newsletter retry count default is 5 (not 3 as some documentation may claim).

### Critical CSS

The `critical.css` file at `app/static/css/critical.css` provides above-the-fold CSS for fast initial paint. It mirrors the actual public and admin shell classes and is loaded immediately by the base templates.

### Celery Queue Names

Tasks declare the queue they are dispatched to in the `shared_task` decorator:
`images`, `newsletter`, `webhooks`, `email`, `backup`. See `app/tasks.py`.

### User Model `__repr__`

Returns `<User id={self.id}>` for PII/security reasons, not username.

### Comment Model Relationships

The Comment model uses `back_populates` for parent/child relationships:

```python
parent = db.relationship("Comment", remote_side=[id], back_populates="replies")
replies = db.relationship("Comment", back_populates="parent", lazy="select")
```

### Health Check Status Logic

Health check only considers critical checks for overall status (optional services don't affect degraded):

```python
critical_checks = {
    k: v for k, v in checks.items()
    if k in ("database", "scheduler", "search", "disk_space", "db_integrity")
}
```

### Snippet Batching

For SQLite parameter limits, batch post_ids. The limit is the module constant
`_SQLITE_MAX_VARS = 500` in `app/search.py`; `get_search_snippets()` splits the
id list into chunks of that size before querying FTS5.

### Backup Isolation

Run backups as Celery tasks to avoid blocking web requests:

```python
@celery_task
def run_backup_task(backup_dir, compress):
    from app.services.backup import create_backup
    return create_backup(db_path, backup_dir, compress=compress)
```

### Webhook Event Triggering

Webhook events are triggered at key state transitions:

```python
# Post publish/unpublish in app/routes/api/posts.py
if "published" in data and was_published != post.published:
    from app.webhooks import create_webhook_event
    create_webhook_event(
        event_type="post.published" if post.published else "post.unpublished",
        payload={"post_id": post.id, "title": post.title, "slug": post.slug},
        target_id=post.id,
        target_type="post"
    )

# Subscriber confirmation in app/routes/public/subscribe.py
sub.confirmed = True
# ... after commit ...
create_webhook_event(
    event_type="subscriber.confirmed",
    payload={"subscriber_id": sub.id, "email": sub.email},
    target_id=sub.id,
    target_type="subscriber"
)
```

### Feed Endpoints

Three main feed endpoints available:

- `/atom` - Atom 1.0 feed
- `/rss` - RSS 2.0 feed
- `/json` - JSON Feed 1.1

Tag-specific feeds:

- `/tag/<slug>/atom` - Atom 1.0 feed for posts with that tag
- `/tag/<slug>/rss` - RSS 2.0 feed for posts with that tag
- `/tag/<slug>/json` - JSON Feed for posts with that tag

Series-specific feeds:

- `/series/<slug>/atom` - Atom 1.0 feed for posts in that series
- `/series/<slug>/rss` - RSS 2.0 feed for posts in that series
- `/series/<slug>/json` - JSON Feed for posts in that series

Tag and series pages include feed discovery links in `<head>` for RSS readers to auto-detect the feeds.

### Webhook Secret Storage

`Webhook.secret` is a property that decrypts `webhook_secret_encrypted` (LargeBinary column) using AES-256-GCM via `app/webhook_encryption.py` (see the `Webhook.secret` getter and setter in `app/models.py`). Do not document `secret` as a plain-text column.

### WebhookEvent Delivery Status

`WebhookEvent` has a `delivery_status` field tracking delivery outcomes:

- `'delivered'` - All webhooks succeeded
- `'partial_failure'` - Some succeeded, some failed
- `'failed'` - All failed

### Search Provider Architecture

`SearchProvider` abstract class in `app/services/search/__init__.py` with implementations:

- `SQLiteSearchProvider` - Current default using FTS5
- `PostgreSQLSearchProvider` - Stub for future PostgreSQL support

Use `get_search_provider()` factory function to get configured provider based on `SEARCH_PROVIDER` config.

**Important**: `SQLiteSearchProvider` wraps the `app/search.py` module-level functions through the `SearchProvider` interface. Each method delegates to the corresponding FTS5 function (`init_fts`, `search`, `sync_fts`, `remove_fts`, `rebuild_fts`, `get_search_snippets`). The `app/search.py` functions are standalone FTS5 implementations that `SQLiteSearchProvider` calls into.

### Comment Submission Rate Limiting

Comments are rate limited by configuration and require CSRF protection via the
global `before_request` hook (route-level `validate_csrf_token()` was removed in
Phase 3).

- Route: `POST /post/<slug>/comment` in `app/routes/public/comments.py`
- Limits: `@limiter.limit(COMMENT_RATE_LIMIT_PER_IP, ...)` and
  `@limiter.limit(COMMENT_RATE_LIMIT_PER_POST, ...)`. The defaults are
  `COMMENT_RATE_LIMIT_PER_IP="5 per minute"` and
  `COMMENT_RATE_LIMIT_PER_POST="3 per minute"`, both overridable through the
  typed `[comments]` config section.
- CSRF: Hidden `csrf_token` field in form, validated before processing

---

## Deprecated Implementations

### Deprecated Function

`deliver_webhook()` in `app/webhooks.py` is deprecated - use `deliver_webhook_task` Celery task instead for all webhook deliveries.

### S3 Credential Clearing Bug

`_clear_credentials()` method in `S3StorageBackend` was removed because it broke client recreation. The method was called after client initialization in the `S3StorageBackend` constructor path in `app/storage.py`.

### CSRF Token Rotation Is On Every Use

`app/csrf.py` rotates tokens on every successful validation, not specifically on privilege changes. The claim in `architecture/deployment/security.md` about "token rotation on privilege changes" is not accurate - that feature is not implemented.

### Admin Image Preview

The admin image preview module is named `image-preview.js` and is loaded by the editor and media routes through the route map in `main.js`.

---

## Actual Routes

When documenting or referring to routes, verify against actual implementation:

- New post: `/admin/new` (NOT `/admin/posts/new`)
- Edit post: `/admin/edit/<id>` (NOT `/admin/posts/<id>/edit`)
- Tag delete: `POST /admin/tags/delete/<id>` (NOT `DELETE`)
- Comment submission: `POST /post/<slug>/comment` (NOT `/comment/<int:post_id>`)
- Subscribe: Only `POST /subscribe` exists (no GET handler)
- API post publish: Use `PUT /api/posts/<id>` with `{"published": true}` body (NOT `POST /api/posts/<id>/publish`)
- `POST /api/auth` does NOT exist — `app/routes/api/auth.py` contains only `require_api_key` decorator
- `POST /api/subscribers/export` does NOT exist — only admin export at `GET /admin/subscribers/export`

---

## Context Processors

Actual context processor function names (not the injected variable names):

- `inject_csrf()` - Injects `csrf_token` and `csp_nonce`
- `inject_config()` - Injects site config variables
- `inject_theme()` - Injects theme settings and `custom_css`
- `inject_appearance()` - Injects the appearance layer settings (typeface, backdrop)
- `inject_footer_data()` - Injects footer links and data
- `inject_show_footer_posts()` - Injects `show_footer_posts` boolean
- `inject_site_settings()` - Injects the site settings row
- `inject_page_menu()` - Injects the resolved page menu

---

## Template Filters

Actual filters (defined in `app/filters.py`):

- `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`
- `post_image_avif_url_stub` — DEPRECATED: stub, always returns None
- NOT `format_date`, `markdown`, `slugify` (these don't exist)

---

## Encryption Modules

Three distinct encryption modules with different key derivation strategies:

- `app/backup_encryption.py` — PBKDF2-HMAC-SHA256 (600K iterations) for backup files
- `app/webhook_encryption.py` — Direct 32-byte key (no PBKDF2) for webhook secrets
- `app/services/encryption.py` — Direct AES-256-GCM using SECRET_KEY for TOTP secrets

---

## S3 Storage Gotchas

### Client Initialization

S3StorageBackend stores credentials at client creation time (not per-request). Credentials remain on the instance to allow client recreation if needed.

### S3 Storage Configuration

S3 settings are read from environment variables, NOT from config.toml or config files:

- `S3_BUCKET`, `S3_REGION`, `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_PUBLIC_URL`
- See the module-level `_S3_*` constants in `app/storage.py` for direct env var reading

---

## Task Names

The Celery tasks in `app/tasks.py`, by function name:

| Task | Queue |
|------|-------|
| `generate_image_variants` | `images` |
| `send_newsletter_task` | `newsletter` |
| `deliver_webhook_task` | `webhooks` |
| `send_confirmation_task` | `email` |
| `send_password_reset_task` | `email` |
| `run_backup_task` | `backup` |

`deliver_webhook_task` dispatches to `deliver_single_webhook_task`, which carries
the per-webhook retry logic.

---

## Test Structure

- Tests live under `tests/`, with subdirectories for `benchmarks`, `cli`, `config`,
  `deployment`, `e2e`, `filesystem`, `installer`, `onboarding`, `packaging` and
  `services`
- Run `ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python -m pytest tests/ --collect-only` to get the current count
- E2E tests use `pytest-playwright`, NOT `@playwright/test`
- All E2E tests are in `tests/e2e/test_e2e.py` with 4 classes: `TestAdminLogin`, `TestPostCreation`, `TestNewsletterSubscription`, `TestMobileResponsiveness`
- RSS/Atom feed tests are in `tests/test_coverage.py`, NOT in a separate `test_rss.py` file
- Benchmark tests in `tests/benchmarks/` don't use a `client` fixture - they create clients ad-hoc with `app.test_client()` within each test function

---

## Misc Implementation Notes

### SMTP Exception Handling

When catching SMTP exceptions, catch both specific subclasses and base classes:

- `smtplib.SMTPException` (base class)
- `smtplib.SMTPServerDisconnected`

These may leak as unhandled exceptions if not explicitly caught.

### Email Task Retry Logic

`send_confirmation_task` and `send_password_reset_task` in `app/tasks.py` now have `max_retries=3` and call `self.retry(exc=e)` on exception for automatic retry with exponential backoff.

### Series.posts Ordering

Series.posts relationship orders by `PostSeries.order_index` (not by date or title).

### Slug Generation Race Condition Mitigated

The slug generation in `app/services/slug.py` has an application-level race condition, but database models have `unique=True` constraints on `Post.slug`, `Page.slug`, and `Tag.slug`. Concurrent requests that generate the same slug will result in one succeeding and one failing with `IntegrityError`. Consider adding retry logic on `IntegrityError` to handle this gracefully.

### Webhook Delivery Per-Webhook Retry (Implemented)

`deliver_webhook_task` dispatches individual webhook deliveries to `deliver_single_webhook_task` for per-webhook retry support. Each webhook gets its own Celery task invocation with independent retry logic (up to 3 retries with exponential backoff). Failed webhooks are no longer silently skipped.

### Login Rate Limiting Lives in the Proxy, Not the Application

As of 2026-10-24 the application does **not** rate limit the login routes. The
operator's position is that the deployment sits behind a reverse proxy or WAF,
so the per-IP limit belongs there and the application should not pay for it -
with a Redis-backed limiter that is a network round trip on every attempt.

What was removed:

- `@limiter.limit("5 per minute")` on `public.login`, `admin.login`,
  `admin.forgot_password` and `admin.login_2fa`.
- The `"login"` key from `ADMIN_RATE_LIMITS` in `app/config_legacy.py`. The
  remaining keys are read only by `app/middleware/rate_limit.py`, whose
  `limit_by_type` decorator is a no-op wrapper - nothing calls it.

What was kept, deliberately: the **per-account lockout**
(`User.failed_login_count`, `User.locked_until`, `MAX_FAILED_ATTEMPTS`,
`LOCKOUT_DURATION_MINUTES`) and `LOGIN_FAILURE_DELAY`. Those are columns on
the user row and a sleep on the failure path, so they cost no extra request.
A per-IP proxy limit does not stop a distributed attempt against one account;
the lockout does.

Where the limit now lives:

- `nginx/conf.d/blog.conf` - `location = /login` and `location = /admin/login`
  share the `login` zone; `nginx/nginx.conf` defines the zone at `rate=5r/m`.
- `app/deployment/proxy.py::render_nginx_config` - emits the
  `limit_req_zone` directives and both login locations. The file must be
  included from the **http** context, because `limit_req_zone` is only valid
  there.
- Caddy has no built-in rate limiting. `render_caddyfile` now warns that the
  proxy needs a plugin (for example `caddy-ratelimit`) or a WAF in front.

### nginx Security Headers

Present in the `add_header` directives of `nginx/conf.d/blog.conf`: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, `Content-Security-Policy`, `Strict-Transport-Security`, `Cross-Origin-Opener-Policy: same-origin`, `Permissions-Policy`. Missing: `X-Download-Options`, `X-Permitted-Cross-Domain-Policies`.

### Template Context Variables

Use `site_title` and `site_description` as context variables (NOT `site_name` or `site_tagline`).

### Feed Tests Are in test_coverage.py

RSS/Atom feed tests are in `tests/test_coverage.py`, NOT in a separate `test_rss.py` file.

### Benchmark Tests Don't Use Fixture

Benchmark tests in `tests/benchmarks/` don't use a `client` fixture - they create clients ad-hoc with `app.test_client()` within each test function.

## Verifying Frontend Visual Defects

The 2026-10-23 frontend review found several defects that no unit test could detect, because the defect *is* the rendering. The technique used to confirm them is reusable and worth repeating.

**Render and inspect the HTML.** The app can be driven with `app.test_client()` against a scratch database. A defect like the double-prefixed image URL (`/static/uploads//static/uploads/<file>`) is visible in the rendered `src` attribute without a browser at all.

**Boot the app and use headless Chrome.** On macOS:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
  --window-size=375,900 --virtual-time-budget=8000 \
  --screenshot=/tmp/mobile.png "http://127.0.0.1:5599/"
```

Caveats: `--window-size` below ~500px still reports `window.innerWidth` of 500, so the screenshot is cropped rather than the layout reflowing. `--dump-dom` serialises the DOM after JavaScript has run, which is how the state of dynamically created elements was confirmed. Media queries inside an `<iframe>` evaluate against the iframe viewport, but the app's CSP sets `frame-src 'none'`, so iframes are not usable for this.

**Read computed styles.** The Browser tool's `query` kind does not expose computed styles. To read them, serve a harness page that loads the same stylesheets in the same order and reports `getComputedStyle` results. The CSP applies to static files too: `style-src` has no `unsafe-inline`, so an inline `<style>` block is blocked, and `script-src-attr 'unsafe-inline'` permits an inline `onload` handler, which is the way to run a diagnostic script.

**Sample pixels.** For "is this element actually painted", compare the sampled colour against the known colours. A post card image area measured `#181825` (the card's `--bg-surface`) rather than `#0d1117` (the `default-post.svg` fill) — proof that the image was at `opacity: 0` rather than merely dark.

**Contrast.** Read the emitted theme variables from the rendered `<style>` block and compute the ratio directly. The post title's `#000000` on `#11111b` is 1.12:1.

Local environment note: the system Python's `brotli` wheel is x86_64-only on arm64, so `flask_compress` fails to import. A stub `brotli.py` on `PYTHONPATH` (outside the repo) is enough to boot the app for review purposes.

### What the corrective pass added to this technique

**Playwright is the better tool than headless Chrome, and it is a dependency.** `pytest-playwright` and `playwright` are in `pyproject.toml`'s dev group. `python3 -m playwright install chromium` is enough. `page.evaluate` gives computed styles, `bounding_box()` gives geometry, and `page.locator(...).click()` performs a real interaction — which is what caught two defects that inspection missed.

**A synthetic `click()` can mask a real bug.** `element.click()` from JavaScript dispatches the event on the element itself. A real user click dispatches on the *innermost* node — an `<svg>` inside the button. When `mobile-menu.jsx` replaced the button's `innerHTML` to swap its icon, the clicked `<svg>` was detached, so the document-level handler's `contains(e.target)` check failed and the menu closed again immediately. The CSS fix alone left the hamburger inert. Always verify with a real `page.locator(...).click()`.

**`tests/e2e/` was unrunnable and silently so.** `BaseWSGIServer.set_app()` was removed in Werkzeug 3.x; the app must now be passed to the constructor. Until that was fixed, the entire e2e suite errored at setup — and because `app/static/dist/` is gitignored, a checkout with no build has no bundled JS, so `import.meta.glob` is undefined in the source `main.js` and **no module loads at all**. A test that asserts a dynamically-created element exists will then pass or fail for the wrong reason, and a test that asserts a server-rendered element exists will pass for the wrong reason too. Build the frontend before trusting an e2e result.

**`page.evaluate("localStorage.…")` before the first navigation throws.** `about:blank` has an opaque origin, so localStorage access is denied. Navigate first, then set the value and reload — or use `page.add_init_script`, which runs before any page script and is what you want when the app reads the value during first paint.

**Measure contrast across the whole theme catalog, not one theme.** A fix that helps the default theme can break another: `--accent` is below 4.5:1 against `--bg` in 21 of the 50 bundled themes, so "all links use `--accent`" would have introduced widespread AA failures. Measure the worst case across every bundled theme before choosing a token pairing.

**A `box-shadow` using an undefined custom property does not degrade gracefully.** It resolves to `none` — the whole declaration is dropped at computed-value time. Eight elevation shadows were silently missing because `--shadow-color` was referenced by the stylesheets and emitted by no one. Grep for `var(--x)` references and compare against what the runtime actually emits; `tests/test_css_contracts.py` now does this.

**Prefer a `BuildError` regression test over a code review.** The dead series navigation called `url_for('public.series')` when the endpoint was `public.series_view` — a latent 500 in a block that only rendered under conditions nobody hit. A test that renders a post in a series and asserts the navigation's links resolve pins the endpoint name.

**A browser test can break a migration test.** The session-scoped `app` fixture is
shared by every test in a directory tree. Starting a live server thread on that
application puts a live connection on the shared database, and the migration
round-trip tests later run DDL against the same database — SQLite's batch table
rebuild then reflects a stale schema and fails with `duplicate column name:
theme_preset`. The symptom appears far from the cause: the failing test is a
migration test, and the offender is a Playwright test several files earlier.
Browser tests belong under `tests/e2e/`, which has its own application and
database; keep them there.

**Before blaming a change for a suite failure, reproduce the failure on a pristine
checkout.** `git worktree add /tmp/<name> HEAD` gives an unmodified tree to run
the same suite against. In this pass the onboarding tests failed only when a
stray `data/devlog.sqlite3` was present in the working directory — creating that
file in the pristine tree reproduced the failure exactly, proving it was
pre-existing repository pollution rather than a regression. Comparing a failure
*set* against a pristine baseline is the only reliable way to separate a real
regression from environment state.

## Second Frontend Review Pass (2026-10-23)

A second review of the running instance found eight more defects. The
interesting ones were not visual at all.

**A test that mutates session-scoped config poisons every test after it.** The
`app` fixture is session-scoped. A test that set `app.config["CSRF_ENABLED"] =
True` and `app.config["TESTING"] = False` without restoring them left CSRF
enforced for the rest of the session: every later admin POST returned 403,
every admin GET redirected to the login page, and the suite went from 76 to
137 failures — all caused by the new test, not by the change under test. Use
`monkeypatch.setitem(app.config, ...)`, which restores the value at teardown.
The symptom (mass authentication failures in unrelated files) points nowhere
near the cause.

**The CSRF token was single-use, so a page could only submit once.** The
sliding window in `app/csrf.py` removed a token on use and rotated it, but
`inject_csrf` only ever publishes `tokens[-1]`, so the window never held more
than one token. The theme preview endpoint consumed the page's only token, and
the "Save Theme Settings" form that followed it was rejected with a 403 — the
theme never changed. The token is now validated against the window without
being consumed, which is also what Flask-WTF, Django and Rails do. Replay
resistance was the only property lost, and it buys nothing against a token
that is unguessable and session-bound.

**The theme preview injected variables nothing reads.** The preview endpoint
returned `loaded_theme.css`, which `to_css_variables` renders with the
`--blog-*` semantic names. No stylesheet references `var(--blog-*)` — the
cascade consumes the legacy alias names `--bg`, `--text`, `--accent`. The
preview therefore always showed the *current* theme. `to_legacy_css()` now
serialises the legacy names, and the preview stylesheet is scoped to
`#theme-preview-container` so that previewing a theme no longer repaints the
whole admin panel.

**`func.date()` returns a string on SQLite.** `admin/analytics.html` called
`day.date.strftime('%b %d')` on the result of `func.date(PageView.created_at)`,
which is a `str` on SQLite and a `date` elsewhere. The page raised
`'str object' has no attribute 'strftime'` and returned 500 whenever the
period contained any views. `_coerce_date()` normalises the value.

**The admin panel had no colour-scheme toggle.** `color-scheme.js` was only in
the public module list and `admin/base.html` had no `.nav-actions` host, so the
one place you would change the theme was the one place you could not.

**`tests/onboarding/` overwrites `.env` and `config.toml` in the repository
root.** Running the suite replaces the local instance's configuration with
`failed = true` and rewrites `ADMIN_PASSWORD`. It does not affect the test run
itself — the config is loaded at import — but it silently breaks a local
server on the next start, and it leaves `.env.backup.*` files behind. Restore
both files after a full-suite run.

**Grid headers and rows are separate grid containers.** A `.post-list-header`
and a `.post-list-item` sized their own tracks, so an `auto` column ended up a
different width in each and the columns drifted apart — the dashboard header
had two cells over rows with four. The list is now a single grid and the rows
are `subgrid`s of it, so every row shares the parent's tracks. Give the header
a transparent 1px border when the items have one, or the rows sit 1px apart.


## Code Block Line Numbers (2026-10-23)

Code blocks are numbered on the left with a CSS counter. No JavaScript and no
client-side library is involved, but the markup has to carry the structure a
counter needs.

**CSS cannot enumerate the lines of a text node.** Python-Markdown renders a
code block as `<pre><code>one\ntwo</code></pre>` — the code is a single text
node, so a stylesheet has nothing to count. `app/markdown_renderer.py` wraps
every line in `<span class="code-line">` and the stylesheet numbers those
spans with `counter-increment` / `content: counter(code-line)`. The renderer
is the single producer: `app/filters.py` (`markdown_safe`), the admin preview
endpoint and the feed renderers all call `render_markdown()`.

**The newlines stay between the spans, not inside them.** That keeps
`textContent` byte-identical to the un-numbered output, so copy and paste
still yields the code the author wrote, and it means a trailing newline does
not become a numbered line of its own. A code block whose content contains raw
HTML is left alone — splitting it per line could cut a tag in half.

**The counter rules live in `base.css`, not `public.css`.** The admin shell
does not load `public.css`, so the admin live preview would have shown
unnumbered code blocks. `base.css` is the only stylesheet both shells load.

**Prism would destroy the line spans.** `Prism.highlightElement()` replaces
the `<code>` element's `innerHTML` with its own token markup, which removes
the `code-line` spans and with them the numbering. Prism used to be inert:
`nh3` stripped the `class` attribute from `<code>` (there was no `code` entry
in `MARKDOWN_ALLOWED_ATTRIBUTES`), so the `pre[class*="language-"]` selector
that loads Prism never matched, and the copy button in `public/code-copy.js`
did nothing either. The renderer now re-attaches the fence language after
sanitisation, writing `class="language-<slug>"` onto both the `<pre>` and its
`<code>`, so Prism does run. `app/static/js/shared/prism-blocks.js` is the
repair for the line spans: it reads the existing spans from `code.children`,
splits the highlighted markup into one fragment per line and rebalances the
tags, so a token that spans lines keeps its colour on every line. The renderer
is still the only producer of the `code-line` spans.

**`getComputedStyle(el, '::before').content` returns the unresolved
expression.** Chrome reports `counter(code-line)`, not `"1"`. To prove a
counter resolved in a browser test, drop the fixed gutter width through the
CSSOM (`rule.style.width = 'auto'` — an injected `<style>` is blocked by the
CSP) and check that the pseudo-element still has a box: a resolved counter
gives the box the width of a digit, an unresolved one gives it no box at all.

## Admin Theme Preview Placement (2026-10-24)

The "Theme Preview" panel on the admin settings page
(`app/templates/admin/settings.html`) used to sit **below** the "Theme"
section, and it was hidden by an inline `style="display: none;"` until a
preview had been fetched. An operator had to scroll down past the selectors to
find the preview, scroll back up to change the selection, and scroll down
again to look at the result. The panel now sits **above** the "Theme" section,
and the section order is Theme Preview → Theme → Theme Registry.

Only the placement changed. The selector, the request path, the endpoint, the
injected stylesheet and the button wiring are the same code that shipped
before — the mechanism was deliberately **not** redesigned. Re-implementing the
preview would have made a placement change impossible to review as one.

**The panel is visible by default and shows a placeholder.** The inline
`display: none` was removed from `#theme-preview-section`. Until a preview is
fetched the container shows the copy "Select a theme below and press its
Preview button to see it here."; after a successful preview the container is
replaced with the sample markup held in `#theme-preview-content-restore`.

**The `.theme-preview-btn` triggers stay with the two `<select>` controls.**
They are `type="button"` and never submit the form. `fetchPreview()` reads the
*current* — possibly unsaved — values of `#theme_dark_name` and
`#theme_light_name` and POSTs them to `admin.settings_theme_preview`, with the
CSRF header name taken from `document.documentElement.dataset.csrfHeader`.
Moving the panel above the controls did not move the buttons with it, and it
must not: the button's `data-target` attribute is what tells `fetchPreview()`
which colour scheme to preview, and the operator needs each button next to the
control it previews.

**`min-height` equals `max-height`, and that is the point.**
`.theme-preview-container` declares `min-height: 380px` and `max-height: 380px`
(300px under the 768px breakpoint), so the box cannot change height when the
placeholder is swapped for real preview content and the controls below it
cannot move. This matters more after the move than before it: the panel is
*above* the controls, so a height change would push the very controls the
operator is driving. If the preview needs more room, change both values
together and keep them equal.

**"Clear Preview" restores the placeholder, it does not hide the section.** The
handler removes the injected `<style>` element and repopulates the container
with a clone of the placeholder node; the section stays visible. Reinstating
`previewSection.style.display = 'none'` on clear would bring back the original
complaint.

**The preview stylesheet stays scoped.** `applyPreviewCss()` injects a
`<style>` element carrying the CSP nonce whose rules are scoped to
`#theme-preview-container[data-color-scheme="dark"|"light"]`, so previewing a
theme never repaints the rest of the admin panel. That scoping predates this
move and must be preserved — it is the difference between a preview and a
re-skin of the admin shell. All preview CSS is inline in the template's
`<style nonce="{{ csp_nonce }}">` block; there are no preview rules in
`app/static/css/*.css`.

**A successful preview scrolls the panel into view.** The success path calls
`previewSection.scrollIntoView({behavior: reduceMotion ? 'auto' : 'smooth',
block: 'nearest'})`, where `reduceMotion` comes from
`matchMedia('(prefers-reduced-motion: reduce)')`. This is what removes the
up-and-down scrolling the placement change was made to fix.

## Site Identity, Authorship and Page Navigation (2026-10-24)

An operator review of the running instance found that the site had no user
accounts a visitor could actually use, no author behind a post, and pages that
were published but unreachable. This section records the contracts that the
implementation now depends on.

### Site settings are one form, one owner

`POST /admin/settings/site` persists six values through
`app/services/site_settings.py:validate_site_settings()`:

| Value | Meaning |
|---|---|
| `comments_enabled` | Comments are accepted on the public site |
| `footer_text` | Footer line, plain text, capped at 300 characters |
| `footer_show_posts` | Show the "Latest from the blog" footer column |
| `footer_show_tags` | Show the "Browse by tag" footer column |
| `show_pages_in_menu` | Master switch for the pages menu |
| `menu_pages` | JSON array of page ids, in menu order |

**The footer text is plain text, never markup.** It is rendered with Jinja
autoescaping and `white-space: pre-line` (`.footer-text` in
`app/static/css/layout.css`) rather than as markdown, so an admin cannot
inject markup into every page of the site.

**The comments switch fails closed.** `app/routes/public/comments.py` refuses
to create a comment when the switch is off, and the comment block is not
rendered at all. Existing comments stay visible — the switch closes the door,
it does not delete the conversation.

**The menu has two layers, and only one owner.** `menu_pages` is an explicit
ordered list of page ids. When it is empty the menu falls back to every
published page with `Page.show_in_menu` set, ordered by title. The format is
parsed in exactly one place, `app/services/site_settings.py:parse_menu_pages()`;
`app/services/navigation.py:parse_menu_page_ids()` is a thin alias over it.

### `SiteSettings.get_instance()` is not safe on a read path

`get_instance()` performs `db.session.flush()`, which pushes unrelated pending
changes into the transaction. It is fine on an admin write path. Public reads
use `app/context_processors.py:get_site_settings()`, which does a plain
`select(SiteSettings).order_by(id).limit(1)`, and
`app/services/navigation.py:get_menu_settings()`, which does the same.

### Profiles

`User` carries `display_name`, `bio_short`, `bio_full` and `avatar_path`.
`User.profile_name` is the only producer of a display name — it falls back to
`username` — and `User.avatar_url` is the only producer of an avatar URL. The
avatar path is a storage-relative filename written by
`app/services/profile.py`; a client-supplied URL is never stored.

The avatar upload reuses `app/routes/admin/helpers/images.py:_save_image()`,
which already does extension allow-listing and magic-byte detection. Replacing
an avatar deletes the previous file from storage — an avatar edit that leaks a
file per change is a defect.

The full bio is markdown and renders through `app/markdown_renderer.py`, the
single sanitised markdown producer. The short bio is plain text.

### Public authentication is a separate authority from the admin panel

`flask_login` keeps one `current_user` per session, so the public sign-in and
the admin sign-in share a session cookie. Three things keep them apart:

1. **The public login refuses admin accounts.** `app/routes/public/auth.py`
   rejects a user with `is_admin` set and points them at the admin panel.
   Without this, a public session would satisfy `admin_required` on its
   `is_admin` check alone.
2. **`admin_required` also requires an `AdminSession` row.** The admin panel
   binds the session to an IP and to the session row; a public session has
   neither.
3. **`public.logout` deletes the `AdminSession` row** before calling
   `logout_user()`, exactly as the admin logout does. Without this, an admin
   who signs out from the public site leaves an orphaned row.

The public login applies the same controls as the admin login: the shared lockout
counters on the `User` row, the `LOGIN_FAILURE_DELAY` sleep on every failure,
`session.clear()` before `login_user()`, and a second factor for accounts that
have one. A public sign-in must never be a weaker path than the admin sign-in.

There is **no per-IP rate limit in the application** on either login route — the
per-IP limit lives in the reverse proxy, as described under
[Login Rate Limiting Lives in the Proxy](#login-rate-limiting-lives-in-the-proxy-not-the-application).

The `?next=` parameter is validated by `is_safe_next_url()` in
`app/routes/public/auth.py`: a single leading slash, no scheme, no netloc, no
backslash, no control characters. It is deliberately **not** the Referer-based
`_safe_redirect_url()` in `app/routes/public/posts.py`, which solves a
different problem.

### Authorship

`Post.author_id` points at `User.id`. The migration backfills every existing
post with the oldest administrator, so no post renders authorless after an
upgrade.

`app/services/authors.py:resolve_author()` is the only producer of an author:
the assigned user, then the legacy config-level author (`AUTHOR_NAME`,
`AUTHOR_ROLE`, `AUTHOR_AVATAR`), then the site title. The name is never
empty.

`AuthorView.username` is `None` for a config-level author. Templates link the
name to `/author/<username>` **only** when it is not `None` — a config author
has no profile page, so linking it would produce a 404.

SQLite does not enforce foreign keys in this application (`PRAGMA
foreign_keys` is never set), so deleting a user nulls `posts.author_id` in the
delete route rather than relying on `ON DELETE SET NULL`.

### Page navigation

`app/services/navigation.py:resolve_page_menu()` is the single producer of the
menu and is read fresh on every call — there is no cache to invalidate, so
publishing, unpublishing or deleting a page is reflected immediately.

### Migration chain

The single Alembic head before this work was `drop_theme_preset_column`. Four
migrations were added in series:

```
drop_theme_preset_column
  -> add_site_settings_content_flags
  -> add_user_profile_fields
  -> add_post_author
  -> add_page_menu_fields
```

`add_post_author` adds the `author_id` column and the index, then creates the
foreign key **only on dialects that can alter constraints** — SQLite cannot,
and `op.add_column` silently drops an inline `REFERENCES` clause there. The
application enforces the delete behaviour in code instead, so the constraint
being absent on SQLite is not a behavioural difference.

**Fixed on 2026-10-24: a fresh install now works.** Running `flask db upgrade`
against a *completely empty* database used to fail with
`duplicate column name: newsletter_attempts`. Two branches of the migration
graph both add `posts.newsletter_attempts` (`89a922eae517` and
`16034e1c5a45`), and both create the `post_revisions` table
(`add_post_revisions` and `16034e1c5a45`). The chain worked for an existing
deployment, which is the upgrade path that matters, but a fresh install from
the migrations alone was broken.

The fix was three parts:

- `16034e1c5a45` now checks before it creates anything. A column or table
  that already exists is left alone, and each index is created
  independently of the table that holds it, so the branch that arrives second
  adds only what the branch that arrived first did not. It also no longer
  runs `UPDATE alembic_version SET version_num=...`, which set every branch
  row to a single revision and corrupted the branch tracking.
- `89a922eae517` and `add_post_revisions` tolerate the sibling branch having
  already dropped their column and their table.
- A new head migration, `reconcile_schema_with_models`, brings a database
  built by the migration graph up to the models. The graph predates several
  models, so the columns and tables those models need were never added by a
  migration: `api_tokens` did not exist, `users` was missing `email`,
  `reset_token`, `reset_token_expires_at`, `failed_login_count`,
  `locked_until`, `totp_secret_encrypted`, `totp_enabled` and
  `backup_codes_hashed`, `webhook_events` was missing the delivery
  counters, `post_tags` was missing its tag index, `users.totp_secret` and
  `webhooks.secret` were leftovers the models had replaced, and seven
  columns had the wrong nullability. Every step is conditional, so on a
  database that already matches the models it changes nothing.

**Rewriting the body of an already-applied migration only affects databases
that have not applied it yet.** Existing deployments have the revision
stamped, so they never run it again. That is what makes it safe to make the
historical migrations conditional instead of squashing the history.

**CI now covers it.** `tests/test_migration_chain.py` builds a database from
scratch in a subprocess and compares the resulting schema with the model
metadata. The upgrade runs in a subprocess because `migrations/env.py` takes
its engine from the current Flask application, and the test suite's own
application is bound to a different database.

---

## Editor Layout, Markdown Toolbar and Footer Subscribe (2026-10-24)

### The editor is one shared component

`app/templates/admin/_editor_body.html` holds a `markdown_editor` macro that
renders the whole body field: the markdown toolbar, the textarea, the preview
toggle, the live preview and the word/character counter. Both
`admin/editor.html` and `admin/page_editor.html` call it. The two editors
cannot drift apart again because there is only one copy of the markup.

### The preview sits under the editor, not beside it

`.editor-split` is a **flex column**, not a two-column grid. The textarea is
full width and the live preview renders below it. The preview is collapsed
through the `#toggle-preview-btn` button, which owns the state: it sets
`preview-visible` / `preview-hidden` on `#editor-split` and keeps
`aria-expanded` and the button label in sync. The button is the single
writer of those classes — `app/static/js/admin/shortcuts.js` clicks the
button rather than toggling the classes itself.

The old contract had the toggle hidden on desktop and the preview forced
hidden on mobile by a media query. Both are gone.

**A Jinja escaping trap to avoid.** The page editor used to write the invalid
state with `{{ ' aria-invalid="true"' if errors and errors.body else '' }}`.
Jinja autoescapes the string literal, so the browser received
`aria-invalid=&#34;true&#34;` — a broken attribute. Inline `{% if %}` blocks
write the attribute literally and are the safe way to emit a literal
attribute value.

### The markdown toolbar

`app/static/js/admin/markdown-toolbar.js` inserts markdown at the caret.
Every button carries `data-md-action="<action>"` and the module holds the one
table of actions.

| Action | Inserted |
|--------|----------|
| `bold` | `**text**` |
| `italic` | `*text*` |
| `underline` | `<u>text</u>` |
| `strikethrough` | `~~text~~` |
| `code` | `` `text` `` |
| `codeblock` | a fenced block |
| `link` | `[text](url)`, with `url` selected |
| `heading` | `## ` |
| `quote` | `> ` |
| `bulletlist` | `- ` |
| `numberedlist` | `1. `, `2. `, ... |

Two details that are easy to get wrong:

- The line actions (heading, quote, both lists) replace the **whole line
  block**, not the selection span. Replacing the selection span duplicates the
  rest of the line, because the block runs from the start of the first line to
  the end of the last one. `replaceSpan()` takes explicit from/to offsets for
  this reason.
- The line actions strip an existing marker of the same kind before adding
  theirs, so clicking "Heading" on `## Heading` does not produce `## ## Heading`.

### Undo and redo

`app/static/js/admin/editor-history.js` owns the editor history. It has two
parts: `createHistory()` is pure logic over a `read`/`write` pair, and
`initEditorHistory()` wires it to the textarea, the keyboard and the buttons.

**The native undo stack is not enough here.** The toolbar sets
`textarea.value` directly, which wipes the browser's undo history — so after a
bold insertion, Cmd+Z could not undo it. The blog therefore keeps its own
stack and takes Cmd+Z over completely.

The rules:

- The stack holds `{value, selectionStart, selectionEnd}` snapshots, 200 deep.
- Typing is **coalesced**: edits within 600ms of each other collapse into one
  entry, so undo removes a burst of typing rather than one character.
- A toolbar insertion is **structural** and always gets its own entry. The
  toolbar dispatches an `editor:structural` event on the textarea before it
  mutates the value; the history listens for it and forces the next record.
  Without that, a toolbar click landing inside the coalescing window would be
  merged into the surrounding typing.
- Editing after an undo truncates the redo tail, which is the standard
  behaviour of every editor.
- `undo()` and `redo()` restore the value **and** the selection, and dispatch
  an `input` event so the live preview and the draft autosave follow.

The toolbar carries an undo and a redo button next to the formatting
buttons. They are `disabled` when there is nothing to undo or redo, which is
why they are the only buttons in the toolbar that change state.

**The history is seeded last.** `initEditorHistory()` runs at the end of
`initEditor()`, after the draft restore. A restored draft is the starting
point, not an undo step — otherwise the first undo would wipe the draft the
author had just recovered. The restore also dispatches an `input` event now,
so the live preview and the word count follow it; before that, the preview
kept showing the empty state after a restore.

### Strikethrough is a first-party extension

Python-Markdown has no `strikethrough` extension and `pymdown-extensions` is
not a dependency. `app/markdown_extensions.py` provides one: an
`InlineProcessor` that turns `~~text~~` into `<s>text</s>`. The sanitiser
already allowed the `s` and `u` tags, so no change was needed there.

`render_markdown()` appends the extension to whatever extension list it is
given, so the page, the editor preview and the feeds all speak the same
dialect. `FEED_EXTENSIONS` in `app/markdown_renderer.py` is the feed list;
the feeds drop `footnotes` (footnote references do not survive a feed) but
keep strikethrough.

The editor preview endpoint now calls `render_markdown()` with the default
extensions, so the preview is byte-for-byte what the published page renders.

### The nav has no "Pages" link

The navbar lists the menu pages themselves and nothing else. There is no
separate "Pages" entry. `GET /pages` still exists and still lists every
published page; the **footer** Pages heading links to it, which is where a
published page that is *not* in the menu stays reachable.

### The subscribe form lives in the footer

The newsletter form was removed from the homepage hero and now sits in the
footer as a **Newsletter** column, so it is on every public page. The
`.subscribe-form-footer` rules already existed in `app/static/css/layout.css`;
the `.hero-subscribe` rules were deleted with the form.

### Restart the server after `npm run build`

`app/vite.py` caches the Vite manifest in a module-level global for the life
of the process. After `npm run build` the manifest names new hashed files and
the old ones are gone, but a running server keeps serving the **old** manifest
— so it references bundle files that no longer exist, the admin JavaScript
never loads, and every editor control silently does nothing.

**Restart the Flask server after every frontend build** before you trust a
browser check. The symptom is a page that renders but whose JavaScript is
dead, which looks like a bug in the code you just wrote.

---

## Themed SVG Art (2026-10-27)

**An SVG loaded through `<img>` cannot read the page's colour.** The plan for
Visual Design Phase 04 assumed it could: that `currentColor` inside the SVG
would resolve against the `<img>` element's own `color` property. It does not.
An SVG loaded as an image is an isolated document with no access to the host
page's cascade, and `currentColor` inside it resolves against the SVG
document's own root element — which is black.

Measured in Chromium: a page whose `<img>` sets `color: rgb(255, 0, 0)` and
whose SVG fills with `currentColor` renders **black**, both read back through a
canvas and sampled from a screenshot. Under that assumption the placeholder
would have rendered black in every theme, including the dark ones.

**Two mechanisms work, and they are not interchangeable.**

| Need | Mechanism |
|---|---|
| The colour comes from the theme | `mask-image` with the SVG as the mask, and `background-color` for the ink — the page backdrops already do this |
| The SVG stays an `<img>` | The SVG carries its own palette and cannot be themed |

Because the colour of an `<img>`'s content cannot be changed by CSS, the themed
mark has to be a `<span role="img" aria-label="…">` with the mask applied to
it, not an `<img>`.

**When a plan describes a browser mechanism, measure it before building on it.**
A plan is a specification, not evidence. The `currentColor` claim was plausible
enough to read as established, and it would have shipped a black-on-black
placeholder in fifty themes.

---

## Index Layout and Article Furniture (2026-10-27)

Two findings from the Visual Design phases that a future maintainer would
otherwise rediscover the hard way. Neither is visible by reading one rule.

### Equal specificity is decided by document order, not by intent

The table-of-contents entries never underlined. `base.css` gives every anchor
`text-decoration: none` and restores the underline on hover and focus with
`a:where(:not(.btn):not(.skip-link)):hover`, while `public.css` declared
`.post-toc a { text-decoration: none }`.

The two selectors have the **same** specificity. `:where()` contributes
nothing, so the hover rule counts as `a` (one type) plus `:hover` (one class)
— and `.post-toc a` counts as one class plus one type. `base.html` links
`public.css` after `base.css`, so the later sheet won the tie and the
entries never underlined, not even on hover, where the colour changed to the
accent but the underline did not appear.

**Equal-specificity conflicts are decided by document order, not by which
sheet "feels" more specific.** A rule that reads as more specific because it
names an element more precisely does not outrank a rule from a later sheet.
`public.css` now declares `text-decoration: underline` on `.post-toc a`
itself, so the entries read as links whatever the cascade does.

### The share panel's height comes from its buttons, not its label

The panel is 70px tall, and that number is set by the buttons. `.share-btn`
declares `min-height: 44px` and carries an 18px icon, so the bar's content
box is 44px; `.share-bar` adds `padding: 12px` above and below and a 1px
border on each side — 44 + 24 + 2 = 70px. The label is not what sets the
height, and the padding alone does not either.

**Any plan or issue that quotes the panel's height has to measure it.** The
same is true of the 94px the move gained: the panel stood above the article
body and is now below it, so the article's first paragraph starts 94px higher
— the 70px panel plus the 24px margin that used to separate it from the body.
Neither figure can be derived from the label.

---

## See Also

- [Architecture overview](../../architecture/overview.md) — the authoritative
  system design index
- [App factory and configuration](../../architecture/core/app-factory.md)
- [Data models](../../architecture/core/models.md)
- [API routes](../../architecture/routes/api-routes.md)
- [Operations services](../../architecture/services/operations.md)
- [Operator CLI](../../architecture/deployment/cli.md)

