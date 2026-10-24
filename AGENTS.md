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

# Run a single test file
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 .venv/bin/python3 -m pytest tests/test_models.py -v

# Run linter
ruff check .
ruff format --check .

# Type check
mypy app/ devlog_cli/

# Check dependency manifest consistency
python scripts/check_dependency_manifest_consistency.py

# Release validation (lint + type + tests + build + Docker + Compose config)
./scripts/release_check.sh
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
| Services | `app/services/AGENTS.override.md` | Centralized service layer (backup, slug, serialization, tag, theme_settings) |
| Architecture | `architecture/AGENTS.override.md` | Architecture documentation |
| Plans | `plans/AGENTS.override.md` | Implementation plans and deferred items |

## Codebase Structure Reference

Important actual file locations (verify before assuming):

| Item | Actual Location |
|------|-----------------|
| API routes | `app/routes/api/` (PACKAGE with posts.py, pages.py, series.py, tags.py, subscribers.py, stats.py, auth.py) |
| API scope matching | `scope_allows()` in `app/routes/api/auth.py` — exact match, `admin:*` grants all, category wildcards (`posts:*` etc.) |
| Validators | `app/validators.py` (NOT `app/core/validators.py`) |
| Backup logic | `app/services/backup.py` (centralized service) |
| Admin Audit Log model | `app/models.py` — `AdminAuditLog` class |
| PostRevision model | `app/models.py` — `PostRevision` class |
| Comment model | `app/models.py` |
| Services | `app/services/` (backup, encryption, search, serialization, slug, tag) |
| Theme settings service | `app/services/theme_settings.py` — validation, migration, effective name resolution |
| Typed config package | `app/config/` — typed config model, loader, validation, provenance, secrets, profiles, serialization, migration |
| Theme config | `app/config.py` → `app/config_legacy.py` — legacy globals re-exported via `app/config/__init__.py` for backward compat |
| Tag Cache | `app/tag_cache.py` (flask-caching with TTL) |
| DB Dialect Helpers | `app/db_utils.py` (`get_database_dialect()`, `is_sqlite_database()`) |
| CLI package | `devlog_cli/` — standalone Click CLI (main, context, output, errors, exit_codes, result) |
| CLI entry point | `devlog_cli.main:main` — registered as `devlog` in `pyproject.toml [project.scripts]` |
| CLI config commands | `devlog_cli/commands/config.py` — `config check`, `config show`, `config explain`, `config paths`, `config init`, `config migrate` |
| CLI admin commands | `devlog_cli/commands/admin.py` |
| CLI db commands | `devlog_cli/commands/db.py` |
| CLI data commands | `devlog_cli/commands/data.py` |
| CLI theme commands | `devlog_cli/commands/themes.py` |
| CLI backup commands | `devlog_cli/commands/backup.py` |
| CLI onboard commands | `devlog_cli/commands/onboard.py` — detect, plan, run with `--scope` option (system/user) |
| CLI deploy commands | `devlog_cli/commands/deploy.py` — `deploy render`, `deploy install`, `deploy check` |
| CLI lifecycle commands | `devlog_cli/commands/lifecycle.py` — `start`, `stop`, `restart`, `status`, `logs` |
| CLI doctor command | `devlog_cli/commands/doctor.py` — `doctor`, `doctor --production`, `doctor --check CHECK_ID`, `doctor --category CATEGORY`, `doctor --fix-safe`, `doctor --list-checks` |
| Operations services | `app/services/operations/` (admin, database, media, transfer, themes, backup, results) |
| Deploy service | `app/services/operations/deploy.py` |
| Onboard service | `app/services/operations/onboard.py` — detect, plan, apply |
| Doctor service | `app/services/operations/doctor.py` — diagnostic check registry, execution engine, safe fixes, 76 check implementations across 14 categories |
| Onboarding package | `app/onboarding/` (model, state, steps, planner, secrets, metadata, rendering) |
| Deployment module | `app/deployment/` (model, systemd, compose, proxy, logrotate, install, drift, lifecycle) |
| Operations tests | `tests/services/` |
| Filesystem layout | `app/filesystem/` (layout, prepare, discovery, migration, verification) |
| Paths CLI commands | `devlog_cli/commands/paths.py` — `paths status`, `paths discover-legacy`, `paths migrate`, `paths check` |
| Dependency consistency | `scripts/check_dependency_manifest_consistency.py` |
| Installer | `scripts/install.sh` — one-shot native/Docker installer |
| Dev setup | `scripts/setup-dev.sh` — development environment setup |
| Checksum generation | `scripts/generate_checksums.py` — release artifact checksums |
| Artifact verification | `scripts/check_release_artifacts.py` — verify wheel/checksums |

## Security & Privacy Rules

- **Log ID, not Username**: When logging user actions or system events, always use `user.id`. Never log raw User objects or usernames to prevent PII leakage.
- **Credential Protection**: Never log `SECRET_KEY`, `ADMIN_PASSWORD`, or API keys.
- **Route Verification**: Before editing or documenting routes, verify against actual implementation. Routes frequently differ from what documentation or comments claim.

## Code Style

- **Linting**: `ruff check .` and `ruff format --check .`
- **Type checking**: `mypy app/ devlog_cli/`
- **SQLAlchemy**: Use SQLAlchemy 2.0 style (`db.session.execute(select(...))` pattern)
- **No comments**: Do not add comments unless explicitly requested
- **Security**: Never commit secrets, keys, or credentials

