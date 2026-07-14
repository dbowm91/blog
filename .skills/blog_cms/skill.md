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

Phase 01 (catalog inventory + token contract), Phase 02 (parser + color primitives), Phase 03 (blog translation layer), Phase 04 (safe registry and external overrides), Phase 05 (packaging), Phase 06 (runtime integration), Phase 07 (Flask and Jinja runtime integration), Phase 08 (visitor color-scheme behavior), Phase 09 (CSS and generated-markup audit), Phase 10 (admin selection and preview), Phase 11 (operator CLI), Phase 12 (accessibility validation), and Phase 13 (performance and reliability — benchmarks, cache validation, malformed file isolation) are complete. Phase 14 (documentation and legacy removal) is in progress. Phase 06 adds `theme_dark_name`, `theme_light_name`, `theme_default_scheme` columns to SiteSettings, Alembic migration, theme settings validation service (`app/services/theme_settings.py`), and config.toml theme section. Phase 07 adds the centralized `ThemeService` class, dual-scheme CSS emission, and context processor overhaul. Phase 08 introduces 3-state color scheme (system/dark/light), `blog-color-scheme` localStorage key, bootstrap script for first-paint scheme application, CSS selector migration from `[data-theme]` to `[data-color-scheme]`, and removal of the static `[data-color-scheme="light"]` palette block (palette now provided by inline theme injection). Phase 09 replaces hardcoded CSS literals with CSS custom properties, adds 7 new ALIASES entries, and emits 35 legacy vars. Phase 10 provides registry-based theme selector with dark/light/scheme selection. Phase 11 adds Flask CLI commands for theme management. Phase 12 adds WCAG contrast validation with severity classification, catalog-wide validation, and classification audit. Phase 13 adds theme performance benchmarks and malformed file isolation tests.

**Small closure pass contracts:**
- Cache freshness: external theme changes require explicit `invalidate()` or `invalidate(name)`; no automatic mtime-based refresh
- Fingerprint: `_compute_fingerprint()` uses `hashlib.sha256()` (64-char hex) for bundled resources
- CI: `theme-package-verification` job builds wheel/sdist and runs `scripts/verify_theme_package.py` as a gate

### Theme Source Locations

| Component | Location | Notes |
|-----------|----------|-------|
| Source catalog | `themes/*.toml` | 50 files; ignore macOS `._*.toml` metadata files |
| Bundled themes | `app/themes/bundled/*.toml` | Packaged copy of source catalog; accessible via `importlib.resources` |
| Runtime authority | `app/models.py:366-457` | `THEME_PRESETS` dict; remains runtime authority until Phase 14 |
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
| `app/services/theme_settings.py` | Theme validation, legacy migration, effective name resolution | 06 | Done |
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

1. Corrective closure and small closure pass for Phases 01–05 are complete; subsequent phases build on the corrected foundation.
2. Do NOT delete or modify `THEME_PRESETS` until Phase 14.
3. Do NOT change `theme_vars` Jinja context shape until Phase 07.
4. Do NOT move/rename `themes/*.toml` files until Phase 05.
5. Bundled resources must use `importlib.resources`, not cwd-relative paths.
6. The 4 legacy preset names (`github-dark`, `github-light`, `solarized-dark`, `monokai`) remain valid selections throughout migration; see `docs/themes/legacy-compatibility.md` for transition rules.
7. CSS variables emitted via `theme_vars` are the current API; do not refactor templates to call theme functions directly until Phase 07.

### Token Contract Summary

44 semantic BlogTheme tokens organized into Backgrounds, Borders, Text, Accent, States, Inputs/Code, Navbar/Chrome, and Overlays categories. 26 aliases preserve existing CSS variable names (`--bg`, `--accent`, etc.) for backward compatibility. See `docs/themes/blog-theme-contract.md` for the full matrix.

### Audit Summary

128 frontend color literals audited: 0 REPLACE (all 34 converted in Phase 09), 71 RETAIN (structural defaults, print stylesheet, brand colors, neutral shadows, intentionally-dark overlays), 9 FALSE_POS (font-face URLs, `currentColor` SVGs). Phase 08 removed 23 static light-palette literals; palette is now provided by inline theme injection. Phase 09 replaced all hardcoded CSS literals with semantic CSS custom properties. See `docs/themes/frontend-literal-audit.md` for the line-by-line audit.

### Phase 02+ Reference

For ongoing work, read `plans/halloy_theme_system_roadmap.md` for the full phased plan. The 14 phases cover parser, translator, registry, packaging, runtime integration, visitor scheme behavior, frontend token completion, admin UX, CLI, accessibility, performance, and cleanup.
