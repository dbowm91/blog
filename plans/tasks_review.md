# Tasks Architecture Review - Improvement Plan

## Summary

Reviewed `architecture/tasks/` documents against implementation in `app/tasks.py`, `app/scheduler.py`, `app/email.py`, and `app/services/backup.py`.

**Overall:** Documentation is accurate with minor discrepancies requiring fixes.

---

## Discrepancies Found

### 1. Wrong Line Numbers in Documentation

**Files affected:**
- `architecture/tasks/celery-tasks.md:57-61`
- `architecture/tasks/scheduler.md:57-61`
- `architecture/infrastructure/webhooks.md:131-135`

**Issue:** Queue routing tables reference incorrect line numbers in `app/tasks.py`:

| Task | Doc Line | Actual Line |
|------|----------|-------------|
| `deliver_webhook_task` | 182 | 185 |
| `send_confirmation_task` | 262 | 265 |
| `send_password_reset_task` | 283 | 286 |
| `run_backup_task` | 304 | 307 |

**Fix:** Update all references to correct line numbers.

---

### 2. `send_confirmation_task` and `send_password_reset_task` Exception Handling

**Location:** `app/tasks.py:278-282` and `app/tasks.py:299-303`

**Issue:** Both tasks catch generic `Exception` and call `self.retry(exc=e)`, but this pattern is inconsistent with other tasks that simply return `False` on error (like `generate_image_variants` which catches `SQLAlchemyError, OSError, ImportError`).

The retry pattern is:
```python
except Exception as e:
    logger.error(f"Confirmation email failed: {e}")
    raise self.retry(exc=e)
```

**Problem:** The task decorator has `max_retries=3` and `retry_backoff=True`. When `self.retry()` is called, Celery will retry with exponential backoff. However, the task returns `bool`, and if max retries are exhausted, the task fails without returning anything explicit.

**Fix:** The current implementation is technically correct (exhausted retries will cause task to fail), but the error handling is inconsistent with other tasks. Consider aligning error handling patterns.

---

### 3. `run_backup_task` Does Not Support Encryption

**Documentation:** `architecture/tasks/celery-tasks.md:88` states backup files are "compressed, unencrypted".

**Actual Code:** `app/tasks.py:318`:
```python
result = create_backup(db_path, backup_dir, compress=True, keep=7, encrypt=False)
```

**Issue:** Documentation correctly notes `encrypt=False`, but `architecture/services/backup.md:55` states "For encrypted/compressed backups, use Celery task `run_backup_task`". This is misleading since `run_backup_task` does NOT support encryption (encrypt=False is hardcoded).

**Fix:** Clarify documentation to state that the Celery task does NOT support encryption - only compression. For encrypted backups, use `create_backup()` directly with `encrypt=True`.

---

### 4. `send_daily_newsletter` Correctly Skips Lock on Timeout

**Documentation:** `architecture/tasks/scheduler.md:17` states `timeout=0` causes skip if lock held.

**Actual Code:** `app/scheduler.py:72-77`:
```python
lock = FileLock(lock_path, timeout=0)
try:
    lock.acquire()
except FileLockTimeout:
    app.logger.warning("Could not acquire lock %s, skipping run", lock_path)
    return
```

**Issue:** None - documentation is correct.

---

### 5. APScheduler Job Schedules Verified Correct

| Job | Doc Schedule | Actual Schedule | Match |
|-----|--------------|-----------------|-------|
| `send_daily_newsletter` | Daily at configured time | `hour=hour, minute=minute` from NEWSLETTER_SEND_TIME | ✓ |
| `cleanup_expired_subscribers` | Every 5 minutes (`*/5`) | `CronTrigger(minute="*/5")` | ✓ |
| `publish_scheduled_posts` | Every 5 minutes (`*/5`) | `CronTrigger(minute="*/5")` | ✓ |
| `run_daily_backup` | Daily at 02:00 | `CronTrigger(hour=2, minute=0)` | ✓ |

---

### 6. Newsletter Scheduler Disabled Without SMTP_HOST

**Documentation:** `architecture/tasks/scheduler.md` notes newsletter disabled when SMTP not configured.

**Actual Code:** `app/scheduler.py:292-302`:
```python
if SMTP_HOST:
    # add newsletter job
else:
    app.logger.info("SMTP_HOST not configured; newsletter scheduler disabled")
```

**Issue:** None - documentation is correct.

---

## Missing Coverage

### 1. `generate_image_variants` Exception Handling

**Location:** `app/tasks.py:119-124`

**Issue:** Catches `ClientError, BotoCoreError` (S3), `SQLAlchemyError, OSError, ImportError` (general). Returns `False` on failure but does not retry. This is intentional but undocumented.

**Recommendation:** Document that image variant generation failures are not retried (non-critical operation).

---

### 2. `send_newsletter_task` Session Management

**Location:** `app/tasks.py:180-181`

**Issue:** Uses `db.session.remove()` in finally block. This pattern is correct for Celery tasks but undocumented.

**Recommendation:** Note that all Celery tasks using the database should call `db.session.remove()` in finally block.

---

## Potential Bugs

### 1. Newsletter Task Retry Exhaustion Logic

**Location:** `app/tasks.py:169-177`

**Issue:** When newsletter fails, the code increments `newsletter_attempts` but does NOT trigger a retry of the Celery task itself. The task simply returns `success` (False). This means:
1. The Celery task fails silently (returns False)
2. `newsletter_attempts` is incremented in the database
3. But no retry is scheduled

**Fix:** The task should call `self.retry()` on failure instead of returning False, or the caller should handle retry logic.

---

### 2. `run_backup_task` Hardcoded Parameters

**Location:** `app/tasks.py:318`

**Issue:** `encrypt=False` is hardcoded. There's no way to trigger an encrypted backup via this task. If encryption is needed, `create_backup()` must be called directly.

**Recommendation:** Either:
- Add `compress` and `encrypt` parameters to `run_backup_task`
- Or document clearly that this task never creates encrypted backups

---

## Recommended Fixes (Priority Order)

1. **High:** Update line numbers in documentation to match actual code
2. **High:** Clarify that `run_backup_task` does NOT support encryption
3. **Medium:** Document `db.session.remove()` pattern for Celery tasks
4. **Medium:** Document `generate_image_variants` non-retry behavior
5. **Low:** Align exception handling pattern in email tasks with other tasks

---

## Verification Checklist

- [x] Queue definitions match actual task decorators
- [x] Task schedules match APScheduler configuration
- [x] Retry logic matches decorator configuration
- [x] Lock file names match actual implementation
- [x] SMTP_HOST check documented correctly
- [x] Backup naming convention documented correctly
- [x] Newsletter retry attempts documented correctly