# Tasks Module Architecture Review

**Reviewed:** 2026-05-31
**Architecture Docs:** overview.md, celery-tasks.md, scheduler.md
**Source Files:** app/tasks.py, app/scheduler.py, app/celery_app.py

## Findings

### Verified Claims (Correct)

- **Queues match:** All 5 queue names (`images`, `newsletter`, `webhooks`, `email`, `backup`) in celery-tasks.md match the actual `queue=` parameters on each task decorator in `app/tasks.py`.
- **Celery global config:** The table in celery-tasks.md lines 153-164 exactly matches `app/celery_app.py:20-31` (all 10 settings and their values).
- **Conditional Celery config:** `task_acks_late=True` and `task_reject_on_worker_lost=True` are only set when `init_celery(app)` is called with a Flask app (celery-tasks.md lines 166-171 matches code at celery_app.py:33-37).
- **Newsletter task overrides:** `send_newsletter_task` has `time_limit=600, soft_time_limit=540` (celery-tasks.md line 174 matches tasks.py:133-134).
- **Backup task retries:** `run_backup_task` has `max_retries=2` (celery-tasks.md line 175 matches tasks.py:386).
- **APScheduler jobs:** All 4 jobs and their schedules match exactly: daily newsletter (conditional on SMTP_HOST), cleanup every 5 min, publish every 5 min, backup at 02:00.
- **FileLock timeout=0:** Confirmed across all 4 scheduler jobs in `app/scheduler.py` (lines 76, 171, 211, 267).
- **SMTP_HOST gating:** Only the daily newsletter job is disabled when SMTP_HOST is not configured (scheduler.py:290). Other 3 jobs always run. Correct.
- **Newsletter task vs. scheduler separation:** Correctly documented that `send_newsletter_task` (Celery) is for manual/ad-hoc sends while `send_daily_newsletter` (APScheduler) is the scheduled path.
- **Two-level webhook dispatch:** `deliver_webhook_task` dispatches to `deliver_single_webhook_task` per webhook (tasks.py:223). Matches documentation.
- **Webhook SSRF protection:** `is_safe_webhook_url()` is called before making requests (tasks.py:251). Matches docs.
- **Webhook HMAC signing:** `X-Webhook-Signature` header via `sign_webhook_payload()` (tasks.py:273-274). Matches docs.
- **Webhook `allow_redirects=False`:** Confirmed at tasks.py:282. Matches docs.
- **Email retry count default is 5:** `NEWSLETTER_MAX_RETRY_ATTEMPTS` defaults to 5 in `app/config.py:119`, confirmed in `config.toml:49`. The `_send_email_with_retry` function signature default is 3 (email.py:111), but it is always called from `send_newsletter()` with `max_retries=NEWSLETTER_MAX_RETRY_ATTEMPTS` which is 5.
- **Backup task parameters:** `create_backup()` is called with `compress=True, keep=7, encrypt=False` (tasks.py:399). Matches docs.
- **Backup naming pattern:** `blog_YYYYMMDD_HHMMSS.db.gz` for compressed backups (backup.py:50-52). Matches docs.
- **DB session cleanup pattern:** All 6 tasks that touch the database use `db.session.remove()` in `finally` blocks (celery-tasks.md lines 185-201). Verified in code.
- **Database session management documentation:** The pattern description and rationale in celery-tasks.md lines 183-201 are accurate.
- **Backup Implementation Comparison table:** All entries in scheduler.md lines 149-161 match the actual code.
- **FTS rollback behavior:** The pre-commit validation pattern described in scheduler.md lines 43-48 matches the code at scheduler.py:248-253.
- **Line number references:** All `app/tasks.py:NNN` line number references in scheduler.md (lines 64-68) are accurate against the current source.

### Discrepancies (Doc vs Code)

1. **celery-tasks.md:140 — `send_newsletter_task` error handling claims explicit `self.retry()`**
   - **Doc claims:** "Exception triggers `self.retry(exc=e)`" with retry = "Yes"
   - **Code does:** The task has NO `except` block and NO `self.retry()` call (tasks.py:144-191). It uses a bare `try/finally`. If `send_newsletter()` returns `False`, the task increments `newsletter_attempts` and returns `False` (no Celery retry). If an unhandled exception propagates, Celery framework auto-retries (because `max_retries=3` is set on the decorator), but the task itself never calls `self.retry()`. Compare with `send_confirmation_task` (tasks.py:358-360) which DOES explicitly call `self.retry(exc=e)`.
   - **Impact:** Medium. Misleads developers about retry mechanism. The task retries on unhandled exceptions via Celery framework, not via explicit `self.retry()`. On `send_newsletter()` returning `False`, there is NO retry at all — just attempt tracking.

