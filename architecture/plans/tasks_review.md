# Tasks Module Architecture Review

**Review Date:** 2026-05-09  
**Reviewer:** tasks_reviewer  
**Files Reviewed:**
- `architecture/tasks/overview.md`
- `architecture/tasks/celery-tasks.md`
- `architecture/tasks/scheduler.md`
- `app/tasks.py`
- `app/scheduler.py`
- `AGENTS.md`

---

## 1. Verified Accurate Claims

### APScheduler Job Schedules (AGENTS.md + scheduler.py)
| Claim | Status |
|-------|--------|
| `cleanup_expired_subscribers` runs every 5 minutes (`minute="*/5"`) | VERIFIED |
| `run_daily_backup` runs at 02:00 (`hour=2, minute=0`) | VERIFIED |
| `publish_scheduled_posts` runs every 5 minutes (`minute="*/5"`) | VERIFIED |

### Celery Queue Names (AGENTS.md + tasks.py)
| Claim | Status |
|-------|--------|
| Queue `images` for `generate_image_variants` (line 29) | VERIFIED |
| Queue `newsletter` for `send_newsletter_task` (line 129) | VERIFIED |
| Queue `webhooks` for `deliver_webhook_task` (line 192) | VERIFIED |
| Queue `email` for `send_confirmation_task` (line 264) | VERIFIED |
| Queue `email` for `send_password_reset_task` (line 285) | VERIFIED |
| Queue `backup` for `run_backup_task` (line 306) | VERIFIED |

### FileLock Mechanism (scheduler.py)
- All four APScheduler jobs use `FileLock` with lock files in `app.instance_path`:
  - `newsletter.lock` for `send_daily_newsletter`
  - `cleanup.lock` for `cleanup_expired_subscribers`
  - `scheduled.lock` for `publish_scheduled_posts`
  - `backup.lock` for `run_daily_backup`
- Lock timeout is 0 (non-blocking) - if lock cannot be acquired, function returns immediately
- **Multi-worker limitation documented correctly** in scheduler.py docstring (lines 1-9)

### Celery Task Retry Configuration
| Claim | Status |
|-------|--------|
| `max_retries=3` for most tasks | VERIFIED (lines 29, 129, 192, 264, 285) |
| `max_retries=2` for `run_backup_task` | VERIFIED (line 306) |
| `retry_backoff=True` (exponential backoff) | VERIFIED |

### Newsletter Queue Time Limits
- `send_newsletter_task` has `time_limit=600, soft_time_limit=540` (line 129) - **VERIFIED**

### Task Signatures
| Task | Signature | Status |
|------|-----------|--------|
| `generate_image_variants` | `(self, filename: str) -> bool` | VERIFIED |
| `send_newsletter_task` | `(self, post_ids: List[int]) -> bool` | VERIFIED |
| `deliver_webhook_task` | `(self, webhook_event_id: int) -> bool` | VERIFIED |
| `send_confirmation_task` | `(self, subscriber_id: int) -> bool` | VERIFIED |
| `send_password_reset_task` | `(self, user_id: int, token: str) -> bool` | VERIFIED |
| `run_backup_task` | `(self) -> bool` | VERIFIED |

---

## 2. Inaccurate/Outdated Claims

### Incorrect: Backup Service Documentation Claims Encryption Type
**Location:** `architecture/services/backup.md` line 8 and line 33

**Issue:** Documentation says "GPG encryption" but `app/services/backup.py` uses AES-256-GCM.

**Correction:** The parameter description should say "AES-256-GCM encryption" not "GPG encryption".

### Missing: `run_backup_task` Calls `create_backup` with Specific Parameters
**Location:** `architecture/tasks/celery-tasks.md` line 84

**Issue:** Documentation says "Runs database backup asynchronously" but does not specify that:
- It uses `compress=True`
- It uses `keep=7`
- It uses `encrypt=False`
- It creates `blog_*.db` files (not `backup_*.db`)

**Correction:** The Celery `run_backup_task` creates compressed, unencrypted `blog_YYYYMMDD_HHMMSS.db.gz` files via `create_backup()`.

### Incorrect: APScheduler "Queue Routing" Section is Misleading
**Location:** `architecture/tasks/scheduler.md` lines 42-52

**Issue:** Table claims these are "Queue Routing" but APScheduler jobs do not use Celery queues - they are in-process jobs. The table correctly shows task definitions with their queues but the section title is misleading.

### Missing: `send_daily_newsletter` Runs Synchronously (Not Via Celery)
**Location:** `architecture/tasks/scheduler.md` line 19

**Issue:** Documentation says "Triggers `send_newsletter_task` Celery task" but actual implementation (scheduler.py lines 78-120) calls `send_newsletter()` directly synchronously.

**Correction:** APScheduler `send_daily_newsletter` runs synchronously, not via Celery. The Celery `send_newsletter_task` is used for manual/ad-hoc newsletter sends only.

---

## 3. Missing Documentation

### Missing: Two Distinct Backup Implementations
**Details:** AGENTS.md correctly notes this, but the architecture docs do not:

| Aspect | APScheduler `run_daily_backup` | Celery `run_backup_task` |
|--------|-------------------------------|--------------------------|
| File naming | `backup_*.db` | `blog_*.db` |
| Encryption | None | Optional (AES-256-GCM) |
| Compression | None | Optional (gzip) |
| Source | Calls `app.services.backup.run_daily_backup()` | Calls `app.services.backup.create_backup()` |

