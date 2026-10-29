# Agent Guidelines

Quick reference for AI agents working on this codebase.

For structure and design rationale, start at
[architecture/overview.md](architecture/overview.md) — it is the module map and
the index to every deep dive.

## Project Overview

DevLog is a Flask blog CMS with an admin dashboard, newsletter scheduling, FTS5
search, a Halloy TOML theme system, an appearance layer for fonts and backdrops,
2FA, comments, post series, multi-admin sessions, a standalone operator CLI, and
a managed deployment module.

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
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python3 -m pytest tests/

# Run a single test file
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python3 -m pytest tests/test_models.py -v

# Run linter
ruff check .
ruff format --check .

# Type check — cover BOTH app/ and devlog_cli/
mypy app/ devlog_cli/

# Check dependency manifest consistency
python scripts/check_dependency_manifest_consistency.py

# Release validation (lint + type + tests + build + Docker + Compose config)
./scripts/release_check.sh
```

The full release gate, the known baseline of pre-existing failures, and the
host-specific gotchas are in the `release_validation` skill.

## Agent Override Convention

This codebase uses a **module-level override system** for agent context. Each
module (directory with a specific purpose) may contain an `AGENTS.override.md`
file that provides specialized handling instructions for that module.

When an agent operates within a module, it should:
1. Read the root `AGENTS.md` for general guidance
2. Check for `AGENTS.override.md` in the current module for specialized handling
3. Override files take precedence over root-level guidance when working within that module

### Module Override Files

| Module | Override File | Purpose |
|--------|---------------|---------|
| App Core | `app/AGENTS.override.md` | Flask app, models, extensions, core utilities |
| Routes | `app/routes/AGENTS.override.md` | General routing concerns, API authentication, RSS feeds, error handlers |
| Admin Routes | `app/routes/admin/AGENTS.override.md` | Admin dashboard, post/subscriber/user management |
| Public Routes | `app/routes/public/AGENTS.override.md` | Public page handlers |
| Frontend | `app/static/AGENTS.override.md` | JS/CSS assets, cross-layer contracts, Vite build |
| Templates | `app/templates/AGENTS.override.md` | Jinja2 templates, filters |
| Tests | `tests/AGENTS.override.md` | Testing patterns, fixtures |
| Documentation | `docs/AGENTS.override.md` | Documentation structure |
| Scripts | `scripts/AGENTS.override.md` | Shell scripts, DevOps |
| Services | `app/services/AGENTS.override.md` | Centralized service layer |
| Architecture | `architecture/AGENTS.override.md` | Architecture documentation |
| Plans | `plans/AGENTS.override.md` | Which plans are active, which are historical |
| OpenCode | `.opencode/AGENTS.override.md` | Agent tool configuration, skills |

## Codebase Structure Reference

The full tree is in [architecture/overview.md](architecture/overview.md#directory-structure).
This table lists only the locations that are easy to get wrong.

| Item | Actual Location |
|------|-----------------|
| API routes | `app/routes/api/` — a package: posts, pages, series, tags, subscribers, stats, auth |
| API scope matching | `scope_allows()` in `app/routes/api/auth.py` — exact match, `admin:*` grants all, category wildcards (`posts:*`) |
| API auth header | `X-API-Key` — the same header carries both the legacy `API_KEY` and a scoped `ApiToken` |
| Validators | `app/validators.py` (NOT `app/core/validators.py`) |
| Typed config package | `app/config/` — model, loader, paths, validation, provenance, secrets, profiles, serialization, migration |
| Legacy config globals | `app/config_legacy.py` (NOT `app/config.py`), re-exported via `app/config/__init__.py` |
| Theme system | `app/themes/` — colors, halloy, model, translate, diagnostics, resources, cache, registry, service |
| Bundled themes | `app/themes/bundled/` — 50 packaged `.toml` files |
| Theme source catalogue | `themes/` at the repo root — the authoring source, **not** a runtime override dir |
| Runtime theme overrides | `themes.external_dir` in `config.toml`, or `THEME_EXTERNAL_DIR` |
| Appearance layer | `app/appearance/` — font and backdrop registries, appearance service, SVG sanitiser, uploads |
| Theme settings service | `app/services/theme_settings.py` |
| Appearance settings service | `app/services/appearance_settings.py` |
| Filesystem layout | `app/filesystem/` — layout, prepare, discovery, migration, verification, lifecycle |
| Onboarding package | `app/onboarding/` — model, state, steps, planner, secrets, metadata, rendering |
| Deployment module | `app/deployment/` — model, systemd, compose, proxy, logrotate, install, drift, lifecycle |
| Operations services | `app/services/operations/` — admin, database, media, transfer, themes, backup, deploy, onboard, doctor, results |
| CLI package | `devlog_cli/` — main, context, output, errors, exit_codes, result, commands/ |
| CLI entry point | `devlog_cli.main:main` — registered as `devlog` in `pyproject.toml [project.scripts]` |
| CLI command groups | `devlog_cli/commands/` — config, admin, db, themes, backup, data, media, onboard, paths, deploy, doctor, lifecycle |
| Flask CLI wrappers | `app/cli.py` — compatibility wrappers over the same services |
| Middleware | `app/middleware/rate_limit.py` |
| Markdown | `app/markdown_renderer.py` — the single producer, exposed as the `markdown_safe` filter |
| Models | `app/models.py` — exactly 23 |
| Backup service | `app/services/backup.py` |
| Tag cache | `app/tag_cache.py` (flask-caching with TTL) |
| DB dialect helpers | `app/db_utils.py` — `get_database_dialect()`, `is_sqlite_database()` |
| Installer | `scripts/install.sh` — one-shot native/Docker installer |
| Dev setup | `scripts/setup-dev.sh` |
| Release gate | `scripts/release_check.sh` |
| Dependency consistency | `scripts/check_dependency_manifest_consistency.py` |
| Checksums / artifact verification | `scripts/generate_checksums.py`, `scripts/check_release_artifacts.py` |

## Security & Privacy Rules

- **Log ID, not Username**: When logging user actions or system events, always use `user.id`. Never log raw User objects or usernames to prevent PII leakage.
- **Credential Protection**: Never log `SECRET_KEY`, `ADMIN_PASSWORD`, or API keys.
- **Route Verification**: Before editing or documenting routes, verify against actual implementation. Routes frequently differ from what documentation or comments claim.

## Code Style

- **Linting**: `ruff check .` and `ruff format --check .`
- **Type checking**: `mypy app/ devlog_cli/`
- **Pinned toolchain**: `ruff>=0.15.2,<0.16`, `mypy>=2.4.0,<2.5`, `pytest>=9.0.2,<10.0` in `requirements-dev.txt`. Ruff's rule selection is declared explicitly in `pyproject.toml` (`select = ["E4", "E7", "E9", "F"]`) so the lint result does not depend on the installed ruff version. Do not widen these bounds without re-running the full gate — a ruff release that changes its defaults otherwise turns the build red on untouched files.
- **SQLAlchemy**: Use SQLAlchemy 2.0 style (`db.session.execute(select(...))` pattern)
- **No comments**: Do not add comments unless explicitly requested
- **Security**: Never commit secrets, keys, or credentials
- **Documentation**: Prefer symbolic references (function names, class names) over line numbers

## Important Notes for Future Agents

### Single-owner rules

These are the seams where a second producer is the defect. Each has one owner.

| Value | Owner |
|---|---|
| Colour | The theme runtime — static CSS consumes tokens only |
| Typeface and backdrop | `app/appearance/service.py` |
| Markdown prose typography | `app/static/css/base.css` (the admin shell does not load `public.css`) |
| The reading measure | `app/static/css/base.css` — `max-width: 34em` on `.prose`, never a pixel width |
| The post placeholder mark | `app/static/css/public.css` — the `.img-placeholder` mask rule; the SVG is never loaded as an image |
| The post list grid | `app/static/css/public.css` — the `.posts-list` grid and its 1024px breakpoint |
| The card's tag row | `app/templates/macros.html` — `post_tag_row` owns the cap; `app/static/css/public.css` owns `.tag-more` |
| The structural voice | The stylesheet that owns the label — `app/static/css/public.css` for `.post-toc-title` and `.share-label`, `app/static/css/layout.css` for `.sidebar-title` |
| The share bar's position | `app/templates/_post_content.html` |
| The "no profile picture" portrait | `app/templates/_default_avatar.html` — one macro, never an initial letter |
| Heading IDs | `app/static/js/shared/heading-slug.js` |
| Heading anchors | `app/static/js/public/anchor-links.js` — a direct child of the heading, never wrapped |
| Markdown rendering | `app/markdown_renderer.py` / the `markdown_safe` filter |
| Post image URL | The `post_image_url` filter — a URL, never re-wrapped with `url_for('static', …)` |
| The CSRF header name | `CSRF_HEADER_NAME` in `app/csrf.py`, published as `data-csrf-header` |
| Filesystem paths | `RuntimePaths` in `app/filesystem/layout.py` |
| Operational logic | `app/services/operations/` — never in a CLI handler |
| Route → JS module mapping | `app/static/js/main.js` — path-segment boundary, longest match first |

`tests/test_css_contracts.py` enforces the CSS halves of these.

### APScheduler multi-container limitation

APScheduler uses FileLock with `timeout=0`, which only works on a single machine. Multiple container replicas will each run their own APScheduler and execute jobs concurrently. **Set `ENABLE_SCHEDULER=true` on exactly ONE container to prevent duplicate jobs.** It is disabled by default so replicas can run without duplicate jobs.

The scheduler handles newsletters, subscriber cleanup, scheduled post publishing, and daily backups. When SMTP_HOST is not configured, only the daily newsletter job is disabled; other jobs continue to run.

See [architecture/tasks/scheduler.md](architecture/tasks/scheduler.md).

### Vite build required for production

`npm run build` must run before production deployment, and `app/static/dist/.vite/manifest.json` must exist. Without it, JS assets resolve to hashed paths that do not exist.

Docker builds handle this automatically via the multi-stage `Dockerfile` — the `frontend-builder` stage runs `npm run build`. This note applies to non-Docker deployments only.

**Restart the Flask server after every build** — `app/vite.py` caches the manifest process-wide.

### Entry point

`run.py` is the development entry point. It wraps the WSGI app with `asgiref.wsgi.WsgiToAsgi` for ASGI compatibility (used by Granian in production). For production, use Granian via Docker Compose rather than `python run.py`.

### Template context and filters

- Context variables are `site_title` and `site_description` (NOT `site_name` or `site_tagline`).
- Filters in `app/filters.py`: `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`, and `post_image_avif_url_stub` (deprecated stub, always returns `None`). There is no `format_date`, `markdown` or `slugify` filter.
- Admin templates (`admin/base.html`) and public templates (`base.html`) are **standalone** root templates. `admin/base.html` does NOT extend `base.html`.

### Critical CSS

`app/static/css/critical.css` provides above-the-fold CSS for fast initial paint. It is loaded in `base.html` with `media="screen"` for immediate loading.

### Docker Compose profiles

All services require explicit profiles. There is no default profile:
- `--profile production`: blog, celery, redis (app on `127.0.0.1:5000`)
- `--profile reverse-proxy`: nginx (optional reverse proxy with TLS)
- `--profile backup`: backup service

### CI workflow

CI configuration is at `.github/workflows/ci.yml`. It includes 11 jobs: `lint-and-type`, `test`, `theme-policy`, `migration-chain`, `theme-package-verification`, `frontend-build`, `security-audit`, `docker-build`, `e2e-tests`, `dependency-consistency`, and `release1-package-smoke`. The E2E job runs the `production` compose profile, whose blog service publishes `127.0.0.1:5000` while nginx sits in the `reverse-proxy` profile, so the suite reaches the application directly. There is no CI compose overlay: Compose merges port lists rather than replacing them, so a second binding of host port 5000 stops the container from starting. The `E2E_BASE_URL` env var controls the test target URL. `security-audit` runs `pip-audit -r requirements.txt -S` and fails on any known vulnerability, so a runtime bound must be raised whenever an advisory lands. See [architecture/deployment/cicd.md](architecture/deployment/cicd.md) for the pinned toolchain and the per-job contract.

### Webhook delivery

Two-level dispatch: `deliver_webhook_task` fans out to one `deliver_single_webhook_task` per webhook, so one failing endpoint does not block the others. Retries live at the subtask level.

See [architecture/infrastructure/webhooks.md](architecture/infrastructure/webhooks.md).

### Model count

There are exactly 23 model classes in `app/models.py`: User, Post, Tag, Subscriber, Page, Project, ProjectDocument, ProjectDocumentAsset, ProjectDocsSnapshot, ProjectRelease, ProjectReleaseAsset, PageView, ShareEvent, AdminSession, SiteSettings, Webhook, WebhookEvent, Series, PostSeries, Comment, PostRevision, AdminAuditLog, ApiToken. `OperationResult` and its subclasses in `app/services/operations/results.py` are plain dataclasses, not SQLAlchemy models.

See [architecture/core/models.md](architecture/core/models.md).

### Filesystem layout

The codebase has a centralized filesystem path system at `app/filesystem/`:

- `app/filesystem/layout.py` — `RuntimePaths` dataclass with `InstallMode` (system, user, docker, development) and `PathProvenance` tracking
- `app/filesystem/prepare.py` — directory creation with permissions and security checks
- `app/filesystem/discovery.py` — legacy layout discovery (read-only)
- `app/filesystem/migration.py` — migration planner and executor; `MigrationPlan` (dry-run) and `execute_migration()` (apply)
- `app/filesystem/verification.py` — post-migration verification
- `app/filesystem/lifecycle.py` — path categories and lifecycle policy

CLI: `devlog paths status`, `devlog paths discover-legacy`, `devlog paths migrate`, `devlog paths check`.

Key rules: all paths are absolute after resolution; explicit overrides always win over env vars and mode defaults; legacy discovery is read-only; migration planning defaults to dry-run; production services must not require write access to source directories.

The application writes only to the directories the typed configuration names. `create_app()` derives the Flask instance path from `paths.runtime_dir`, the upload folder from `paths.uploads_dir` (falling back to `paths.data_dir/uploads`) and the log directory from `paths.log_dir`. The container image sets `DEVLOG_DATA_DIR=/data`, `DEVLOG_LOG_DIR=/var/log/devlog` and `DEVLOG_RUNTIME_DIR=/run/devlog`, because the installation directory itself is read-only for the unprivileged runtime user. Without those variables the application falls back to `instance/`, `app/static/uploads/` and `logs/` inside the source tree, which is correct for a development checkout. See [architecture/deployment/docker.md](architecture/deployment/docker.md) and `tests/test_runtime_directories.py`.

`execute_migration()` returns a `MigrationExecutionResult` tracking `ok`, `completed_steps`, `total_steps`, `errors`, `completed_paths`, and performs a SQLite WAL checkpoint (`PRAGMA wal_checkpoint(TRUNCATE)`) on the source database before executing move/copy steps.

See [architecture/core/filesystem.md](architecture/core/filesystem.md).

### Service extraction

Operational business logic lives in `app/services/operations/`. The standalone `devlog` CLI commands in `devlog_cli/commands/` call these services; Flask commands in `app/cli.py` remain as compatibility wrappers.

Service functions never depend on Click, terminal output or process exit. They return typed `OperationResult` subclasses, require an application context, and use `commit_with_rollback()` for transaction boundaries.

```
CLI handler → CliContext.ensure_app_context() → call service function → render Result
Flask command wrapper → call same service function → render compatibility output
```

See [architecture/services/operations.md](architecture/services/operations.md).

### Typed configuration

`app/config/` replaces the legacy globals in `app/config_legacy.py`:

- `app/config/model.py` — 23 frozen dataclasses (`DevLogConfig` + 22 section classes)
- `app/config/loader.py` — `load_effective_config()` with precedence chain (env vars > config.toml > defaults)
- `app/config/paths.py` — path resolution with source tracking
- `app/config/validation.py` — multi-layer validation (schema, security, filesystem, dependencies, compatibility)
- `app/config/provenance.py` — source tracking for config values
- `app/config/secrets.py` — secret field identification and redaction
- `app/config/profiles.py` — deployment profiles (development, native-production, docker-production, minimal, full)
- `app/config/serialization.py` — TOML/JSON output with redaction
- `app/config/migration.py` — config version migration support

**`app/config/model.py` is the canonical source of truth for all configuration fields and their defaults.** It defines 23 frozen dataclasses — `DevLogConfig` plus 22 section classes — one per `[section]` in `config.toml`. `config.toml.example` mirrors these defaults. When adding or modifying a config field, update the dataclass first — the loader and example file follow from it.

Env var fallback chains, defined in `app/config/loader.py`:

| Setting | Chain |
|---|---|
| Database URI | `SQLALCHEMY_DATABASE_URI` → `DATABASE_URL` → SQLite default |
| Cache Redis | `CACHE_REDIS_URL` → `REDIS_URL` → `redis://localhost:6379/0` |
| Rate limit Redis | `RATELIMIT_STORAGE_URI` → `redis_url` → `redis://localhost:6379/0` |
| Celery broker | `CELERY_BROKER_URL` → `REDIS_URL` → `redis://localhost:6379/0` |

