---
name: blog_cms
description: "Blog CMS - Flask-based blogging platform with admin dashboard, newsletter scheduling, FTS5 search, multi-admin sessions, custom CSS theming, syntax highlighting themes, post series, Atom feed, 2FA, Comments, Audit Log, Post Revision Diff. Use when working with Flask app, SQLAlchemy, session management, CSRF, newsletter, APScheduler, FTS5, REST API, password reset, post revisions, preview links, toasts, dashboard charts, graceful shutdown, Docker deployment, Vite bundler, 2FA, Comments, Audit Log."
---

# Blog CMS Skill

Specialized knowledge for working with this Flask-based blog CMS codebase.

## Architecture Overview

This is a Flask-based blog CMS with:
- SQLAlchemy 2.0 with SQLite (WAL mode)
- APScheduler for background jobs
- Celery for async tasks
- FTS5 full-text search
- Custom CSS theming with theme presets
- 2FA via pyotp
- RSS/Atom/JSON feed endpoints
- Webhook delivery system

## Key File Locations

| Component | Location |
|-----------|----------|
| App factory | `app/__init__.py` |
| Typed config | `app/config/` (model, loader, validation, provenance, secrets, profiles, serialization, migration) |
| Legacy config | `app/config_legacy.py` (re-exported via `app/config/__init__.py`) |
| Models | `app/models.py` |
| Routes (API) | `app/routes/api/` |
| Routes (Admin) | `app/routes/admin/` |
| Routes (Public) | `app/routes/public/` |
| Routes (RSS) | `app/routes/rss.py` |
| Services | `app/services/` |
| Tasks | `app/tasks.py` |
| Webhooks | `app/webhooks.py` |
| Email | `app/email.py` |
| Search | `app/services/search/` |
| Storage | `app/storage.py` |
| Templates | `app/templates/` |
| Static CSS | `app/static/css/` |
| CLI package | `devlog_cli/` — standalone Click CLI (entry point: `devlog_cli.main:main`, registered as `devlog` in `pyproject.toml`) |
| Operations services | `app/services/operations/` — business logic for CLI commands |

## Operations Service Layer

Business logic for CLI commands lives in `app/services/operations/`:

- `admin.py` — create_admin, promote_admin, reset_admin_password, list_admins
- `database.py` — check_database_integrity, rebuild_search_index
- `media.py` — scan_orphaned_media, apply_orphaned_media_cleanup
- `transfer.py` — export_site_data, validate_import, import_site_data
- `themes.py` — list_theme_descriptors, validate_theme, inspect_theme, refresh_theme_registry, get_theme_paths, run_accessibility_check
- `backup.py` — create_backup_operation, verify_backup

Service functions:
- Never depend on Click or terminal output
- Return typed OperationResult subclasses
- Require Flask application context
- Use commit_with_rollback() for transactions

Standalone CLI commands in `devlog_cli/commands/` call these services.
Flask commands in `app/cli.py` are compatibility wrappers.

### CLI Commands (`devlog`)

Entry point: `devlog_cli.main:main` registered as `devlog` in `pyproject.toml [project.scripts]`.

| Command group | Module | Purpose |
|---------------|--------|---------|
| `devlog config` | `devlog_cli/commands/config.py` | check, show, explain, paths, init, migrate |
| `devlog admin` | `devlog_cli/commands/admin.py` | Admin user management |
| `devlog db` | `devlog_cli/commands/db.py` | Database operations |
| `devlog data` | `devlog_cli/commands/data.py` | Import/export |
| `devlog themes` | `devlog_cli/commands/themes.py` | Theme operations |
| `devlog backup` | `devlog_cli/commands/backup.py` | Backup operations |

## Verified Routes

| Route | Path | Method |
|-------|------|--------|
| New post | `/admin/new` | GET/POST |
| Edit post | `/admin/edit/<id>` | GET/POST |
| Tag delete | `/admin/tags/delete/<id>` | POST |
| Comment submission | `/POST /post/<slug>/comment` | POST |
| Subscribe | `/subscribe` | POST only |
| API post publish | `PUT /api/posts/<id>` | PUT with `{"published": true}` |

## Important Patterns

### Feed Endpoints
Three feed endpoints available at `/atom`, `/rss`, `/json`:
- `/atom` - Atom 1.0 feed
- `/rss` - RSS 2.0 feed
- `/json` - JSON Feed 1.1

Implementation in `app/routes/rss.py`.