2. **celery-tasks.md:79-100 — Duplicate `deliver_single_webhook_task` section**
   - **Doc claims:** The same task is documented twice — first at lines 64-100, then again at lines 79-100 with nearly identical content.
   - **Code does:** There is only one `deliver_single_webhook_task` function (tasks.py:230-309).
   - **Impact:** Low. Confusing but not misleading about behavior.

3. **celery-tasks.md:140 — Error handling table implies `send_newsletter_task` always retries on failure**
   - **Doc claims:** The table says `send_newsletter_task` has retry behavior = "Yes"
   - **Code does:** The task only retries on *unhandled exceptions* (Celery framework level). When `send_newsletter()` returns `False` (SMTP failure after internal retries), the task increments `newsletter_attempts` and returns `False` without Celery-level retry. The error handling table does not distinguish between "returns False" failures and "raises exception" failures.
   - **Impact:** Medium. The task will NOT retry if the newsletter function returns False after exhausting its own internal SMTP retries (which use `NEWSLETTER_MAX_RETRY_ATTEMPTS=5` retries per subscriber).

4. **scheduler.md:91-93 — Log message template is inaccurate**
   - **Doc claims:** Lock skip warning logs: `WARNING - Job "send_daily_newsletter" was not executed because the lock file ... is already acquired`
   - **Code does:** The actual warning format is: `"Could not acquire lock %s, skipping run"` (scheduler.py:80). The doc shows a hypothetical APScheduler log format that doesn't match the actual code.
   - **Impact:** Low. Misleading for log monitoring setup.

### Missing Documentation

1. **`send_newsletter_task` does not retry on `send_newsletter()` returning `False`**
   The task only increments `newsletter_attempts` and returns `False`. There is no Celery-level retry on this failure path. The documentation should clarify that retry only happens on uncaught exceptions (e.g., database errors), not on SMTP failures reported as `False` by `send_newsletter()`.

2. **`_send_email_with_retry` default `max_retries=3` vs. newsletter override `5`**
   The email module's `_send_email_with_retry` has a default parameter of `max_retries=3` (email.py:111), but `send_newsletter()` always overrides it to `NEWSLETTER_MAX_RETRY_ATTEMPTS` (default 5). The docs mention the default is 5 (correct for newsletter), but the per-subscriber retry count in the email function itself is 3 unless overridden. This layered retry is not documented.

3. **`ENABLE_SCHEDULER` config key is exported in `__all__` but never read**
   `ENABLE_SCHEDULER` is listed in `config.py:55` in `__all__` but never actually read or used anywhere in the codebase. `init_scheduler()` is always called unconditionally from `app/__init__.py:457`. The scheduler runs in every app instance regardless of this config. This is dead configuration.

4. **`generate_image_variants` has `max_retries=3` but never retries intentionally**
   The task catches all expected exceptions and returns `False` (tasks.py:121-126). It never calls `self.retry()`. Celery framework would auto-retry on uncaught exceptions (e.g., `MemoryError`), but this is not the intended behavior. The `max_retries=3` decorator parameter is misleading — it suggests intentional retries that don't exist in the task logic.

5. **`run_backup_task` has same issue as above**
   The task catches `(SQLAlchemyError, OSError, ImportError)` and returns `False` (tasks.py:401-403) without calling `self.retry()`. But `max_retries=2` is set. Any other exception type (e.g., `ValueError`, `TypeError`) would trigger Celery auto-retry, which is not the intended behavior.

6. **Race condition in `_update_delivery_status` (tasks.py:312-341)**
   When multiple `deliver_single_webhook_task` instances complete concurrently, each calls `_update_delivery_status` which reads `event.successful_deliveries` and `event.failed_deliveries`, compares to `total_count`, and potentially commits. With `worker_prefetch_multiplier=1` and `--concurrency=1` this is mitigated, but the doc does not mention this constraint or the fact that the correctness of delivery status tracking depends on single-concurrency execution.

7. **`send_newsletter_task` logging uses stale loop variable** (tasks.py:183-187)
   The `logger.warning` at line 186 uses `post.newsletter_attempts` where `post` is the loop variable from the preceding `for post in posts:` loop. This will always be the *last* post's attempts count, not necessarily representative of all posts.