The full env var → config field mapping is in `_ENV_OVERRIDE_MAP`.

`app/config_legacy.py:_env_str(key, default="")` treats an empty string as unset. Use it instead of `os.environ.get()` when empty-string-means-unset is wanted.

See [architecture/core/configuration.md](architecture/core/configuration.md).

### Health and metrics endpoints

`/health` has two modes:
- **Basic** (`/health`): database + scheduler status only. Fast, no auth. Used for Docker healthchecks.
- **Detailed** (`/health?detailed=true`): all checks with details. Requires `HEALTH_CHECK_SECRET` via header (`X-Health-Secret`), Bearer token, or `?secret=`. In production without the secret, returns 403.

`/metrics` is disabled by default (`ENABLE_METRICS=false`). When enabled, production requires `METRICS_SECRET`; without it, returns 403. Startup validation raises `RuntimeError` if `ENABLE_METRICS=true` + production + no `METRICS_SECRET`.

See [architecture/infrastructure/overview.md](architecture/infrastructure/overview.md).

### SESSION_COOKIE_SECURE

Defaults to `"true"` (read in `app/__init__.py`). In production behind HTTPS, keep it `true`. For local HTTP testing at `http://localhost:5000`, set it to `false` or admin login cookies will not persist. Never use `false` in production behind HTTPS.