### Webhook Event Triggering
Events are triggered at these points:
```python
# Post publish/unpublish - app/routes/api/posts.py
if "published" in data and was_published != post.published:
    from app.webhooks import create_webhook_event
    create_webhook_event(
        event_type="post.published" if post.published else "post.unpublished",
        payload={"post_id": post.id, "title": post.title, "slug": post.slug},
        target_id=post.id,
        target_type="post"
    )

# Subscriber confirmation - app/routes/public/subscribe.py
create_webhook_event(
    event_type="subscriber.confirmed",
    payload={"subscriber_id": sub.id, "email": sub.email},
    target_id=sub.id,
    target_type="subscriber"
)
```

### Page View Buffer
The page view buffer (`app/page_view_buffer.py`) can cause test interference. Disable in tests:
```python
app.config["PAGE_VIEW_BUFFER_SIZE"] = 0
from app.page_view_buffer import shutdown_page_view_buffer
shutdown_page_view_buffer()
```

### Snippet Batching for SQLite
When batching post_ids for SQLite, use 500 at a time:
```python
chunk_size = 500
for i in range(0, len(post_ids), chunk_size):
    chunk = post_ids[i:i + chunk_size]
```

### Configuration Priority
env vars > config.toml > defaults

### Typed Configuration System

The codebase has a typed configuration system at `app/config/`:
- `app/config/model.py` — 20 frozen dataclasses (`DevLogConfig` + 19 section classes)
- `app/config/loader.py` — `load_effective_config()` with precedence chain
- `app/config/validation.py` — Multi-layer validation (schema, security, filesystem, dependencies, compatibility)
- `app/config/provenance.py` — Source tracking for config values
- `app/config/secrets.py` — Secret field identification and redaction
- `app/config/profiles.py` — Deployment profiles (development, native-production, docker-production, minimal, full)
- `app/config/serialization.py` — TOML/JSON output with redaction
- `app/config/migration.py` — Config version migration support

CLI commands: `devlog config check`, `config show`, `config explain`, `config paths`, `config init`, `config migrate`

### Newsletter Retry Count
Default is 5 (not 3)

### APScheduler Schedules
- `cleanup_expired_subscribers`: `minute="*/5"` (NOT hourly)
- `run_daily_backup`: `hour=2, minute=0` (NOT midnight)

### Celery Queue Names
- `images` - Image processing
- `newsletter` - Newsletter delivery
- `webhooks` - Webhook delivery
- `email` - Transactional email
- `backup` - Backup tasks

### Comment Model Relationships
```python
parent = db.relationship("Comment", remote_side=[id], back_populates="replies")
replies = db.relationship("Comment", back_populates="parent", lazy="select")
```

### Health Check Critical Checks
```python
critical_checks = {
    k: v for k, v in checks.items()
    if k in ("database", "scheduler", "search", "disk_space", "db_integrity")
}
```

## Deployment

- Docker with Granian ASGI server
- Celery worker requires `PYTHONPATH=/home/blog`
- nginx runs as `nginx` user (not `blog`)
- Backup encryption uses AES-256-GCM (NOT GPG)

## Security Rules

1. **Log ID, not Username** - When logging user actions, always use `user.id`
2. **Credential Protection** - Never log `SECRET_KEY`, `ADMIN_PASSWORD`, or API keys
3. **SSRF Protection** - Webhook URLs validated via `app/utils.py:is_safe_webhook_url()`
4. **CSRF** - Sliding window of 5 valid tokens with `hmac.compare_digest`, API blueprint exempt via `should_skip_csrf()`

### 2FA Implementation
- TOTP secrets encrypted at rest using AES-256-GCM (`app/services/encryption.py`)
- `User.totp_secret` is a property that decrypts on access
- `User.set_totp_secret()` encrypts before storage
- Backup codes are SHA-256 hashed and single-use
- Routes:
  - `GET/POST /admin/2fa/setup` - Generate TOTP secret
  - `GET/POST /admin/2fa/verify` - Verify code and enable 2FA
  - `GET /admin/2fa/backup-codes` - Display one-time backup codes
  - `GET/POST /admin/2fa/disable` - Disable 2FA
  - `GET/POST /admin/login-2fa` - TOTP verification during login

### LOGIN_FAILURE_DELAY
Minimum enforced at 0.1s in `app/config.py` to prevent brute force.

### Thread-Safe Storage
`app/storage.py:get_storage()` uses double-checked locking with `threading.Lock()`.

### Security Headers
- Flask sets `X-Frame-Options: DENY` and `Cross-Origin-Opener-Policy: same-origin`
- nginx aligned to use `DENY` and `Cross-Origin-Opener-Policy: same-origin`

## Rate Limiting