8. **`create_backup()` uses local time, `run_daily_backup()` uses UTC**
   `app/services/backup.py:49` (`create_backup`, called by Celery task) uses `datetime.now()` (local time) for backup filenames. `backup.py:181` (`run_daily_backup`, called by scheduler) uses `datetime.now(timezone.utc)`. This inconsistency means backup filenames have different timezone semantics depending on which path created them.

9. **Scheduler does not check `ENABLE_SCHEDULER` config**
   `init_scheduler(app)` is always called unconditionally from `app/__init__.py:457`. The `ENABLE_SCHEDULER` config key exists but is never referenced. There is no way to disable the scheduler via configuration.

### Potential Bugs / Concerns

1. **`send_newsletter_task` does not retry on `send_newsletter()` returning `False`** (tasks.py:178-187)
   When `send_newsletter()` returns `False` (indicating SMTP failures for some/all subscribers), the task increments `newsletter_attempts` and returns `False` without raising an exception. Since there is no `self.retry()` call and no exception is raised, Celery does NOT retry this task. The only retry mechanism is the APScheduler job which re-runs daily and checks `newsletter_attempts < NEWSLETTER_MAX_RETRY_ATTEMPTS`. However, for the manual/ad-hoc path (admin triggers `send_newsletter_task`), a failed send will never be retried by Celery — only by the next daily scheduled run if the same posts are still in the "needs newsletter" state. This may be intentional but is a design concern.

2. **Variable scope issue in `send_newsletter_task` logging** (tasks.py:183-187)
   ```python
   logger.warning(
       "Newsletter task failed for %d posts (attempts incremented to %d)",
       len(posts),
       post.newsletter_attempts,  # <-- `post` is last loop iteration variable
   )
   ```
   The variable `post` references the last post from the `for post in posts:` loop. If `posts` was empty after the initial filter (line 146), this would be an `UnboundLocalError` — but this is prevented by the early return at line 148-149. Still, the log message reports only the last post's attempt count, which could differ from others.

3. **Race condition in `_update_delivery_status`** (tasks.py:312-341)
   Multiple `deliver_single_webhook_task` instances could call `_update_delivery_status` concurrently. The function reads `event.successful_deliveries` and `event.failed_deliveries`, checks `completed_count < total_count`, and commits. While `--concurrency=1` in production mitigates this, the code does not use any database-level locking (e.g., `SELECT ... FOR UPDATE`) or optimistic concurrency control. If the concurrency constraint is ever relaxed, this could lead to:
   - Lost counter increments (two tasks both see `completed_count < total_count`, both return without setting final status)
   - Incorrect `delivery_status` (partial commit)
   The doc does not mention that correctness of delivery status tracking depends on single-concurrency execution.

4. **`generate_image_variants` catches `ClientError`/`BotoCoreError` at outer scope but imports them inside S3 branch** (tasks.py:121-122)
   The `except (ClientError, BotoCoreError)` clause at line 121 catches exceptions from `botocore.exceptions`, but these names are imported inside the `S3StorageBackend` branch (line 74). If the S3 branch was not taken (i.e., using local storage), these names would not be in local scope. However, since they can only be raised if the S3 code path was taken, this works in practice. But it is fragile — if code is refactored to move imports, these exception handlers could break silently.

5. **`_update_delivery_status` re-queries enabled webhooks independently** (tasks.py:316-320)
   The function queries `Webhook.filter_by(enabled=True, event_type=event.event_type)` to determine `total_count`. This query is independent of the webhooks that `deliver_webhook_task` dispatched to (tasks.py:210-214). If a webhook is disabled or a new webhook is added between dispatch and delivery completion, the `total_count` could differ from the number of dispatched tasks, causing the delivery status to never resolve (stuck in limbo) or resolve prematurely.

6. **Scheduler `atexit` handler may not fire in containerized deployments** (scheduler.py:327-331)
   The scheduler shutdown is registered via `atexit.register(_shutdown_scheduler)`. In Docker, SIGTERM is sent and Python processes may be killed before `atexit` handlers complete. The `BackgroundScheduler` has `daemon=True` (line 288), so it will be killed with the main thread. This is low-impact since the scheduler is daemonized, but the doc does not mention this behavior.