### STORAGE_BACKEND

`STORAGE_BACKEND` (default `"local"`) controls media storage. Set to `"s3"` for S3-compatible storage, which requires `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`; optional `S3_REGION`, `S3_ENDPOINT`, `S3_PUBLIC_URL`. If the required vars are missing, it falls back to local storage with a warning.

See [architecture/infrastructure/storage.md](architecture/infrastructure/storage.md).

### config.toml and .env

`config.toml.example` is the committed template; `config.toml` is gitignored. `scripts/setup-dev.sh` copies it if absent. If `config.toml` is missing, `app/config_legacy.py` falls back to `config.toml.example` with a warning.

`python-dotenv` auto-loads `.env` via `load_dotenv()` in both `run.py` and `app/config/__init__.py`, so manual `source` commands are unnecessary.

### Theme system

The project migrated from a 4-preset hardcoded theme system to a Halloy-compatible system with 50 bundled themes. The migration is complete.

- `BlogTheme` is a frozen dataclass with **52 fields: 43 `RGB` + 9 `RGBA`**. `CSS_VARS` has **52 entries**, `ALIASES` has **40 entries**.
- `THEME_PRESETS` and the `SiteSettings.theme_preset` column were removed. The emergency fallback is `EMERGENCY_DEFAULT`.
- `SiteSettings.theme_dark_name` (default `Catppuccin Mocha`), `theme_light_name` (default `Catppuccin Latte`), `theme_default_scheme` (`system`).
- `ThemeService` is per-process, stored on `app.extensions["theme_service"]`. `inject_theme()` in `app/context_processors.py` builds `theme_vars`.
- Cache freshness requires an explicit `invalidate()` / `invalidate(name)` — there is no automatic mtime refresh. Entries carry a `source_fingerprint` computed with `hashlib.sha256()`.
- Accessibility policy is three-tier: `recommended`, `compatible-with-exceptions`, `experimental`. The exception manifest is `app/themes/ACCESSIBILITY_EXCEPTIONS.json` (`schema_version: 2`). CI enforces it via the `theme-policy` job.
- Bundled resources use `importlib.resources`, never a cwd-relative path.

