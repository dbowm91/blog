# Changelog

All notable changes to DevLog will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release status

**DevLog has no tagged releases yet.** The package version in `pyproject.toml`
is `1.0.0`, but no `vX.Y.Z` tag has been pushed, so there is no published
release history to record.

Everything below therefore sits under **[Unreleased]** and describes the work
accumulated for the current version. When the first release is tagged, move the
`[Unreleased]` section under a `[X.Y.Z]` heading with its date, as described in
[RELEASE.md](RELEASE.md).

## [Unreleased]

### Added

**Blog and content**
- Posts, pages, tags, post series, comments, media library and short URLs
  (`/s/<base62>`) with permanent per-post codes
- SQLite with WAL journalling and FTS5 full-text search — prefix matching
  (2–4 characters), did-you-mean suggestions and highlighted snippets
- Feeds: RSS 2.0 (`/rss`), Atom 1.0 (`/atom`), JSON Feed 1.1 (`/json`), plus
  per-tag and per-series variants, all with ETag conditional GET
- Newsletter with double opt-in confirmation, scheduled daily digest, retry
  handling and one-click unsubscribe
- Analytics: page views, share events, traffic-source categorisation
  (Direct / Search / Social / Other), a dashboard and `/admin/analytics`
- Multi-admin support with admin session tracking, IP binding, per-role
  access (admin and author) and a full audit log
- TOTP two-factor authentication with single-use backup codes
- Public site identity: visitor login and account pages, author pages, a
  pages index, per-page navigation entries, footer column toggles, a profile
  editor and a post author selector
- Syntax highlighting for fenced code blocks, with a copy button and token
  colours taken from the active theme
- A capped reading measure: the prose column is 34 em wide and centred, so a
  line of text is 65–75 characters long instead of 85–94, at every viewport
- A themed placeholder for posts with no cover image — a line-art mark that
  takes its colour from the active theme instead of hard-coding one
- A two-column post list: the index shows two cards per row from 1024px, with
  a tighter card and a summary clamped to two lines
- A capped tag row on post cards: a card shows at most four tags and names the
  number it hides, and the post page lists the whole set
- One shared voice for the structural elements — the table-of-contents title,
  the share label and the sidebar headings

**Halloy theme system**
- 50 bundled Halloy `.toml` themes, with the root `themes/` directory acting
  as the authoring catalogue
- Typed theme model (`BlogTheme`) of 52 colour tokens — 43 `RGB` and 9
  `RGBA` — emitting 52 CSS custom properties and 40 backwards-compatible
  aliases
- Theme registry with caching, external override directory, accessibility
  diagnostics with severity classification, and a visitor colour-scheme
  switcher (system / dark / light)
- Appearance layer for font families and page backdrops
- Two derived text roles — `--text-caption` for small-but-readable text and
  `--accent-text` for accent-coloured text — each guaranteed to clear the
  WCAG AA 4.5:1 floor on every surface it can land on

**Operations**
- Typed configuration package (`app/config/`) with 22 section dataclasses plus
  the top-level `DevLogConfig`, resolved as environment variables >
  `config.toml` > built-in defaults
- Standalone `devlog` operator CLI: `config`, `admin`, `db`, `themes`,
  `backup`, `data`, `media`, `onboard`, `paths`, `deploy`, `doctor`, and the
  `start` / `stop` / `restart` / `status` / `logs` lifecycle commands
- `devlog doctor` diagnostics: 76 checks across 20 categories, with parallel
  execution, category filtering and safe fixes
- Filesystem layout system with install modes, legacy discovery and a
  migration planner/executor
- First-run and reconfiguration onboarding (`devlog onboard detect|plan|run|resume`)
- Deployment rendering for systemd, Compose, reverse proxy and logrotate, with
  drift detection (`devlog deploy render|install|check`)
- One-shot installer with versioned layout, atomic symlink, SHA-256 checksum
  verification and release artifacts
- Docker Compose deployment with explicit `production`, `reverse-proxy` and
  `backup` profiles, a multi-stage image and a non-root user
- Celery and Redis for newsletter delivery, webhook delivery, image variants
  and backups
- Webhooks with per-target SSRF protection, HMAC signing, retries and
  encrypted secrets at rest
- Backups with optional gzip compression, AES-256-GCM encryption, PBKDF2 key
  derivation and integrity verification
- Pluggable media storage: local filesystem by default, or S3-compatible
  object storage with `STORAGE_BACKEND=s3`
- Health endpoints: unauthenticated basic `/health` and secret-gated
  detailed mode, plus an opt-in Prometheus `/metrics` endpoint

### Changed

- Login rate limiting moved from the application to the reverse proxy; the
  per-account lockout remains in the application
- `app/config.py` was replaced by `app/config_legacy.py` plus the typed
  `app/config/` package; the legacy flat names are still re-exported
- The legacy `THEME_PRESETS` list and the `theme_preset` column were removed
  in favour of the Halloy registry
- The default theme is `Catppuccin Mocha`
- Operational logic was extracted from the Flask CLI into
  `app/services/operations/`; the Flask commands remain as compatibility
  wrappers over the same services
- The SQLite database resolves to `data/devlog.sqlite3` by default
  (override with `DEVLOG_DATABASE_PATH`, `SQLALCHEMY_DATABASE_URI` or
  `DATABASE_URL`)
- Editorial tooling expanded: undo/redo in the editor, a markdown toolbar, a
  stacked live preview pane, and numbered code blocks
- The `syntax_theme` setting and the six vendored Prism palettes were removed.
  Prism's token classes are remapped onto the active theme's own colours, and
  Prism itself is now a built npm dependency rather than a hand-assembled
  grammar bundle
- Markdown renderer supports strikethrough
- The share panel moved below the article body, so the article's first
  paragraph starts higher on the page
- Documentation reorganised: `DEPLOY.md` is the operator reference,
  `USAGE.md` the administration guide

### Removed

- The sidebar's duplicate "Recent posts" list, and the query behind it

### Fixed

- A fresh install now runs migrations successfully end to end
- The test suite no longer overwrites the developer's local configuration
- Corrected backdrop shape, font selection, profile picture rendering, editor
  preview layout and heading anchor navigation
- Heading anchors are applied consistently across rendered posts
- Small text — the table of contents, the share label, the post metadata, the
  footer links and the navigation links — now clears the WCAG AA 4.5:1 floor
  in every bundled theme, and the eight themes whose code surface was
  indistinguishable from their own card surface were repaired
- The post placeholder no longer renders as an opaque black band in the light
  scheme, and the card image band no longer crops a quarter off the height of
  a 16:9 screenshot

### Security

- CSRF validation on every browser POST request, with API-key requests exempt
  and protected by token secrecy, scopes, rate limits and audit logging
- Security headers on every response: CSP with nonces, HSTS,
  X-Frame-Options, X-Content-Type-Options, Referrer-Policy and
  Permissions-Policy
- Password hashing via `werkzeug.security` (pbkdf2:sha256), with complexity
  rules enforced on the user creation, password change and password reset
  routes
- Login failure delay and per-account lockout on both the admin and public
  login routes
- Constant-time comparison for API keys, CSRF tokens and health-check secrets
- HTML sanitisation via `nh3` and CSS sanitisation via `tinycss2`
- Webhook and backup secrets encrypted at rest with AES-256-GCM
