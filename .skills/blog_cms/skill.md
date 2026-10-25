---
name: blog_cms
description: "DevLog — self-hosted Flask blog CMS with an admin dashboard, newsletter scheduling, FTS5 search, REST API, 2FA, comments, post series, a Halloy TOML theme system, an appearance layer for fonts and backdrops, an operations service layer, a standalone `devlog` CLI, filesystem path management and a managed deployment module. Use when working with the Flask app, SQLAlchemy models, session management, CSRF, newsletters, APScheduler, Celery, FTS5, the REST API, 2FA, comments, audit logs, post revisions, webhooks, themes, the appearance layer, the `devlog` CLI, config.toml, onboarding, filesystem paths, systemd, compose, nginx, logrotate or service lifecycle."
---

# DevLog Blog CMS Skill

Operational knowledge for working in this codebase. For structure and design
rationale, read `architecture/overview.md` — it is the index to every module's
deep dive. This skill covers what you need to *know before editing*, plus the
gotchas that are easy to get wrong.

## Orientation

| Module | Source | Deep dive |
|---|---|---|
| App factory | `app/__init__.py` | `architecture/core/app-factory.md` |
| Typed configuration | `app/config/` | `architecture/core/configuration.md` |
| Legacy config globals | `app/config_legacy.py` | — |
| Data models (17) | `app/models.py` | `architecture/core/models.md` |
| Filesystem paths | `app/filesystem/` | `architecture/core/filesystem.md` |
| Onboarding | `app/onboarding/` | `architecture/core/onboarding.md` |
| Theme system | `app/themes/` | `architecture/core/themes.md` |
| Appearance layer | `app/appearance/` | `architecture/frontend/appearance.md` |
| Routes | `app/routes/` | `architecture/routes/` |
| Services | `app/services/` | `architecture/services/overview.md` |
| Operations services | `app/services/operations/` | `architecture/services/operations.md` |
| Tasks | `app/tasks.py`, `app/scheduler.py` | `architecture/tasks/` |
| Infrastructure | `app/search.py`, `app/email.py`, `app/storage.py`, `app/webhooks.py` | `architecture/infrastructure/` |
| Standalone CLI | `devlog_cli/` | `architecture/deployment/cli.md` |
| Managed deployment | `app/deployment/` | `architecture/deployment/managed-deployment.md` |
| Middleware | `app/middleware/rate_limit.py` | `architecture/deployment/security.md` |

## Hard Rules

These are the contracts most easily broken by an otherwise-correct change.

1. **The theme system owns colour.** Static CSS consumes theme tokens only
   (`var(--bg-surface)`, `var(--border)`, `var(--text-dim)`, `var(--radius)`,
   `var(--space-*)`). No colour literals in a stylesheet, no token renames.
2. **`base.css` owns the shared prose rules**, because the admin shell does not
   load `public.css`. `public.css` must not define `.prose` rules.
3. **One default profile image.** `app/templates/_default_avatar.html` exports a
   single `default_avatar()` macro. Never fall back to the first letter of a
   name.
4. **One markdown producer.** `app/markdown_renderer.py` / the `markdown_safe`
   filter. Do not add a second markdown path.
5. **One heading ID generator** (`app/static/js/shared/heading-slug.js`) and one
   heading-anchor producer (`app/static/js/public/anchor-links.js`). The anchor
   is a direct child of the heading — no wrapper element.
6. **One path resolver.** `RuntimePaths` in `app/filesystem/layout.py`. Never
   derive a path independently.
7. **Services never import Click.** `app/services/operations/` functions take no
   Click, no terminal output and no process exit; they return a typed
   `OperationResult` and use `commit_with_rollback()` for transaction
   boundaries.
8. **Log the user id, never the username or the raw user object.**
9. **Never log or return `SECRET_KEY`, `ADMIN_PASSWORD`, API keys, TOTP
   secrets or backup codes.**
10. **CSRF applies to every POST except the API blueprint.** `should_skip_csrf()`
    in `app/csrf.py` is the only exemption.

## The Operations Service Layer

`app/services/operations/` holds operational logic so it can be called from the
standalone CLI, from the Flask CLI wrappers in `app/cli.py`, and from tests.