- `ADMIN_RATE_LIMITS` in `app/config.py`:
  - `login`: 5 per 60 seconds
  - `api_write`: 100 per 60 seconds
  - `api_read`: 500 per 60 seconds
  - `settings`: 50 per 60 seconds
- `app/middleware/rate_limit.py` provides `AdminRateLimiter` class
- Flask-Limiter already integrated with `key_func=get_client_ip`

## Typed Config Package

The `app/config/` package provides structured configuration management:
- **Model**: 20 frozen dataclasses in `app/config/model.py` (`DevLogConfig` + 19 section classes)
- **Loader**: `load_effective_config()` in `app/config/loader.py` with precedence chain (env vars > config.toml > defaults)
- **Validation**: Multi-layer validation in `app/config/validation.py` (schema, security, filesystem, dependencies, compatibility)
- **Provenance**: Source tracking for config values in `app/config/provenance.py`
- **Secrets**: Secret field identification and redaction in `app/config/secrets.py`
- **Profiles**: Deployment profiles in `app/config/profiles.py` (development, native-production, docker-production, minimal, full)
- **Serialization**: TOML/JSON output with redaction in `app/config/serialization.py`
- **Migration**: Config version migration support in `app/config/migration.py`

CLI commands: `devlog config check`, `config show`, `config explain`, `config paths`, `config init`, `config migrate`

## Testing Fixtures

All test fixtures should disable page view buffer:
- `tests/conftest.py` - has `ensure_buffer_disabled` autouse fixture
- `tests/e2e/conftest.py` - has `ensure_buffer_disabled` autouse fixture
- `tests/benchmarks/conftest.py` - has `ensure_buffer_disabled` autouse fixture
- `tests/test_api.py` - has `ensure_buffer_disabled` autouse fixture

### Test Database Session
`db.session.refresh()` fails if object isn't in current session. Re-query from database instead.

## Template Filters

Actual filters in `app/filters.py`:
- `markdown_safe` - Render markdown to HTML with nh3 sanitization
- `reading_time` - Calculate reading time from text content
- `sanitize_css` - Sanitize custom CSS input
- `post_image_url` - Get post image URL with request-level caching
- `post_image_srcset` - Generate srcset for responsive images
- `post_image_avif_url_stub` - DEPRECATED: stub, always returns None

Note: `truncate` is Jinja2's built-in filter, not defined in app/filters.py
Note: `custom_css` is a context variable (from `inject_theme()`), not a filter

## Context Processors

From `app/context_processors.py`:
- `inject_config()` - site_title, site_description, author_name, etc.
- `inject_theme()` - theme settings including `custom_css`
- `inject_footer_data()` - recent_posts_footer, footer_tags, etc.
- `inject_csrf()` - csrf_token and csp_nonce
- `inject_show_footer_posts()` - show_footer_posts boolean

## Backup Implementations

Two separate backup implementations (both use `blog_*.db` naming):
- `app/services/backup.py:create_backup()` - Celery task, supports AES-256-GCM encryption/compression
- `app/scheduler.py:run_daily_backup()` - APScheduler, no encryption/compression

`cleanup_old_backups()` correctly handles both since May 2026 fix.

## Slug Generation

Slug collision limit hardcoded to 100 tries before UUID suffix fallback (`app/services/slug.py`).

## Search Abstraction

- `app/services/search/__init__.py` - `SearchProvider` abstract class
- `app/services/search/sqlite.py` - `SQLiteSearchProvider` (current FTS5)
- `app/services/search/postgresql.py` - `PostgreSQLSearchProvider` (stub for future)
- `get_search_provider()` factory selects by `SEARCH_PROVIDER` config
- `SEARCH_PROVIDER` defaults to 'sqlite', can be set to 'postgresql'

## Frontend

- Vite configured for code splitting in `vite.config.js`
- `manualChunks`: vendor, admin, public chunks
- `post_image_avif_url` filter in `app/filters.py` (stub - returns None until AVIF enabled)

## Brotli

- `nginx/nginx.conf` includes commented Brotli configuration
- Requires custom nginx image with `--with-http_brotli_module`
- To enable: uncomment Brotli module load and settings sections

## Maintenance

Project is in maintenance mode. No active implementation plans.
- See `docs/internals/agent-maintainer-notes.md` for detailed implementation history

## Halloy Theme Migration

