# APScheduler (`app/scheduler.py`)

In-process scheduled job scheduler.

## Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| `send_daily_newsletter` | Daily at configured time | Send newsletter to subscribers |
| `cleanup_expired_subscribers` | Every 5 minutes | Remove unconfirmed expired subscribers |
| `publish_scheduled_posts` | Every 5 minutes | Auto-publish scheduled posts |
| `run_daily_backup` | Daily at 02:00 | Create database backup |

### `send_daily_newsletter`

Runs daily at `NEWSLETTER_SEND_TIME` (default: 08:00):
1. Queries confirmed subscribers
2. Gets posts published since last newsletter
3. Triggers `send_newsletter_task` Celery task

### `cleanup_expired_subscribers`

Runs every 5 minutes:
1. Finds subscribers past `expires_at` without confirmation
2. Deletes unconfirmed expired records

### `publish_scheduled_posts`

Runs every 5 minutes:
1. Finds posts where `scheduled_publish_at <= now` and `published = False`
2. Sets `published = True` and `published_at = now`
3. Syncs to FTS index

### `run_daily_backup`

Runs daily at 02:00:
1. Creates backup using `run_daily_backup()` service
2. Respects retention policy

## Initialization

```python
def init_scheduler(app: Flask) -> None:
    # Called during app factory
```

## See Also
- [Celery Tasks](tasks/celery-tasks.md) - Async task queue
- [Backup Service](../services/backup.md) - Backup implementation
