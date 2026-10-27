# Architecture Overview

DevLog is a Flask blog CMS with SQLAlchemy ORM, FTS5 full-text search, Celery task processing, a self-contained operator CLI, and a Vanilla JS frontend built with Vite.

This document is the **birds-eye view**: it names every discrete module, explains how the modules fit together, and links each one to a deep-dive document for focused review. Read this first to know the shape of the system; then follow a link to examine one component in detail.

---

## How To Read This Document

- **Sections 1–13** are the module map. Each names the module, its source, its responsibility, and its deep-dive link.
- **System Architecture** shows the runtime topology across processes.
- **Request Lifecycle** traces a single request through the layers.
- **Cross-Cutting Contracts** lists the seams where modules meet — these are where defects live.
- **Directory Structure** and **Key Technologies** are reference tables.

Every deep-dive link in this file is relative and resolves from `architecture/`.

---

## The Module Map

| # | Module | Responsibility | Deep Dive |
|---|--------|----------------|-----------|
| 1 | [Core Application](#1-core-application) | App factory, extensions, filters, context processors | [core/app-factory.md](core/app-factory.md) |
| 2 | [Configuration](#2-configuration) | Typed config dataclasses, loader, validation, provenance | [core/configuration.md](core/configuration.md) |
| 3 | [Data Models](#3-data-models) | 17 SQLAlchemy models and their relationships | [core/models.md](core/models.md) |
| 4 | [Filesystem Layout](#4-filesystem-layout) | Path resolution, install modes, legacy migration | [core/filesystem.md](core/filesystem.md) |
| 5 | [Onboarding](#5-onboarding) | First-run configuration, secrets, admin bootstrap | [core/onboarding.md](core/onboarding.md) |
| 6 | [Theme System](#6-theme-system) | Halloy TOML themes → typed tokens → CSS variables | [core/themes.md](core/themes.md) |
| 7 | [Appearance Layer](#7-appearance-layer) | Typeface and page backdrop registries | [frontend/appearance.md](frontend/appearance.md) |
| 8 | [Routes](#8-routes) | Public, admin, API and feed request handlers | [routes/public-routes.md](routes/public-routes.md), [routes/admin-routes.md](routes/admin-routes.md), [routes/api-routes.md](routes/api-routes.md), [routes/rss-feeds.md](routes/rss-feeds.md) |
| 9 | [Services](#9-services) | Business logic shared by CLI, API and admin | [services/overview.md](services/overview.md) |
| 10 | [Operations Services](#10-operations-services) | Terminal-free operational logic behind the CLI | [services/operations.md](services/operations.md), [services/doctor.md](services/doctor.md) |
| 11 | [Task Processing](#11-task-processing) | Celery queues and APScheduler jobs | [tasks/overview.md](tasks/overview.md), [tasks/celery-tasks.md](tasks/celery-tasks.md), [tasks/scheduler.md](tasks/scheduler.md) |
| 12 | [Infrastructure](#12-infrastructure) | Search, email, storage, webhooks, health | [infrastructure/overview.md](infrastructure/overview.md) |
| 13 | [Frontend](#13-frontend) | Templates, CSS, JavaScript, Vite build | [frontend/overview.md](frontend/overview.md), [frontend/templates.md](frontend/templates.md), [frontend/static-assets.md](frontend/static-assets.md) |
| 14 | [Operator CLI](#14-operator-cli) | The standalone `devlog` command surface | [deployment/cli.md](deployment/cli.md) |
| 15 | [Managed Deployment](#15-managed-deployment) | systemd units, compose/proxy rendering, drift, lifecycle | [deployment/managed-deployment.md](deployment/managed-deployment.md) |
| 16 | [Middleware & Security](#16-middleware--security) | Rate limiting, auth, CSRF, headers, encryption | [deployment/security.md](deployment/security.md) |
| 17 | [Testing](#17-testing) | pytest units, Playwright E2E, benchmarks | [testing/test-suite.md](testing/test-suite.md) |
| 18 | [Packaging & Install](#18-packaging--install) | Installer, Docker, CI/CD | [deployment/installation.md](deployment/installation.md), [deployment/docker.md](deployment/docker.md), [deployment/cicd.md](deployment/cicd.md) |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                               Clients                                        │
│                    (Browser, API Clients, RSS Readers)                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              Optional Reverse Proxy (nginx/Caddy/Traefik)                    │
│        TLS Termination, Static Files, Rate Limiting, Security Headers        │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Granian ASGI Server (Rust)                            │
│              Flask App + APScheduler (in-process) on 127.0.0.1:5000          │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
             ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
              ▼                         ▼                         ▼
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│   Celery Worker │     │       Redis         │     │                 │
│   (Redis Queue) │◄────│  (Broker + Cache   │────►│  (Rate Limits)  │
│                 │     │   + Rate Limits)    │     │                 │
│  • images       │     │                     │     │                 │
│  • newsletter   │     │  Queues:           │     │                 │
│  • webhooks     │     │  • images          │     │                 │
│  • email        │     │  • newsletter      │     │                 │
│  • backup       │     │  • webhooks        │     │                 │
│                 │     │  • email           │     │                 │
│                 │     │  • backup          │     │                 │
│                 │     │                     │     │                 │
│                 │     │  Single REDIS_URL  │     │                 │
│                 │     │  (multiple uses)   │     │                 │
└─────────────────┘     └─────────────────────┘     └─────────────────┘
             │                         │
             └─────────────────────────┼─────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SQLite (WAL) / PostgreSQL                             │
│                                                                              │
│  Tables: users, posts, tags, subscribers, page_views, share_events,           │
│          admin_sessions, site_settings, pages, post_revisions,                │
│          webhooks, webhook_events, series, post_series, comments,             │
│          admin_audit_logs, api_tokens                                         │
│                                                                              │
│  FTS5: posts_fts (full-text search virtual table)                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

The web process and the Celery worker are separate processes sharing one Redis. The scheduler is **in-process** with the web app — see [Task Processing](#11-task-processing) for the multi-container caveat.

---

## Request Lifecycle

A public page request crosses these layers in order:

```
   HTTP request
        │
        ▼
   ┌─────────────────┐
   │  Reverse proxy  │  TLS, static files, coarse rate limit
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │  Flask before_  │  CSRF (non-API POSTs), security headers,
   │  request handler│  session load, rate-limit keys
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │  Blueprint route│  public/ · admin/ · api/
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │    Services     │  tag, slug, authors, search, theme, appearance
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │   SQLAlchemy    │  models → SQLite (WAL) / PostgreSQL
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │  Template render│  context processors inject theme_vars,
   │                 │  site settings, footer, nav
   └────────┬────────┘
            ▼
   HTML response
```

An API request diverges at two points: it skips CSRF validation (`should_skip_csrf()` exempts the `api` blueprint) and it authenticates with an API key or scoped `ApiToken` rather than a session cookie. A background action (publish, subscribe, comment) additionally enqueues a Celery task.

---

## 1. Core Application

**Source:** `app/__init__.py`, `app/extensions.py`, `app/filters.py`, `app/context_processors.py`, `app/csrf.py`, `app/transaction.py`, `app/vite.py`, `app/validators.py`, `app/utils.py`

**Purpose:** Create and configure the Flask application, and provide the primitives the rest of the system builds on.

| Component | File | Purpose |
|-----------|------|---------|
| App factory | `app/__init__.py` | `create_app()` — registers blueprints, extensions, middleware, error handlers |
| Extensions | `app/extensions.py` | `db` (SQLAlchemy), `login_manager`, `migrate` |
| Filters | `app/filters.py` | Jinja filters: `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`, `post_image_avif_url_stub` (deprecated stub) |
| Context processors | `app/context_processors.py` | Inject `theme_vars`, site settings, footer data, page menu, canonical URL |
| CSRF | `app/csrf.py` | Sliding-window tokens (5 valid); `should_skip_csrf()` exempts the API blueprint |
| Transactions | `app/transaction.py` | `@transactional` decorator, `db_transaction()` context manager, slug retry |
| Vite integration | `app/vite.py` | `vite_asset()` — content-hashed URLs, CDN prefix, manifest lookup |
| Validation | `app/validators.py` | API input validation |
| Utilities | `app/utils.py` | SSRF protection, email validation, `UTCDateTime` |
| Markdown | `app/markdown_config.py`, `app/markdown_renderer.py`, `app/markdown_extensions.py` | One markdown pipeline; `nh3` allowlists; wraps code lines in `.code-line` spans |
| Misc utilities | `app/base62.py`, `app/csv_utils.py`, `app/db_utils.py`, `app/page_view_buffer.py`, `app/tag_cache.py` | Short share URLs, formula-safe CSV export, dialect helpers, buffered page views, tag count cache |

**Deep Dive:** [core/app-factory.md](core/app-factory.md)

---

## 2. Configuration

**Source:** `app/config/` (typed package), `app/config_legacy.py` (legacy globals)

Configuration is centralized in `config.toml` with environment variable overrides.

| Module | Purpose |
|--------|---------|
| `app/config/model.py` | 20 frozen dataclasses (`DevLogConfig` + 19 section classes) — the canonical source of truth for every field and its default |
| `app/config/loader.py` | `load_effective_config()` — precedence chain env vars > config.toml > defaults |
| `app/config/paths.py` | Path resolution with source tracking |
| `app/config/validation.py` | Multi-layer validation: schema, security, filesystem, dependencies, compatibility |
| `app/config/provenance.py` | Tracks which source supplied each value |
| `app/config/secrets.py` | Secret field identification and redaction |
| `app/config/profiles.py` | Deployment profiles: development, native-production, docker-production, minimal, full |
| `app/config/serialization.py` | TOML/JSON output with redaction |
| `app/config/migration.py` | Config version migration |

`app/config_legacy.py` re-exports the legacy module-level globals via `app/config/__init__.py` for backward compatibility. `config.toml.example` mirrors the dataclass defaults; `config.toml` itself is gitignored.

**Deep Dive:** [core/configuration.md](core/configuration.md)

---

## 3. Data Models

**Source:** `app/models.py` — exactly 17 models

| Model | Purpose |
|-------|---------|
| `User` | Admin users with TOTP 2FA, backup codes, account lockout |
| `Post` | Blog posts with revisions, tags, series |
| `Tag` | Post categorization |
| `Subscriber` | Newsletter subscribers with confirmation tokens |
| `Page` | Static pages |
| `PageView` | Analytics page views |
| `ShareEvent` | Social sharing tracking |
| `AdminSession` | Admin login session tracking with IP binding |
| `SiteSettings` | Singleton site configuration |
| `Webhook` | Webhook endpoints with encrypted secrets |
| `WebhookEvent` | Webhook delivery events with status tracking |
| `Series` | Post series groupings |
| `PostSeries` | Series-post junction with ordering |
| `Comment` | Threaded comments with parent-child relationships |
| `PostRevision` | Post edit history |
| `AdminAuditLog` | Security audit trail |
| `ApiToken` | API authentication tokens with scoped access |

`OperationResult` and its subclasses in `app/services/operations/results.py` are plain dataclasses, **not** SQLAlchemy models.

**Deep Dive:** [core/models.md](core/models.md)

---

## 4. Filesystem Layout

**Source:** `app/filesystem/`

`RuntimePaths` in `app/filesystem/layout.py` is the sole path-resolution authority — neither the installer nor onboarding derives paths independently.

| Mode | Data Root | Config | Logs | Runtime |
|------|-----------|--------|------|---------|
| System | `/var/lib/devlog` | `/etc/devlog/config.toml` | `/var/log/devlog` | `/run/devlog` |
| User | `$XDG_DATA_HOME/devlog` | `$XDG_CONFIG_HOME/devlog/config.toml` | `$XDG_STATE_HOME/devlog/logs` | `$XDG_RUNTIME_DIR/devlog` |
| Docker | `/data` | `/etc/devlog/config.toml` | `/var/log/devlog` | `/run/devlog` |
| Development | `./data` | `./config.toml` | `./logs` | `./instance` |

Each path carries provenance metadata (explicit override, env var, mode default). Explicit overrides always win over env vars and mode defaults. Legacy discovery is read-only; migration planning defaults to dry-run. Production services must not require write access to source directories.

CLI: `devlog paths status` · `devlog paths discover-legacy` · `devlog paths migrate` · `devlog paths check`

**Deep Dive:** [core/filesystem.md](core/filesystem.md)

---

## 5. Onboarding

**Source:** `app/onboarding/`, `app/services/operations/onboard.py`

Onboarding is the first-run configuration flow: detect installation → resolve mode → resolve paths → collect input → build config → resolve secrets → plan → validate → write config → write env → create directories → run migrations → create administrator → verify assets.

**Responsibility boundary:** the installer (`scripts/install.sh`) installs *code artifacts only*. Onboarding creates *configuration, secrets, database and admin state*. The two never overlap.

CLI: `devlog onboard detect` · `plan` · `run` · `resume`

**Deep Dive:** [core/onboarding.md](core/onboarding.md)

---

## 6. Theme System

**Source:** `app/themes/`, `app/themes/bundled/` (50 Halloy `.toml` themes)

The theme system owns **colour**. Static CSS may only consume the tokens it emits; it may never name a colour directly.

```
Halloy .toml → halloy.py parser → translate.py → BlogTheme (52 fields: 43 RGB + 9 RGBA)
             → to_css_variables() → theme_vars → templates
```

| Module | Purpose |
|--------|---------|
| `colors.py` | RGB/RGBA, hex parsing, WCAG contrast, mixing, lightness adjustment |
| `halloy.py` | Typed TOML parser with structured error classes |
| `model.py` | `BlogTheme` frozen dataclass, `CSS_VARS`, `ALIASES`, `EMERGENCY_DEFAULT` |
| `translate.py` | `translate_halloy_theme()`, `to_css_variables()`, `to_theme_vars()`, `to_legacy_vars()` |
| `diagnostics.py` | Accessibility validation, severity classification, structured findings |
| `resources.py` | `ThemeResource` protocol; bundled discovery via `importlib.resources`; external overrides |
| `cache.py` | In-process cache with `source_fingerprint` freshness validation |
| `registry.py` | `ThemeRegistry` — catalogue discovery, resolution, loading, invalidation, structured exceptions |
| `service.py` | `ThemeService` — per-process, stored on `app.extensions["theme_service"]` |

**Deep Dive:** [core/themes.md](core/themes.md)

---

## 7. Appearance Layer

**Source:** `app/appearance/`, `app/services/appearance_settings.py`

The appearance layer answers "which typeface?" and "which graphic sits behind the page?" — the questions the theme registry does not answer. It follows the same registry → service → settings → runtime shape as the theme system, so there is one mechanism to learn rather than two.

| Module | Purpose |
|--------|---------|
| `model.py` | `FontFamily` and `BackdropDescriptor` records |
| `fonts.py` | `FontRegistry` — bundled families plus operator uploads |
| `backdrops.py` | `BackdropRegistry` — bundled graphics plus operator uploads |
| `service.py` | `AppearanceService` — resolves the choice and emits the CSS |
| `svg.py` | `sanitize_svg()` — makes an uploaded backdrop inert |
| `uploads.py` | Validates and stores uploaded fonts and backdrops |

Ten font families ship locally (4 sans, 6 mono) as `woff2` files in `app/static/fonts/`. Three backdrops ship in `app/static/img/backdrops/`. A custom font or backdrop whose file has been deleted is treated as missing so the runtime falls back to a bundled asset rather than emitting a 404-backed stack.

**Deep Dive:** [frontend/appearance.md](frontend/appearance.md)

---

## 8. Routes

**Source:** `app/routes/`

| Blueprint | Prefix | Purpose |
|-----------|--------|---------|
| `public` | — | Homepage, archive, tags, series, posts, pages, search, share, subscribe, comments, authors, sitemap, robots, health |
| `admin` | `/admin` | Dashboard, editor, posts, pages, series, tags, users, sessions, media, backup, analytics, newsletter, settings, audit, comments |
| `api` | `/api` | REST API with scoped tokens |
| `rss` | — | Atom, RSS and JSON feeds |
| `errors` | — | 404, 500, 413 handlers |

### API Endpoints

| Endpoint | File | Purpose |
|----------|------|---------|
| `/api/posts` | `api/posts.py` | Post CRUD with pagination, search, filtering |
| `/api/pages` | `api/pages.py` | Static page management |
| `/api/series` | `api/series.py` | Post series management |
| `/api/tags` | `api/tags.py` | Tag management |
| `/api/subscribers` | `api/subscribers.py` | Subscriber management |
| `/api/stats` | `api/stats.py` | Dashboard statistics |
| — | `api/auth.py` | `require_api_key` decorator, `scope_allows()` scope matching |

`scope_allows()` supports exact match, `admin:*` for full access, and category wildcards such as `posts:*`.

**Deep Dive:** [routes/public-routes.md](routes/public-routes.md), [routes/admin-routes.md](routes/admin-routes.md), [routes/api-routes.md](routes/api-routes.md), [routes/rss-feeds.md](routes/rss-feeds.md)

---

## 9. Services

**Source:** `app/services/`

Business logic shared by the CLI, the API and the admin routes. Services do not import Flask request context and are callable from any of the three.

| Service | File | Purpose |
|---------|------|---------|
| Authors | `services/authors.py` | Author view resolution, author URLs, default author |
| Navigation | `services/navigation.py` | Menu page-ID parsing, menu resolution |
| Profile | `services/profile.py` | Profile validation, avatar storage |
| Site settings | `services/site_settings.py` | Site-settings form parsing and cache invalidation |
| Theme settings | `services/theme_settings.py` | Theme validation, legacy preset migration, effective name resolution |
| Appearance settings | `services/appearance_settings.py` | Appearance form parsing and key resolution |
| Backup | `services/backup.py` | Database backup with compression/encryption |
| Encryption | `services/encryption.py` | AES-256-GCM for TOTP secrets |
| Serialization | `services/serialization.py` | JSON export/import |
| Slug | `services/slug.py` | Unique slug generation with collision handling |
| Tag | `services/tag.py` | Tag CRUD |
| Search | `services/search/` | `SearchProvider` abstraction: SQLite FTS5 implementation, PostgreSQL stub |

The standalone FTS5 functions in `app/search.py` are **separate** from the `SearchProvider` abstraction — `SQLiteSearchProvider` wraps its own implementation rather than delegating to `app/search.py`.

**Deep Dive:** [services/overview.md](services/overview.md), [services/backup.md](services/backup.md), [services/search.md](services/search.md), [services/slug.md](services/slug.md), [services/tag.md](services/tag.md), [services/encryption.md](services/encryption.md), [services/serialization.md](services/serialization.md), [services/tag_cache.md](services/tag_cache.md)

---

## 10. Operations Services

**Source:** `app/services/operations/`

Operational business logic extracted from CLI handlers so it can run from the standalone CLI, from Flask CLI wrappers and from tests without a terminal.

| Module | Purpose |
|--------|---------|
| `results.py` | `OperationResult` base plus typed subclasses with stable operation codes |
| `admin.py` | Admin user create / promote / reset-password / list; centralised password complexity rules |
| `database.py` | SQLite integrity check, FTS rebuild, migration status |
| `media.py` | Orphaned media scan and cleanup |
| `transfer.py` | Site data export/import with atomic writes |
| `themes.py` | Theme list / validate / inspect / refresh / paths / accessibility facade |
| `backup.py` | Backup creation and verification with structured results |
| `deploy.py` | Managed deployment render / install / check |
| `onboard.py` | Onboarding detect / plan / apply |
| `doctor.py` | Diagnostic check registry — 76 checks across 20 categories |

The contract: no Click, no terminal output, no process exit. App-context required. Typed `OperationResult` return. `commit_with_rollback()` at transaction boundaries. Secrets are never returned or logged.

**Deep Dive:** [services/operations.md](services/operations.md), [services/doctor.md](services/doctor.md)

---

## 11. Task Processing

**Source:** `app/tasks.py`, `app/scheduler.py`, `app/celery_app.py`

| System | Purpose |
|--------|---------|
| Celery | Async task queue with a Redis broker, five queues |
| APScheduler | In-process scheduled jobs, four of them |

### Celery Queues

| Queue | Task | Purpose |
|-------|------|---------|
| `images` | `generate_image_variants` | Image variant generation |
| `newsletter` | `send_newsletter_task` | Newsletter delivery (no attempt-count check) |
| `webhooks` | `deliver_webhook_task` → `deliver_single_webhook_task` | Two-level webhook delivery |
| `email` | `send_confirmation_task`, `send_password_reset_task`, `notify_pending_comment_task` | Transactional emails |
| `backup` | `run_backup_task` | Database backups |

Webhook delivery is two-level: `deliver_webhook_task` fans out to one `deliver_single_webhook_task` per webhook, so one failing endpoint does not block the others. Retries live at the subtask level, not the parent.

### APScheduler Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| `send_daily_newsletter` | Daily at configured time | Auto-send newsletter |
| `cleanup_expired_subscribers` | Every 5 minutes | Remove unconfirmed expired subscribers |
| `publish_scheduled_posts` | Every 5 minutes | Auto-publish scheduled posts |
| `run_daily_backup` | Daily at 02:00 | Daily database backup |

**Newsletter delivery has two paths** that both terminate at `email.send_newsletter()`. The scheduler path respects `NEWSLETTER_MAX_RETRY_ATTEMPTS` (default 5); the Celery task sends for all requested post IDs regardless of prior failures.

> **⚠️ APScheduler multi-container limitation:** APScheduler uses `FileLock` with `timeout=0`, which only works on a single machine. Multiple container replicas each run their own scheduler and may execute jobs concurrently. Set `ENABLE_SCHEDULER=true` on exactly **one** container. It is disabled by default so replicas can run without duplicate jobs.

**Deep Dive:** [tasks/overview.md](tasks/overview.md), [tasks/celery-tasks.md](tasks/celery-tasks.md), [tasks/scheduler.md](tasks/scheduler.md)

---

## 12. Infrastructure

**Source:** `app/search.py`, `app/email.py`, `app/storage.py`, `app/webhooks.py`, `app/utils.py`, `app/routes/public/meta.py`

| Component | Purpose |
|-----------|---------|
| Search | FTS5 full-text search; BM25 ranking, snippets, did-you-mean |
| Email | SMTP delivery, `send_newsletter()` is the single newsletter terminus |
| Storage | Local/S3 abstraction with a thread-safe singleton |
| Webhooks | Event creation and HMAC-SHA256 signed delivery |
| SSRF protection | URL validation against private IP ranges (`app/utils.py`) |
| Health check | `GET /health` — basic mode is unauthenticated, detailed mode needs `HEALTH_CHECK_SECRET` |
| Metrics | `GET /metrics` — disabled unless `ENABLE_METRICS=true`; production requires `METRICS_SECRET` |

**FTS init is silent:** `app/__init__.py` catches `OperationalError` during FTS initialisation and rolls back without informing the user. If the FTS table cannot be created, search silently returns nothing.

**Deep Dive:** [infrastructure/overview.md](infrastructure/overview.md), [infrastructure/search.md](infrastructure/search.md), [infrastructure/email.md](infrastructure/email.md), [infrastructure/storage.md](infrastructure/storage.md), [infrastructure/webhooks.md](infrastructure/webhooks.md)

---

## 13. Frontend

**Source:** `app/templates/`, `app/static/`

| Component | Location | Purpose |
|-----------|----------|---------|
| Templates | `app/templates/` | Jinja2 — public pages, admin pages, email bodies |
| CSS | `app/static/css/` | `base.css` (tokens, prose, reset), `layout.css`, `forms.css`, `admin.css`, `public.css`, `utilities.css`, `critical.css`, `prism.css` (Prism token colours) |
| JavaScript | `app/static/js/` | Vanilla ES modules: `shared/`, `public/`, `admin/`, `lib/` |
| Fonts | `app/static/fonts/` | Self-hosted `woff2` families |
| Images | `app/static/img/` | Favicon, default post image, backdrops |
| Uploads | `app/static/uploads/` | User media, custom fonts and backdrops |
| Build output | `app/static/dist/` | Vite bundle + `manifest.json` |

JavaScript is loaded route-by-route: `main.js` maps path prefixes to module lists, matching on a path-segment boundary with the longest prefix winning. `admin/base.html` and `base.html` are **standalone** root templates — neither extends the other.

All JS assets in templates use `vite_asset()` for content-hashed filenames and optional CDN prefix support.

> **⚠️ Production requirement:** `npm run build` must run before production deployment. `app/static/dist/.vite/manifest.json` must exist, otherwise JS assets resolve to hashed paths that do not exist. Docker builds handle this in the `frontend-builder` stage.

**Deep Dive:** [frontend/overview.md](frontend/overview.md), [frontend/templates.md](frontend/templates.md), [frontend/static-assets.md](frontend/static-assets.md)

---

## 14. Operator CLI

**Source:** `devlog_cli/` — the standalone `devlog` entry point

A Click CLI that shares no code path with the Flask app except through the services layer. It builds its own `CliContext`, calls an operations service, and renders a `Result`.

| Component | Purpose |
|-----------|---------|
| `main.py` | Root Click group and sub-group registration |
| `context.py` | `CliContext` — config path, env file, output flags |
| `result.py` | `Result` dataclass with success/failure factories |
| `output.py` | Human-readable and JSON rendering |
| `errors.py` | Domain exception hierarchy |
| `exit_codes.py` | Stable `ExitCode` IntEnum |

### Command Groups

| Group | Commands |
|-------|----------|
| `config` | `check`, `show`, `explain`, `paths`, `init`, `migrate` |
| `admin` | `create`, `promote`, `reset-password`, `list` |
| `db` | `check`, `rebuild-search`, `status`, `migrate` |
| `themes` | `list`, `validate`, `inspect`, `refresh`, `paths`, `accessibility` |
| `backup` | `create`, `verify`, `inspect` |
| `data` | `export`, `import` |
| `media` | `scan`, `cleanup` |
| `onboard` | `detect`, `plan`, `run`, `resume` |
| `paths` | `status`, `discover-legacy`, `migrate`, `check` |
| `deploy` | `render`, `install`, `check` |
| `doctor` | `doctor` with `--production`, `--check`, `--category`, `--fix-safe`, `--list-checks` |
| lifecycle | `start`, `stop`, `restart`, `status`, `logs` |

**Deep Dive:** [deployment/cli.md](deployment/cli.md)

---

## 15. Managed Deployment

**Source:** `app/deployment/`

The layer that renders and installs host-level configuration for a native (non-Docker) installation, and keeps it in sync with drift detection.

| Module | Purpose |
|--------|---------|
| `model.py` | `DeploymentContext`, `RenderResult`, context validation |
| `systemd.py` | Renders and validates web / worker / scheduler units |
| `compose.py` | Renders a compose file and its env file |
| `proxy.py` | Renders and validates Caddyfile and nginx configs |
| `logrotate.py` | Renders the logrotate policy |
| `install.py` | Install plan, atomic writes, backup and restore |
| `drift.py` | Content-hash drift detection against a managed manifest |
| `lifecycle.py` | Service status, start / stop / restart, logs — systemd or compose backend |

**Deep Dive:** [deployment/managed-deployment.md](deployment/managed-deployment.md)

---

## 16. Middleware & Security

**Source:** `app/middleware/rate_limit.py`, `app/csrf.py`, `app/routes/admin/auth.py`, `app/services/encryption.py`

| Feature | Implementation |
|---------|---------------|
| **Authentication** | Session-based with optional TOTP 2FA |
| **2FA** | TOTP secrets encrypted with AES-256-GCM |
| **Backup codes** | SHA-256 hashed, single-use (8 codes) |
| **CSRF** | Sliding-window tokens (5 valid), enforced for all POSTs except the API blueprint |
| **API auth** | Two-tier: legacy `API_KEY` env var with HMAC comparison, plus scoped `ApiToken` with `require_scope()` |
| **Rate limiting** | Flask-Limiter — global (100/min) plus per-admin and per-IP admin limits |
| **Account lockout** | 5 failed attempts → 15-minute lockout |
| **SSRF protection** | URL validation against private IP ranges |
| **Webhook signing** | HMAC-SHA256 via the `X-Webhook-Signature` header |
| **XSS** | `nh3` HTML sanitiser, CSP headers |
| **Audit logging** | `AdminAuditLog` for admin actions |
| **Session fixation** | `session.clear()` before `login_user()` |

**Deep Dive:** [deployment/security.md](deployment/security.md)

---

## 17. Testing

**Source:** `tests/`

| Test Type | Location | Tool |
|-----------|----------|------|
| Unit/Integration | `tests/test_*.py` | pytest |
| Benchmarks | `tests/benchmarks/` | pytest |
| E2E | `tests/e2e/` | Playwright |

**Key fixtures:** `app`, `db`, `client`, `admin_user`, `authenticated_client`, `api_client`, `sample_post`, `sample_tag`, `sample_subscriber`. Shared fixtures live in `tests/shared_fixtures.py`.

The E2E suite defines its own session-scoped `app` fixture in `tests/e2e/conftest.py` with a separate `blog_e2e` database, so `pytest tests/e2e/` runs standalone.

**Deep Dive:** [testing/test-suite.md](testing/test-suite.md)

---

## 18. Packaging & Install

**Source:** `scripts/install.sh`, `Dockerfile`, `docker-compose.yml`, `nginx/`, `.github/workflows/ci.yml`

| Component | Purpose |
|-----------|---------|
| Installer | One-shot native or Docker install with SHA-256 checksum verification; versioned release layout with an atomic `current` symlink |
| Onboarding | First-run configuration — see [Onboarding](#5-onboarding) |
| Docker | Multi-stage build; the `frontend-builder` stage runs the Vite build |
| Docker Compose | All services require explicit profiles — there is no default profile |
| nginx | Optional TLS-terminating reverse proxy (`--profile reverse-proxy`) |
| CI | 11 jobs in `.github/workflows/ci.yml` |

Docker Compose profiles:

| Profile | Services |
|---------|----------|
| `production` | blog, celery, redis — app bound to `127.0.0.1:5000` |
| `reverse-proxy` | nginx (optional) |
| `backup` | backup service |

**Deep Dive:** [deployment/installation.md](deployment/installation.md), [deployment/docker.md](deployment/docker.md), [deployment/cicd.md](deployment/cicd.md)

---

## Cross-Cutting Contracts

These are the seams where modules meet. Each has a single owner; violating them is how the layers drift apart.

| Value | Owner | Consumers must |
|---|---|---|
| Colour | The theme runtime | Static CSS consumes tokens only; every referenced token is emitted or defined |
| Typeface | The appearance runtime | `--font-sans` and `--font-mono` are emitted by `app/appearance/service.py`; stylesheets never name a family |
| Prose typography | `app/static/css/base.css` | The admin shell does not load `public.css`, so `public.css` must not own `.prose` rules |
| Default profile image | `app/templates/_default_avatar.html` | One macro for every "no profile picture" surface; never fall back to the first letter of a name |
| Heading ID | `app/static/js/shared/heading-slug.js` | One generator only |
| Heading anchor | `app/static/js/public/anchor-links.js` | The anchor is a child of the heading, never wrapped; transparent until the heading is hovered or the anchor focused |
| Post image URL | `post_image_url` filter (`app/filters.py`) | Use the URL directly; never re-wrap with `url_for('static', …)` |
| Responsive `srcset` | `post_image_srcset` filter | Guard the attribute — the filter returns `None` when no variants exist |
| Markdown | `app/markdown_renderer.py` / `markdown_safe` | One producer; do not add a second markdown pipeline |
| CSRF header name | `app/csrf.py` (`CSRF_HEADER_NAME`) | Read it from `data-csrf-header` or `csrfHeaders()`; never hard-code it |
| Route → JS modules | `app/static/js/main.js` | Match on a path-segment boundary, longest match first |
| Filesystem paths | `RuntimePaths` (`app/filesystem/layout.py`) | One resolver; do not derive paths independently |
| Secrets | The generating module | Never log, never return, never echo into a result payload |
| Transaction boundary | `commit_with_rollback()` | Use it in services; do not call `db.session.commit()` directly |

---

## Directory Structure

```
blog/
├── app/                              # Main application package
│   ├── __init__.py                   # create_app() — Flask app factory
│   ├── extensions.py                 # db, login_manager, migrate
│   ├── models.py                     # SQLAlchemy models (17)
│   ├── filters.py                    # Jinja2 template filters
│   ├── context_processors.py         # Template context injectors
│   ├── csrf.py                       # CSRF token handling
│   ├── transaction.py                # Transaction decorator/context manager
│   ├── validators.py                 # API input validation
│   ├── utils.py                      # SSRF protection, UTCDateTime, email validation
│   ├── base62.py                     # Short URL encoding
│   ├── csv_utils.py                  # CSV export with formula-injection prevention
│   ├── db_utils.py                   # Database dialect helpers
│   ├── page_view_buffer.py           # Buffered page-view writes
│   ├── tag_cache.py                  # Tag count cache
│   ├── vite.py                       # Vite integration (hashed asset URLs)
│   ├── markdown_config.py            # Shared nh3 sanitiser allowlists
│   ├── markdown_renderer.py          # The single markdown pipeline
│   ├── markdown_extensions.py        # Markdown extension registration
│   ├── storage.py                    # Local/S3 storage abstraction
│   ├── search.py                     # Standalone FTS5 implementation
│   ├── email.py                      # SMTP email sending
│   ├── webhooks.py                   # Webhook event creation and delivery
│   ├── backup_encryption.py          # AES-256-GCM backup encryption
│   ├── backup_integrity.py           # Backup checksum and SQLite validation
│   ├── webhook_encryption.py         # AES-256-GCM webhook secret encryption
│   ├── config_legacy.py              # Legacy config globals (re-exported)
│   ├── cli.py                        # Flask CLI compatibility wrappers
│   ├── celery_app.py                 # Celery configuration
│   ├── tasks.py                      # Celery async tasks
│   ├── scheduler.py                  # APScheduler jobs
│   │
│   ├── config/                       # Typed configuration package
│   │   ├── model.py                  # 20 frozen dataclasses
│   │   ├── loader.py                 # load_effective_config()
│   │   ├── paths.py                  # Path resolution with source tracking
│   │   ├── validation.py             # Multi-layer validation
│   │   ├── provenance.py              # Source tracking
│   │   ├── secrets.py                # Secret identification and redaction
│   │   ├── profiles.py               # Deployment profiles
│   │   ├── serialization.py          # TOML/JSON output with redaction
│   │   └── migration.py              # Config version migration
│   │
│   ├── themes/                       # Halloy theme subsystem
│   │   ├── colors.py                 # RGB/RGBA, hex parsing, WCAG contrast
│   │   ├── halloy.py                 # Typed Halloy TOML parser
│   │   ├── model.py                  # BlogTheme, CSS_VARS, ALIASES
│   │   ├── translate.py              # Translation and CSS generation
│   │   ├── diagnostics.py            # Accessibility validation
│   │   ├── resources.py              # ThemeResource protocol, discovery
│   │   ├── cache.py                  # In-process cache with fingerprints
│   │   ├── registry.py               # Authoritative theme registry
│   │   ├── service.py                # Per-process ThemeService
│   │   └── bundled/                  # 50 packaged .toml themes
│   │
│   ├── appearance/                   # Typeface and backdrop layer
│   │   ├── model.py                  # FontFamily, BackdropDescriptor
│   │   ├── fonts.py                  # FontRegistry
│   │   ├── backdrops.py              # BackdropRegistry
│   │   ├── service.py                # AppearanceService
│   │   ├── svg.py                    # SVG sanitiser
│   │   └── uploads.py                # Upload validation and storage
│   │
│   ├── filesystem/                   # Centralised path system
│   │   ├── layout.py                 # RuntimePaths, InstallMode, provenance
│   │   ├── prepare.py                # Directory creation with permissions
│   │   ├── discovery.py              # Legacy layout discovery (read-only)
│   │   ├── migration.py              # Migration planner and executor
│   │   ├── verification.py           # Post-migration verification
│   │   └── lifecycle.py              # Path categories and lifecycle policy
│   │
│   ├── onboarding/                   # First-run configuration flow
│   │   ├── model.py                  # OnboardingInput, build_config_from_input
│   │   ├── state.py                  # InstallState, detect_installation
│   │   ├── steps.py                  # The step pipeline
│   │   ├── planner.py                # PlannedAction, plan rendering
│   │   ├── secrets.py                # Secret generation and env files
│   │   ├── metadata.py               # OnboardingMetadata
│   │   └── rendering.py              # Completion rendering
│   │
│   ├── deployment/                   # Managed deployment rendering
│   │   ├── model.py                  # DeploymentContext, RenderResult
│   │   ├── systemd.py                # systemd unit rendering
│   │   ├── compose.py                # Compose file rendering
│   │   ├── proxy.py                  # Caddy / nginx rendering
│   │   ├── logrotate.py              # Logrotate rendering
│   │   ├── install.py                # Install plan, atomic writes, backups
│   │   ├── drift.py                  # Drift detection
│   │   └── lifecycle.py              # Service status and control
│   │
│   ├── routes/                       # Route blueprints
│   │   ├── admin/                    # Admin blueprint (auth, posts, users, …)
│   │   │   ├── posts/                # editor.py, manage.py, revisions.py
│   │   │   └── helpers/              # Shared admin utilities
│   │   ├── api/                      # REST API blueprint
│   │   ├── public/                   # Public-facing blueprint
│   │   ├── rss.py                    # Atom, RSS, JSON feeds
│   │   └── errors.py                 # 404, 500, 413 handlers
│   │
│   ├── services/                     # Business logic services
│   │   ├── operations/               # Terminal-free operational services
│   │   │   ├── results.py            # Typed OperationResult dataclasses
│   │   │   ├── admin.py              # Admin user management
│   │   │   ├── database.py           # Integrity, FTS rebuild, migration status
│   │   │   ├── media.py              # Orphaned media scan and cleanup
│   │   │   ├── transfer.py           # Export/import
│   │   │   ├── themes.py             # Theme facade
│   │   │   ├── backup.py             # Backup create/verify
│   │   │   ├── deploy.py             # Managed deployment facade
│   │   │   ├── onboard.py            # Onboarding facade
│   │   │   └── doctor.py             # Diagnostic check registry
│   │   ├── search/                   # SearchProvider abstraction
│   │   ├── authors.py                # Author resolution
│   │   ├── navigation.py             # Menu resolution
│   │   ├── profile.py                # Profile validation and avatar storage
│   │   ├── site_settings.py          # Site settings parsing
│   │   ├── theme_settings.py         # Theme validation and migration
│   │   ├── appearance_settings.py    # Appearance form parsing
│   │   ├── backup.py                 # Backup service
│   │   ├── encryption.py             # AES-256-GCM
│   │   ├── serialization.py          # JSON export/import
│   │   ├── slug.py                   # Slug generation
│   │   └── tag.py                    # Tag CRUD
│   │
│   ├── middleware/                   # WSGI middleware
│   │   └── rate_limit.py             # Admin and per-IP rate limiting
│   │
│   └── static/                       # Frontend assets
│       ├── css/                      # Stylesheets
│       ├── js/                       # JavaScript modules
│       ├── img/                      # Static images and backdrops
│       ├── fonts/                    # Self-hosted woff2 families
│       ├── uploads/                  # User media
│       └── dist/                     # Vite build output
│
├── devlog_cli/                       # Standalone CLI package
│   ├── main.py                       # Root Click group (devlog entry point)
│   ├── context.py                    # CliContext
│   ├── output.py                     # Human/JSON rendering
│   ├── errors.py                     # Domain exception hierarchy
│   ├── exit_codes.py                 # Stable ExitCode IntEnum
│   ├── result.py                     # Result dataclass with factories
│   └── commands/                     # One module per command group
│
├── tests/                            # Test suite
│   ├── conftest.py                   # Pytest fixtures and configuration
│   ├── shared_fixtures.py            # Shared fixtures
│   ├── test_*.py                     # Unit/integration tests
│   ├── benchmarks/                   # Performance tests
│   └── e2e/                          # Playwright E2E tests
│
├── migrations/                       # Flask-Migrate database migrations
├── architecture/                     # This directory
│   ├── overview.md                   # This file
│   ├── core/                         # App factory, configuration, models, filesystem, onboarding, themes
│   ├── routes/                       # Public, admin, API, feeds
│   ├── services/                     # Service layer and operations services
│   ├── tasks/                        # Celery and APScheduler
│   ├── infrastructure/               # Search, email, storage, webhooks
│   ├── frontend/                     # Templates, static assets, appearance
│   ├── deployment/                   # CLI, managed deployment, security, install, Docker, CI/CD
│   └── testing/                      # Test suite
│
├── themes/                           # Halloy authoring catalogue (source of truth for bundled themes)
├── scripts/                          # DevOps scripts (installer, dev setup, release checks)
├── plans/                            # Implementation plans and review roadmaps
├── docs/                             # User and operator documentation
├── nginx/                            # Nginx configuration
├── run.py                            # Development entry point (ASGI wrapper)
├── config.toml                       # Local configuration (gitignored)
├── docker-compose.yml                # Container orchestration
├── Dockerfile                        # Container image
├── requirements.txt                  # Python dependencies
├── package.json                      # Node dependencies
└── vite.config.js                    # Vite bundler config
```

---

## Database Schema

```
┌─────────────────┐     ┌─────────────────┐
│      User       │────►│  AdminSession   │
└────────┬────────┘     └─────────────────┘
         │
         ├──────────────────────────────┐
         │                              │
         ▼                              ▼
┌─────────────────┐           ┌─────────────────┐
│  AdminAuditLog  │           │  PostRevision    │
└─────────────────┘           └─────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│      Post        │────►│      Tag        │◄────│    post_tags    │
└────────┬────────┘     └─────────────────┘     └─────────────────┘
         │
         ├──────────────┬───────────────┬───────────────┬───────────────┐
         │              │               │               │               │
         ▼              ▼               ▼               ▼               ▼
┌─────────────────┐ ┌─────────┐ ┌─────────────┐ ┌───────────┐ ┌─────────────┐
│   PageView      │ │ShareEvent│ │  Comment    │ │PostSeries │ │PostRevision │
└─────────────────┘ └─────────┘ └──────┬──────┘ └───────────┘ └─────────────┘
                                       │ (self-referential)
                                       ▼
                                   ┌─────────────┐
                                   │   Comment   │
                                   │  (parent_id)│
                                   └─────────────┘
┌─────────────────┐     ┌─────────────────┐
│   Subscriber     │     │     Series       │
└─────────────────┘     └────────┬────────┘
                                  │
                                  ▼
                           ┌─────────────┐
                           │  PostSeries │
                           └─────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Webhook     │────►│  WebhookEvent   │     │   SiteSettings  │
└─────────────────┘     └─────────────────┘     └─────────────────┘

┌─────────────────┐
│    ApiToken     │
│ (scoped access) │
└─────────────────┘
```

---

## Key Technologies

| Component | Technology |
|-----------|------------|
| Web framework | Flask 3.1+ |
| ORM | SQLAlchemy 2.0 |
| Database | SQLite (WAL) / PostgreSQL |
| ASGI server | Granian (Rust) |
| Task queue | Celery 5.x + Redis |
| Scheduler | APScheduler |
| Cache | Flask-Caching + Redis |
| Rate limiting | Flask-Limiter |
| Compression | Flask-Compress |
| Frontend build | Vite 6.x |
| CSS | Vanilla CSS (no framework) |
| JavaScript | Vanilla JS (ES modules) |
| Templates | Jinja2 |
| Migrations | Flask-Migrate / Alembic |
| HTML sanitiser | nh3 |
| 2FA | pyotp (TOTP) |
| QR codes | qrcode |
| Image processing | Pillow |
| S3 client | boto3 |
| HTTP client | requests |
| Cryptography | cryptography (AES-256-GCM) |
| Monitoring | Prometheus (optional) |

---

## Related Documents

**Start here:** [README.md](../README.md) for the quickstart, then
[DEPLOY.md](../DEPLOY.md) for production deployment and
[USAGE.md](../USAGE.md) for the admin features.

**Architecture:**
- [AGENTS.md](../AGENTS.md) — Agent guidelines and codebase conventions
- [ARCHITECTURE.md](../ARCHITECTURE.md) — The entry point for this directory
- [Plans](../plans/AGENTS.override.md) — Which plan series are active and which are historical

**Agent skills** (canonical copies in `.skills/`):
- [blog_cms](../.skills/blog_cms/skill.md) — The codebase map, hard rules, gotchas and known defects
- [release_validation](../.skills/release_validation/skill.md) — The pre-release gate and how to diagnose a failing stage
- [e2e_testing](../.skills/e2e_testing/skill.md) — Browser-level testing with Playwright
- [architecture_review](../.skills/architecture_review/skill.md) — The review workflow these documents follow

**Operator and user documentation:**
- [docs/index.md](../docs/index.md) — The documentation entry point
- [Operator Guide](../docs/themes/operator-guide.md) — Theme operation
- [Filesystem Layout](../docs/filesystem-layout.md) — Path layout reference
- [API docs](../docs/api/posts.md) — API usage
- [OpenAPI spec](../docs/openapi.yaml) — also served at `/api/docs`

