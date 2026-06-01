# Tasks Architecture Review

**Reviewed:** 2026-05-31
**Architecture Docs:** overview.md, celery-tasks.md, scheduler.md
**Source Files:** app/tasks.py, app/scheduler.py, app/celery_app.py

## Findings

### Verified Claims (Correct)

| Claim | Source | Status |
|-------|--------|--------|
| Celery queues: `images`, `newsletter`, `webhooks`, `email`, `backup` | `app/tasks.py:30,129,198,234,348,369,390` | ✅ Correct |
| APScheduler jobs: daily newsletter, cleanup, publish, backup | `app/scheduler.py:291-321` | ✅ Correct |
| Newsletter retry count = 5 (`NEWSLETTER_MAX_RETRY_ATTEMPTS`) | `app/config.py:118` (default 5) | ✅ Correct |
| `send_newsletter_task` has `time_limit=600, soft_time_limit=540` | `app/tasks.py:133-134` | ✅ Correct |
| `run_backup_task` has `max_retries=2` (not 3) | `app/tasks.py:390` | ✅ Correct |
| Celery global config: `task_time_limit=300, task_soft_time_limit=240` | `app/celery_app.py:27-28` | ✅ Correct |
| `worker_prefetch_multiplier=1` | `app/celery_app.py:29` | ✅ Correct |
| `task_acks_late=True` when Flask app available | `app/celery_app.py:35` | ✅ Correct |
| `task_reject_on_worker_lost=True` when Flask app available | `app/celery_app.py:36` | ✅ Correct |
| Scheduler uses FileLock with `timeout=0` | `app/scheduler.py:76,171,211,267` | ✅ Correct |
| Newsletter is conditional on `SMTP_HOST` | `app/scheduler.py:290` | ✅ Correct |
| `publish_scheduled_posts` rolls back on FTS failure | `app/scheduler.py:248-253` | ✅ Correct |
| Database session cleanup via `db.session.remove()` in finally blocks | `app/tasks.py:194,231,313,366,387,409` | ✅ Correct |
| Backup uses `compress=True, keep=7, encrypt=False` | `app/tasks.py:403` | ✅ Correct |
| All Celery tasks use `retry_backoff=True` | `app/tasks.py:30,129,198,234,348,369,390` | ✅ Correct |

### Discrepancies (Doc vs Code)

1. **`generate_image_variants` retry config is misleading**
   - Doc (`celery-tasks.md:20`): Shows `max_retries=3` in the signature
   - Code (`app/tasks.py:30`): `max_retries=3` is configured, but the task **never calls `self.retry()`** — it catches all exceptions and returns `False`
   - The doc's "Non-Retry Behavior" section (line 31) correctly explains this, but showing `max_retries=3` in the signature block is confusing since it's dead config
   - **Impact**: Low — docs do explain the behavior, but the signature block creates a misleading impression

2. **`run_backup_task` retry config is dead**
   - Doc (`celery-tasks.md:102`): Shows `max_retries=2` in signature
   - Code (`app/tasks.py:390`): `max_retries=2` configured, but task catches all exceptions and returns `False` — never calls `self.retry()`
   - Doc's "Non-Retry Behavior" section (line 112) correctly explains this
   - **Impact**: Low — same misleading signature pattern

3. **Scheduler backup doc description is vague**
   - Doc (`scheduler.md:53`): "Creates backup using inline `run_daily_backup()` service function"
   - Code (`app/scheduler.py:264`): Imports and calls `app.services.backup.run_daily_backup` — not "inline"
   - **Impact**: Low — misleading wording

4. **Doc line number references are slightly stale**
   - `celery-tasks.md:130`: References `app/celery_app.py:20-31` for config — actual config spans lines 20-31 ✅
   - `scheduler.md:64-68`: References `app/tasks.py:31,137,195,345,366,387` — actual lines are 30,129,198,348,369,390 (off by 1 on each due to decorators)
   - **Impact**: Very low — off-by-one on line references

### Missing Documentation

1. **No documentation of `generate_image_variants` S3 upload loop duplication**
   - `app/tasks.py:87-103` and `app/tasks.py:106-118` have near-identical loops for generating and uploading variants. The generation loop (87-103) is nested inside a tempdir context, and then a separate upload loop (106-118) iterates again. This is correct but could benefit from documentation explaining the two-pass approach (generate locally, then upload).

2. **No documentation of `deliver_single_webhook_task` error handling flow**
   - The task has 3 distinct error paths: SSRF block (`app/tasks.py:258-261`), missing secret (`app/tasks.py:266-270`), and request failure (`app/tasks.py:298-301`). All increment `delivery_attempts` and `failed_deliveries` before the retry or return. This is not documented in `celery-tasks.md`.

3. **No documentation of `_update_delivery_status` logic**
   - `app/tasks.py:316-345` implements the delivery status determination logic (delivered/failed/partial_failure). The function queries all enabled webhooks to determine total count and compares against completed count. This function is not documented in the architecture docs.

4. **`send_newsletter_task` subscriber query returns a `ResultProxy`**
   - `app/tasks.py:169`: `subscribers = db.session.execute(stmt).scalars()` returns a lazy scalars result. This is passed directly to `send_newsletter()`. If `send_newsletter()` iterates multiple times or the session is closed, this could cause issues. No documentation of this behavior.

5. **No docs on `generate_image_variants` returning `False` on missing file**
   - `app/tasks.py:48-49`: Returns `False` if the file doesn't exist locally. Not documented.

