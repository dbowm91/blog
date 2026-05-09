# Tasks Architecture Review

**Review Date:** 2026-05-09
**Files Reviewed:**
- `architecture/tasks/celery-tasks.md`
- `architecture/tasks/scheduler.md`
- `architecture/tasks/overview.md`
- `app/tasks.py`
- `app/scheduler.py`
- `app/services/backup.py`

---

## Verified Claims

### Celery Tasks (`app/tasks.py`)

| Task | Queue | Verified | Location |
|------|-------|----------|----------|
| `generate_image_variants` | `images` | ✅ | `app/tasks.py:29` |
| `send_newsletter_task` | `newsletter` | ✅ | `app/tasks.py:129` |
| `deliver_webhook_task` | `webhooks` | ✅ | `app/tasks.py:192` |
| `send_confirmation_task` | `email` | ✅ | `app/tasks.py:264` |
| `send_password_reset_task` | `email` | ✅ | `app/tasks.py:285` |
| `run_backup_task` | `backup` | ✅ | `app/tasks.py:306` |

**Retry Policy Verified:**
- `max_retries=3` for all tasks except `run_backup_task` which uses `max_retries=2` ✅
- `retry_backoff=True` (exponential backoff) on all tasks ✅
- `time_limit=600, soft_time_limit=540` on `send_newsletter_task` ✅

### APScheduler Jobs (`app/scheduler.py`)

| Job | Schedule | Verified | Location |
|-----|----------|----------|----------|
| `send_daily_newsletter` | Daily at `NEWSLETTER_SEND_TIME` | ✅ | `app/scheduler.py:272-278` |
| `cleanup_expired_subscribers` | `minute="*/5"` | ✅ | `app/scheduler.py:279-285` |
| `publish_scheduled_posts` | `minute="*/5"` | ✅ | `app/scheduler.py:286-292` |
| `run_daily_backup` | `hour=2, minute=0` | ✅ | `app/scheduler.py:293-299` |

### Queue Routing (Verified Line Numbers)

| Queue | Tasks | Location |
|-------|-------|----------|
| `images` | `generate_image_variants` | `app/tasks.py:29` |
| `newsletter` | `send_newsletter_task` | `app/tasks.py:129` |
| `webhooks` | `deliver_webhook_task` | `app/tasks.py:192` |
| `email` | `send_confirmation_task`, `send_password_reset_task` | `app/tasks.py:264,285` |
| `backup` | `run_backup_task` | `app/tasks.py:306` |

---

## Discrepancies

### 1. `send_newsletter_task` Signature Mismatch
**Documented in `celery-tasks.md:36`:**
```python
def send_newsletter_task(self, post_ids: List[int]) -> bool:
```

**Actual in `app/tasks.py:130`:**
```python
def send_newsletter_task(self: Any, post_ids: List[int]) -> bool:
```
The `self` parameter in the docstring should be `self: Any` for consistency with actual implementation.

### 2. Queue Routing Line Numbers Inaccurate
**Documented in `scheduler.md:48-52`:**
```
| `images`    | Image processing     | `app/tasks.py:29`        | ✅ Correct
| `newsletter` | Newsletter delivery  | `app/tasks.py:129`       | ✅ Correct
| `webhooks`  | Webhook delivery     | `app/tasks.py:192`       | ✅ Correct
| `email`     | Transactional email  | `app/tasks.py:264,285`   | ✅ Correct
| `backup`    | Backup tasks         | `app/tasks.py:306`       | ✅ Correct
```

Actually the document has the correct line numbers! No discrepancy here.

### 3. APScheduler Job Descriptions Missing Implementation Details

The `scheduler.md` documents job behavior at a high level but omits important implementation details:

**`send_daily_newsletter`**: Document states it "Triggers `send_newsletter_task` Celery task" but actual implementation (`app/scheduler.py:70-140`) calls `send_newsletter()` directly — it does NOT trigger a Celery task.

**`run_daily_backup`**: Document correctly notes it uses `run_daily_backup()` service function and creates `backup_*.db` files (line 40). However, the document is internally inconsistent — line 36 says "Runs daily at 02:00" which is correct, but the description doesn't emphasize that this is DIFFERENT from the Celery `run_backup_task` which creates `blog_*.db` files with compression/encryption.

---

## Bugs Found

### Bug 1: Newsletter Sender Bypasses Queue
**Severity:** Medium
**Location:** `app/scheduler.py:70-140` (`send_daily_newsletter`)

