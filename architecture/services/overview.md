# Services Layer

Business logic layer for the blog application.

## Overview

| Service | File | Purpose |
|---------|------|---------|
| Backup | `app/services/backup.py` | Database backup with compression/encryption |
| Encryption | `app/services/encryption.py` | AES-256-GCM for TOTP secrets |
| Backup Encryption | `app/backup_encryption.py` | AES-256-GCM backup file encryption with PBKDF2 key derivation |
| Webhook Encryption | `app/webhook_encryption.py` | AES-256-GCM encryption for webhook secrets at rest |
| Serialization | `app/services/serialization.py` | JSON export/import |
| Slug | `app/services/slug.py` | Unique slug generation |
| Tag | `app/services/tag.py` | Tag CRUD and count management |
| Tag Cache | `app/tag_cache.py` | Tag count caching with TTL |
| AI Authoring | `app/services/ai_assist.py` | Optional, bounded provider suggestions for the post editor; no persistence |
| Search | `app/services/search/` | Search provider abstraction (SQLite FTS5, PostgreSQL stub) |
| Search (FTS5) | `app/search.py` | Standalone FTS5 functions (search, sync, snippets, did-you-mean) |
| Theme Registry | `app/themes/registry.py` | Authoritative theme registry: listing, resolution, loading, fallback, `_CatalogEntry` |
| Theme Resources | `app/themes/resources.py` | `ThemeResource` protocol, `importlib.resources` bundled discovery, external override |
| Theme Cache | `app/themes/cache.py` | In-process theme caching with current-source-state freshness validation |
| Theme Service | `app/themes/service.py` | App-scoped `ThemeService`: owns the registry, resolves effective theme names from `SiteSettings`, builds Jinja context dict, stored on `app.extensions["theme_service"]`. Provides preview (load + CSS without persist) and refresh (rebuild registry from disk) operations |
| Theme Settings | `app/services/theme_settings.py` | Theme configuration validation, legacy preset migration, effective theme name resolution |
| Projects | `app/services/projects.py` | Project validation, publication queries, repository identity, and project-scoped theme resolution |
| Navigation | `app/services/navigation.py` | Published page/project navigation projection from `SiteSettings` |
| Site Settings | `app/services/site_settings.py` | Homepage target validation and navigation/settings persistence |
| Cache Contract | `docs/themes/cache-contract.md` | Cache freshness model, invalidation API, multi-worker deployment notes |

## Optional AI Authoring

`app/services/ai_assist.py` is the only provider HTTP client. It supports a configurable OpenAI-compatible Chat Completions endpoint and OpenCode Go. AI is opt-in: `AiConfig.model` defaults to empty, so controls are hidden and no provider is contacted until an operator selects a model. The compatible endpoint defaults to loopback (`http://127.0.0.1:1234/v1`) but is not active by default; configuring a local model does not require an API key. OpenCode Go uses its documented fixed endpoint, model-family routing (including Responses for Muse Spark Contributor), and `OPENCODE_GO_API_KEY`. Generic compatible endpoints use `AI_API_KEY` only when required. Credentials are environment-only; `ai.api_key` in TOML is rejected and ignored.

Only an explicit action from an authenticated post editor sends the current unsaved title/body. The request is bounded to 64 KiB, uses a 3-second connect timeout and configurable read timeout (180 seconds by default for local inference), caps provider output at 64 KiB, and does not stream model output. One retry is made for connection errors, empty/malformed responses, incomplete completions, invalid JSON shape, and transient HTTP statuses; the retry increases the output-token budget. Permanent 4xx responses are not retried. Safe diagnostics record provider status and failure category, never prompts or model output. OpenCode Go requests include a stable random session header with no author identifier or draft content.

**Rate-limiting decision:** Application-side AI throttling is unlimited by default; the optional per-user `ai.rate_limit_per_user` / `AI_RATE_LIMIT_PER_USER` setting remains for operators with a concrete deployment need. Hosted providers own their quotas and abuse controls, while local model operators own local capacity controls. Short, bounded, user-triggered authoring requests are not a meaningful source of provider abuse; a low limit such as 12/hour makes the editor impractical without materially protecting a provider. The service already caps input/output bytes, timeout, model output, and tag-action calls. Do not add a low built-in ceiling. If a future preset needs one, set at least 1,000 requests per user per hour: beyond realistic human interaction and negligible for these bounded requests.

Summary output is plain text, validated to at most 500 characters, and applied only after an explicit user action. Title output shares that contract and is validated to at most 120 characters, so it stays inside the post title column. Tag proposals use `Tag.generate_slug()` and `validate_tag_name()`, are exact-matched against a compact catalog before a conditional semantic pass, and fall back to first-pass proposals if mapping fails. Non-admin catalog data is limited to tags used by published posts; admin-only private taxonomy metadata has no unpublished post titles or bodies. The service never writes posts/tags, creates tags, updates indexes or caches, or logs prompt content. Normal post Save is the only persistence path.

Both actions request a single JSON object, and the parser tolerates the wrappers local models commonly add — a Markdown code fence, a short preamble, or trailing prose — while the object's own shape stays strict (exactly one expected key). A response that carries no parseable JSON object is still rejected as an invalid suggestion.

## Operations Service Layer

Extracted from CLI handlers into reusable, testable services at `app/services/operations/`.

| Module | Purpose |
|--------|---------|
| `results.py` | Typed `OperationResult` dataclasses with stable operation codes |
| `admin.py` | Admin user create/promote/reset-password/list |
| `database.py` | SQLite integrity check, FTS rebuild, migration status |
| `media.py` | Orphaned media scan and cleanup |
| `transfer.py` | Site data export/import with atomic writes |
| `themes.py` | Theme list/validate/inspect/refresh/paths/accessibility facade |
| `backup.py` | Backup creation and verification with structured results |

Service functions never depend on Click, terminal output, or process exit. They require Flask application context, return typed `OperationResult` subclasses, and use `commit_with_rollback()` for transaction boundaries.

The standalone `devlog` CLI commands (`devlog_cli/commands/`) call these services. Flask commands (`app/cli.py`) remain as compatibility wrappers calling the same services.

## See Also
- [Operations Services](operations.md) - The terminal-free operational service layer
- [Doctor](doctor.md) - The diagnostic check framework
- [Backup Service](backup.md) - Detailed backup documentation
- [Serialization](serialization.md) - Data export/import
- [Slug Service](slug.md) - Slug generation
- [Tag Service](tag.md) - Tag management
- [Tag Cache](tag_cache.md) - Tag count caching
- [Search Provider](search.md) - Full-text search abstraction
- [Theme System](../core/themes.md) - The Halloy theme subsystem
- [Theme Supported Schema](../../docs/themes/supported-schema.md) - Halloy TOML input schema
- [Theme Service](../../docs/themes/operator-guide.md) - ThemeService singleton, CLI commands, preview, and refresh
