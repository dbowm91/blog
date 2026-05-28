# Infrastructure Components

Supporting systems for the blog application.

## Overview

| Component | File | Purpose |
|-----------|------|---------|
| Search | `app/search.py` | FTS5 full-text search |
| Email | `app/email.py` | SMTP email delivery |
| Storage | `app/storage.py` | Local/S3 storage abstraction |
| Webhooks | `app/webhooks.py` | Webhook delivery |
| Health Check | `app/routes/public/meta.py` | Health monitoring |

## Health Check (`GET /health`)

Health endpoint with optional `?detailed=1` parameter.

### Critical Checks (determine overall status)

| Check | What it validates |
|-------|-------------------|
| `database` | SQLite connectivity |
| `scheduler` | APScheduler running |
| `search` | FTS5 availability |
| `disk_space` | Available space > 100MB |
| `db_integrity` | Database passes integrity check |

### Optional Checks (do not affect overall status)

| Check | What it validates |
|-------|-------------------|
| `backup_freshness` | Most recent backup < 24 hours old |
| `email` | SMTP connectivity (if configured) |
| `redis` | Redis connectivity |
| `celery` | Celery worker availability |

### Status Logic

- `ok`: All critical checks pass (status in "ok", "running", "disabled")
- `degraded`: Any critical check fails

## Storage (`app/storage.py`)

Storage abstraction layer for media files with local and S3 backends.

### Architecture

| Class | File | Purpose |
|-------|------|---------|
| `StorageBackend` | `app/storage.py` | Abstract base class defining the interface |
| `LocalStorageBackend` | `app/storage.py` | Local filesystem storage |
| `S3StorageBackend` | `app/storage.py` | S3-compatible storage via boto3 |

### Configuration

Configured via `STORAGE_BACKEND` env var: `"local"` (default) or `"s3"`.

S3 environment variables:
- `S3_BUCKET` (required)
- `S3_REGION` (default: `us-east-1`)
- `S3_ENDPOINT` (optional, for S3-compatible services)
- `S3_ACCESS_KEY` (required)
- `S3_SECRET_KEY` (required)
- `S3_PUBLIC_URL` (optional, for custom CDN URLs)

### Singleton Pattern

`get_storage()` returns a module-level singleton. Lazy client initialization for S3 uses `threading.Lock`.

### Error Handling

S3 methods return `False` or empty lists on failure. `LocalStorageBackend` methods raise on filesystem errors.

## See Also
- [Search](infrastructure/search.md) - Full-text search
- [Email](infrastructure/email.md) - Email system
- [Webhooks](infrastructure/webhooks.md) - Webhook delivery
