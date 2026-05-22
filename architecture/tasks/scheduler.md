# APScheduler (`app/scheduler.py`)

In-process scheduled job scheduler.

## Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| `send_daily_newsletter` | Daily at configured time | Send newsletter to subscribers |
| `cleanup_expired_subscribers` | Every 5 minutes (`*/5`) | Remove unconfirmed expired subscribers |
| `publish_scheduled_posts` | Every 5 minutes (`*/5`) | Auto-publish scheduled posts |
| `run_daily_backup` | Daily at 02:00 | Create database backup |

### `send_daily_newsletter`

Runs daily at `NEWSLETTER_SEND_TIME` (default: 08:00):
1. Acquires FileLock (`newsletter.lock`) with `timeout=0` - skips if lock held
2. Queries confirmed subscribers
3. Gets posts where:
   - Published and has `published_at`
   - `newsletter_sent_at` is NULL
   - `newsletter_attempts < NEWSLETTER_MAX_RETRY_ATTEMPTS`
4. **Synchronously** calls `send_newsletter()` directly (not via Celery task)
5. On success: sets `newsletter_sent_at = now` and resets `newsletter_attempts = 0`
6. On failure: increments `newsletter_attempts` for retry

**Retry Logic:** Respects `NEWSLETTER_MAX_RETRY_ATTEMPTS` configuration. Posts with `newsletter_attempts >= NEWSLETTER_MAX_RETRY_ATTEMPTS` are excluded from selection until reset.

### `cleanup_expired_subscribers`

Runs every 5 minutes (`minute="*/5"`):
1. Finds subscribers past `expires_at` without confirmation
2. Deletes unconfirmed expired records

### `publish_scheduled_posts`

Runs every 5 minutes (`minute="*/5"`):
1. Finds posts where `scheduled_publish_at <= now` and `published = False`
2. Sets `published = True` and `published_at = now`
3. Syncs to FTS index via `sync_fts_batch()`
4. Invalidates tag cache via `invalidate_tag_cache()`

### `run_daily_backup`

Runs daily at 02:00 (`hour=2, minute=0`):
1. Creates backup using inline `run_daily_backup()` service function
2. Respects retention policy

**Naming Convention:** This scheduler job uses `blog_*.db` naming pattern (e.g., `blog_20260509_020000.db`). For encrypted/compressed backups, use the Celery task `run_backup_task` which also uses `blog_*.db` naming but supports compression and encryption via `create_backup()`.

## Celery Queue Routing

Celery tasks use specific queues for different workloads (for reference - APScheduler jobs run in-process, not via Celery):

| Queue | Tasks | Location |
|-------|-------|----------|
| `images` | Image processing | `app/tasks.py:28` |
| `newsletter` | Newsletter delivery | `app/tasks.py:127` |
| `webhooks` | Webhook delivery | `app/tasks.py:184` |
| `email` | Transactional email | `app/tasks.py:263,284` |
| `backup` | Backup tasks | `app/tasks.py:305` |

## Multi-Worker Deployment

**Important:** APScheduler's FileLock only works on a single machine. In multi-container deployments:
- Each container runs its own APScheduler
- Without external coordination (Redis, etcd), jobs may run on all replicas
- FileLock uses `timeout=0` (non-blocking) - silently skips if lock held
- Lock file locations: `{instance_path}/{job_name}.lock`
  - `newsletter.lock` - Daily newsletter sending
  - `cleanup.lock` - Expired subscriber cleanup
  - `scheduled.lock` - Scheduled post publishing
  - `backup.lock` - Daily backup

## Initialization

```python
def init_scheduler(app: Flask) -> None:
    # Called during app factory
```

## See Also
- [Celery Tasks](tasks/celery-tasks.md) - Async task queue
- [Backup Service](../services/backup.md) - Backup implementation
