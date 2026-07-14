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
mypy app/

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
| Theme config | `app/config.py` — `THEME_EXTERNAL_DIR`, `THEME_ALLOW_EXTERNAL`, `THEME_STRICT_VALIDATION`, `THEME_DEFAULT_DARK`, `THEME_DEFAULT_LIGHT`, `THEME_DEFAULT_SCHEME` |
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

CI configuration is at `.github/workflows/ci.yml`. It includes 7 jobs: `lint-and-type`, `test`, `frontend-build`, `security-audit`, `docker-build`, `e2e-tests`, and `theme-package-verification`. E2E tests run through a CI-only compose override (`docker-compose.ci.yml`) that publishes port 5000 directly, bypassing nginx. The `E2E_BASE_URL` env var controls the test target URL.

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

`app/config.py:_env_str(key, default="")` reads env vars and treats empty strings as unset (returns default). Use this instead of `os.environ.get()` when empty-string-means-unset is desired.

### Env Var Fallback Chains

Database URI: `SQLALCHEMY_DATABASE_URI` → `DATABASE_URL` → SQLite default.
Cache Redis: `CACHE_REDIS_URL` → `REDIS_URL` → `redis://localhost:6379/0`.
Celery broker: `CELERY_BROKER_URL` → `REDIS_URL` → `redis://localhost:6379/0`.
Metrics: `ENABLE_METRICS=true` + `METRICS_SECRET` required in production.

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

`config.toml.example` exists as a template. `setup.sh` copies it to `config.toml` if absent. `config.toml` is gitignored — only `config.toml.example` is committed. If `config.toml` is missing, `app/config.py` falls back to `config.toml.example` with a warning.

### python-dotenv Auto-Loading

`python-dotenv` is included in `requirements.txt` and called via `load_dotenv()` in both `run.py` and `app/config.py`. The app auto-loads `.env` without requiring manual `source` commands.

### setup.sh Behavior

`setup.sh` creates a venv, installs deps, generates `.env` (if missing), copies `config.toml` from template, then sources `.env`. It does NOT start the server — the final message tells the user to run `python run.py`.

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

### Halloy Theme Migration (in progress)

The project is migrating from a 4-preset hardcoded theme system to a Halloy-compatible theme system with 50+ bundled themes. Phase 01 (inventory + token contract), Phase 02 (parser + color primitives), Phase 03 (blog translation layer), Phase 04 (safe registry and external overrides), Phase 05 (packaging), Phase 06 (runtime integration — SiteSettings columns, Alembic migration, theme settings validation service, config.toml theme section), Phase 07 (Flask and Jinja runtime integration — centralized ThemeService, dual-scheme CSS emission, context processor overhaul), Phase 08 (visitor color-scheme behavior — 3-state system/dark/light, bootstrap script, CSS selector migration, static light palette block removed), Phase 09 (CSS and generated-markup audit — hardcoded literals replaced with CSS custom properties, 34 REPLACE converted, 35 legacy vars emitted), Phase 10 (admin selection and preview — registry-based theme selector), Phase 11 (operator CLI — flask themes list/validate/inspect/refresh/accessibility), Phase 12 (accessibility validation — WCAG contrast checks with severity classification, catalog-wide validation, classification audit), and Phase 13 (performance and reliability — benchmarks, cache validation, malformed file isolation) are complete. Phase 14 (documentation and legacy removal) is in progress. Phase 13 deliverables include theme performance benchmarks, cache validation tests, and malformed file isolation tests. Phase 06-10 corrective pass is complete: persisted default scheme applies to first-time visitors, admin validation errors are typed and never produce 500s, legacy migration preserves visual mode, theme service is app-scoped via `app.extensions`, and legacy THEME_PRESETS fallback is bounded. The phased plan is at `plans/halloy_theme_system_roadmap.md`. Phase status can be checked by reading the plans directory.

**Small closure pass contracts:**
- Cache freshness: external theme changes require explicit `invalidate()` or `invalidate(name)`; no automatic mtime-based refresh
- Fingerprint: `_compute_fingerprint()` uses `hashlib.sha256()` (64-char hex) for bundled resources
- CI: `theme-package-verification` job builds wheel/sdist and runs `scripts/verify_theme_package.py` as a gate

#### Key files (existing runtime)

- `app/models.py:366-457` — `THEME_PRESETS` dict (runtime authority until Phase 14)
- `app/context_processors.py:67-76` — `theme_vars` injection from preset
- `app/templates/base.html:42-48` and `app/templates/admin/base.html:17-23` — `theme_vars` CSS custom property injection
- `app/routes/admin/settings.py` — admin settings page
- `app/cli.py:343-610` — theme CLI commands (list, validate, inspect, refresh, paths, accessibility)
- `app/services/theme_settings.py` — `LEGACY_PRESET_MAP`, `validate_theme_settings()`, `migrate_legacy_preset()`, `get_effective_theme_names()`
- `app/themes/service.py` — `ThemeService` class, `init_theme_service()`, `get_theme_service()` (Phase 07, app-scoped via `app.extensions["theme_service"]` since corrective pass)

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

#### Hard rules during migration

