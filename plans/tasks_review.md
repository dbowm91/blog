# Tasks Architecture Review

**Reviewed:** 2026-05-29
**Architecture Docs:** architecture/tasks/overview.md, architecture/tasks/celery-tasks.md, architecture/tasks/scheduler.md
**Source Files:** app/tasks.py, app/scheduler.py, app/celery_app.py

---

## Findings

### Verified Claims (Correct)

**Celery App Configuration (`celery_app.py`):**
- All global Celery settings confirmed: `task_serializer="json"`, `accept_content=["json"]`, `result_serializer="json"`, `timezone="UTC"`, `enable_utc=True`, `task_track_started=True`, `task_time_limit=300`, `task_soft_time_limit=240`, `worker_prefetch_multiplier=1`, `worker_max_tasks_per_child=100` (lines 20-31)
- Flask-context settings confirmed: `task_acks_late=True`, `task_reject_on_worker_lost=True` (lines 33-37)

**Task Definitions (`app/tasks.py`):**
- `generate_image_variants`: `bind=True, max_retries=3, retry_backoff=True, queue="images"` (line 30) -- correct
- `send_newsletter_task`: `bind=True, max_retries=3, retry_backoff=True, time_limit=600, soft_time_limit=540, queue="newsletter"` (lines 129-136) -- correct
- `deliver_webhook_task`: `bind=True, max_retries=3, retry_backoff=True, queue="webhooks"` (line 194) -- correct; dispatches to `deliver_single_webhook_task` at line 223
- `deliver_single_webhook_task`: `bind=True, max_retries=3, retry_backoff=True, queue="webhooks"` (line 233) -- correct; SSRF protection, HMAC signing, retry logic, delivery status updates all confirmed
- `send_confirmation_task`: `bind=True, max_retries=3, retry_backoff=True, queue="email"` (line 333) -- correct
- `send_password_reset_task`: `bind=True, max_retries=3, retry_backoff=True, queue="email"` (line 354) -- correct
- `run_backup_task`: `bind=True, max_retries=2, retry_backoff=True, queue="backup"` (line 375); uses `compress=True, keep=7, encrypt=False` (line 387) -- correct

**Non-Retry Behavior (confirmed in code):**
- `generate_image_variants`: catches exceptions and returns `False` without calling `self.retry()` (lines 121-126) -- correct
- `run_backup_task`: catches exceptions and returns `False` without calling `self.retry()` (lines 389-391) -- correct