### Missing: `publish_scheduled_posts` FTS Sync and Tag Cache Invalidation
**Details:** The `publish_scheduled_posts` job (scheduler.py lines 186-234):
1. Publishes posts where `scheduled_publish_at <= now` and `published = False`
2. Syncs to FTS index via `sync_fts_batch()`
3. Invalidates tag cache via `invalidate_tag_cache()`

This detail is missing from `architecture/tasks/scheduler.md`.

### Missing: `send_daily_newsletter` Retry Logic
**Details:** The APScheduler `send_daily_newsletter` respects `NEWSLETTER_MAX_RETRY_ATTEMPTS` configuration and only selects posts where `newsletter_attempts < NEWSLETTER_MAX_RETRY_ATTEMPTS`. This is not documented.

### Missing: FileLock Usage and Lock File Paths
**Details:** Documentation does not mention:
- Lock file locations (`{instance_path}/newsletter.lock`, etc.)
- `timeout=0` behavior (non-blocking, silently skips if lock held)
- Implications for multi-worker deployments

### Missing: `run_backup_task` Return Value Semantics
**Details:** The Celery `run_backup_task` returns `result is not None` (tasks.py line 319). This means it returns `True` if a backup path is created, `False` otherwise. This behavior is not documented.

---

## 4. Potential Issues

### Issue 1: `run_backup_task` Has Bare `except Exception` Clause
**Location:** `app/tasks.py` lines 320-321

```python
except Exception as e:
    logger.error("Backup task failed: %s", e)
    return False
```

**Risk:** Catches ALL exceptions including `SystemExit`, `KeyboardInterrupt`. Should catch specific exceptions.

**Note:** AGENTS.md line 65 lists `app/tasks.py` as a "High-Risk Files (Error Handling)" file. This suggests the issue is known but not yet fixed.

### Issue 2: Lock File Race Condition - Silent Skip on Stale Locks
**Location:** `app/scheduler.py` lines 71-76

```python
lock = FileLock(lock_path, timeout=0)
try:
    lock.acquire()
except FileLockTimeout:
    return
```

**Risk:** With `timeout=0`, if the lock file exists (from a previous crashed process), the job silently skips. This could lead to missed newsletter sends or missed cleanup cycles if workers are restarted frequently.

**Recommendation:** Document this behavior as intentional for crash recovery, or add stale lock detection.

### Issue 3: Newsletter Task Uses Two Queries for Subscribers
**Location:** `app/tasks.py` lines 144-158

The newsletter task executes:
1. Count query for confirmed subscribers
2. Full select query for confirmed subscribers

**Risk:** Minor inefficiency. Could be optimized by fetching all subscribers once.

### Issue 4: No Distributed Coordination for Multi-Worker Deployments
**Location:** `app/scheduler.py` docstring (lines 3-8)

**Risk:** If deployed in a multi-container environment without external coordination (Redis, etcd), backup and newsletter jobs could run on all replicas simultaneously. The FileLock only works within a single machine.

**Recommendation:** This should be clearly flagged in deployment documentation.

### Issue 5: APScheduler Newsletter Sends Synchronously (Not Via Celery)
**Location:** `app/scheduler.py` lines 78-120 vs `architecture/tasks/scheduler.md` line 19

**Inconsistency:** Documentation claims APScheduler "Triggers `send_newsletter_task` Celery task" but it actually calls `send_newsletter()` directly. This is a significant accuracy issue.

---

## 5. Recommended Improvements

### Priority 1: Fix Documentation Errors

1. **Update `architecture/services/backup.md` line 33:**
   - Change "GPG encryption" to "AES-256-GCM encryption"

2. **Update `architecture/tasks/scheduler.md`:**
   - Fix line 19: `send_daily_newsletter` runs synchronously (does NOT queue Celery task)
   - Remove or rename "Queue Routing" section (APScheduler jobs don't use Celery queues)
   - Add FileLock documentation with lock file paths
   - Add backup implementation comparison table

3. **Update `architecture/tasks/celery-tasks.md`:**
   - Add parameter details for `run_backup_task` (compress=True, keep=7, encrypt=False)
   - Clarify file naming (`blog_*.db`)

### Priority 2: Code Quality Fixes

1. **Fix bare `except Exception` in `run_backup_task`** (`app/tasks.py:320`):
   ```python
   # Change from:
   except Exception as e:
   
   # To specific exceptions:
   except (OSError, IOError, RuntimeError) as e:
   ```

2. **Document `timeout=0` behavior** as intentional design decision for crash recovery scenarios.

### Priority 3: Enhanced Documentation

1. **Add multi-worker deployment considerations** to deployment docs
2. **Document `NEWSLETTER_MAX_RETRY_ATTEMPTS`** configuration
3. **Document FTS sync and tag cache invalidation** in `publish_scheduled_posts`
4. **Consider adding sequence diagram** for newsletter flow showing APScheduler vs Celery paths

---

## Summary

| Category | Count |
|----------|-------|
| Verified Accurate Claims | 14 |
| Inaccurate/Outdated Claims | 4 |
| Missing Documentation Items | 5 |
| Potential Issues | 5 |
| Recommended Improvements | 7 |

**Critical Finding:** The documentation inconsistently describes the newsletter sending flow - APScheduler documentation claims it "Triggers `send_newsletter_task` Celery task" but actual implementation calls `send_newsletter()` directly (synchronously). This is the most significant accuracy issue.

**Secondary Finding:** The two distinct backup implementations (`backup_*.db` vs `blog_*.db`) are correctly noted in AGENTS.md but not adequately documented in the architecture files, leading to potential confusion about which backup method to use.