6. **Missing `__all__` documentation**
   - `app/tasks.py:19-27` defines `__all__` but the architecture docs don't mention the public API surface.

### Potential Bugs / Concerns

1. **`send_newsletter_task` — UnboundLocalError risk** ⚠️
   - **Location**: `app/tasks.py:190`
   - `post.newsletter_attempts` references the loop variable `post` from the `for post in posts` loop (line 177-179). If `posts` is empty (unlikely but possible if all posts were deleted between the query at line 149 and this point), the variable `post` would be unbound.
   - **Impact**: Low probability, but would cause `UnboundLocalError` in the warning log.
   - **Severity**: Low

2. **`generate_image_variants` — ClientError/BotoCoreError caught outside S3 block**
   - **Location**: `app/tasks.py:121`
   - The `except (ClientError, BotoCoreError)` handler catches exceptions from the entire try block, but these exceptions can only occur inside the S3 branch (`app/tasks.py:71-118`). If `ClientError` were raised outside the S3 branch (impossible in practice), it would be silently caught. Not a real bug but structurally misleading.
   - **Impact**: None in practice
   - **Severity**: Informational

3. **`_update_delivery_status` — Race condition with `--concurrency=1` dependency**
   - **Location**: `app/tasks.py:316-345`
   - The function reads and writes `event.successful_deliveries`, `event.failed_deliveries`, and `event.delivery_status` without any locking. Multiple concurrent `deliver_single_webhook_task` invocations for the same event could race on these fields.
   - **Doc reference**: `scheduler.md:81` documents this dependency on `--concurrency=1`.
   - **Impact**: Race condition if concurrency > 1. Currently mitigated by `--concurrency=1` requirement.
   - **Severity**: Medium (operational constraint)

4. **`deliver_webhook_task` — Dispatches but doesn't wait for results**
   - **Location**: `app/tasks.py:227`
   - Uses `.delay()` which is fire-and-forget. The parent task returns `True` before any individual webhook deliveries complete. If all child tasks fail, the parent still reports success.
   - **Impact**: Parent task success doesn't indicate webhook delivery success. This is by design (dispatch pattern) but could confuse monitoring.
   - **Severity**: Informational

5. **`send_newsletter_task` — No explicit retry, but Celery auto-retries on uncaught exceptions**
   - **Location**: `app/tasks.py:129-195`
   - The task never calls `self.retry()`. However, if an uncaught exception occurs (e.g., database connection error), Celery will auto-retry up to `max_retries=3` with exponential backoff. The doc's error handling table (line 119) says "No (no explicit retry)" which is correct but doesn't mention implicit auto-retry.
   - **Impact**: Tasks may retry unexpectedly on transient DB errors.
   - **Severity**: Low

6. **`run_backup_task` — Dead `max_retries=2` config**
   - **Location**: `app/tasks.py:390`
   - `max_retries=2` is configured but the task catches all exceptions and returns `False` without calling `self.retry()`. The retry config has no effect.
   - **Impact**: Confusing but harmless.
   - **Severity**: Low

7. **APScheduler FileLock `timeout=0` race**
   - **Location**: `app/scheduler.py:76` (and similar for all jobs)
   - `timeout=0` means non-blocking: if two processes call `lock.acquire()` at the exact same nanosecond, one will succeed and one will fail. However, there's a TOCTOU gap between checking and using. In practice, this is fine for single-machine deployments.
   - **Impact**: Negligible for single-container deployments.
   - **Severity**: Informational

### Improvement Suggestions

1. **Remove dead `max_retries` from non-retrying tasks**
   - `generate_image_variants` and `run_backup_task` never call `self.retry()`. Remove `max_retries` and `retry_backoff` to avoid confusion, or add retry logic if retries are actually desired.

2. **Document `_update_delivery_status` function**
   - Add architecture docs explaining the delivery status determination logic and its dependency on `--concurrency=1`.

3. **Fix UnboundLocalError in `send_newsletter_task`**
   - Move the warning log outside the `else` block, or use a variable to track the last `newsletter_attempts` value during the loop.

4. **Add docstring to `_update_delivery_status` explaining the concurrency constraint**
   - The function should document that it requires `--concurrency=1` for correctness.

5. **Consider adding task-level metrics/logging**
   - Several tasks log on failure but not on success. Adding success logging would improve observability.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | Medium | Fix UnboundLocalError risk in `send_newsletter_task` (line 190) — `post` variable may be unbound if `posts` is empty | `app/tasks.py` |
| 2 | Medium | Document `_update_delivery_status` function and its `--concurrency=1` dependency | `architecture/tasks/celery-tasks.md` |
| 3 | Low | Remove dead `max_retries`/`retry_backoff` from `generate_image_variants` and `run_backup_task`, or add actual retry logic | `app/tasks.py` |
| 4 | Low | Fix stale line number references in `architecture/tasks/scheduler.md:64-68` (off by 1) | `architecture/tasks/scheduler.md` |
| 5 | Low | Fix misleading "inline" wording in scheduler backup doc (`scheduler.md:53`) | `architecture/tasks/scheduler.md` |
| 6 | Informational | Document `send_newsletter_task` subscriber query returning lazy `ResultProxy` | `architecture/tasks/celery-tasks.md` |
| 7 | Informational | Document the fire-and-forget dispatch pattern in `deliver_webhook_task` | `architecture/tasks/celery-tasks.md` |