| Module | Public functions |
|---|---|
| `results.py` | `OperationResult` plus 27 typed subclasses with stable operation codes |
| `admin.py` | `create_admin`, `promote_admin`, `reset_admin_password`, `list_admins` |
| `database.py` | `check_database_integrity`, `rebuild_search_index`, `get_migration_status`, `run_migrations` |
| `media.py` | `scan_orphaned_media`, `apply_orphaned_media_cleanup` |
| `transfer.py` | `export_site_data`, `validate_import`, `import_site_data` |
| `themes.py` | `list_theme_descriptors`, `validate_theme`, `inspect_theme`, `refresh_theme_registry`, `get_theme_paths`, `run_accessibility_check` |
| `backup.py` | `create_backup_operation`, `verify_backup` |
| `deploy.py` | `deploy_render`, `deploy_install`, `deploy_check` |
| `onboard.py` | `detect_installation`, `generate_plan`, `apply_onboarding` |
| `doctor.py` | Diagnostic registry — **76 checks across 20 categories** |

Two consumer flows:

```
CLI handler → CliContext.ensure_app_context() → service function → render Result
Flask command wrapper → service function → render compatibility output
```

## The `devlog` CLI

Entry point `devlog_cli.main:main`, registered as the `devlog` console script in
`pyproject.toml`.

| Group | Module | Subcommands |
|---|---|---|
| `config` | `commands/config.py` | check, show, explain, paths, init, migrate |
| `admin` | `commands/admin.py` | create, promote, reset-password, list |
| `db` | `commands/db.py` | check, rebuild-search, status, migrate |
| `themes` | `commands/themes.py` | list, validate, inspect, refresh, paths, accessibility |
| `backup` | `commands/backup.py` | create, verify, inspect |
| `data` | `commands/data.py` | export, import |
| `media` | `commands/media.py` | scan, cleanup |
| `onboard` | `commands/onboard.py` | detect, plan, run, resume |
| `paths` | `commands/paths.py` | status, discover-legacy, migrate, check |
| `deploy` | `commands/deploy.py` | render, install, check |
| `doctor` | `commands/doctor.py` | doctor — `--production`, `--check`, `--category`, `--fix-safe`, `--list-checks` |
| lifecycle | `commands/lifecycle.py` | start, stop, restart, status, logs |

Global flags: `--config`, `--env-file`, `--json`, `--quiet`, `--verbose`,
`--no-color`.

### Known CLI defects

Verified against the source; see the deep dives for detail.

- `devlog deploy render|install|check` all raise `KeyError: 'DEVLOG_CONFIG'`.
  `_build_context()` reads `current_app.config["DEVLOG_CONFIG"]`, which
  `create_app()` never sets — only `tests/deployment/conftest.py` does.
- `devlog deploy render` renders **zero** files by default: `--target` defaults
  to `["all"]` but `_render_target()` dispatches only on concrete names.
- `devlog config explain` raises `TypeError` for at least `admin.username`,
  `database.pool_size` and `logging.level`.
- `--quiet` and `--no-color` are stored on `CliContext` but never read.
- `devlog deploy render --output DIR` creates `DIR` and writes nothing: the
  service emits `filename`, not `path`, and the CLI reads `path`.

## Theme System

Halloy-compatible TOML themes. The full contract is in `docs/themes/`; the
architecture is in `architecture/core/themes.md`.

- 50 bundled themes in `app/themes/bundled/`, packaged via `importlib.resources`.
- The **root `themes/` directory is the authoring catalogue** — the source the
  bundled package is generated from. It is *not* a runtime override directory.
  Runtime overrides come from `themes.external_dir` in `config.toml` or
  `THEME_EXTERNAL_DIR`.
- `BlogTheme` — frozen dataclass, **50 fields: 41 `RGB` + 9 `RGBA`**.
  `CSS_VARS` has **50 entries**, `ALIASES` has **38 entries**.
- Legacy `THEME_PRESETS` and the `SiteSettings.theme_preset` column were
  removed. `EMERGENCY_DEFAULT` is the emergency fallback.
