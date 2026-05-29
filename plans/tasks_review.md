# Tasks Module Architecture Review

**Reviewed:** May 29, 2026
**Architecture Docs:** overview.md, celery-tasks.md, scheduler.md
**Source Files:** app/tasks.py, app/scheduler.py, app/celery_app.py

## Findings

### Verified Claims (Correct)

- **Overview.md**: Table of systems (Celery, APScheduler) and files is accurate.
- **celery-tasks.md**: Queue list (`images`, `newsletter`, `webhooks`, `email`, `backup`) matches source.
- **celery-tasks.md**: `generate_image_variants` signature, `max_retries=3`, queue, return-on-failure behavior all correct.
- **celery-tasks.md**: `send_newsletter_task` signature, `max_retries=3`, time limits, queue all match source.
- **celery-tasks.md**: `send_confirmation_task` and `send_password_reset_task` signatures and retry behavior correct.
- **celery-tasks.md**: `run_backup_task` signature, `max_retries=2`, `compress=True`, `keep=7`, `encrypt=False` all match.
- **celery-tasks.md**: Error handling table — `generate_image_variants`, `send_newsletter_task`, `send_confirmation_task`, `send_password_reset_task`, `run_backup_task` all accurate.
- **celery-tasks.md**: Database session management section and line number references for `send_newsletter_task` (line 127), `deliver_webhook_task` (line 259), `send_confirmation_task` (line 280), `send_password_reset_task` (line 301), `run_backup_task` (line 320) are all valid.
- **scheduler.md**: Jobs table (`send_daily_newsletter`, `cleanup_expired_subscribers`, `publish_scheduled_posts`, `run_daily_backup`) matches source.
- **scheduler.md**: `send_daily_newsletter` — query logic, retry logic, sync call behavior, FileLock (`newsletter.lock`, `timeout=0`) all correct.
- **scheduler.md**: `cleanup_expired_subscribers` — cron schedule (`minute="*/5"`), FileLock (`cleanup.lock`, `timeout=0`) correct.
- **scheduler.md**: `publish_scheduled_posts` — cron schedule (`minute="*/5"`), query logic, FTS sync, tag cache invalidation, FileLock (`scheduled.lock`, `timeout=0`) correct.
- **scheduler.md**: `run_daily_backup` — cron schedule (`hour=2, minute=0`), FileLock (`backup.lock`, `timeout=0`), service function delegation correct.
- **scheduler.md**: `init_scheduler` function name and basic behavior correct.
- **scheduler.md**: Multi-worker deployment warning and FileLock table all correct.
- **scheduler.md**: Backup Implementation Comparison table — schedule, lock, compression, encryption, output format all accurate.

### Discrepancies (Doc vs Code)

1. **celery-tasks.md:48-61** — `deliver_webhook_task` doc says "Exceptions during webhook delivery are caught and logged... but `self.retry()` is **never called**" and references `app/tasks.py:234-246`. This is **wrong**. The current `deliver_webhook_task` (line 194) dispatches to `deliver_single_webhook_task` which **does** call `self.retry()` (lines 294, 298). The doc describes old behavior from before the refactor to per-webhook retry.

2. **celery-tasks.md:98-107** — Error handling table row for `deliver_webhook_task` says "No" for retry. This is wrong — `deliver_single_webhook_task` does retry (called from `deliver_webhook_task`).

3. **celery-tasks.md:107** — Note paragraph repeats the incorrect claim that `deliver_webhook_task` never calls `self.retry()`. The dispatch pattern means retries happen at the `deliver_single_webhook_task` level.

4. **scheduler.md:9** — Jobs table does not indicate `send_daily_newsletter` is conditional on `SMTP_HOST`. Source (`app/scheduler.py:290`) only adds this job when `SMTP_HOST` is configured. The conditional behavior is documented later in the file but missing from the summary table.

5. **scheduler.md:59** — Celery Queue Reference table lists `images` at `app/tasks.py:28`. Actual location is line 30 (off by 2 lines).

6. **scheduler.md:88** — `init_scheduler` return type shown as `None`. Source (`app/scheduler.py:281`) returns `Optional["BackgroundScheduler"]`.

