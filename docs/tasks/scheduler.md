# APScheduler Configuration

## Job Scheduling

The scheduler runs as a **daemon thread** (see `app/scheduler.py:290`):

```python
scheduler = BackgroundScheduler(daemon=True)
```

**Important**: A daemon thread will not prevent the process from exiting. When the web server shuts down, the scheduler thread terminates automatically without waiting for running jobs to complete.

## FileLock Multi-Container Warning

**APScheduler uses FileLock which only works on a single machine.**

The scheduler uses `filelock.FileLock` to prevent duplicate job execution:

```python
lock_path = os.path.join(app.instance_path, "newsletter.lock")
lock = FileLock(lock_path, timeout=0)
lock.acquire()
```

### Multi-Worker Limitation

- **Single machine**: FileLock prevents duplicate newsletter sends when multiple worker processes exist on the same host
- **Multi-container/multi-machine**: FileLock provides **no protection** across different machines or containers

For multi-machine deployments, use an external scheduler:
- Celery Beat for periodic tasks
- cron jobs with distributed locking (Redis, etcd)
- External task queue with built-in scheduling

## Scheduled Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| `send_daily_newsletter` | Configurable (default 08:00) | Sends newsletter to subscribers |
| `cleanup_expired_subscribers` | Every 5 minutes | Removes unconfirmed subscribers past expiry |
| `publish_scheduled_posts` | Every 5 minutes | Auto-publishes posts at scheduled time |
| `run_daily_backup` | 02:00 daily | Creates encrypted database backups |

## SMTP Configuration

When `SMTP_HOST` is not configured:
- Newsletter job is **disabled** (no error logged)
- All other scheduled jobs continue to run normally

## Health Check

The scheduler health endpoint reports:
- `status`: "running" or "stopped"
- `last_newsletter_send`: ISO timestamp of last successful send
- `next_run`: ISO timestamp of next scheduled job