- Runtime authority: `SiteSettings.theme_dark_name` (default `Catppuccin
  Mocha`), `theme_light_name` (default `Catppuccin Latte`),
  `theme_default_scheme` (`system`).
- `ThemeService` is per-process, stored on `app.extensions["theme_service"]`.
  `inject_theme()` in `app/context_processors.py` builds the `theme_vars` dict.
- Cache freshness requires an explicit `invalidate()` / `invalidate(name)`;
  there is no automatic mtime refresh. Entries carry a `source_fingerprint`
  computed with `hashlib.sha256()`.
- Accessibility policy is three-tier: `recommended`, `compatible-with-exceptions`,
  `experimental`. Exceptions live in `app/themes/ACCESSIBILITY_EXCEPTIONS.json`.

### Known theme defect

`shift_lightness()` in `app/themes/colors.py` computes `q` with an identical
expression in both branches of the `lightness < 0.5` test, so dark colours take
the light-colour path. `shift_lightness(from_hex('#161b22'), 0.06)` returns
`#002459` where a reference HSL conversion gives `#222a35`. This affects the
derived tokens `surface_hover`, `surface_active`, `border_strong` and, for a
dark accent, `accent_hover` / `text_link_hover`. Existing colour tests only
exercise grey, white and black, which take the unaffected path.

## Appearance Layer

`app/appearance/` answers "which typeface?" and "which graphic sits behind the
page?" — the questions the theme registry does not answer. It mirrors the theme
system's shape: registry → service → settings → runtime CSS.

- 10 bundled font families (4 sans, 6 mono) as `woff2` in `app/static/fonts/`.
- 3 bundled backdrops in `app/static/img/backdrops/`.
- A custom font or backdrop whose file has been **deleted** is treated as
  missing: both registries check that the file still exists, so the runtime
  falls back to a bundled asset instead of emitting a 404-backed stack.
- `app/appearance/svg.py` sanitises an uploaded backdrop so it stays inert.

## Onboarding and Installation

The installer installs **code artifacts only**. Onboarding creates
**configuration, secrets, database and admin state**. The two never overlap.

- 17 steps in `app/onboarding/steps.py`, driven by `StepContext` / `StepResult`.
- Metadata file: `onboarding-metadata.json` in the data directory (not
  `.devlog-installation.json`).
- `devlog onboard detect|plan|run|resume`.
- Omitting `--scope` falls back to `InstallMode.DEVELOPMENT` — it does **not**
  detect the scope from the current installation.
- Dry-run skips the file writes, but `step_resolve_paths()` still creates the
  config and data directories.
- The env file is rewritten from a fixed key set, so a re-run **drops any
  hand-added `.env` key**. Onboarding is re-runnable, but not idempotent in the
  strict sense.

## Configuration

`app/config/` is the typed system; `app/config_legacy.py` re-exports the legacy
module-level globals for backward compatibility. Precedence is
**env vars > config.toml > defaults**.

- `app/config/model.py` — 23 frozen dataclasses (`DevLogConfig` + 22 sections).
  This is the canonical source of truth for every field and its default.
- `app/config/loader.py` — `load_effective_config()`.
- `app/config/validation.py` — schema, security, filesystem, dependency and
  compatibility layers.
- `app/config/provenance.py` — tracks which source supplied each value.
- `app/config/secrets.py` — secret identification and redaction.
- `app/config/profiles.py` — development, native-production, docker-production,
  minimal, full.
- `app/config/serialization.py` — TOML/JSON output with redaction.

`config.toml.example` mirrors the dataclass defaults. `config.toml` is
gitignored. `devlog config explain <field>` documents a field.

## Gotchas

**Test interference.** `app/page_view_buffer.py` batches page views and can
break tests. Disable it:

```python
app.config["PAGE_VIEW_BUFFER_SIZE"] = 0
from app.page_view_buffer import shutdown_page_view_buffer
shutdown_page_view_buffer()
```

The `ensure_buffer_disabled` autouse fixture already does this in
`tests/conftest.py`, `tests/e2e/conftest.py`, `tests/benchmarks/conftest.py`
and `tests/test_api.py`.

**Session refresh.** `db.session.refresh()` fails if the object is not in the
current session — re-query from the database instead.