The phased plan is at `plans/halloy_theme_system_roadmap.md`; the schema, token contract and operator guide are in `docs/themes/`.

See [architecture/core/themes.md](architecture/core/themes.md).

### Appearance layer

The theme system owns colour. The appearance layer (`app/appearance/`) owns the typeface and the page backdrop — the questions the theme registry does not answer. It mirrors the theme mechanism exactly: registry → service → `SiteSettings` → admin UI → runtime CSS, so there is one customisation mechanism, not two.

- Ten families ship locally (4 sans, 6 mono), including one Nerd Font (`meslo-nerd-font`) whose `unicode-range` names the powerline and devicons blocks in the Private Use Area. `app/static/css/base.css` declares every `@font-face`.
- Three backdrops ship in `app/static/img/backdrops/`.
- The backdrop SVG supplies **shape only** — it is applied through `mask-image`, so its own fill is irrelevant.
- Uploaded SVGs are sanitised before storage (`app/appearance/svg.py`).
- Panels are translucent via `color-mix(in srgb, var(--bg-surface) 94%, transparent)` with a plain `var(--bg-surface)` fallback first.
- The page background is three layers: the theme `bg` on the canvas, a gradient mixed from `bg` and `bg-surface` (`body::before`), and the backdrop shape (`body::after`).
- The stored key is the family key — `SiteSettings.font_sans` holds either `inter` or `custom-font-<slug>-<hash>.woff2`, so no second column is needed.
- **A choice whose file is gone falls back.** Both registries check storage before resolving a custom font or backdrop, so a missing file resolves to a bundled family instead of emitting a stack whose first entry never loads.

