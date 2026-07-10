# Infrastructure Overview

Cross-cutting view of how the infrastructure subsystems — search, email, storage, webhooks, and health checks — interact. Each subsystem has a dedicated doc; this document explains the seams between them.

## System Topology

```
┌─────────────────────────────────────────────────────────┐
│                     Flask App                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │  Search   │  │  Email   │  │ Storage  │  │Webhooks │ │
│  │ (FTS5)    │  │  (SMTP)  │  │(Local/S3)│  │(HTTP)   │ │
│  └─────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
│        │             │             │              │      │
│        └─────────────┴──────┬──────┴──────────────┘      │
│                             │                            │
│                    ┌────────▼────────┐                   │
│                    │  Celery (Redis) │                   │
│                    └────────┬────────┘                   │
│                             │                            │
│                    ┌────────▼────────┐                   │
│                    │  Health Check   │                   │
│                    │  (GET /health)  │                   │
│                    └─────────────────┘                   │
└─────────────────────────────────────────────────────────┘
```

## Celery as the Integration Layer

All five subsystems connect through Celery queues. Each queue isolates workload so a slow webhook doesn't delay newsletter delivery.

| Queue | Consumers | Producers |
|-------|-----------|-----------|
| `images` | `generate_image_variants` | Storage upload |
| `newsletter` | `send_newsletter_task` | APScheduler, admin actions |
| `email` | `send_confirmation_task`, `send_password_reset_task` | Subscriber/user actions |
| `webhooks` | `deliver_webhook_task` → `deliver_single_webhook_task` | Post publish/unpublish, subscriber confirm |
| `backup` | `run_backup_task` | APScheduler, admin actions |

**Key design decision:** Webhook delivery uses two-level dispatch. `deliver_webhook_task` fans out to N `deliver_single_webhook_task` invocations (one per webhook), so one failing endpoint doesn't block others.

## Subsystem Interactions

### Search ↔ App

- **Initialization:** `init_fts()` runs during `create_app()` (`app/__init__.py:430-433`). Failures are caught silently — the app runs without FTS.
- **Sync:** `sync_fts()` / `sync_fts_batch()` called *before* `db.session.commit()` in admin routes. FTS is kept in sync with the `posts` table.
- **Health:** The `/health` endpoint checks `posts_fts` table existence and reports `"ok"` or `"unavailable"`. This is a *critical* check — if FTS is down, overall status is `"degraded"`.
- **Fallback:** Search functions return empty lists when FTS is unavailable. No errors propagate to the user.

### Email ↔ Celery

- **Transactional emails** (confirmation, password reset) are sent synchronously by wrapper functions, but the *calling* Celery tasks handle retries and queue management.
- **Newsletter delivery** is a bulk operation: `send_newsletter_task` calls `send_newsletter()` which opens one SMTP connection, pre-renders templates, and iterates subscribers.
- **Retry counts differ:** 3 for transactional, 5 for newsletters (via `NEWSLETTER_MAX_RETRY_ATTEMPTS`).
- **SMTP failure disables the scheduler:** When `SMTP_HOST` is not configured, only the daily newsletter APScheduler job is disabled. Other jobs (backup, cleanup, scheduled posts) continue.

### Storage ↔ Celery

- `upload_with_processing()` saves the file, then queues `generate_image_variants` on the `images` queue.
- **S3 flow:** Original → S3 → Celery task retrieves from S3 → generates variants locally → uploads variants back to S3 → cleans up temp files.
- **Local flow:** Files stay on disk. Variants written as `400_`, `800_`, `1200_` prefixed copies.
- **Variant cleanup:** When uploading a new file with the same name, old variants are deleted first via prefix matching.

### Webhooks ↔ Celery ↔ Events

- `create_webhook_event()` writes a `WebhookEvent` record, then queues `deliver_webhook_task` on the `webhooks` queue.
- **Silent failure:** If Celery can't queue the task, the event record stays `delivered=False` forever. No retry, no notification.
- **SSRF protection** runs at delivery time (`deliver_single_webhook_task`), not at registration time. URLs are validated against private IPs, cloud metadata endpoints, and link-local addresses.
- **Event types:** `post.published`, `post.unpublished`, `subscriber.confirmed`.
- **Secret encryption:** Webhook secrets are AES-256-GCM encrypted at rest (`app/webhook_encryption.py`). Decrypted on demand via the `Webhook.secret` property.

### Health Check ↔ All Subsystems

The `/health` endpoint (`app/routes/public/meta.py:188`) is the single integration point that observes all subsystems:

| Check | Source | Critical? |
|-------|--------|-----------|
| `database` | `SELECT 1` | Yes |
| `search` | SQLite: `sqlite_master` FTS5 table check; non-SQLite: `unsupported` | Yes |
| `disk_space` | `shutil.disk_usage()` — 10% threshold | Yes |
| `db_integrity` | SQLite: `PRAGMA integrity_check`; non-SQLite: `unsupported` | Yes |
| `scheduler` | `get_scheduler_health()` — always checked; newsletter job skipped if SMTP absent | Yes |
| `redis` | `redis.ping()` | No |
| `celery` | `celery_app.control.inspect().ping()` | No |
| `backup_freshness` | File age of latest backup — 24h threshold | No |

**Overall status** is `"degraded"` if any *critical* check fails. Non-critical checks are informational only.

**Detailed mode:** `GET /health?detailed=true&secret=<HEALTH_CHECK_SECRET>` returns latency metrics and scheduler details. Requires `HEALTH_CHECK_SECRET` env var.

## Failure Modes

| Scenario | Impact | Recovery |
|----------|--------|----------|
| FTS init fails | Search returns empty lists | `rebuild_fts()` or app restart |
| SMTP down | Newsletter job disabled; transactional emails queue retries | SMTP server recovery |
| S3 unreachable | `upload_with_processing()` fails; variants not generated | Celery retries (max 3) |
| Redis down | All Celery queues blocked; webhooks/emails/images stall | Redis restart |
| Celery workers down | Queues accumulate; no async processing | Scale workers |
| Webhook target unreachable | Per-webhook retry (3 attempts, exponential backoff) | Target recovery |
| Disk < 10% free | Health check reports `"degraded"` | Manual cleanup |

## Configuration Summary

| Subsystem | Key Config | Env Var |
|-----------|-----------|---------|
| Search | `SEARCH_PROVIDER` | `SEARCH_PROVIDER` (default: `sqlite`) |
| Email | SMTP settings | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `FROM_ADDRESS` |
| Storage | Backend selection | `STORAGE_BACKEND` (`local` / `s3`) |
| Webhooks | Encryption key | `WEBHOOK_ENCRYPTION_KEY` |
| Health | Detailed access secret | `HEALTH_CHECK_SECRET` |
| Celery | Broker URL | `REDIS_URL` |

## Related Documents

- [Search](search.md) — FTS5 internals, query processing, fallback
- [Email](email.md) — SMTP configuration, templates, retry logic
- [Storage](storage.md) — Backend abstraction, image processing, S3 flow
- [Webhooks](webhooks.md) — SSRF protection, HMAC signing, delivery architecture