**SQLite batching.** When batching `post_ids` for SQLite, use chunks of 500.

**Newsletter retries.** Default is 5, not 3. The Celery task does not apply
that limit — it sends for all requested post IDs. The scheduler path does.

**Scheduler cadence.** `cleanup_expired_subscribers` and
`publish_scheduled_posts` run every 5 minutes; `run_daily_backup` runs at
02:00, not midnight.

**APScheduler is in-process.** It uses a FileLock with `timeout=0`, so it only
works on a single machine. Set `ENABLE_SCHEDULER=true` on exactly one
container. It is disabled by default.

**FTS init is silent.** `app/__init__.py` catches `OperationalError` during FTS
initialisation and rolls back without telling the user. If the FTS table cannot
be created, search silently returns nothing.

**`SiteSettings.get_instance()` flushes.** Creating the singleton flushes any
other uncommitted changes in the session. Use `db.session.merge()` or
`SELECT FOR UPDATE` instead.

**Legacy config globals live in `app/config_legacy.py`.** `app/config.py` no
longer exists. `_env_str()` there treats an empty string as unset.

**CSRF header name.** Read it from `data-csrf-header` or `csrfHeaders()` —
never hard-code it.

**Post image URLs.** Use the `post_image_url` filter; never re-wrap it with
`url_for('static', ...)`. Guard `srcset` — the filter returns `None` when no
variants exist.

**Route → JS modules.** `app/static/js/main.js` matches on a path-segment
boundary, longest prefix first.

**Vite build required.** `npm run build` must run before production.
`app/static/dist/.vite/manifest.json` must exist or JS assets resolve to
hashed paths that do not exist. Docker builds handle this in the
`frontend-builder` stage. **Restart the Flask server after every build** —
`app/vite.py` caches the manifest process-wide.

**Model count.** Exactly 17 models in `app/models.py`. `OperationResult` and its
subclasses in `app/services/operations/results.py` are plain dataclasses, not
models.

## Security

- Passwords hashed with `werkzeug.security` (pbkdf2:sha256).
- TOTP secrets encrypted at rest with AES-256-GCM (`app/services/encryption.py`).
  `User.totp_secret` decrypts on access; `set_totp_secret()` encrypts first.
- Backup codes are SHA-256 hashed and single-use (8 codes).
- Account lockout after 5 failed attempts for 15 minutes.
- `LOGIN_FAILURE_DELAY` has a 0.1 s floor (`app/config_legacy.py`).
- Webhook URLs validated by `is_safe_webhook_url()` in `app/utils.py`.
- Webhook payloads signed with HMAC-SHA256 in the `X-Webhook-Signature` header.
- `SESSION_IP_BINDING` is enforced by the `admin_required` decorator in
  `app/routes/admin/__init__.py`, not in the global `before_request` handler.
- API auth is two-tier: the legacy `API_KEY` env var (all scopes) and scoped
  `ApiToken` objects. `scope_allows()` supports exact match, `admin:*` for
  everything, and category wildcards such as `posts:*`.
- `app/storage.py:get_storage()` uses double-checked locking.

## Deployment

- Docker Compose requires explicit profiles — there is no default profile.
  `--profile production` runs blog, celery and redis; `--profile reverse-proxy`
  adds nginx; `--profile backup` adds the backup service.
- The app binds `127.0.0.1:5000` in Docker. Terminate TLS with a host-level
  reverse proxy.
- Celery worker needs `PYTHONPATH=/home/blog`.
- nginx runs as the `nginx` user.
- Backup encryption is AES-256-GCM, not GPG.
- CI runs **11 jobs**: `lint-and-type`, `test`, `theme-policy`,
  `migration-chain`, `theme-package-verification`, `frontend-build`,
  `security-audit`, `docker-build`, `e2e-tests`, `dependency-consistency`,
  `release1-package-smoke`.

## Where The Work Is Tracked

- `plans/AGENTS.override.md` — which plan series are active and which are
  historical. Read it before planning new work.
- `architecture/overview.md` — the module index and deep-dive map.
- `docs/` — operator and user documentation.
- `docs/internals/agent-maintainer-notes.md` — implementation history and
  deprecated-feature caveats.