All 15 phases of the Halloy theme migration are complete, plus a final verification pass. Phases: 01 (catalog inventory + token contract), 02 (parser + color primitives), 03 (blog translation layer), 04 (safe registry and external overrides), 05 (packaging), 06 (runtime integration), 07 (Flask and Jinja runtime integration), 08 (visitor color-scheme behavior), 09 (CSS and generated-markup audit), 10 (admin selection and preview), 11 (operator CLI), 12 (accessibility validation), 13 (performance and reliability), 14 (documentation and legacy removal), and 15 (legacy removal and release closure — THEME_PRESETS removed, theme_preset column dropped, emergency fallback uses EMERGENCY_DEFAULT).

**Small closure pass contracts:**
- Cache freshness: external theme changes require explicit `invalidate()` or `invalidate(name)`; no automatic mtime-based refresh
- Fingerprint: `_compute_fingerprint()` uses `hashlib.sha256()` (64-char hex) for bundled resources
- CI: 9 jobs including `theme-policy` (accessibility strict check) and `migration-chain` (real Alembic Operations context tests)

**Accessibility policy:** Three-tier classification system — `recommended` (zero failures), `compatible-with-exceptions` (failures covered by manifest), `experimental` (uncovered failures). Exception manifest at `app/themes/ACCESSIBILITY_EXCEPTIONS.json` with `schema_version: 2`. CI enforces via `theme-policy` job and `flask themes accessibility --strict`.

### Theme Source Locations

| Component | Location | Notes |
|-----------|----------|-------|
| Source catalog | `themes/*.toml` | 50 files; ignore macOS `._*.toml` metadata files |
| Bundled themes | `app/themes/bundled/*.toml` | Packaged copy of source catalog; accessible via `importlib.resources` |
| Runtime authority | `app/models.py` | Theme configuration via `theme_dark_name`, `theme_light_name`, `theme_default_scheme` columns |
| Context injection | `app/context_processors.py:67-76` | `inject_theme()` builds `theme_vars` dict via `ThemeService` |
| Template consumption | `app/templates/base.html:42-48`, `app/templates/admin/base.html:17-23` | CSS variable injection into `<style>` blocks |
| Color scheme | `app/static/js/shared/color-scheme.js` | 3-state scheme manager, localStorage key `blog-color-scheme` |
| CSS selectors | `base.css`, `public.css`, `prism-okaidia.css` | Use `[data-color-scheme="light"]` (not `[data-theme]`) |

### Planned Module Layout

Phases 05+ will create these modules:

| Module | Purpose | Phase | Status |
|--------|---------|-------|--------|
| `app/themes/halloy.py` | Typed parser models for Halloy TOML schema | 02 | Done |
| `app/themes/colors.py` | Color primitives (hex parsing, luminance, contrast) | 02 | Done |
| `app/themes/model.py` | `BlogTheme` frozen dataclass (50 fields, CSS_VARS, ALIASES, EMERGENCY_DEFAULT) | 03 | Done |
| `app/themes/translate.py` | `translate_halloy_theme()`, `to_css_variables()`, `to_theme_vars()`, `to_legacy_vars()` | 03 | Done |
| `app/themes/diagnostics.py` | `check_blog_theme_contrast()`, `ContrastWarning`, `TranslationDiagnostics` | 03 | Done |
| `app/themes/resources.py` | `ThemeResource` protocol, `_PathResource`/`_TraversableResource`, `normalize_theme_name()`, `ThemeFileInfo.read_bytes()` | 04 | Done |
| `app/themes/cache.py` | `ThemeCache` in-process cache, `ThemeCacheEntry` with `source_fingerprint`, `invalidate_prefix()`, `validate_entry()` | 04 | Done |
| `app/themes/registry.py` | `ThemeRegistry`, `ThemeDescriptor`, `LoadedTheme`, `_CatalogEntry`, structured exceptions, `_THEME_ALIASES`, `_compute_fingerprint()`, default `Catppuccin Mocha` | 04 | Done |
| `app/themes/bundled/*.toml` | Packaged theme files shipped with the app | 05 | Done |
| `app/services/theme_settings.py` | Theme validation, effective name resolution | 06 | Done |
| `app/themes/service.py` | `ThemeService` class, app-scoped via `app.extensions["theme_service"]`, context builder (Phase 07) | 07 | Done |
| `app/static/js/shared/color-scheme.js` | 3-state color scheme manager (system/dark/light), bootstrap, toggle | 08 | Done |
| `app/static/js/shared/dark-mode.js` | Backward-compatible re-export from color-scheme.js | 08 | Done |

### Phase 02 API

#### Entry Points

- `parse_halloy_theme_bytes(data: bytes, *, source_name: str) -> HalloyTheme`
- `parse_halloy_theme(source: str | Path | IO[bytes] | bytes) -> HalloyTheme`

#### Dataclass Models

