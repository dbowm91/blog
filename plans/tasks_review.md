# Task Architecture Review

Cross-reference of `architecture/tasks/` documentation against `app/tasks.py` and `app/scheduler.py`.

## celery-tasks.md

### Verified Claims

| Claim | Status |
|-------|--------|
| Queue names (`images`, `newsletter`, `webhooks`, `email`, `backup`) | ✅ Verified |
| `generate_image_variants` at line 31 | ✅ Verified |
| `send_newsletter_task` with `time_limit=600, soft_time_limit=540` | ✅ Verified |
| `deliver_webhook_task` with SSRF protection and HMAC signing | ✅ Verified |
| `run_backup_task` with `max_retries=2`, `compress=True`, `keep=7`, `encrypt=False` | ✅ Verified |
| Retry policy `retry_backoff=True` for all tasks | ✅ Verified |

### Discrepancies

**1. Missing `max_retries` on email tasks**
- **Doc (lines 62, 70):** Claims `max_retries=3` for `send_confirmation_task` and `send_password_reset_task`
- **Code (lines 267, 289):** No `max_retries` parameter
```python
# Documented:
@shared_task(bind=True, max_retries=3, retry_backoff=True, queue='email')

# Actual:
@shared_task(bind=True, retry_backoff=True, queue='email')  # missing max_retries
```

**2. Queue line number references are stale**
- **Doc (line 61):** "email | `app/tasks.py:262,283`"
- **Actual:** email tasks are at lines 267 and 289
- **Doc (line 61):** "backup | `app/tasks.py:304`"
- **Actual:** backup task is at line 311

### Bugs Found

**1. Email tasks silently swallow exceptions without retrying**
- `app/tasks.py:282-284` and `app/tasks.py:304-306` catch Exception and return `False`
- Without `max_retries`, this means failure after one attempt
- With `max_retries` missing entirely, there's no retry mechanism
- The `retry_backoff=True` setting is useless without `max_retries` and `self.retry()`

**2. Line numbers in documentation will become stale again**

## scheduler.md

### Verified Claims

| Claim | Status |
|-------|--------|
| `send_daily_newsletter` runs at `NEWSLETTER_SEND_TIME` | ✅ Verified |
| `cleanup_expired_subscribers` runs every 5 minutes (`minute="*/5"`) | ✅ Verified |
| `publish_scheduled_posts` runs every 5 minutes (`minute="*/5"`) | ✅ Verified |
| `run_daily_backup` runs at 02:00 (`hour=2, minute=0`) | ✅ Verified |
| FileLock with `timeout=0` for all jobs | ✅ Verified |
| Lock file paths documented correctly | ✅ Verified |
| APScheduler disabled when SMTP not configured | ✅ Verified (line 292) |
| Multi-worker FileLock limitation documented | ✅ Verified |

### Discrepancies

**1. Stale line number references in queue routing table**
- **Doc (lines 59-61):** References `app/tasks.py:262,283` for email and `app/tasks.py:304` for backup
- **Actual:** Tasks are at lines 267, 289, and 311

**2. Backup naming description incomplete**
- **Doc (line 49):** Mentions `blog_*.db` naming for scheduler backup
- **Doc (line 88 in celery-tasks.md):** Claims `blog_YYYYMMDD_HHMMSS.db.gz` for compressed backup
- **Actual:** Both use `create_backup()` which may produce different naming

### Bugs Found

**1. Dead code - unused constant**
- `app/scheduler.py:261` defines `BACKUP_RETENTION_COUNT = 7`
- Never used anywhere in the file

### Improvement Opportunities

**1. Update line number references or use dynamic references**
- Queue routing table line numbers are brittle and will become stale
- Consider removing specific line numbers or noting they may be outdated

**2. Add `max_retries` to email tasks for consistency**
- All other tasks have `max_retries=3` (or 2 for backup)
- Email tasks should have explicit `max_retries=3` if retry behavior is desired

**3. Consider removing dead `BACKUP_RETENTION_COUNT` constant**
- Or use it if retention cleanup is intended but not implemented

**4. Document the actual backup file naming convention**
- Verify what naming `create_backup()` produces vs what documentation claims

## overview.md

### Verified Claims

| Claim | Status |
|-------|--------|
| Two systems: Celery and APScheduler | ✅ Verified |
| Files: `app/celery_app.py`, `app/tasks.py`, `app/scheduler.py` | ✅ Verified |

### Discrepancies

- None found - this is a high-level overview that remains accurate

## Summary

### Priority: Medium

**Key Issues:**
1. Email tasks (`send_confirmation_task`, `send_password_reset_task`) missing `max_retries=3` despite documentation claiming it exists
2. Email tasks silently fail without retrying (catch Exception, return False, no `self.retry()`)
3. Line number references in docs are already stale (current code has shifted ~5-7 lines)
4. Dead code constant `BACKUP_RETENTION_COUNT` in scheduler.py

**Impact:**
- Email tasks may fail permanently on first error, with no retry mechanism
- Documentation does not match implementation for email task retry config

**Recommended Actions:**
1. Add `max_retries=3` to `send_confirmation_task` and `send_password_reset_task` (or clarify if retries are intentionally disabled)
2. Update documentation line numbers or remove them entirely
3. Remove dead `BACKUP_RETENTION_COUNT` constant or implement retention cleanup
4. Verify actual backup file naming and update documentation accordingly