**Database Session Management:**
- All 5 database tasks use `db.session.remove()` in `finally` blocks -- confirmed for `send_newsletter_task` (line 191), `deliver_webhook_task` (line 230), `deliver_single_webhook_task` (line 308), `send_confirmation_task` (line 351), `send_password_reset_task` (line 372)
- `run_backup_task` does NOT use `db.session.remove()` because it does not access the database -- this is consistent (see Bug #1)

**APScheduler Jobs (`app/scheduler.py`):**
- `send_daily_newsletter`: only added when `SMTP_HOST` is configured (lines 290-300) -- correct; uses FileLock with `timeout=0` (lines 75-81); calls `send_newsletter()` synchronously (line 145); respects `NEWSLETTER_MAX_RETRY_ATTEMPTS` (lines 91-108, 118) -- correct
- `cleanup_expired_subscribers`: `CronTrigger(minute="*/5")` (lines 301-307); FileLock `timeout=0` with `cleanup.lock` (lines 170-176) -- correct
- `publish_scheduled_posts`: `CronTrigger(minute="*/5")` (lines 308-314); FileLock `timeout=0` with `scheduled.lock` (lines 210-216); FTS rollback behavior confirmed (lines 248-253); tag cache invalidation confirmed (line 256) -- correct
- `run_daily_backup`: `CronTrigger(hour=2, minute=0)` (lines 315-321); FileLock `timeout=0` with `backup.lock` (lines 266-272) -- correct

**Backup Implementation Comparison (confirmed):**
- APScheduler backup: `blog_YYYYMMDD_HHMMSS.db` (no compression, `backup.py:173`) -- correct
- Celery backup: `blog_YYYYMMDD_HHMMSS.db.gz` (with compression, `tasks.py:387` + `backup.py:46-48`) -- correct
- Both use retention of 7 (`BACKUP_RETENTION_COUNT = 7` in backup.py:21; `keep=7` in tasks.py:387) -- correct
- Both use `sqlite3.backup()` API -- correct

**Email Retry Count:**
- `NEWSLETTER_MAX_RETRY_ATTEMPTS` default is 5 (`config.py:119`) -- correct
- Used in `send_newsletter()` via `max_retries=NEWSLETTER_MAX_RETRY_ATTEMPTS` (`email.py:209`) -- correct

---

### Discrepancies (Doc vs Code)

1. **scheduler.md:64-68 -- Celery queue line numbers are inaccurate**
   - Doc: `webhooks` at `app/tasks.py:194` -- but `deliver_webhook_task` starts at line 194 and `deliver_single_webhook_task` starts at line 233
   - The queue reference table is informational (not normative), but line numbers are misleading

2. **celery-tasks.md:88 -- delivery_status update description is incomplete**
   - Doc says: "Updates `WebhookEvent.delivery_status` via `_update_delivery_status()`"
   - The implementation (lines 311-330) sets `delivery_status = "delivered"` if `event.delivered` else `"failed"`. However, `event.delivered` was set to `True` by `deliver_webhook_task` (the dispatcher) at line 226 BEFORE any individual webhook deliveries were attempted. The status check is therefore semantically incorrect -- it checks the dispatcher's state, not per-webhook success. This is a design bug (see Bug #2), not a pure doc issue.

3. **scheduler.md line 109 -- backup naming format is correct but potentially confusing**
   - The doc correctly shows APScheduler output as `blog_YYYYMMDD_HHMMSS.db` and Celery as `blog_YYYYMMDD_HHMMSS.db.gz`
   - However, the phrasing "For encrypted/compressed backups, use the Celery task" implies compression = encrypted, but the Celery backup uses `encrypt=False` by default

---

### Missing Documentation

1. **No default queue defined**: `celery_app.py` does NOT set `task_default_queue`, meaning the default is `"celery"`. No tasks use this queue. This gap is not documented anywhere.

2. **No `WEBHOOK_TIMEOUT` value documented**: `deliver_single_webhook_task` uses `WEBHOOK_TIMEOUT` from config (`tasks.py:282`) but the default value is not documented in any tasks doc.

3. **`_update_delivery_status` complexity**: The function at `tasks.py:311-330` has non-obvious logic: it queries all webhooks for the event type and sets delivery_status based on `event.delivered` (which is set by the dispatcher, not per-webhook results). This should be explained or refactored.

4. **Newsletter three-way relationship**: The architecture has three distinct newsletter paths: (a) scheduler's `send_daily_newsletter()` calls `email.send_newsletter()` synchronously, (b) admin's `send_newsletter_task` Celery task calls `email.send_newsletter()` asynchronously, (c) `email.send_newsletter()` is the core implementation. This relationship is only partially explained.

---

### Potential Bugs / Concerns

1. **`run_backup_task` -- missing `db.session.remove()` finally block** (`tasks.py:375-391`)
   - All other database tasks use `try/finally` with `db.session.remove()` but `run_backup_task` does not.
   - However, `run_backup_task` does NOT use `db.session` at all -- it only calls `create_backup()`.
   - Impact: LOW (no DB session to clean up). Inconsistency is stylistic, not functional.

2. **`_update_delivery_status` logic bug -- incorrect status tracking** (`tasks.py:311-330`)
   - Sets `delivery_status = "delivered"` if `event.delivered` else `"failed"`.
   - But `event.delivered` is set to `True` by `deliver_webhook_task` (dispatcher) at line 226 BEFORE any individual `deliver_single_webhook_task` calls are even made.
   - Result: `_update_delivery_status` will almost always report `"delivered"` even when all per-webhook deliveries failed.
   - Impact: MEDIUM -- webhook delivery status in the database will be misleading in production.

3. **Silent exception swallowing in `deliver_single_webhook_task`** (`tasks.py:303-306`)
   - `except Exception` catches all non-`RequestException` errors (including coding bugs), logs them, updates status, and returns `False` without retry.
   - This prevents infinite retry loops but could mask real bugs.
   - Impact: LOW for network errors (already retried), but could mask programming errors.

4. **APScheduler multi-worker race condition** (`scheduler.py:3-8`, `scheduler.md:72-75`)
   - FileLock with `timeout=0` only works on a single machine. Multiple container replicas will each run their own APScheduler and attempt to execute jobs concurrently.
   - Impact: HIGH for multi-container deployments -- duplicate newsletter sends, duplicate backups, duplicate post publishes.

---

### Improvement Suggestions

1. **Fix `_update_delivery_status` logic**: Track per-webhook success instead of relying on the dispatcher's `event.delivered` flag. Consider adding a `failed_webhook_ids` set or a `successful_webhook_count` counter to `WebhookEvent`.

2. **Add `task_default_queue` to `celery_app.py`**: Either explicitly set `task_default_queue = "celery"` (and document it) or set it to one of the meaningful queues (`"email"` perhaps) to avoid confusion.

3. **Document `WEBHOOK_TIMEOUT` default**: Add the config default value to celery-tasks.md.

4. **Fix queue line number references** in scheduler.md: Update the Celery Queue Reference table with accurate line numbers (`deliver_webhook_task:194`, `deliver_single_webhook_task:233`).

5. **Add architecture diagram for newsletter paths**: Clarify the three-way relationship between scheduler, Celery task, and email module.

6. **Clarify backup compression vs encryption**: The doc implies `run_backup_task` produces encrypted/compressed backups, but `compress=True, encrypt=False` by default. Separate these concepts clearly.

---

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|---------|
| 1 | high | Fix `_update_delivery_status` logic -- it checks dispatcher's `event.delivered` instead of per-webhook success | source (tasks.py:311-330) |
| 2 | med | Add explicit `task_default_queue` config or document default `"celery"` queue | source (celery_app.py) + docs |
| 3 | med | Document `WEBHOOK_TIMEOUT` default value in celery-tasks.md | docs |
| 4 | low | Fix line number references in scheduler.md Celery Queue Reference table | docs |
| 5 | low | Add `db.session.remove()` finally block to `run_backup_task` for consistency | source (tasks.py:375) |
| 6 | low | Add newsletter architecture diagram clarifying scheduler vs Celery vs email module roles | docs |
