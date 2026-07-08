# Agent Guidelines

Quick reference for AI agents working on this codebase.

## Project Overview

DevLog is a Flask blog CMS with admin dashboard, newsletter scheduling, FTS5 search, custom CSS theming, 2FA, comments, post series, and multi-admin sessions.

## Setup Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Set required env vars
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export ADMIN_PASSWORD="your-strong-password"

# Initialize database
export FLASK_APP=run:app
flask db upgrade

# Run tests
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python3 -m pytest tests/

# Run linter
ruff check .
ruff format --check .

# Type check
mypy app/
```

## Agent Override Convention

This codebase uses a **module-level override system** for agent context. Each module (directory with a specific purpose) may contain an `AGENTS.override.md` file that provides specialized handling instructions for that module.

When an agent operates within a module, it should:
1. Read the root `AGENTS.md` for general guidance
2. Check for `AGENTS.override.md` in the current module for specialized handling
3. Override files take precedence over root-level guidance when working within that module

## Module Override Files

| Module | Override File | Purpose |
|--------|---------------|---------|
| App Core | `app/AGENTS.override.md` | Flask app, models, extensions, core utilities |
| Routes | `app/routes/AGENTS.override.md` | General routing concerns, API authentication, RSS feeds, error handlers |
| Admin Routes | `app/routes/admin/AGENTS.override.md` | Admin dashboard, post/subscriber/user management |
| Public Routes | `app/routes/public/AGENTS.override.md` | Public page handlers |
| Frontend | `app/static/AGENTS.override.md` | JS/CSS assets, Vite build |
| Templates | `app/templates/AGENTS.override.md` | Jinja2 templates, filters |
| Tests | `tests/AGENTS.override.md` | Testing patterns, fixtures |
| Documentation | `docs/AGENTS.override.md` | Documentation structure |
| Scripts | `scripts/AGENTS.override.md` | Shell scripts, DevOps |
| Services | `app/services/AGENTS.override.md` | Backup, slug, serialization, tag services |
| Architecture | `architecture/AGENTS.override.md` | Architecture documentation |
| Plans | `plans/AGENTS.override.md` | Implementation plans and deferred items |

## Structure Convention

When adding agent guidance for a specific module:
1. Create `AGENTS.override.md` inside that module directory
2. Do not create a separate "agents" directory
3. Override files should be focused on module-specific concerns
4. Update this index when adding new override files

## Codebase Structure Reference

Important actual file locations (verify before assuming):

| Item | Actual Location |
|------|-----------------|
| API routes | `app/routes/api/` (PACKAGE with posts.py, subscribers.py, stats.py, auth.py) |
| Validators | `app/validators.py` (NOT `app/core/validators.py`) |
| Backup logic | `app/services/backup.py` (centralized service) |
| Admin Audit Log model | `app/models.py:461-481` |
| PostRevision model | `app/models.py:236-249` |
| User model `__repr__` | `app/models.py:63-64` |
| Comment model | `app/models.py` |
| Services | `app/services/` (backup, slug, serialization, tag) |
| Tag Cache | `app/tag_cache.py` (flask-caching with TTL) |
| DB Dialect Helpers | `app/db_utils.py` (`get_database_dialect()`, `is_sqlite_database()`) |

## Security & Privacy Rules

- **Log ID, not Username**: When logging user actions or system events, always use `user.id`. Never log raw User objects or usernames to prevent PII leakage.
- **Credential Protection**: Never log `SECRET_KEY`, `ADMIN_PASSWORD`, or API keys.
- **Route Verification**: Before editing or documenting routes, verify against actual implementation. Routes frequently differ from what documentation or comments claim.

## Code Style

- **Linting**: `ruff check .` and `ruff format --check .`
- **Type checking**: `mypy app/`
- **SQLAlchemy**: Use SQLAlchemy 2.0 style (`db.session.execute(select(...))` pattern)
- **No comments**: Do not add comments unless explicitly requested
- **Security**: Never commit secrets, keys, or credentials

## Important Notes for Future Agents

### APScheduler Multi-Container Limitation

APScheduler uses FileLock with `timeout=0` which only works on a single machine. Multiple container replicas will each run their own APScheduler and execute jobs concurrently. **Set `ENABLE_SCHEDULER=true` on exactly ONE container to prevent duplicate jobs.** The scheduler has an idempotency guard, but explicit opt-in via `ENABLE_SCHEDULER` is the recommended approach.

See [architecture/tasks/scheduler.md](architecture/tasks/scheduler.md) for full scheduler documentation.

### Vite Build Required for Production

The `npm run build` (or `vite build`) must be run before production deployment. The `manifest.json` must be present. If Vite build hasn't run, JS assets will return hashed paths that don't exist.

**Docker builds handle this automatically** via the multi-stage `Dockerfile` — the `frontend-builder` stage runs `npm run build` and copies the output to the final image. This note applies to non-Docker deployments only.

### APScheduler SMTP Handling

When SMTP_HOST is not configured, only the daily newsletter job is disabled. Other scheduler jobs (cleanup_expired_subscribers, publish_scheduled_posts, run_daily_backup) continue to run.

### Email Retry Count

Newsletter retry count default is 5 (not 3 as some documentation may claim).

### Template Context Variables

Use `site_title` and `site_description` as context variables (NOT `site_name` or `site_tagline`).

### Template Filters

Actual filters (defined in `app/filters.py`):

- `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`, `post_image_avif_url_stub`
- NOT `format_date`, `markdown`, `slugify` (these don't exist)

### Critical CSS

The `critical.css` file at `app/static/css/critical.css` provides above-the-fold CSS for fast initial paint. It is loaded in `base.html:24` with `media="screen"` for immediate loading.

### ENABLE_SCHEDULER

`ENABLE_SCHEDULER` (default: `false`) controls whether the APScheduler scheduler starts in a given container. Set it to `true` on exactly one container when running in production. The scheduler handles newsletters, subscriber cleanup, scheduled post publishing, and daily backups. Disabled by default so multiple replicas can run without duplicate jobs.

### Docker Compose Profiles

All services require explicit profiles. There is no default profile:
- `--profile production`: blog, celery, redis (app on `127.0.0.1:5000`)
- `--profile reverse-proxy`: nginx (optional reverse proxy with TLS)
- `--profile backup`: backup service

### CI Workflow

CI configuration is at `.github/workflows/ci.yml`. It includes 6 jobs: `lint-and-type`, `test`, `frontend-build`, `security-audit`, `docker-build`, `e2e-tests`. E2E tests run through a CI-only compose override (`docker-compose.ci.yml`) that publishes port 5000 directly, bypassing nginx. The `E2E_BASE_URL` env var controls the test target URL.

### Webhook Delivery Architecture

Webhook delivery uses a two-level dispatch pattern:
- `deliver_webhook_task` dispatches to `deliver_single_webhook_task`
- `deliver_single_webhook_task` handles per-webhook SSRF protection, HMAC signing, retry logic, and delivery status updates

See [architecture/infrastructure/webhooks.md](architecture/infrastructure/webhooks.md) for full details.

### Model Count

There are exactly 17 model classes in `app/models.py`: User, Post, Tag, Subscriber, Page, PageView, ShareEvent, AdminSession, SiteSettings, Webhook, WebhookEvent, Series, PostSeries, Comment, PostRevision, AdminAuditLog, ApiToken. Any documentation claiming 19 or 20 models is outdated.

See [architecture/core/models.md](architecture/core/models.md) for model details.

### Thread-Safe Storage Singleton

`app/storage.py:get_storage()` uses double-checked locking pattern with `threading.Lock()` for thread-safe singleton initialization.

### E2E Test Isolation

`tests/e2e/conftest.py` defines its own session-scoped `app` fixture with a separate database (`blog_e2e`). Running `pytest tests/e2e/` alone works. The `app_server` fixture uses readiness polling for server startup.

### Login Template Asset Loading

`admin/login_base.html` uses `vite_asset()` for CSS/JS assets, enabling CDN prefix support.

### Prism CSS Loading

Prism CSS is loaded via `data-prism-css-url` attribute which templates set using `vite_asset()`.

### Session IP Binding

`SESSION_IP_BINDING` is enforced via the `admin_required` decorator in `app/routes/admin/__init__.py:25-55`, not in the global `before_request_handler`. When IP mismatch is detected and mode is `enforce`, the admin session is invalidated and the user is redirected to login. When mode is `warn`, a warning is logged but session continues.

### Silent FTS Initialization

`app/__init__.py:430-433` catches `OperationalError` during FTS init silently. User is never informed if search won't work.

### LOGIN_FAILURE_DELAY

`app/routes/admin/auth.py:90` has `time.sleep(LOGIN_FAILURE_DELAY)` after invalid credentials. A minimum of 0.1s is enforced in `app/config.py`.

### Comment Rate Limit IP Resolution (Fixed)

Previously, comment rate limiting read `X-Forwarded-For` directly, which could be spoofed. Both limiter key functions now use `request.remote_addr`, which is normalized by `ProxyFix`. Proper `PROXY_COUNT` configuration remains important for correct IP resolution behind proxies.

### Nginx Proxy Configuration

`nginx/conf.d/blog.conf` uses `proxy_pass http://blog:5000` (Docker service name).