7. **No retry logic for `deliver_webhook_task` dispatch failures** (tasks.py:194-227)
   The dispatcher task catches exceptions and returns `False` without calling `self.retry()`. If the database query fails or a transient error occurs during dispatch, the entire event is silently dropped. Individual webhook deliveries are never attempted. The doc's error handling table says "N/A (dispatch only)" which is technically correct but understates the risk: a transient DB error during dispatch means the event is never delivered to ANY webhook.

8. **Newsletter task doesn't check `NEWSLETTER_MAX_RETRY_ATTEMPTS`** (tasks.py:129-191)
   Unlike the scheduler path (`send_daily_newsletter` in scheduler.py:118), the Celery `send_newsletter_task` does NOT check `Post.newsletter_attempts < NEWSLETTER_MAX_RETRY_ATTEMPTS` before sending. It will attempt to send newsletters for posts that have already exceeded the max retry threshold. The scheduler properly excludes these posts, but the manual Celery path does not.

### Improvement Suggestions

1. **Document the retry semantics of each task clearly**
   Each task should explicitly state:
   - Whether it calls `self.retry()` explicitly
   - Whether it relies on Celery framework auto-retry (uncaught exceptions)
   - What failure modes trigger retry vs. silent return
   The current error handling table is too coarse.

2. **Add `self.retry()` to `send_newsletter_task` for consistency**
   If the task should retry on failure, add an explicit `except` block with `self.retry()`. If it should NOT retry (relying on the daily scheduler), remove `max_retries=3` and `retry_backoff=True` from the decorator to avoid confusion.

3. **Remove duplicate `deliver_single_webhook_task` section** from celery-tasks.md (lines 79-100).

4. **Fix the log message template** in scheduler.md line 91-93 to match the actual code: `"Could not acquire lock %s, skipping run"`.

5. **Document that delivery status tracking depends on `--concurrency=1`** for Celery workers. Add a note in celery-tasks.md that `_update_delivery_status` assumes single-concurrency execution for correct counter semantics.

6. **Remove or implement `ENABLE_SCHEDULER`** config. Either use it to gate `init_scheduler()` in `app/__init__.py:457`, or remove it from `config.py:__all__` to avoid confusion.

7. **Add `Post.newsletter_attempts < NEWSLETTER_MAX_RETRY_ATTEMPTS` check to `send_newsletter_task`** for parity with the scheduler path, or document why the Celery path intentionally skips this check.

8. **Use `datetime.now(timezone.utc)` consistently** in `create_backup()` (backup.py:49) to match the scheduler path (backup.py:181). Local time timestamps in backups are confusing in multi-timezone deployments.

9. **Consider adding `SELECT ... FOR UPDATE`** or optimistic concurrency in `_update_delivery_status` if concurrency is ever increased beyond 1.

10. **Document the `_send_email_with_retry` default parameter vs. newsletter override** — the email function defaults to `max_retries=3` but newsletter always passes `max_retries=5`.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | high | Fix celery-tasks.md error handling table: `send_newsletter_task` does NOT call `self.retry()` — document actual behavior (returns False on failure, Celery auto-retry on uncaught exceptions only) | docs |
| 2 | high | Remove duplicate `deliver_single_webhook_task` section in celery-tasks.md (lines 79-100) | docs |
| 3 | high | Document that `send_newsletter_task` does NOT check `NEWSLETTER_MAX_RETRY_ATTEMPTS` (unlike scheduler path) and explain why | docs |
| 4 | medium | Fix scheduler.md log message template to match actual code (`"Could not acquire lock %s, skipping run"`) | docs |
| 5 | medium | Document that `_update_delivery_status` correctness depends on `--concurrency=1` and the race condition risk if concurrency is increased | docs |
| 6 | medium | Document or remove `ENABLE_SCHEDULER` config key (currently dead code, never read) | docs/source |
| 7 | medium | Document the `_send_email_with_retry` default `max_retries=3` vs. newsletter override to 5 | docs |
| 8 | low | Fix `send_newsletter_task` logging at tasks.py:186 to not rely on loop variable `post` (use a different variable or log max attempts) | source |
| 9 | low | Use `datetime.now(timezone.utc)` in `create_backup()` (backup.py:49) for consistency with `run_daily_backup` (backup.py:181) | source |
| 10 | low | Document that Celery worker runs with `--concurrency=1` and `worker_prefetch_multiplier=1` as production requirements (currently only in docker-compose.yml comment) | docs |
