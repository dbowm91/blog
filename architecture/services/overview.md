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