The APScheduler's `send_daily_newsletter` calls `send_newsletter()` directly from `app.email`, not via the Celery task `send_newsletter_task`. This means:

1. Newsletter sending runs synchronously in the scheduler process
2. No Redis/Celery infrastructure utilized for this critical path
3. If newsletter sending is slow, it blocks other scheduler jobs
4. No timeout protection (Celery task has `time_limit=600`)

**Code Reference:** `app/scheduler.py:120` — `success = send_newsletter(list(posts), subscribers, subscriber_count)`

**Recommendation:** Either:
- Document this clearly (it's a deliberate design choice)
- Or refactor to use `send_newsletter_task.delay(post_ids)` for consistency

### Bug 2: Cleanup Lock Timeout Could Block Forever
**Severity:** Low
**Location:** `app/scheduler.py:71-76`

```python
lock = FileLock(lock_path, timeout=0)
try:
    lock.acquire()
except FileLockTimeout:
    return
```

`timeout=0` means if lock is held by another process (stuck/crashed), this instance immediately returns without doing work. However, if another process acquires the lock and hangs (doesn't release), this process silently skips — no warning logged.

**Recommendation:** Log a warning when lock acquisition fails so operators know cleanup is not happening.

### Bug 3: Mixed Import Style
**Severity:** Low (Code quality)
**Location:** `app/tasks.py:37-38`

```python
from PIL import Image
import os
```

Local import of `os` after global imports. The `os` module is already imported at line 7. This is a duplicate/unnecessary import.

---

## Security Considerations

### 1. Webhook SSRF Protection — Verified
`deliver_webhook_task` at `app/tasks.py:221-225` correctly uses `is_safe_webhook_url()` for SSRF protection.

### 2. HMAC Signing — Verified
`deliver_webhook_task` at `app/tasks.py:235-240` signs payloads with HMAC-SHA256 via `_sign_webhook_payload()`.

### 3. Webhook Secret Decryption — Verified
`app/tasks.py:228-233` handles both encrypted and plaintext webhook secrets.

---

## Improvement Recommendations

### Priority 1: Document Newsletter Sync vs Async

**File:** `architecture/tasks/scheduler.md`

Add note after `send_daily_newsletter` description:
```
Note: Unlike other jobs, send_daily_newsletter calls send_newsletter()
directly (synchronous) rather than queuing send_newsletter_task (async).
This is a deliberate design choice to ensure newsletter sends complete
before the scheduler job returns.
```

### Priority 2: Fix Celery Task Docstring

**File:** `architecture/tasks/celery-tasks.md:36`

Change:
```python
def send_newsletter_task(self, post_ids: List[int]) -> bool:
```
To:
```python
def send_newsletter_task(self: Any, post_ids: List[int]) -> bool:
```

### Priority 3: Remove Duplicate Import

**File:** `app/tasks.py:37`

Remove `import os` from line 37 since `os` is already imported at line 7.

### Priority 4: Add Lock Warning Logs

**File:** `app/scheduler.py:75,149,193,249`

Change:
```python
except FileLockTimeout:
    return
```
To:
```python
except FileLockTimeout:
    app.logger.warning("Could not acquire lock %s, skipping run", lock_path)
    return
```

Apply to all four lock acquisitions:
- Line 75 (`send_daily_newsletter`)
- Line 149 (`cleanup_expired_subscribers`)
- Line 193 (`publish_scheduled_posts`)
- Line 249 (`run_daily_backup`)

### Priority 5: Clarify Backup Naming Distinction

**File:** `architecture/tasks/scheduler.md:40`

Enhance the note:
```markdown
Note: This scheduler job uses the `run_daily_backup()` service function
which creates unencrypted, uncompressed `backup_*.db` files. For
encrypted/compressed backups, use the Celery task `run_backup_task`
which calls `create_backup()` with `blog_*.db` naming. These serve
different purposes: scheduler provides frequent unencrypted backups
while Celery provides encrypted/compressed disaster recovery.
```

---

## Summary

| Category | Count |
|----------|-------|
| Verified Claims | 17 |
| Discrepancies | 2 (minor) |
| Bugs | 3 (low-medium severity) |
| Recommendations | 5 |

**Overall Assessment:** The architecture documents are accurate and well-structured. The main issue is that `send_daily_newsletter` bypasses the Celery queue — this should be explicitly documented as a design decision. All other findings are minor documentation corrections or low-priority code quality improvements.