Settings: `SiteSettings.font_sans`, `font_mono`, `backdrop`. Admin route: `admin.settings_appearance` (`POST /admin/settings/appearance`).

See [architecture/frontend/appearance.md](architecture/frontend/appearance.md).

### Frontend styling ownership

- **Markdown prose lives in `base.css`.** The admin shell does not load `public.css`, and the admin live preview renders `.prose` content, so prose rules in `public.css` are missing in the preview.
- **The heading anchor is a child of the heading**, so the heading is its containing block and the `#` sits in the left gutter, revealed on hover or focus. It is never wrapped in a span — that broke the positioning rule and painted a `#` at the end of every title.
- **The "no profile picture" portrait is one macro**, `app/templates/_default_avatar.html`, used by the account page, the author page, the post footer and the admin profile page.
- **The post page owns the full tag list.** A post card shows at most four tags and counts the rest in a `+N` label; `_post_content.html` renders every tag in the post's footer, so a card never hides the only copy of a tag.
- `main.js` must not import a stylesheet — Flask links them so dev and production share one cascade order.
- Every `var(--x)` a stylesheet references must be emitted by the theme runtime or defined in a stylesheet. `tests/test_css_contracts.py` enforces this.

See `app/static/AGENTS.override.md` for the full cross-layer contract list.

### Onboarding and the installation contract

`devlog onboard` provides first-run and reconfiguration onboarding: 17 ordered steps in `app/onboarding/steps.py` — detect, resolve mode/paths, collect inputs, build config, resolve secrets, plan changes, validate, write config/env, create dirs, run migrations, create admin, verify assets, readiness check, write metadata, render completion.

The installer/onboarding boundary is strict:

- `scripts/install.sh` installs verified code artifacts and creates only minimal release/bundle scaffolding (symlink, launcher). It must not create configuration, database state, or secrets.
- `devlog onboard` creates and validates configuration, secrets, state directories, database schema, administrator state, and installation metadata.
- `RuntimePaths` is the sole authority for runtime path resolution. Neither the installer nor onboarding derives paths independently.
- The installer must not maintain a parallel configuration schema, secret generator, profile system, or database migration implementation.

Scope and mode: `--scope system` resolves to system-level paths via `RuntimePaths.for_mode(InstallMode.SYSTEM)`; `--scope user` to user-level paths; Docker mode ignores `--scope`. **When `--scope` is omitted, `step_resolve_paths()` falls back to `InstallMode.DEVELOPMENT`** — it does not detect the scope from the current installation.

Key rules: secrets never appear in JSON output or logs; config writes are atomic (temp + rename); existing files are backed up before overwrite; non-interactive mode never prompts.

**Dry-run skips the file writes, but `step_resolve_paths()` still creates the config and data directories.** The env file is rewritten from a fixed key set, so a re-run drops any hand-added `.env` key — onboarding is re-runnable but not idempotent in the strict sense.

Metadata is written as `onboarding-metadata.json` in the data directory.

See [architecture/core/onboarding.md](architecture/core/onboarding.md).

### Deployment commands

- `devlog deploy render --mode <mode> --target <target>` — renders deployment files (systemd, compose, caddy, nginx, logrotate)
- `devlog deploy install --mode <mode>` — installs deployment files atomically
- `devlog deploy check --mode <mode>` — checks for deployment drift
- `devlog start|stop|restart|status|logs` — lifecycle commands (backend-aware)

Backend detection: system mode uses systemd, user mode uses systemd user units, docker mode uses compose, development mode reports foreground guidance.

