# Tasks Architecture Review

**Reviewed:** 2026-06-02
**Architecture Docs:** `architecture/tasks/overview.md`, `architecture/tasks/celery-tasks.md`, `architecture/tasks/scheduler.md`
**Source Files:** `app/tasks.py`, `app/scheduler.py`, `app/celery_app.py`

## Findings

### Verified Claims (Correct)
- Email retry count is **5** (not 3) — `NEWSLETTER_MAX_RETRY_ATTEMPTS` defaults to 5 in `app/config.py:120`, used by `send_newsletter()` via `_send_email_with_retry(max_retries=NEWSLETTER_MAX_RETRY_ATTEMPTS)` at `app/email.py:210`
- `worker_prefetch_multiplier=1` at `app/celery_app.py:29`
- `worker_max_tasks_per_child=100` at `app/celery_app.py:30`
- `task_acks_late=True` and `task_reject_on_worker_lost=True` when app context is available (`app/celery_app.py:34-37`)
- APScheduler job schedules: `cleanup_expired_subscribers` and `publish_scheduled_posts` use `minute="*/5"` (`app/scheduler.py:303,310`)
- `run_daily_backup` runs at `hour=2, minute=0` (`app/scheduler.py:317`)
- FileLock with `timeout=0` for all scheduler jobs
- Queue names: `images`, `newsletter`, `webhooks`, `email`, `backup` (verified in `app/tasks.py` decorators)
- `_update_delivery_status()` logic (lines 318-347) matches doc description exactly
- `deliver_webhook_task` dispatches via `.delay()` at `app/tasks.py:229`
- `deliver_single_webhook_task` raises `self.retry(exc=e)` on HTTP errors at `app/tasks.py:299,303`
- `send_confirmation_task` and `send_password_reset_task` have `max_retries=3, retry_backoff=True, queue="email"`
- Docker worker uses `--concurrency=1` (`docker-compose.yml:66`)
- `run_backup_task` uses `compress=True, keep=7, encrypt=False` as documented

### Discrepancies (Doc vs Code)

#### 1. `generate_image_variants` decorator is incorrectly documented
- **Doc** (`architecture/tasks/celery-tasks.md:20`): `@shared_task(bind=True, max_retries=3, retry_backoff=True, queue='images')`
- **Actual** (`app/tasks.py:30`): `@shared_task(bind=True, queue="images")`
- **Impact**: The doc claims `max_retries=3, retry_backoff=True` but the task has NO retry configuration at all. It will never retry on failure. The error behavior (returns `False`) is correct in the doc's error table, but the decorator signature is wrong.

#### 2. `run_backup_task` decorator is incorrectly documented
- **Doc** (`architecture/tasks/celery-tasks.md:104`): `@shared_task(bind=True, max_retries=2, retry_backoff=True, queue='backup')`
- **Actual** (`app/tasks.py:392`): `@shared_task(bind=True, queue="backup")`
- **Impact**: The doc claims `max_retries=2, retry_backoff=True` but the task has NO retry configuration. It will never retry on failure. Error behavior in the doc is correct (returns `False`), but decorator is wrong.

#### 3. `send_newsletter_task` retry configuration is documented as "No (no explicit retry)" but has `max_retries=3`
- **Doc** (`architecture/tasks/celery-tasks.md:139`): Error table says "Returns `False` on send failure; Celery auto-retry only on uncaught exceptions" with "No (no explicit retry)"
- **Doc** (`architecture/tasks/celery-tasks.md:176-180`): Retry Policy section says `max_retries=3` for tasks (2 for backup)
- **Actual** (`app/tasks.py:129-136`): `@shared_task(bind=True, max_retries=3, retry_backoff=True, ...)`
- **Impact**: The `max_retries=3` is set but **never triggered** because `send_newsletter()` returns `False` (not `None`) on failure — it never raises an exception. Celery's automatic retry only fires on raised exceptions. So the `max_retries=3` is effectively dead code. The doc correctly describes the behavior (no actual retries occur) but incorrectly says "no explicit retry" when there IS explicit retry config that simply doesn't work.