### RSS Cache Invalidation

`app/routes/rss.py:103-107` `invalidate_rss_cache()` invalidates `rss_feed_posts`, `atom_feed_posts`, and `json_feed_posts` cache keys.

### Prism Loading

Prism JS is loaded dynamically via `loadPrismIfNeeded()` in `main.js` when code blocks exist. Prism CSS and JS URLs are read from `data-prism-css-url`, `data-prism-js-url`, and `data-prism-langs-url` attributes on script tags, which use `vite_asset()` for theme selection.

### Admin Prism CSS Theme

`admin/base.html:9` uses `syntax_theme` variable for dynamic Prism CSS theme selection via `vite_asset('css/' + syntax_theme + '.css')`.

### Test Password Standardization

All tests use `os.environ["ADMIN_PASSWORD"]` to stay in sync with the environment variable. The `ADMIN_PASSWORD` env var must be set when running tests.

### Shared Test Fixtures Location

`clean_analytics_cache` and `ensure_buffer_disabled` are defined in `tests/shared_fixtures.py` and imported into all conftest files via `from tests.shared_fixtures import *`. The `api_client` fixture in `tests/conftest.py:120-130` is functionally identical to `authenticated_client`.

### Template Inheritance

Admin templates (`admin/base.html`) and public templates (`base.html`) are standalone root templates. `admin/base.html` does NOT extend `base.html`.

