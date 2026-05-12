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

### Status Logic

- `ok`: All critical checks pass (status in "ok", "running", "disabled")
- `degraded`: Any critical check fails

## See Also
- [Search](infrastructure/search.md) - Full-text search
- [Email](infrastructure/email.md) - Email system
- [Storage](infrastructure/storage.md) - File storage
- [Webhooks](infrastructure/webhooks.md) - Webhook delivery