7. **scheduler.md:47-48** — `run_daily_backup` doc says "Creates backup using inline `run_daily_backup()` service function" — this is correct (delegates to `app.services.backup.run_daily_backup`). However, the comparison table at line 98 says entry point is `app/services.backup.run_daily_backup` which is also correct, but the naming is confusing since the scheduler function and service function share the same name.

### Missing Documentation

1. **`deliver_single_webhook_task`** — This task (`app/tasks.py:233-308`) is not documented anywhere in celery-tasks.md. It is exported in `__all__` (line 23) and is critical to the webhook delivery chain. It handles per-webhook SSRF protection, HMAC signing, retry logic, and delivery status updates.

2. **`_update_delivery_status`** — Helper function (`app/tasks.py:311-330`) used by `deliver_single_webhook_task` to determine final delivery status. Not documented.

3. **Celery global configuration** (`app/celery_app.py:20-31`) — `task_time_limit=300`, `task_soft_time_limit=240`, `worker_prefetch_multiplier=1`, `worker_max_tasks_per_child=100` are not documented. These are relevant for understanding task execution behavior.

4. **Scheduler conditional SMTP behavior** — The fact that `send_daily_newsletter` is only added when `SMTP_HOST` is configured is mentioned in scheduler.md text but not reflected in the summary jobs table. Also not mentioned in overview.md.

5. **`publish_scheduled_posts` rollback behavior** — Source (`app/scheduler.py:248-253`) shows that if `sync_fts_batch()` fails, the entire publish is rolled back. This failure/rollback behavior is not documented.

### Potential Bugs / Concerns

1. **`deliver_webhook_task` immediate `delivered=True` commit** (`app/tasks.py:226-227`) — After dispatching to `deliver_single_webhook_task`, the event is immediately marked `delivered = True`. The individual webhook tasks then update `delivery_status` via `_update_delivery_status`. This means the event appears "delivered" before individual webhooks actually complete. If the worker crashes after dispatch but before individual tasks run, the event would be marked delivered with no actual delivery.

2. **`send_newsletter_task` error logging** (`app/tasks.py:186`) — Logs `post.newsletter_attempts` after the loop, but `post` refers to the last post in the list, not necessarily the one that failed. The log message could be misleading if posts have different attempt counts.

3. **`generate_image_variants` no `db.session.remove()`** — Not a bug (the task doesn't use the database), but the celery-tasks.md pattern section implies all tasks use this pattern. The task is correctly excluded from the line references.

### Improvement Suggestions

1. **celery-tasks.md**: Rewrite the `deliver_webhook_task` section to describe the dispatch pattern to `deliver_single_webhook_task`. Document `deliver_single_webhook_task` as a separate task definition with its own retry behavior.

2. **celery-tasks.md**: Update the Error handling table and Note paragraph to reflect that retries happen at the `deliver_single_webhook_task` level, not `deliver_webhook_task`.

3. **scheduler.md**: Add a note to the jobs table (or a "Conditional" column) indicating `send_daily_newsletter` requires `SMTP_HOST`.

4. **scheduler.md**: Fix `init_scheduler` return type to `Optional["BackgroundScheduler"]`.

5. **scheduler.md**: Fix line number for `images` queue in Celery Queue Reference (line 30, not 28).

6. **celery-tasks.md or scheduler.md**: Document Celery global configuration (time limits, prefetch multiplier, max tasks per child).

7. **scheduler.md**: Document `publish_scheduled_posts` rollback behavior on FTS sync failure.

## Action Items

| # | Priority | Description | Docs Affected |
|---|----------|-------------|---------------|
| 1 | high | Document `deliver_single_webhook_task` and update `deliver_webhook_task` to describe dispatch pattern; fix retry behavior claims | celery-tasks.md |
| 2 | high | Fix error handling table and Note paragraph for webhook retry behavior | celery-tasks.md |
| 3 | medium | Add conditional note for `send_daily_newsletter` in jobs table | scheduler.md |
| 4 | low | Fix `init_scheduler` return type to `Optional["BackgroundScheduler"]` | scheduler.md |
| 5 | low | Fix `images` queue line number (30, not 28) in Celery Queue Reference | scheduler.md |
| 6 | low | Document Celery global config (`task_time_limit`, `worker_prefetch_multiplier`, etc.) | celery-tasks.md |
| 7 | low | Document `publish_scheduled_posts` rollback on FTS sync failure | scheduler.md |