See [architecture/deployment/managed-deployment.md](architecture/deployment/managed-deployment.md).

### Thread-safe storage singleton

`app/storage.py:get_storage()` uses a double-checked locking pattern with `threading.Lock()` for thread-safe singleton initialization.

### E2E test isolation

`tests/e2e/conftest.py` defines its own session-scoped `app` fixture with a separate database (`blog_e2e`). Running `pytest tests/e2e/` alone works. The `app_server` fixture uses readiness polling for server startup. Browser-level tests belong under `tests/e2e/` — a live server thread on the session-scoped application shares its database with the migration tests and corrupts their DDL.

### Session IP binding

`SESSION_IP_BINDING` is enforced via the `admin_required` decorator in `app/routes/admin/__init__.py`, not in the global `before_request_handler`. When IP mismatch is detected and mode is `enforce`, the admin session is invalidated and the user is redirected to login. When mode is `warn`, a warning is logged but the session continues.

### Silent FTS initialization

`app/__init__.py` catches `OperationalError` during FTS init silently. The user is never informed if search will not work.

### LOGIN_FAILURE_DELAY

`app/routes/admin/auth.py` has `time.sleep(LOGIN_FAILURE_DELAY)` after invalid credentials. A minimum of 0.1s is enforced in `app/config_legacy.py`.

### CSRF applies to all POSTs except the API blueprint

CSRF validation is enforced globally for all POST requests in `app/__init__.py`, except API endpoints. The `should_skip_csrf()` predicate in `app/csrf.py` exempts requests where `request.blueprint == "api"`. API-key authenticated requests are protected by token secrecy, HTTPS, scopes, rate limits, and audit logging instead of browser CSRF tokens. Browser form POSTs (admin, public, subscribe, comments, logout) all require valid CSRF tokens.

### SiteSettings.get_instance() flush side effect

`SiteSettings.get_instance()` does `db.session.flush()` when creating a new instance. If called within a session that has other uncommitted changes, those changes are flushed (but not committed) as a side effect. Use `db.session.merge()` or `SELECT FOR UPDATE` to avoid this.

### Test conventions

All tests use `os.environ["ADMIN_PASSWORD"]` to stay in sync with the environment variable; it must be set when running tests.

`clean_analytics_cache` and `ensure_buffer_disabled` are defined in `tests/shared_fixtures.py` and imported into all conftest files via `from tests.shared_fixtures import *`. The `api_client` fixture in `tests/conftest.py` is functionally identical to `authenticated_client`.

`tests/benchmarks/conftest.py` configures `task_always_eager=True` for benchmark tests.

`Post.published` and `Page.published` have `nullable=False`. `User.failed_login_count` has `nullable=False`.

### Line number references in documentation

Line number references in architecture documentation drift over time. Prefer symbolic references (function names, class names) over exact line numbers when possible. When line numbers are required, verify against the current codebase before publishing.

### Maintainer context

For detailed implementation history, deprecated features, actual route corrections, test interference notes, encryption module details, and other maintainer context, see:

> [docs/internals/agent-maintainer-notes.md](docs/internals/agent-maintainer-notes.md)

## Known Defects

Verified against the source on 2026-10-29 and **not yet fixed**. Each has a
"Notes and Gotchas" entry in the relevant architecture document.

| Defect | Where |
|---|---|
| `shift_lightness()` computes `q` identically in both branches of the `lightness < 0.5` test, so dark colours take the light-colour path (`#161b22` +0.06 → `#002459`, not `#222a35`) | `app/themes/colors.py` |
| Create/update/delete handlers expose internal exception text via `flash(f"Error …: {str(e)}")` | `app/routes/admin/series.py` |
| `--quiet` and `--no-color` are stored on `CliContext` but never read | `devlog_cli/context.py`, `devlog_cli/main.py` |

### Fixed in the deployment-audit pass (2026-10-28)

These were listed above and are now repaired; the notes are kept here so the
history is not lost.