### marked.min.js Loading

`marked.min.js` is loaded via `vite_asset()` for content hashing and CDN support.

### Post/Page Published Nullable Columns

`Post.published` and `Page.published` at `app/models.py:196,166` have `nullable=False`. The database columns no longer allow NULL.

### User.failed_login_count Nullable

`User.failed_login_count` at `app/models.py:31` has `nullable=False`.

### CSRF Applies to All POSTs Except API Blueprint

CSRF validation is enforced globally for all POST requests in `app/__init__.py:301-303`, except API endpoints. The `should_skip_csrf()` predicate in `app/csrf.py` exempts requests where `request.blueprint == "api"`. API-key authenticated requests are protected by token secrecy, HTTPS, scopes, rate limits, and audit logging instead of browser CSRF tokens. Browser form POSTs (admin, public, subscribe, comments, logout) all require valid CSRF tokens.

### Benchmark Tests Celery Eager Config

`tests/benchmarks/conftest.py` configures `task_always_eager=True` for benchmark tests.

### SiteSettings.get_instance() Flush Side Effect

`SiteSettings.get_instance()` at `app/models.py:359` does `db.session.flush()` when creating a new instance. If called within a session that has other uncommitted changes, those changes are flushed (but not committed) as a side effect. Use `db.session.merge()` or `SELECT FOR UPDATE` to avoid this.

### _env_str Helper

`app/config.py:_env_str(key, default="")` reads env vars and treats empty strings as unset (returns default). Use this instead of `os.environ.get()` when empty-string-means-unset is desired.

### Env Var Fallback Chains