## Important Notes for Future Agents

### APScheduler Multi-Container Limitation

APScheduler uses FileLock with `timeout=0` which only works on a single machine. Multiple container replicas will each run their own APScheduler and execute jobs concurrently. **Set `ENABLE_SCHEDULER=true` on exactly ONE container to prevent duplicate jobs.** The scheduler has an idempotency guard, but explicit opt-in via `ENABLE_SCHEDULER` is the recommended approach. Disabled by default so multiple replicas can run without duplicate jobs.

The scheduler handles newsletters, subscriber cleanup, scheduled post publishing, and daily backups. When SMTP_HOST is not configured, only the daily newsletter job is disabled; other jobs continue to run.

See [architecture/tasks/scheduler.md](architecture/tasks/scheduler.md) for full scheduler documentation.

### Vite Build Required for Production

The `npm run build` (or `vite build`) must be run before production deployment. The `manifest.json` must be present. If Vite build hasn't run, JS assets will return hashed paths that don't exist.

**Docker builds handle this automatically** via the multi-stage `Dockerfile` — the `frontend-builder` stage runs `npm run build` and copies the output to the final image. This note applies to non-Docker deployments only.

### Entry Point

`run.py` is the development entry point. It wraps the WSGI app with `asgiref.wsgi.WsgiToAsgi` for ASGI compatibility (used by Granian in production). For production, use Granian via Docker Compose rather than `python run.py`.

### Email Retry Count

Newsletter retry count default is 5 (not 3 as some documentation may claim).

### Template Context Variables

Use `site_title` and `site_description` as context variables (NOT `site_name` or `site_tagline`).

### Template Filters

Actual filters (defined in `app/filters.py`):