| Defect | Fix |
|---|---|
| **The backup tests shared one directory, so `test_download_backup` failed at random.** `tests/services/test_operations_backup.py` wrote `blog_verify_<uuid>.db` into the session's backup directory; `tests/test_phase8.py` downloaded the first entry of an *unsorted* listing, and the route refuses a name that is not `blog_<timestamp>.db`. On an unmodified checkout the test failed 10 runs out of 10 when the two modules shared a session | The services fixture writes into `tmp_path`; `test_download_backup` selects a name the route's own `validate_backup_filename()` accepts |
| **`test_backup_retention_policy` never created a backup.** It passed `app.instance_path/blog.db` to `create_backup()`, which is not where the application keeps its database, so every call returned `None` and the assertion counted whatever other tests had left in the shared directory — it failed on CI with `assert 4 <= 3` and passed locally by luck | The test resolves the live database through `resolve_database_file()`, backs up into `tmp_path`, and asserts that exactly the retention limit survives and that the oldest one is the file removed |
| The scheduled backup looked for `instance/blog.db` instead of the configured database | `resolve_database_file()` / `resolve_backup_dir()` in `app/services/backup.py`; `app/tasks.py`, `app/services/operations/backup.py` and `backup.py` all use them |
| `_build_context()` read `current_app.config["DEVLOG_CONFIG"]`, which the app factory never set — the whole `devlog deploy` group raised `KeyError` | `create_app()` sets `app.config["DEVLOG_CONFIG"]` |
| `deploy render` defaulted `--target` to `["all"]` but the service dispatched only on concrete names, rendering zero files | `_resolve_targets()` expands `all` to the five concrete targets |
| `deploy render --output DIR` created the directory and wrote nothing — the service emitted `filename`, the CLI read `path` | The CLI reads `filename`/`target` and writes `{target}-{basename}` |
| `config explain` raised `TypeError` for fields without an environment variable | The command tolerates a missing `env_var` |
| The `[storage]` section in `config.toml` was inert — `app/storage.py` read env vars only | `_storage_settings()` prefers the typed configuration |
| Environment variables did not override `config.toml` section fields (`APP_TITLE`, `BASE_URL`, `SMTP_HOST`, …) | `_build_section()` prefers the section-prefixed key and coerces the value to the field type |
| `config_to_toml()` dropped ten sections, so onboarding's config file carried no database URI | The serialiser writes every section of the model |
| The installed systemd units pointed at `/opt/devlog/current` even for a user-scope install, and `RuntimePaths` resolved the system release to `/etc/devlog/releases/current` | The release dir is `/opt/devlog/current` (overridable with `DEVLOG_RELEASE_DIR`); the units derive their paths from `ctx.paths.release_dir` |
| The installer extracted the Docker bundle one directory too deep and the release never published that bundle | `tar --strip-components=1`; `release.yml` builds and publishes `docker-bundle-<version>.tar.gz` |
| The Docker image excluded `migrations/` and nothing applied the schema | `.dockerignore` keeps `migrations`; the container CMD runs `flask db upgrade` before granian |
| The admin backup endpoints and the backup services used different directories, and the restore path fell back to `instance/blog.db` | The admin routes resolve the database and the backup directory through the same helpers as the services |
| The systemd unit's `WorkingDirectory` was the data directory, so `run:asgi_app` could not be imported | The unit runs from the release directory, and the ASGI application is exposed as `app.asgi:asgi_app` inside the package |
| The user-scope units ran `devlog serve`, `devlog worker` and `devlog scheduler`, none of which existed; the system unit ran `flask scheduler-start`, which was not registered | The three commands exist, and `flask scheduler-start` starts the scheduler in the foreground |
| `devlog deploy install` wrote every file into one directory, so the systemd unit never reached `/etc/systemd/system` | Each target has its own default directory; `--base-dir` still overrides it |
| The logrotate `postrotate` hook called `invoke-rc.d devlog`, a SysV unit that is never produced | It reloads `devlog-web` |
| `/health` reported `backup_freshness` from the legacy `instance/backups` directory, so a healthy install always looked like it had no backups | The check resolves the directory through `resolve_backup_dir()` |
| `/health?detailed=true` reported the database path as `//Users/…/data/devlog.sqlite3` — the URI prefix was replaced without accounting for the absolute-path slash | The detail uses `resolve_database_file()` |
| The hard-coded-path guard's `instance_backups` pattern matched nothing once the backup path was fixed, failing its own effectiveness check | The patterns are consolidated into `instance_data_path` and `hardcoded_data_filename`, which still match the remaining allowlisted fallbacks |
| The release wheel shipped stale `migrations/**/__pycache__/*.pyc` bytecode, and the sdist check flagged the committed `config.toml.example` template as a secret | `MANIFEST.in` excludes bytecode and cache directories, `pyproject.toml` adds `exclude-package-data`, and the packaging test allows the template by name |
| The rendered systemd units ran as `devlog`, but nothing created that account — and no document said to | Creating a system account is the operator's step: it is documented in `DEPLOY.md` and `docs/installation.md`, onboarding warns when it is missing, and `devlog doctor --check fs.service_account` reports it |
| `/var/log/devlog` was never created and `/run/devlog` is a tmpfs, so the unit's own `ExecStartPre` directory checks failed | Onboarding creates the log and runtime directories and hands them to the service account; the units declare `RuntimeDirectory=devlog` so systemd recreates the runtime path on every start |
| `DEPLOY.md` told non-Docker operators to run `npm ci && npm run build`, but a release wheel already contains the built assets | The build step is documented as a source-checkout step only; a release install needs no Node.js |
| `tests/config/test_legacy_import_boundary.py` scanned the whole repository root, so a nested worktree copy of the project failed the test | The scan is scoped to this project's source and skips VCS, cache and worktree directories |


## Architecture Cross-Reference

`architecture/overview.md` is the index. Each row links the deep dive that
covers it.