Database URI: `SQLALCHEMY_DATABASE_URI` → `DATABASE_URL` → SQLite default.
Cache Redis: `CACHE_REDIS_URL` → `REDIS_URL` → `redis://localhost:6379/0`.
Celery broker: `CELERY_BROKER_URL` → `REDIS_URL` → `redis://localhost:6379/0`.
Metrics: `ENABLE_METRICS=true` + `METRICS_SECRET` required in production.

### config.toml.example

`config.toml.example` exists as a template. `setup.sh` copies it to `config.toml` if absent. `config.toml` is gitignored — only `config.toml.example` is committed. If `config.toml` is missing, `app/config.py` falls back to `config.toml.example` with a warning.

### Health Endpoint Split

`/health` has two modes:
- **Basic** (`/health`): Returns only database + scheduler status. Fast, no auth required. Used for Docker healthchecks.
- **Detailed** (`/health?detailed=true`): Returns all 8 checks with details. Requires `HEALTH_CHECK_SECRET` via header (`X-Health-Secret`), Bearer token, or `?secret=` query param. In production without `HEALTH_CHECK_SECRET`, returns 403.

See [architecture/overview.md](architecture/overview.md#health-check-get-health) for full health check documentation.

### ENABLE_METRICS / METRICS_SECRET

`/metrics` is disabled by default (`ENABLE_METRICS=false`). When `ENABLE_METRICS=true`:
- Production: requires `METRICS_SECRET` via header (`X-Metrics-Secret`), Bearer token, or `?secret=` query param
- Without `METRICS_SECRET` in production: returns 403
- Startup validation: raises `RuntimeError` if `ENABLE_METRICS=true` + `is_production()` + no `METRICS_SECRET`

### python-dotenv Auto-Loading

`python-dotenv` is included in `requirements.txt` and called via `load_dotenv()` in both `run.py` and `app/config.py`. The app auto-loads `.env` without requiring manual `source` commands.

### setup.sh Behavior

`setup.sh` creates a venv, installs deps, generates `.env` (if missing), copies `config.toml` from template, then sources `.env`. It does NOT start the server — the final message tells the user to run `python run.py`.

### RELEASE.md

There is a release checklist at `RELEASE.md` for version bumps and release process. Refer to it before tagging releases.

### STORAGE_BACKEND

`STORAGE_BACKEND` env var (default: `"local"`) controls media storage. Set to `"s3"` for S3-compatible storage. When using S3, required env vars: `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`. Optional: `S3_REGION`, `S3_ENDPOINT`, `S3_PUBLIC_URL`. If required S3 vars are missing, falls back to local storage with a warning.

See [architecture/infrastructure/storage.md](architecture/infrastructure/storage.md) for storage architecture details.

## Additional Notes for Future Agents

### Line Number References in Documentation

Line number references in architecture documentation drift over time. Prefer symbolic references (function names, class names) over exact line numbers when possible. When line numbers are required, verify against current codebase before publishing.

For detailed implementation history, deprecated features, actual route corrections, test interference notes, encryption module details, task line numbers, and other maintainer context, see:

> [docs/internals/agent-maintainer-notes.md](docs/internals/agent-maintainer-notes.md)

## Skills

Load specialized skills using the `skill` tool with the skill name.

| Skill | Description | Triggers |
|-------|-------------|----------|
| `blog_cms` | Blog CMS - Flask-based blogging platform with admin dashboard, newsletter scheduling, FTS5 search, multi-admin sessions, custom CSS theming, syntax highlighting themes, post series, Atom feed, 2FA, Comments, Audit Log, Post Revision Diff | Flask app, SQLAlchemy, session management, CSRF, newsletter, APScheduler, FTS5, REST API, password reset, post revisions, preview links, toasts, dashboard charts, graceful shutdown, Docker deployment, Vite bundler, 2FA, Comments, Audit Log |
| `architecture_review` | Architecture documentation review and improvement workflow | architecture, review, documentation, verify, cross-reference, architecture review plan |

## Skills Directory Note

Skills are stored in `.skills/` (local directory). The `blog_cms` skill is also registered in `.opencode/skills/blog_cms/` for the opencode agent. When adding new skills, create a `skill.md` in `.skills/<skill_name>/` and optionally register in `.opencode/skills/<skill_name>/SKILL.md`.
