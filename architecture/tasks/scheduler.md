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
1. Queries confirmed subscribers
2. Gets posts published since last newsletter
3. Triggers `send_newsletter_task` Celery task

### `cleanup_expired_subscribers`

Runs every 5 minutes (`minute="*/5"`):
1. Finds subscribers past `expires_at` without confirmation
2. Deletes unconfirmed expired records

### `publish_scheduled_posts`

Runs every 5 minutes:
1. Finds posts where `scheduled_publish_at <= now` and `published = False`
2. Sets `published = True` and `published_at = now`
3. Syncs to FTS index

### `run_daily_backup`

Runs daily at 02:00 (`hour=2, minute=0`):
1. Creates backup using inline `run_daily_backup()` service
2. Respects retention policy

Note: This scheduler job uses the `run_daily_backup()` service function which creates unencrypted, uncompressed `backup_*.db` files. For encrypted/compressed backups, use the Celery task `run_backup_task` which calls `create_backup()` with `blog_*.db` naming.

## Queue Routing

Celery tasks use specific queues for different workloads:

| Queue | Tasks | Location |
|-------|-------|----------|
| `images` | Image processing | `app/tasks.py:29` |
| `newsletter` | Newsletter delivery | `app/tasks.py:129` |
| `webhooks` | Webhook delivery | `app/tasks.py:192` |
| `email` | Transactional email | `app/tasks.py:264,285` |
| `backup` | Backup tasks | `app/tasks.py:306` |

## Initialization

```python
def init_scheduler(app: Flask) -> None:
    # Called during app factory
```

## See Also
- [Celery Tasks](tasks/celery-tasks.md) - Async task queue
- [Backup Service](../services/backup.md) - Backup implementation