| Topic | Document |
|-------|----------|
| **Birds-eye module map (start here)** | [architecture/overview.md](architecture/overview.md) |
| App factory, configuration | [architecture/core/app-factory.md](architecture/core/app-factory.md), [architecture/core/configuration.md](architecture/core/configuration.md) |
| Data models (23 models) | [architecture/core/models.md](architecture/core/models.md) |
| Filesystem layout, install modes | [architecture/core/filesystem.md](architecture/core/filesystem.md) |
| Onboarding (first-run setup) | [architecture/core/onboarding.md](architecture/core/onboarding.md) |
| Theme system (Halloy) | [architecture/core/themes.md](architecture/core/themes.md) |
| Routes (admin, public, API, RSS) | [architecture/routes/admin-routes.md](architecture/routes/admin-routes.md), [architecture/routes/public-routes.md](architecture/routes/public-routes.md), [architecture/routes/api-routes.md](architecture/routes/api-routes.md), [architecture/routes/rss-feeds.md](architecture/routes/rss-feeds.md) |
| Services (overview) | [architecture/services/overview.md](architecture/services/overview.md) |
| Services (individual) | [architecture/services/backup.md](architecture/services/backup.md), [architecture/services/encryption.md](architecture/services/encryption.md), [architecture/services/search.md](architecture/services/search.md), [architecture/services/serialization.md](architecture/services/serialization.md), [architecture/services/slug.md](architecture/services/slug.md), [architecture/services/tag.md](architecture/services/tag.md), [architecture/services/tag_cache.md](architecture/services/tag_cache.md) |
| Operations services | [architecture/services/operations.md](architecture/services/operations.md) |
| Doctor diagnostics | [architecture/services/doctor.md](architecture/services/doctor.md) |
| Celery tasks, APScheduler | [architecture/tasks/celery-tasks.md](architecture/tasks/celery-tasks.md), [architecture/tasks/scheduler.md](architecture/tasks/scheduler.md) |
| Infrastructure (overview) | [architecture/infrastructure/overview.md](architecture/infrastructure/overview.md) |
| Infrastructure (individual) | [architecture/infrastructure/search.md](architecture/infrastructure/search.md), [architecture/infrastructure/email.md](architecture/infrastructure/email.md), [architecture/infrastructure/storage.md](architecture/infrastructure/storage.md), [architecture/infrastructure/webhooks.md](architecture/infrastructure/webhooks.md) |
| Frontend (overview) | [architecture/frontend/overview.md](architecture/frontend/overview.md) |
| Frontend (individual) | [architecture/frontend/templates.md](architecture/frontend/templates.md), [architecture/frontend/static-assets.md](architecture/frontend/static-assets.md), [architecture/frontend/appearance.md](architecture/frontend/appearance.md) |
| Testing (pytest, E2E, benchmarks) | [architecture/testing/test-suite.md](architecture/testing/test-suite.md) |
| Security (2FA, CSRF, rate limiting) | [architecture/deployment/security.md](architecture/deployment/security.md) |
| Operator CLI (`devlog`) | [architecture/deployment/cli.md](architecture/deployment/cli.md) |
| Managed deployment (systemd, proxy, drift) | [architecture/deployment/managed-deployment.md](architecture/deployment/managed-deployment.md) |
| Deployment (Docker, CI/CD) | [architecture/deployment/deployment.md](architecture/deployment/deployment.md), [architecture/deployment/docker.md](architecture/deployment/docker.md), [architecture/deployment/cicd.md](architecture/deployment/cicd.md) |
| Theme authoring (schema, tokens, operator guide) | [docs/themes/supported-schema.md](docs/themes/supported-schema.md), [docs/themes/blog-theme-contract.md](docs/themes/blog-theme-contract.md), [docs/themes/operator-guide.md](docs/themes/operator-guide.md) |

## Skills

Load a specialized skill using the `skill` tool with the skill name. The
canonical files live in `.skills/`; `.opencode/skills/<name>/SKILL.md` is a
symlink to them.

| Skill | Description | Triggers |
|-------|-------------|----------|
| `blog_cms` | The codebase map, hard rules, gotchas and known defects | Flask app, SQLAlchemy, CSRF, newsletter, APScheduler, FTS5, REST API, 2FA, comments, themes, appearance layer, `devlog` CLI, config.toml, onboarding, filesystem paths, systemd, compose, nginx |
| `release_validation` | The pre-release gate and how to diagnose a failing stage | release, tag, version bump, release check, lint, mypy, pytest, vite build, docker build, compose config |
| `e2e_testing` | Browser-level testing with Playwright | E2E tests, playwright, pytest-playwright, UI testing |
| `architecture_review` | Architecture documentation review workflow | architecture, review, documentation, verify, cross-reference |

When adding a skill, create `.skills/<skill_name>/skill.md` and add the matching
symlink `.opencode/skills/<skill_name>/SKILL.md` → `../../../.skills/<skill_name>/skill.md`.

## Plans

Plan status lives in [plans/AGENTS.override.md](plans/AGENTS.override.md). It
declares which series are active and which are historical, and points at the
architecture document that now holds each outcome. Read it before planning new
work — do not derive a plan from a phase file in isolation.

Three series still have work outstanding:

- **Site Identity, Authorship and Layout** — phase 06 (comment layout) is not
  started. CSS and template work only; it needs no migration.
- **Config/CLI Release 4** — the backup phase is partially implemented (create,
  verify, inspect and encryption shipped; the manifest, listing, restore
  planner and prune commands did not), and the update/uninstall phase has not
  started at all. There is no `devlog update` and no `devlog uninstall`.
- **Project Pages, Documentation and Distribution** — phases 01–02 are
  implemented, phases 03–05 are partially implemented and phase 06 ships the
  DevLog-native manifest only. Binary mirrors and any eggpack/eggup support
  are deferred by operator decision. The open gates are recorded per phase in
  `plans/`.

