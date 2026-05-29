# APScheduler (`app/scheduler.py`)

In-process scheduled job scheduler.

## Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| `send_daily_newsletter` | Daily at configured time | Send newsletter to subscribers (only when `SMTP_HOST` is configured) |
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

**Celery vs. Scheduler:** This job sends newsletters synchronously via `app.email.send_newsletter()`. The Celery `send_newsletter_task` (`app/tasks.py:129`) is separate and used only for manual/ad-hoc sends from the admin dashboard — it is never invoked by the scheduler.

### `cleanup_expired_subscribers`

Runs every 5 minutes (`minute="*/5"`):
1. Finds subscribers past `expires_at` without confirmation
2. Deletes unconfirmed expired records

### `publish_scheduled_posts`

Runs every 5 minutes (`minute="*/5"`):
1. Acquires FileLock (`scheduled.lock`) with `timeout=0` - skips if lock held
2. Finds posts where `scheduled_publish_at <= now` and `published = False`
3. Sets `published = True`, `published_at = now`, clears `scheduled_publish_at`
4. Builds FTS batch items from post data
5. Calls `sync_fts_batch()` to update the FTS5 search index
6. **If FTS sync fails**: rolls back the entire database transaction and logs a warning — posts remain unpublished and will be retried on the next run
7. On success: commits, invalidates tag cache via `invalidate_tag_cache()`

**FTS Rollback Behavior:** The function uses a pre-commit validation pattern. Posts are marked as published in the session but the commit only occurs after `sync_fts_batch()` succeeds. If FTS sync returns `False` (e.g., due to a database error or FTS5 unavailability), the entire batch publish is rolled back. This ensures FTS index consistency with the database — posts never appear published in the DB but missing from search. The posts will be re-selected and re-attempted on the next scheduler cycle (every 5 minutes).

### `run_daily_backup`

Runs daily at 02:00 (`hour=2, minute=0`):
1. Creates backup using inline `run_daily_backup()` service function
2. Respects retention policy

**Naming Convention:** This scheduler job uses `blog_*.db` naming pattern (e.g., `blog_20260509_020000.db`). For encrypted/compressed backups, use the Celery task `run_backup_task` which also uses `blog_*.db` naming but supports compression and encryption via `create_backup()`.

## Celery Queue Reference

Celery tasks use specific queues for different workloads (for reference — APScheduler jobs are in-process direct function calls, not routed through Celery queues):

| Queue | Tasks | Location |
|-------|-------|----------|
| `images` | Image processing | `app/tasks.py:30` |
| `newsletter` | Newsletter delivery | `app/tasks.py:129` |
| `webhooks` | Webhook delivery | `app/tasks.py:194` |
| `email` | Transactional email | `app/tasks.py:333,354` |
| `backup` | Backup tasks | `app/tasks.py:375` |

## Multi-Worker Deployment

**Important:** APScheduler's FileLock only works on a single machine. In multi-container deployments:
- Each container runs its own APScheduler
- Without external coordination (Redis, etcd), jobs may run on all replicas
- FileLock uses `timeout=0` (non-blocking) - silently skips if lock held

### FileLock Usage

Each scheduler job acquires a `FileLock` with `timeout=0` before executing. `timeout=0` means non-blocking: if the lock is already held (e.g., by another process on the same machine), the job immediately skips execution with a warning log. This prevents duplicate concurrent runs on a single machine.

| Job Function | Lock File | Purpose |
|-------------|-----------|---------|
| `send_daily_newsletter` | `newsletter.lock` | Prevents duplicate newsletter sends |
| `cleanup_expired_subscribers` | `cleanup.lock` | Prevents duplicate subscriber cleanup |
| `publish_scheduled_posts` | `scheduled.lock` | Prevents duplicate scheduled post publishing |
| `run_daily_backup` | `backup.lock` | Prevents duplicate backup creation |

Lock files are created at `{instance_path}/{job_name}.lock`. All four jobs follow the same pattern: acquire lock → do work in `try` block → release lock in `finally`.

## Initialization

```python
def init_scheduler(app: Flask) -> Optional["BackgroundScheduler"]:
    # Called during app factory
```

## Backup Implementation Comparison

There are two separate backup implementations with different capabilities:

| Aspect | APScheduler Backup | Celery Backup |
|--------|-------------------|---------------|
| Entry point | `app/scheduler.py:run_daily_backup` → `app.services.backup.run_daily_backup` | `app/tasks.py:run_backup_task` → `app.services.backup.create_backup` |
| Schedule | Daily at 02:00 (`hour=2, minute=0`) | Manual trigger only (admin/API) |
| Lock | `backup.lock` with `timeout=0` | None (Celery queue isolation) |
| Compression | No | Yes (`compress=True`) |
| Encryption | No | No (`encrypt=False`) |
| Retention | 7 backups (`BACKUP_RETENTION_COUNT`) | 7 backups (`keep=7`) |
| Output format | `blog_YYYYMMDD_HHMMSS.db` | `blog_YYYYMMDD_HHMMSS.db.gz` |
| Encryption support | No | Yes (when `encrypt=True`, uses AES-256-GCM) |
| Backup method | `sqlite3.backup()` API | `sqlite3.backup()` API via `create_backup()` |

Both implementations use the `blog_*.db` naming pattern and share the same retention count of 7. The key difference is that the APScheduler backup is a simple scheduled copy, while the Celery backup supports compression and encryption for production use.

## See Also
- [Celery Tasks](celery-tasks.md) - Async task queue
- [Backup Service](../services/backup.md) - Backup implementation