- `HalloyTheme` — top-level container
- `HalloyGeneral` — general theme settings
- `HalloyText` — text color settings
- `HalloyBuffer` — buffer color settings
- `HalloyBufferServerMessages` — server message colors
- `HalloyButtons` — button color settings

#### Exception Classes

- `ThemeParseError` — TOML parse failure (has `.source` attribute)
- `ThemeSchemaError` — structural/schema violation (has `.source` and `.field_path` attributes)
- `ThemeColorError` — invalid color value (has `.source` and `.field_path` attributes)

#### Color Primitives (`app/themes/colors.py`)

- `RGB`, `RGBA` — immutable color containers
- `from_hex`, `to_hex`, `to_css` — conversion utilities
- `alpha_composite` — alpha blending
- `relative_luminance`, `contrast_ratio`, `wcag_level` — WCAG contrast helpers
- `is_dark_background`, `is_light_background` — classification
- `mix`, `adjust_lightness`, `shift_lightness` — color manipulation

**Note:** The parser has zero Flask/SQLAlchemy/templates/registry coupling. It depends only on Python stdlib `tomllib`.

### Phase 04 API

#### ThemeRegistry (`app/themes/registry.py`)

- `ThemeRegistry(bundled_root=None, external_root=None, default_theme="Catppuccin Mocha")`
- `list_themes()` -> sorted list of `ThemeDescriptor`
- `resolve(name)` -> `ThemeDescriptor | None`
- `load(name)` -> `LoadedTheme` (with caching)
- `invalidate(name=None)` -> clear cache/catalog
- `get_fallback(configured=None)` -> `LoadedTheme` (emergency fallback chain)

Structured exceptions: `ThemeNotFoundError`, `ThemeParseFailure`, `ThemeLoadError`, `ThemeValidationError`.

`_CatalogEntry` pairs descriptor + file_info internally. `_THEME_ALIASES` maps legacy names to Halloy equivalents. `_compute_fingerprint()` validates cache entries against current source state.

#### ThemeDescriptor (frozen dataclass)

Safe public metadata: `canonical_name`, `display_name`, `source`, `overrides_bundled`, `is_dark`, `status`, `warnings`. No absolute paths exposed.

#### LoadedTheme (frozen dataclass)

Complete loaded result: `descriptor`, `blog_theme`, `halloy_theme`, `css`, `is_dark`, `diagnostics`, `css_vars`, `legacy_vars`.

#### Resources (`app/themes/resources.py`)

- `ThemeResource` protocol with `_PathResource` and `_TraversableResource` implementations
- `normalize_theme_name(name)` -> canonical stem or raises ValueError
- `discover_bundled_package(root)` -> `_TraversableResource` via `importlib.resources`
- `ThemeFileInfo.read_bytes()` method for safe content access

#### Cache (`app/themes/cache.py`)

- `ThemeCache` in-process cache with `source_fingerprint` validation
- `ThemeCacheEntry` stores halloy_theme, blog_theme, css, diagnostics, css_vars, legacy_vars, `source_fingerprint`
- `invalidate_prefix()` for bulk invalidation
- `validate_entry()` accepts current metadata from caller to check freshness

### Hard Rules for Agents

1. All 15 phases of the Halloy theme migration are complete, plus final verification pass.
2. `THEME_PRESETS` has been removed from `app/models.py`; `theme_preset` column dropped from `SiteSettings`.
3. Bundled resources must use `importlib.resources`, not cwd-relative paths.
4. CSS variables emitted via `theme_vars` are the current API.
5. Accessibility policy uses three-tier classification: `recommended`, `compatible-with-exceptions`, `experimental`.

### Token Contract Summary

44 semantic BlogTheme tokens organized into Backgrounds, Borders, Text, Accent, States, Inputs/Code, Navbar/Chrome, and Overlays categories. 26 aliases preserve existing CSS variable names (`--bg`, `--accent`, etc.) for backward compatibility. See `docs/themes/blog-theme-contract.md` for the full matrix.

### Audit Summary

128 frontend color literals audited: 0 REPLACE (all 34 converted in Phase 09), 71 RETAIN (structural defaults, print stylesheet, brand colors, neutral shadows, intentionally-dark overlays), 9 FALSE_POS (font-face URLs, `currentColor` SVGs). Phase 08 removed 23 static light-palette literals; palette is now provided by inline theme injection. Phase 09 replaced all hardcoded CSS literals with semantic CSS custom properties. See `docs/themes/frontend-literal-audit.md` for the line-by-line audit.

### Phase 02+ Reference

All 15 phases are complete plus final verification pass. The phased plan is at `plans/halloy_theme_system_roadmap.md`.