- Corrective closure and small closure pass for Phases 01–05 are complete; subsequent phases build on the corrected foundation
- Do NOT delete or replace `THEME_PRESETS` until Phase 14
- Do NOT change `theme_vars` Jinja context shape until Phase 07
- Do NOT move or rename `themes/*.toml` until Phase 05
- Future phases must add new code under `app/themes/` (planned: `halloy.py`, `colors.py`, `registry.py`, `resources.py`, `model.py`, `translate.py`, `diagnostics.py`, `bundled/`); do not scatter migration code across other modules
- Bundled theme resources must use `importlib.resources`, never `Path(__file__).parent.parent.parent` or cwd-relative paths
- Existing CSS files (`base.css`, `critical.css`, `layout.css`, etc.) must continue to work unchanged through Phase 09 (complete)

#### Key files (catalog source)

- `themes/*.toml` — top-level Halloy catalog (50 source files; ignore macOS `._*.toml` metadata files)
- `app/themes/bundled/` — packaged Halloy theme files shipped with the app (50 `.toml` files + `__init__.py` + `catalog_manifest.json` + `ATTRIBUTION.md`)

## Architecture Cross-Reference

For detailed architecture documentation, see the `architecture/` directory:

| Topic | Document |
|-------|----------|
| App factory, configuration | [architecture/core/app-factory.md](architecture/core/app-factory.md), [architecture/core/configuration.md](architecture/core/configuration.md) |
| Data models (17 models) | [architecture/core/models.md](architecture/core/models.md) |
| Routes (admin, public, API, RSS) | [architecture/routes/admin-routes.md](architecture/routes/admin-routes.md), [architecture/routes/public-routes.md](architecture/routes/public-routes.md), [architecture/routes/api-routes.md](architecture/routes/api-routes.md), [architecture/routes/rss-feeds.md](architecture/routes/rss-feeds.md) |
| Services (overview) | [architecture/services/overview.md](architecture/services/overview.md) |
| Services (individual) | [architecture/services/backup.md](architecture/services/backup.md), [architecture/services/encryption.md](architecture/services/encryption.md), [architecture/services/search.md](architecture/services/search.md), [architecture/services/serialization.md](architecture/services/serialization.md), [architecture/services/slug.md](architecture/services/slug.md), [architecture/services/tag.md](architecture/services/tag.md), [architecture/services/tag_cache.md](architecture/services/tag_cache.md) |
| Celery tasks, APScheduler | [architecture/tasks/celery-tasks.md](architecture/tasks/celery-tasks.md), [architecture/tasks/scheduler.md](architecture/tasks/scheduler.md) |
| Infrastructure (overview) | [architecture/infrastructure/overview.md](architecture/infrastructure/overview.md) |
| Infrastructure (individual) | [architecture/infrastructure/search.md](architecture/infrastructure/search.md), [architecture/infrastructure/email.md](architecture/infrastructure/email.md), [architecture/infrastructure/storage.md](architecture/infrastructure/storage.md), [architecture/infrastructure/webhooks.md](architecture/infrastructure/webhooks.md) |
| Frontend (Vite, templates, CSS) | [architecture/frontend/overview.md](architecture/frontend/overview.md), [architecture/frontend/templates.md](architecture/frontend/templates.md), [architecture/frontend/static-assets.md](architecture/frontend/static-assets.md) |
| Testing (pytest, E2E, benchmarks) | [architecture/testing/test-suite.md](architecture/testing/test-suite.md) |
| Security (2FA, CSRF, rate limiting) | [architecture/deployment/security.md](architecture/deployment/security.md) |
| Deployment (Docker, CI/CD) | [architecture/deployment/docker.md](architecture/deployment/docker.md), [architecture/deployment/cicd.md](architecture/deployment/cicd.md) |
| Theme system (Halloy migration) | [docs/themes/supported-schema.md](docs/themes/supported-schema.md), [docs/themes/blog-theme-contract.md](docs/themes/blog-theme-contract.md), [docs/themes/operator-guide.md](docs/themes/operator-guide.md) |
| System overview | [architecture/overview.md](architecture/overview.md) |

## Skills

Load specialized skills using the `skill` tool with the skill name.

| Skill | Description | Triggers |
|-------|-------------|----------|
| `blog_cms` | Blog CMS - Flask-based blogging platform with admin dashboard, newsletter scheduling, FTS5 search, multi-admin sessions, custom CSS theming, syntax highlighting themes, post series, Atom feed, 2FA, Comments, Audit Log, Post Revision Diff | Flask app, SQLAlchemy, session management, CSRF, newsletter, APScheduler, FTS5, REST API, password reset, post revisions, preview links, toasts, dashboard charts, graceful shutdown, Docker deployment, Vite bundler, 2FA, Comments, Audit Log |
| `architecture_review` | Architecture documentation review and improvement workflow | architecture, review, documentation, verify, cross-reference, architecture review plan |

## Skills Directory Note

Skills are stored in `.skills/` (local directory). The `blog_cms` skill is also registered in `.opencode/skills/blog_cms/` for the opencode agent. When adding new skills, create a `skill.md` in `.skills/<skill_name>/` and optionally register in `.opencode/skills/<skill_name>/SKILL.md`.