- `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`
- `post_image_avif_url_stub` — DEPRECATED: stub, always returns None
- NOT `format_date`, `markdown`, `slugify` (these don't exist)

### Critical CSS

The `critical.css` file at `app/static/css/critical.css` provides above-the-fold CSS for fast initial paint. It is loaded in `base.html` with `media="screen"` for immediate loading.

### Docker Compose Profiles

All services require explicit profiles. There is no default profile:
- `--profile production`: blog, celery, redis (app on `127.0.0.1:5000`)
- `--profile reverse-proxy`: nginx (optional reverse proxy with TLS)
- `--profile backup`: backup service

### CI Workflow

CI configuration is at `.github/workflows/ci.yml`. It includes 11 jobs: `lint-and-type`, `test`, `theme-policy`, `migration-chain`, `theme-package-verification`, `frontend-build`, `security-audit`, `docker-build`, `e2e-tests`, `dependency-consistency`, and `release1-package-smoke`. E2E tests run through a CI-only compose override (`docker-compose.ci.yml`) that publishes port 5000 directly, bypassing nginx. The `E2E_BASE_URL` env var controls the test target URL.

### Webhook Delivery Architecture

Webhook delivery uses a two-level dispatch pattern:
- `deliver_webhook_task` dispatches to `deliver_single_webhook_task`
- `deliver_single_webhook_task` handles per-webhook SSRF protection, HMAC signing, retry logic, and delivery status updates

See [architecture/infrastructure/webhooks.md](architecture/infrastructure/webhooks.md) for full details.

### Model Count

There are exactly 17 model classes in `app/models.py`: User, Post, Tag, Subscriber, Page, PageView, ShareEvent, AdminSession, SiteSettings, Webhook, WebhookEvent, Series, PostSeries, Comment, PostRevision, AdminAuditLog, ApiToken. Any documentation claiming 19 or 20 models is outdated. Note: `OperationResult` and its subclasses in `app/services/operations/results.py` are plain dataclasses, not SQLAlchemy models.

Type-check coverage includes both `app/` and `devlog_cli/`.

See [architecture/core/models.md](architecture/core/models.md) for model details.

### Filesystem Layout (Phase F)

The codebase has a centralized filesystem path system at `app/filesystem/`:

- `app/filesystem/layout.py` — `RuntimePaths` dataclass with `InstallMode` (system, user, docker, development) and `PathProvenance` tracking
- `app/filesystem/prepare.py` — directory creation with permissions and security checks
- `app/filesystem/discovery.py` — legacy layout discovery (read-only)
- `app/filesystem/migration.py` — migration planner and executor; `MigrationPlan` (dry-run) and `execute_migration()` (apply)
- `app/filesystem/verification.py` — post-migration verification

CLI commands: `devlog paths status`, `devlog paths discover-legacy`, `devlog paths migrate`, `devlog paths check`

Key items:
- `MigrationExecutionResult` dataclass returned by `execute_migration()` — tracks `ok`, `completed_steps`, `total_steps`, `errors`, `completed_paths`
- `execute_migration()` performs a SQLite WAL checkpoint (`PRAGMA wal_checkpoint(TRUNCATE)`) on the source database before executing move/copy steps

The `PathsConfig` section in `app/config/model.py` allows overriding derived paths via `config.toml` or `DEVLOG_*` env vars.

Key rules:
- All paths are absolute after resolution
- Explicit overrides always win over env vars and mode defaults
- Legacy discovery is read-only; migration planning defaults to dry-run
- Production services must not require write access to source directories

### Service Extraction (Phase C)

Operational business logic has been extracted from `app/cli.py` into `app/services/operations/`. The standalone `devlog` CLI commands in `devlog_cli/commands/` call these services. Flask commands in `app/cli.py` remain as compatibility wrappers.

Service functions:
- Never depend on Click, terminal output, or process exit
- Return typed `OperationResult` subclasses from `app/services/operations/results.py`
- Require application context (use `from flask import current_app`)
- Use `commit_with_rollback()` for transaction boundaries

CLI command flow:
```
CLI handler -> CliContext.ensure_app_context() -> call service function -> render Result
```

Flask compatibility flow:
```
Flask command wrapper -> call same service function -> render compatibility output
```

## Codebase Structure Reference

Important actual file locations (verify before assuming):

| Item | Actual Location |
|------|-----------------|
| API routes | `app/routes/api/` (PACKAGE with posts.py, pages.py, series.py, tags.py, subscribers.py, stats.py, auth.py) |
| API scope matching | `scope_allows()` in `app/routes/api/auth.py` — exact match, `admin:*` grants all, category wildcards (`posts:*` etc.) |
| Validators | `app/validators.py` (NOT `app/core/validators.py`) |
| Backup logic | `app/services/backup.py` (centralized service) |
| Admin Audit Log model | `app/models.py` — `AdminAuditLog` class |
| PostRevision model | `app/models.py` — `PostRevision` class |
| Comment model | `app/models.py` |
| Services | `app/services/` (backup, encryption, search, serialization, slug, tag) |
| Theme settings service | `app/services/theme_settings.py` — validation, migration, effective name resolution |
| Typed config package | `app/config/` — typed config model, loader, validation, provenance, secrets, profiles, serialization, migration |
| Theme config | `app/config.py` → `app/config_legacy.py` — legacy globals re-exported via `app/config/__init__.py` for backward compat |
| Tag Cache | `app/tag_cache.py` (flask-caching with TTL) |
| DB Dialect Helpers | `app/db_utils.py` (`get_database_dialect()`, `is_sqlite_database()`) |
| CLI package | `devlog_cli/` — standalone Click CLI (main, context, output, errors, exit_codes, result) |
| CLI entry point | `devlog_cli.main:main` — registered as `devlog` in `pyproject.toml [project.scripts]` |
| CLI config commands | `devlog_cli/commands/config.py` — `config check`, `config show`, `config explain`, `config paths`, `config init`, `config migrate` |
| CLI admin commands | `devlog_cli/commands/admin.py` |
| CLI db commands | `devlog_cli/commands/db.py` |
| CLI data commands | `devlog_cli/commands/data.py` |
| CLI theme commands | `devlog_cli/commands/themes.py` |
| CLI backup commands | `devlog_cli/commands/backup.py` |
| CLI onboard commands | `devlog_cli/commands/onboard.py` — detect, plan, run with `--scope` option (system/user) |
| CLI deploy commands | `devlog_cli/commands/deploy.py` — `deploy render`, `deploy install`, `deploy check` |
| CLI lifecycle commands | `devlog_cli/commands/lifecycle.py` — `start`, `stop`, `restart`, `status`, `logs` |
| CLI doctor command | `devlog_cli/commands/doctor.py` — `doctor`, `doctor --production`, `doctor --check CHECK_ID`, `doctor --category CATEGORY`, `doctor --fix-safe`, `doctor --list-checks` |
| Operations services | `app/services/operations/` (admin, database, media, transfer, themes, backup, results) |
| Deploy service | `app/services/operations/deploy.py` |
| Onboard service | `app/services/operations/onboard.py` — detect, plan, apply |
| Doctor service | `app/services/operations/doctor.py` — diagnostic check registry, execution engine, safe fixes, 76 check implementations across 14 categories |
| Deployment module | `app/deployment/` (model, systemd, compose, proxy, logrotate, install, drift, lifecycle) |
| Operations tests | `tests/services/` |
| Filesystem layout | `app/filesystem/` (layout, prepare, discovery, migration, verification) |
| Paths CLI commands | `devlog_cli/commands/paths.py` — `paths status`, `paths discover-legacy`, `paths migrate`, `paths check` |

### Thread-Safe Storage Singleton

`app/storage.py:get_storage()` uses double-checked locking pattern with `threading.Lock()` for thread-safe singleton initialization.

### E2E Test Isolation

`tests/e2e/conftest.py` defines its own session-scoped `app` fixture with a separate database (`blog_e2e`). Running `pytest tests/e2e/` alone works. The `app_server` fixture uses readiness polling for server startup.

### Session IP Binding

`SESSION_IP_BINDING` is enforced via the `admin_required` decorator in `app/routes/admin/__init__.py`, not in the global `before_request_handler`. When IP mismatch is detected and mode is `enforce`, the admin session is invalidated and the user is redirected to login. When mode is `warn`, a warning is logged but session continues.

### Silent FTS Initialization

`app/__init__.py` catches `OperationalError` during FTS init silently. User is never informed if search won't work.

### LOGIN_FAILURE_DELAY

`app/routes/admin/auth.py` has `time.sleep(LOGIN_FAILURE_DELAY)` after invalid credentials. A minimum of 0.1s is enforced in `app/config.py`.

### CSRF Applies to All POSTs Except API Blueprint

CSRF validation is enforced globally for all POST requests in `app/__init__.py`, except API endpoints. The `should_skip_csrf()` predicate in `app/csrf.py` exempts requests where `request.blueprint == "api"`. API-key authenticated requests are protected by token secrecy, HTTPS, scopes, rate limits, and audit logging instead of browser CSRF tokens. Browser form POSTs (admin, public, subscribe, comments, logout) all require valid CSRF tokens.

### SiteSettings.get_instance() Flush Side Effect

`SiteSettings.get_instance()` does `db.session.flush()` when creating a new instance. If called within a session that has other uncommitted changes, those changes are flushed (but not committed) as a side effect. Use `db.session.merge()` or `SELECT FOR UPDATE` to avoid this.

### _env_str Helper

`app/config_legacy.py:_env_str(key, default="")` reads env vars and treats empty strings as unset (returns default). Use this instead of `os.environ.get()` when empty-string-means-unset is desired.

### Typed Configuration System

The codebase has a typed configuration system at `app/config/` that replaces the legacy `app/config.py` (now `app/config_legacy.py`). The package provides:

- `app/config/model.py` — 20 frozen dataclasses (`DevLogConfig` + 19 section classes)
- `app/config/loader.py` — `load_effective_config()` with precedence chain (env vars > config.toml > defaults)
- `app/config/paths.py` — path resolution with source tracking
- `app/config/validation.py` — multi-layer validation (schema, security, filesystem, dependencies, compatibility)
- `app/config/provenance.py` — source tracking for config values
- `app/config/secrets.py` — secret field identification and redaction
- `app/config/profiles.py` — deployment profiles (development, native-production, docker-production, minimal, full)
- `app/config/serialization.py` — TOML/JSON output with redaction
- `app/config/migration.py` — config version migration support

`app/config/__init__.py` re-exports legacy globals for backward compat. The CLI provides `devlog config check/show/explain/paths/init/migrate` commands. Tests are in `tests/config/` (235 tests).

**The typed config system (`app/config/model.py`) is the canonical source of truth for all configuration fields and their defaults.** `config.toml.example` mirrors these defaults. When adding or modifying config fields, update the dataclass in `model.py` first — the loader and example file follow from it.

### Env Var Fallback Chains

Database URI: `SQLALCHEMY_DATABASE_URI` → `DATABASE_URL` → SQLite default.
Cache Redis: `CACHE_REDIS_URL` → `REDIS_URL` → `redis://localhost:6379/0`.
Rate limit Redis: `RATE_LIMIT_STORAGE_URI` → `redis_url` → `redis://localhost:6379/0`.
Celery broker: `CELERY_BROKER_URL` → `REDIS_URL` → `redis://localhost:6379/0`.
Metrics: `ENABLE_METRICS=true` + `METRICS_SECRET` required in production.

These chains are defined in `app/config/loader.py` (`_resolve_database_uri`, `_resolve_cache_redis_url`, `_resolve_celery_broker_url`). The full env var → config field mapping is in `_ENV_OVERRIDE_MAP`.

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

### SESSION_COOKIE_SECURE

`SESSION_COOKIE_SECURE` defaults to `"true"` (read in `app/__init__.py`). In production behind HTTPS, keep it `true`. For local HTTP testing at `http://localhost:5000`, set `SESSION_COOKIE_SECURE=false` or admin login cookies will not persist. Never use `SESSION_COOKIE_SECURE=false` in production behind HTTPS.

### STORAGE_BACKEND

`STORAGE_BACKEND` env var (default: `"local"`) controls media storage. Set to `"s3"` for S3-compatible storage. When using S3, required env vars: `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`. Optional: `S3_REGION`, `S3_ENDPOINT`, `S3_PUBLIC_URL`. If required S3 vars are missing, falls back to local storage with a warning.

See [architecture/infrastructure/storage.md](architecture/infrastructure/storage.md) for storage architecture details.

### config.toml.example

`config.toml.example` exists as a template. `scripts/setup-dev.sh` copies it to `config.toml` if absent. `config.toml` is gitignored — only `config.toml.example` is committed. If `config.toml` is missing, `app/config_legacy.py` falls back to `config.toml.example` with a warning. The typed config system (`app/config/loader.py`) resolves the same precedence chain: env vars > config.toml > defaults.

### python-dotenv Auto-Loading

`python-dotenv` is included in `requirements.txt` and called via `load_dotenv()` in both `run.py` and `app/config/__init__.py`. The app auto-loads `.env` without requiring manual `source` commands.

### setup.sh Behavior

`scripts/setup-dev.sh` creates a venv, installs deps, generates `.env` (if missing), copies `config.toml` from template, then sources `.env`. It does NOT start the server — the final message tells the user to run `python run.py`.

### Installer

`scripts/install.sh` is a one-shot installer for native and Docker modes. It downloads versioned release artifacts, verifies SHA-256 checksums, installs into a versioned directory layout (`/opt/devlog/releases/X.Y.Z/venv/`), creates an atomic symlink at `/opt/devlog/current`, and creates a launcher at `/usr/local/bin/devlog`. The installer does not create configuration or database state — that is delegated to `devlog onboard`.

### RELEASE.md

There is a release checklist at `RELEASE.md` for version bumps and release process. Refer to it before tagging releases.

### Test Password Standardization

All tests use `os.environ["ADMIN_PASSWORD"]` to stay in sync with the environment variable. The `ADMIN_PASSWORD` env var must be set when running tests.

### Shared Test Fixtures Location

`clean_analytics_cache` and `ensure_buffer_disabled` are defined in `tests/shared_fixtures.py` and imported into all conftest files via `from tests.shared_fixtures import *`. The `api_client` fixture in `tests/conftest.py` is functionally identical to `authenticated_client`.

### Template Inheritance

Admin templates (`admin/base.html`) and public templates (`base.html`) are standalone root templates. `admin/base.html` does NOT extend `base.html`.

### Post/Page Published Nullable Columns

`Post.published` and `Page.published` have `nullable=False`. The database columns no longer allow NULL.

### User.failed_login_count Nullable

`User.failed_login_count` has `nullable=False`.

### Benchmark Tests Celery Eager Config

`tests/benchmarks/conftest.py` configures `task_always_eager=True` for benchmark tests.

### Line Number References in Documentation

Line number references in architecture documentation drift over time. Prefer symbolic references (function names, class names) over exact line numbers when possible. When line numbers are required, verify against current codebase before publishing.

### Maintainer Context

For detailed implementation history, deprecated features, actual route corrections, test interference notes, encryption module details, task line numbers, and other maintainer context, see:

> [docs/internals/agent-maintainer-notes.md](docs/internals/agent-maintainer-notes.md)

### Halloy Theme Migration (complete + final verification pass)

The project migrated from a 4-preset hardcoded theme system to a Halloy-compatible theme system with 50 bundled themes. All 15 phases are complete and the final verification pass is done:

- Phase 01: inventory + token contract
- Phase 02: parser + color primitives
- Phase 03: blog translation layer
- Phase 04: safe registry and external overrides
- Phase 05: packaging
- Phase 06: runtime integration (SiteSettings columns, Alembic migration, theme settings validation service, config.toml theme section)
- Phase 07: Flask and Jinja runtime integration (centralized ThemeService, dual-scheme CSS emission, context processor overhaul)
- Phase 08: visitor color-scheme behavior (3-state system/dark/light, bootstrap script, CSS selector migration, static light palette block removed)
- Phase 09: CSS and generated-markup audit (hardcoded literals replaced with CSS custom properties, 34 REPLACE converted, 35 legacy vars emitted)
- Phase 10: admin selection and preview (registry-based theme selector)
- Phase 11: operator CLI (flask themes list/validate/inspect/refresh/accessibility)
- Phase 12: accessibility validation (WCAG contrast checks with severity classification, catalog-wide validation, classification audit)
- Phase 13: performance and reliability (benchmarks, cache validation, malformed file isolation)
- Phase 14: documentation and legacy removal (THEME_PRESETS removed, emergency fallback uses EMERGENCY_DEFAULT)
- Phase 15: legacy removal and release closure (THEME_PRESETS removed, theme_preset column dropped, emergency fallback uses EMERGENCY_DEFAULT)

The phased plan is at `plans/halloy_theme_system_roadmap.md`.

#### Key files (runtime)

- `app/context_processors.py` — `theme_vars` injection from ThemeService
- `app/templates/base.html:42-48` and `app/templates/admin/base.html:17-23` — `theme_vars` CSS custom property injection
- `app/routes/admin/settings.py` — admin settings page (registry-based theme selector)
- `app/cli.py:343-610` — theme CLI commands (list, validate, inspect, refresh, paths, accessibility)
- `app/services/theme_settings.py` — `validate_theme_settings()`, `get_effective_theme_names()`
- `app/themes/service.py` — `ThemeService` class, `init_theme_service()`, `get_theme_service()` (app-scoped via `app.extensions["theme_service"]`)

#### Key files (Phase 01 deliverables)

- `scripts/theme_inventory.py` — catalog inventory CLI/Python API
- `tests/themes/` — inventory tests
- `docs/themes/supported-schema.md` — Phase 02 parser input contract
- `docs/themes/blog-theme-contract.md` — Phase 03 translator output contract (44 semantic tokens + 26 aliases)
- `docs/themes/frontend-literal-audit.md` — Phase 09 execution list (128 literals: 34 REPLACE converted, 71 RETAIN, 9 FALSE_POS)
- `docs/themes/legacy-compatibility.md` — Phase 06/14 migration rules

#### Key files (Phase 02 deliverables)

- `app/themes/__init__.py` — public API exports
- `app/themes/colors.py` — color primitives (RGB, RGBA, hex parsing, alpha compositing, luminance, WCAG contrast, dark/light classification, mix, lightness adjustment, HSL shifting)
- `app/themes/halloy.py` — typed Halloy TOML parser with dataclass models and structured error classes
- `tests/themes/test_colors.py` — color primitive tests
- `tests/themes/test_halloy_parser.py` — parser tests including parametrized catalog test (50 files)
- `tests/themes/fixtures/*.toml` — minimal, full, light, dark, alpha, extra_sections, wrong_type, malformed, invalid_color, injection fixtures

#### Key files (Phase 03 deliverables)

- `app/themes/model.py` — `BlogTheme` frozen dataclass (50 fields: 44 semantic tokens + 6 RGBA fields), `CSS_VARS` mapping, `ALIASES` backward-compat mapping, `EMERGENCY_DEFAULT` constant
- `app/themes/translate.py` — `translate_halloy_theme()`, `to_css_variables()`, `to_theme_vars()`, `to_legacy_vars()`
- `app/themes/diagnostics.py` — expanded accessibility validation with severity categories, structured findings, catalog-wide validation
- `tests/themes/test_translation.py` — translation, derivation, foreground selection, catalog-wide tests
- `tests/themes/test_theme_css.py` — CSS serialization, ordering, selector, legacy vars tests
- `scripts/theme_accessibility_report.py` — catalog quality report generator
- `tests/themes/test_accessibility.py` — comprehensive accessibility tests

#### Key files (Phase 04 deliverables — corrective closure + small closure pass complete)

- `app/themes/resources.py` — `ThemeResource` protocol, `_PathResource`/`_TraversableResource` implementations, `normalize_theme_name()`, `ThemeFileInfo.read_bytes()` method; `discover_bundled_package()` attaches `_TraversableResource`
- `app/themes/cache.py` — `ThemeCache` in-process cache, `ThemeCacheEntry` dataclass with `source_fingerprint` field, `invalidate_prefix()` method, `validate_entry()` accepts current metadata from caller
- `app/themes/registry.py` — `ThemeRegistry` class (`list_themes()`, `resolve()`, `load()`, `invalidate()`, `get_fallback()`), `ThemeDescriptor`, `LoadedTheme`, `_CatalogEntry` (pairs descriptor + file_info), structured exceptions (`ThemeNotFoundError`, `ThemeParseFailure`, `ThemeLoadError`, `ThemeValidationError`), `_THEME_ALIASES` for legacy migration, `_compute_fingerprint()` for cache validation, named invalidation rebuilds catalog. Default `default_theme="Catppuccin Mocha"`
- `tests/themes/test_registry.py` — Updated for new exception types and default theme name
- `tests/themes/test_theme_resolution_security.py` — 44 tests: name validation, symlink escape, traversal attacks, encoded separators

#### Key files (Phase 05 deliverables)

- `app/themes/bundled/` — packaged Halloy theme files shipped with the app (50 `.toml` files + `__init__.py` + `catalog_manifest.json` + `ATTRIBUTION.md`)
- `app/themes/resources.py` — `discover_bundled_package()` using `importlib.resources` for wheel-safe resource access
- `app/themes/registry.py` — default `bundled_root` changed to `app/themes/bundled/`
- `pyproject.toml` — `[tool.setuptools.package-data]` entry for `app.themes.bundled`
- `MANIFEST.in` — `recursive-include app/themes/bundled *.toml` for sdist inclusion
- `tests/themes/test_build_artifact.py` — Rewritten with fast archive-content tests + slow wheel-build tests
- `scripts/verify_theme_package.py` — New manual verification script

#### Hard rules (post-migration)

- `THEME_PRESETS` has been removed from `app/models.py`; `theme_preset` column dropped from `SiteSettings`; emergency fallback uses `EMERGENCY_DEFAULT` from `app/themes/model.py`
- `theme_vars` Jinja context shape is stable and consumed by templates
- `themes/*.toml` source catalog is the canonical development reference
- Bundled theme resources use `importlib.resources`, never `Path(__file__).parent.parent.parent` or cwd-relative paths
- Existing CSS files (`base.css`, `critical.css`, `layout.css`, etc.) use CSS custom properties for all theme-sensitive colors

#### Accessibility policy

The accessibility policy uses a three-tier classification system: `recommended`, `compatible-with-exceptions`, and `experimental`. Classification is performed by `classify_theme_eligibility()` in `app/themes/diagnostics.py`. The exception manifest is at `app/themes/ACCESSIBILITY_EXCEPTIONS.json` with `schema_version: 2` and per-theme `policy_class` entries. CI enforces the policy via the `theme-policy` job and the `flask themes accessibility --strict` CLI flag.

#### Key files (catalog source)

- `themes/*.toml` — top-level Halloy catalog (50 source files; ignore macOS `._*.toml` metadata files)
- `app/themes/bundled/` — packaged Halloy theme files shipped with the app (50 `.toml` files + `__init__.py` + `catalog_manifest.json` + `ATTRIBUTION.md`)

### Frontend Corrective Roadmap (complete)

A frontend review on 2026-10-23 found 50 findings across the public site, admin dashboard, stylesheet layer, and JavaScript module layer (5 critical, 12 high, 25 medium, 8 low). **All 50 are fixed.** The phased plan and the per-phase closure evidence are at `plans/frontend_corrective_roadmap.md`.

Phases, in dependency order:

- `plans/frontend_corrective_phase_01_image_pipeline.md` — post image URLs were double-prefixed and 404, `srcset="None"` was emitted, and every `loading="lazy"` image was permanently `opacity: 0`
- `plans/frontend_corrective_phase_02_public_interaction_and_build.md` — the lightbox never opened, the mobile menu and colour-scheme default were broken, the Vite build emitted an orphaned CSS asset
- `plans/frontend_corrective_phase_03_admin_form_contracts.md` — media uploads always failed, Theme Preview always 403'd, the unsanitised markdown preview was an XSS vector
- `plans/frontend_corrective_phase_04_css_cascade_and_theme_tokens.md` — the mobile nav could not collapse, the post title was 1.12:1 in dark mode, `--shadow-color` and `--code-bg` were never emitted
- `plans/frontend_corrective_phase_05_accessibility_and_seo.md` — the sidebar's series navigation pointed at a non-existent endpoint, social metadata was empty by default

These are now the standing contract for the affected surfaces:

- `post_image_url` returns a **URL** (not a filename) and must not be re-wrapped with `url_for('static', ...)`.
- The admin CSRF header is `X-CSRF-Token`, defined once in `app/csrf.py` as `CSRF_HEADER_NAME` and published to the browser as `data-csrf-header`. Client code uses `csrfHeaders()`.
- CSS rules that must win must not tie on specificity with a later stylesheet — scope them instead.
- `main.js` must not import a stylesheet; Flask links them so dev and production share one cascade.
- Every `var(--x)` a stylesheet references must be emitted by the theme runtime or defined in a stylesheet. `tests/test_css_contracts.py` enforces this.

See `app/static/AGENTS.override.md` for the full cross-layer contract list.

### Site Identity, Authorship and Layout Roadmap (open)

An operator review of the running instance on 2026-10-24 found eight gaps.
**The plan is written; no phase is implemented yet.** The roadmap and the
per-phase findings are at `plans/site_identity_authoring_roadmap.md`. Every
finding was confirmed by rendering the instance in Chromium and measuring the
DOM, not by reading templates.

Phases, in dependency order:

- `plans/site_identity_phase_01_admin_settings.md` — the theme preview sat *below* the theme selector it previews, so the operator had to keep scrolling up and down to see a result; there was no comments switch; the footer was hardcoded. **Part A (the preview placement) has shipped** — the mechanism is unchanged, only the panel moved above the selector, gained a reserved non-resizing footprint, and is scrolled into view when produced
- `plans/site_identity_phase_02_user_profiles.md` — `users` had no profile fields; `/admin/users` had no profile editor, so there was nowhere to set a picture or a bio
- `plans/site_identity_phase_03_public_auth.md` — there was no public login, so the three non-admin accounts in the database could not authenticate at all
- `plans/site_identity_phase_04_authorship_and_author_pages.md` — `posts` had no `author_id`; the rendered author was a single config value, empty by default and never a link; there was no author page
- `plans/site_identity_phase_05_page_navigation.md` — published pages worked at `/page/<slug>` but nothing on the site linked to them
- `plans/site_identity_phase_06_comments_layout.md` — the comment block had no CSS at all and sat 176px to the left of the post column on desktop; replies had no indent

Rules that apply to this series:

- One value, one producer. `comments_enabled` and `footer_text` are owned by Phase 01; the page-menu fields by Phase 05; the profile fields by Phase 02; `Post.author_id` by Phase 04; the comment CSS by Phase 06.
- The single Alembic head is `drop_theme_preset_column`; each phase's migration chains from the previous phase.
- New CSS uses theme tokens only; bios and other rich-text fields render through `app/markdown_renderer.py`, the single sanitised markdown producer.
- Browser-level tests belong under `tests/e2e/`.

### Deployment Commands

Phase G provides deployment artifact generation and service lifecycle management:

- `devlog deploy render --mode <mode> --target <target>` — renders deployment files (systemd, compose, caddy, nginx, logrotate)
- `devlog deploy install --mode <mode>` — installs deployment files atomically
- `devlog deploy check --mode <mode>` — checks for deployment drift
- `devlog start|stop|restart|status|logs` — lifecycle commands (backend-aware)

Backend detection: system mode uses systemd, user mode uses systemd user units, docker mode uses compose, development mode reports foreground guidance.

Systemd units include hardening directives (NoNewPrivileges, PrivateTmp, ProtectSystem=strict, ProtectHome=true). Worker and scheduler units are separate when Celery/scheduler is enabled.

See [architecture/deployment/deployment.md](architecture/deployment/deployment.md) for full documentation.

### Onboarding System

The `devlog onboard` command provides first-run and reconfiguration onboarding:

- **State machine**: 17 ordered steps in `app/onboarding/steps.py` — detect, resolve mode/paths, collect inputs, build config, resolve secrets, plan changes, validate, write config/env, create dirs, run migrations, create admin, verify assets, readiness check, write metadata, render completion
- **Input model**: `app/onboarding/model.py` — `OnboardingInput` frozen dataclass + `build_config_from_input(data_dir=)` → `DevLogConfig`
- **Secret handling**: `app/onboarding/secrets.py` — generates SECRET_KEY, health secret, metrics secret; preserves existing on re-run; writes `.env` with mode 0600
- **Planner**: `app/onboarding/planner.py` — dry-run plan generation with create/preserve/update/skip/conflict actions
- **Metadata**: `app/onboarding/metadata.py` — persists installation state for resume/idempotency
- **Service layer**: `app/services/operations/onboard.py` — wraps onboarding package for CLI
- **CLI**: `devlog_cli/commands/onboard.py` — detect, plan, run subcommands; `--scope` option on `plan` and `run` controls native installation scope (system/user directories)
- **Tests**: `tests/onboarding/` (151 unit tests) + `tests/cli/test_onboard_commands.py` (15 CLI tests)

Scope and mode relationship:
- `--scope system` resolves to system-level paths (e.g. `/etc/devlog/`, `/var/lib/devlog/`) via `RuntimePaths.for_mode(InstallMode.SYSTEM)`
- `--scope user` resolves to user-level paths (e.g. `~/.config/devlog/`, `~/.local/share/devlog/`) via `RuntimePaths.for_mode(InstallMode.USER)`
- Docker mode ignores `--scope` and uses container-standard paths (`/data/`, `/config/`)
- When `--scope` is omitted, the onboarding step detects the appropriate scope from the current installation

Key internals:
- `detect_installation()` uses `RuntimePaths.for_mode(detect_mode())` when no explicit paths are provided, ensuring path resolution stays centralized
- `build_config_from_input(inp, data_dir=)` accepts an optional `data_dir` parameter to override the default database location
- `_save_progress()` populates `package_version` from `importlib.metadata.version("devlog")` for installation provenance tracking

Key rules:
- Secrets never appear in JSON output or logs
- Config writes are atomic (temp + rename)
- Existing files are backed up before overwrite
- Dry-run mode skips all mutations
- Non-interactive mode requires all values via options, never prompts

### Installation Contract (R2C1)

The Release 2 Closure installation contract defines strict responsibilities between the installer and onboarding:

- `scripts/install.sh` installs verified code artifacts and creates only minimal release/bundle scaffolding (symlink, launcher). It must not create configuration, database state, or secrets.
- `devlog onboard` creates and validates configuration, secrets, state directories, database schema, administrator state, and installation metadata.
- `RuntimePaths` is the sole authority for runtime path resolution. Neither the installer nor onboarding should derive paths independently.
- The installer must not maintain a parallel configuration schema, secret generator, profile system, or database migration implementation.

This separation ensures that `install.sh` remains a minimal, auditable artifact-delivery mechanism while `devlog onboard` owns all configuration and state lifecycle.

## Architecture Cross-Reference

For detailed architecture documentation, see the `architecture/` directory:

| Topic | Document |
|-------|----------|
| App factory, configuration | [architecture/core/app-factory.md](architecture/core/app-factory.md), [architecture/core/configuration.md](architecture/core/configuration.md) |
| Data models (17 models) | [architecture/core/models.md](architecture/core/models.md) |
| Routes (admin, public, API, RSS) | [architecture/routes/admin-routes.md](architecture/routes/admin-routes.md), [architecture/routes/public-routes.md](architecture/routes/public-routes.md), [architecture/routes/api-routes.md](architecture/routes/api-routes.md), [architecture/routes/rss-feeds.md](architecture/routes/rss-feeds.md) |
| Services (overview) | [architecture/services/overview.md](architecture/services/overview.md) |
| Services (individual) | [architecture/services/backup.md](architecture/services/backup.md), [architecture/services/encryption.md](architecture/services/encryption.md), [architecture/services/search.md](architecture/services/search.md), [architecture/services/serialization.md](architecture/services/serialization.md), [architecture/services/slug.md](architecture/services/slug.md), [architecture/services/tag.md](architecture/services/tag.md), [architecture/services/tag_cache.md](architecture/services/tag_cache.md) |
| Operations services | `app/services/operations/` — admin, database, media, transfer, themes, backup, results |
| Celery tasks, APScheduler | [architecture/tasks/celery-tasks.md](architecture/tasks/celery-tasks.md), [architecture/tasks/scheduler.md](architecture/tasks/scheduler.md) |
| Infrastructure (overview) | [architecture/infrastructure/overview.md](architecture/infrastructure/overview.md) |
| Infrastructure (individual) | [architecture/infrastructure/search.md](architecture/infrastructure/search.md), [architecture/infrastructure/email.md](architecture/infrastructure/email.md), [architecture/infrastructure/storage.md](architecture/infrastructure/storage.md), [architecture/infrastructure/webhooks.md](architecture/infrastructure/webhooks.md) |
| Frontend (Vite, templates, CSS) | [architecture/frontend/overview.md](architecture/frontend/overview.md), [architecture/frontend/templates.md](architecture/frontend/templates.md), [architecture/frontend/static-assets.md](architecture/frontend/static-assets.md) |
| Testing (pytest, E2E, benchmarks) | [architecture/testing/test-suite.md](architecture/testing/test-suite.md) |
| Security (2FA, CSRF, rate limiting) | [architecture/deployment/security.md](architecture/deployment/security.md) |
| Deployment (Docker, CI/CD) | [architecture/deployment/deployment.md](architecture/deployment/deployment.md), [architecture/deployment/docker.md](architecture/deployment/docker.md), [architecture/deployment/cicd.md](architecture/deployment/cicd.md) |
| Theme system (Halloy migration) | [docs/themes/supported-schema.md](docs/themes/supported-schema.md), [docs/themes/blog-theme-contract.md](docs/themes/blog-theme-contract.md), [docs/themes/operator-guide.md](docs/themes/operator-guide.md) |
| System overview | [architecture/overview.md](architecture/overview.md) |

## Skills

Load specialized skills using the `skill` tool with the skill name.

| Skill | Description | Triggers |
|-------|-------------|----------|
| `blog_cms` | Blog CMS - Flask-based blogging platform with admin dashboard, newsletter scheduling, FTS5 search, multi-admin sessions, custom CSS theming, syntax highlighting themes, post series, Atom feed, 2FA, Comments, Audit Log, Post Revision Diff, operations service layer, filesystem layout, deployment module | Flask app, SQLAlchemy, session management, CSRF, newsletter, APScheduler, FTS5, REST API, password reset, post revisions, preview links, toasts, dashboard charts, graceful shutdown, Docker deployment, Vite bundler, 2FA, Comments, Audit Log, operations services, filesystem layout, paths CLI, deployment, systemd, compose, caddy, nginx, logrotate, lifecycle |
| `architecture_review` | Architecture documentation review and improvement workflow | architecture, review, documentation, verify, cross-reference, architecture review plan |

## Skills Directory Note

Skills are stored in `.skills/` (local directory). The `blog_cms` skill is also registered in `.opencode/skills/blog_cms/` for the opencode agent. When adding new skills, create a `skill.md` in `.skills/<skill_name>/` and optionally register in `.opencode/skills/<skill_name>/SKILL.md`.
