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

## See Also
- [Backup Service](services/backup.md) - Detailed backup documentation
- [Serialization](services/serialization.md) - Data export/import
- [Slug Service](services/slug.md) - Slug generation
- [Tag Service](services/tag.md) - Tag management
- [Tag Cache](services/tag_cache.md) - Tag count caching
- [Search Provider](services/search.md) - Full-text search abstraction
