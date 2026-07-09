# Services Overview

## Backup Service

The blog has two separate backup implementations:

### 1. Celery Task Backup (`app/services/backup.py:create_backup()`)

- Used by Celery workers for on-demand backups
- Supports **AES-256-GCM encryption** with PBKDF2-HMAC-SHA256 key derivation (600,000 iterations)
- Supports **gzip compression**
- Naming pattern: `blog_*.db`, `blog_*.db.gz`, `blog_*.db.gpg`
- Called via `run_backup_task` Celery task

### 2. APScheduler Backup (`app/services/backup.py:run_daily_backup()`)

- Used by APScheduler for daily scheduled backups
- **No encryption or compression**
- Naming pattern: `blog_*.db`
- Called by `run_daily_backup` job in `app/scheduler.py`

### Shared Retention Policy

Both use `cleanup_old_backups()` which keeps the last 7 backups and recognizes `blog_*.db` pattern.

## Search Service

See [search.md](search.md) for SearchProvider abstraction.

## Encryption Service

Location: `app/services/encryption.py`

AES-256-GCM encryption for TOTP secrets (2FA). Used by `User.totp_secret` property.

## Slug Service

Location: `app/services/slug.py`

Handles URL-safe slug generation with collision detection (up to 100 tries before UUID fallback).

## Tag Service

Location: `app/services/tag.py`

Provides tag validation, normalization, and related post queries.