#### 4. Line references in Queue Reference table
- `send_newsletter_task` — doc says `app/tasks.py:137`, actual is `129` (off by 8)
- `generate_image_variants` — doc says `app/tasks.py:31`, actual is `30` (off by 1)
- Other line references match correctly

#### 5. Missing `db.session.remove()` in `generate_image_variants` and `run_backup_task`
- **Doc** (`architecture/tasks/celery-tasks.md:200`): Lists tasks using `db.session.remove()` pattern: `send_newsletter_task`, `deliver_webhook_task`, `deliver_single_webhook_task`, `send_confirmation_task`, `send_password_reset_task`, `run_backup_task`
- **Actual**: `run_backup_task` (`app/tasks.py:392-411`) has NO `db.session.remove()` in its finally block (it doesn't even have a try/finally with db.session)
- **Actual**: `generate_image_variants` (`app/tasks.py:30-127`) also lacks `db.session.remove()`
- **Impact**: These two tasks don't use `db.session.remove()` pattern. The doc's error table (which says "Returns `False`" for both) is correct, but the session management section is inaccurate.

### Missing Documentation

1. **`generate_image_variants` non-retry behavior is intentional but undocumented**: The code catches `ClientError, BotoCoreError` and `SQLAlchemyError, OSError, ImportError` at lines 121-126, logs errors, and returns `False` without calling `self.retry()`. This is intentional (non-critical task) but the decorator doesn't reflect this.

2. **`send_newsletter_task` `max_retries=3` is ineffective**: The `max_retries=3` is configured but never triggered because the wrapped function doesn't raise exceptions. This dead configuration should be documented.

3. **`send_newsletter_task` increments `newsletter_attempts` without bound**: When `send_newsletter()` returns `False`, the task increments `newsletter_attempts` without checking `NEWSLETTER_MAX_RETRY_ATTEMPTS`. Since Celery retries never fire, `newsletter_attempts` can grow unbounded for persistently failing posts. The scheduler's query at `app/scheduler.py:118` filters `newsletter_attempts < NEWSLETTER_MAX_RETRY_ATTEMPTS`, so posts with exhausted attempts are excluded from future scheduler runs. But the Celery task's unbounded increment is not documented.

4. **S3 memory usage in `generate_image_variants`**: The S3 path loads entire file into memory via `storage.load(filename)` then writes to temp file. Large images could cause memory issues. Not documented.

5. **`_update_delivery_status` concurrency requirement**: While the doc mentions `--concurrency=1` requirement, the code itself has no enforcement. If someone changes docker-compose, the race condition would silently introduce incorrect delivery counts.

### Potential Bugs / Concerns

#### Bug 1: `send_newsletter_task` has dead retry configuration
- **Location**: `app/tasks.py:129-136`
- **Issue**: `max_retries=3, retry_backoff=True` is configured but `send_newsletter()` returns `False` on failure, never raising an exception. Celery's automatic retry only fires on raised exceptions.
- **Expected**: If retry is desired, `send_newsletter()` should raise an exception on failure instead of returning `False`. Or the task should check the return value and call `self.retry()` explicitly.
- **Current behavior**: `send_newsletter_task` calls `send_newsletter()`, and if it returns `False`, the task returns `False` immediately with no retry. The `max_retries=3` in the decorator is never used.

#### Bug 2: Unbounded `newsletter_attempts` in `send_newsletter_task`
- **Location**: `app/tasks.py:183-188`
- **Issue**: On failure, the task increments `newsletter_attempts` without any upper bound check. There's no `if post.newsletter_attempts < NEWSLETTER_MAX_RETRY_ATTEMPTS` guard here (unlike the scheduler at `app/scheduler.py:118`).
- **Scenario**: If an admin repeatedly triggers manual newsletter sends for a post that always fails, `newsletter_attempts` keeps incrementing past `NEWSLETTER_MAX_RETRY_ATTEMPTS`. The scheduler will exclude it (good), but the Celery task doesn't know about the limit.
- **Not a critical bug** because the scheduler path handles this correctly, but it's inconsistent.

#### Bug 3: `_update_delivery_status` relies on external concurrency enforcement
- **Location**: `app/tasks.py:318-347`
- **Issue**: The code has no mechanism to enforce `--concurrency=1` on the webhooks queue. If `docker-compose.yml` is changed to `--concurrency=2+`, concurrent calls to `db.session.commit()` on the same `WebhookEvent` could cause lost updates to `successful_deliveries` and `failed_deliveries`.
- **Mitigation**: Documented in scheduler.md line 81-82 and celery-tasks.md line 132
- **Concern**: Enforcement is solely at the deployment config level, not code level. No runtime check or warning.

#### Bug 4: `generate_image_variants` S3 path loads entire file into memory
- **Location**: `app/tasks.py:78`
- **Code**: `file_data = storage.load(filename)` followed by `with open(tmp_path, "wb") as f: f.write(file_data)`
- **Issue**: For very large image files (e.g., 50MB uncompressed), this loads the entire file into memory before writing to disk. Could cause memory pressure on worker.
- **Not a critical bug** for typical image sizes, but an edge case.

#### Bug 5: `deliver_webhook_task` early return doesn't update delivery status
- **Location**: `app/tasks.py:213-214`
- **Code**: `if not event or event.delivered: return False`
- **Issue**: If the event is already delivered or doesn't exist, the task returns `False` without setting `event.delivered = True` or `delivery_status`. This is a minor inconsistency — subsequent calls would keep returning `False`.
- **Not critical** because this is an edge case (event already processed).

### Improvement Suggestions

1. **Add explicit retry logic to `send_newsletter_task`**:
   ```python
   if not success:
       raise self.retry(exc=Exception("Newsletter send failed"))
   ```
   Or remove the dead `max_retries=3` from the decorator if retry is not intended.

2. **Add `newsletter_attempts` upper bound check in `send_newsletter_task`**:
   ```python
   for post in posts:
       if post is not None:
           post.newsletter_attempts = min((post.newsletter_attempts or 0) + 1, NEWSLETTER_MAX_RETRY_ATTEMPTS)
   ```

3. **Add `db.session.remove()` to `generate_image_variants` and `run_backup_task`** for consistency, even though they don't use SQLAlchemy models heavily.

4. **Consider adding a runtime warning** in `_update_delivery_status` if `worker_concurrency > 1` is detected for the webhooks queue.

5. **Fix line references in architecture docs**:
   - `send_newsletter_task` line 137 → 129
   - `generate_image_variants` line 31 → 30

6. **Update `generate_image_variants` decorator** to accurately reflect behavior:
   ```python
   @shared_task(bind=True, queue="images")  # No retries — non-critical task
   ```
   Or add `max_retries=3, retry_backoff=True` if retries are desired.

7. **Update `run_backup_task` decorator** to accurately reflect behavior or add retry logic.

8. **Consider streaming S3 download** in `generate_image_variants` to avoid memory issues with large files.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|---------|
| 1 | high | Fix or remove dead `max_retries=3` in `send_newsletter_task` (`app/tasks.py:129-136`): either add explicit `self.retry()` call when `send_newsletter()` returns `False`, or remove the ineffective retry config | source |
| 2 | high | Fix line references in `architecture/tasks/celery-tasks.md`: `send_newsletter_task` at line 137 should be 129, `generate_image_variants` at line 31 should be 30 | docs |
| 3 | high | Correct `generate_image_variants` decorator documentation: task has NO `max_retries` or `retry_backoff` | docs |
| 4 | high | Correct `run_backup_task` decorator documentation: task has NO `max_retries=2` or `retry_backoff=True` | docs |
| 5 | medium | Add `newsletter_attempts` upper bound check in `send_newsletter_task` failure path (`app/tasks.py:186`) to match scheduler behavior | source |
| 6 | medium | Add `db.session.remove()` to `run_backup_task` and `generate_image_variants` for consistency with other tasks | source |
| 7 | medium | Update `celery-tasks.md` error table for `send_newsletter_task`: "No (no explicit retry)" is misleading since `max_retries=3` IS configured (even though ineffective) | docs |
| 8 | low | Add runtime concurrency check/warning in `_update_delivery_status()` for webhooks queue | source |
| 9 | low | Consider streaming S3 download in `generate_image_variants` for large files | source |
