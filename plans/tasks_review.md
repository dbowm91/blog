# Tasks Module Architecture Review

**Review Date:** 2026-05-21
**Reviewer:** tasks_reviewer

---

## 1. Verified Accurate Claims

| Claim | Source | Line Reference |
|-------|--------|----------------|
| Celery queues: `images`, `newsletter`, `webhooks`, `email`, `backup` | `app/tasks.py` | Lines 31, 130, 182, 262, 283, 304 |
| `generate_image_variants` uses `queue='images'`, `max_retries=3` | `app/tasks.py:31` | ✅ Exact match |
| `send_newsletter_task` uses `queue='newsletter'`, `max_retries=3`, `time_limit=600`, `soft_time_limit=540` | `app/tasks.py:130` | ✅ Exact match |
| `deliver_webhook_task` uses `queue='webhooks'`, `max_retries=3` | `app/tasks.py:182` | ✅ Exact match |
| `send_confirmation_task` uses `queue='email'`, `max_retries=3` | `app/tasks.py:262` | ✅ Exact match |
| `send_password_reset_task` uses `queue='email'`, `max_retries=3` | `app/tasks.py:283` | ✅ Exact match |
| `run_backup_task` uses `queue='backup'`, `max_retries=2` | `app/tasks.py:304` | ✅ Exact match |
| `run_backup_task` uses `compress=True`, `keep=7`, `encrypt=False` | `app/tasks.py:316` | ✅ Exact match |
| APScheduler `cleanup_expired_subscribers` runs every 5 minutes (`minute="*/5"`) | `app/scheduler.py:305` | ✅ Exact match |
| APScheduler `publish_scheduled_posts` runs every 5 minutes (`minute="*/5"`) | `app/scheduler.py:312` | ✅ Exact match |
| APScheduler `run_daily_backup` runs at 02:00 (`hour=2, minute=0`) | `app/scheduler.py:319` | ✅ Exact match |
| APScheduler uses `FileLock` with `timeout=0` for newsletter job | `app/scheduler.py:72` | ✅ Exact match |
| APScheduler uses `FileLock` with `timeout=0` for cleanup job | `app/scheduler.py:168` | ✅ Exact match |
| APScheduler uses `FileLock` with `timeout=0` for scheduled posts job | `app/scheduler.py:212` | ✅ Exact match |
| APScheduler uses `FileLock` with `timeout=0` for backup job | `app/scheduler.py:269` | ✅ Exact match |
| Lock file paths use `{instance_path}/{job_name}.lock` pattern | `app/scheduler.py:71,167,211,268` | ✅ Exact match |
| `send_daily_newsletter` respects `NEWSLETTER_MAX_RETRY_ATTEMPTS` | `app/scheduler.py:87-121` | ✅ Exact match |
| `send_daily_newsletter` logs excluded posts after max retry attempts | `app/scheduler.py:100-106` | ✅ Exact match |
| Multi-worker FileLock limitation documented in scheduler.py | `app/scheduler.py:3-8` | ✅ Exact match |
| APScheduler uses `daemon=True` BackgroundScheduler | `app/scheduler.py:290` | ✅ Exact match |
| APScheduler registers atexit shutdown handler | `app/scheduler.py:333` | ✅ Exact match |
| `send_daily_newsletter` only runs when `SMTP_HOST` is configured | `app/scheduler.py:292-302` | ✅ Exact match |

---

## 2. Inaccurate/Outdated Claims

| Claim | Documentation | Actual Behavior | Correction Needed |
|-------|---------------|-----------------|-------------------|
| `send_daily_newsletter` uses Celery task | scheduler.md:23 | Directly calls `send_newsletter()` synchronously (scheduler.py:142) | Update docs to clarify it calls `send_newsletter()` directly, not via Celery |
| `run_backup_task` uses `blog_YYYYMMDD_HHMMSS.db.gz` naming | celery-tasks.md:88 | Actual code at tasks.py:316 doesn't specify naming; depends on `create_backup()` service | The `.gz` extension is an assumption; actual naming comes from `create_backup()` |
| `send_daily_newsletter` runs "Daily at configured time" | scheduler.md:9, scheduler.md:16 | Default is `NEWSLETTER_SEND_TIME` (default "08:00"), not strictly "daily" | Correct - claimed "Daily at configured time" is accurate |
| Newsletter retry count default is 3 | celery-tasks.md (implied) | Actual default is 5 (from `NEWSLETTER_MAX_RETRY_ATTEMPTS` in config) | Documentation should state "default is 5" not imply 3 |

---

## 3. Bugs Identified

| Severity | Location | Description |
|----------|----------|-------------|
| **Medium** | `app/tasks.py:274-278` | `send_confirmation_task` catches `SQLAlchemyError, OSError, ImportError` and returns `False` without raising. With `max_retries=3`, the task will NOT automatically retry because the exception is swallowed. Either: (1) Remove `max_retries=3` if retry not desired, or (2) Re-raise or use `self.retry()` to trigger actual retries. |
| **Medium** | `app/tasks.py:295-299` | `send_password_reset_task` has same issue - catches exceptions and returns `False` silently, yet has `max_retries=3` configured. No automatic retry will occur. Same fix needed as above. |
| **Low** | `app/scheduler.py:100-106` | `send_daily_newsletter` logs excluded posts with first 5 IDs/titles at WARNING level. This is good for debugging but could leak post titles to log aggregation systems. Should use only post IDs in production logs to avoid potential PII leakage if post titles contain sensitive info. |
| **Low** | `app/tasks.py:172-175` | `send_newsletter_task` increments `newsletter_attempts` on failure but has no logging equivalent to scheduler.py:100-106. When Celery task fails repeatedly, no visibility into which posts are being retried. |

---

## 4. Missing Documentation

| Item | Location | Description |
|------|----------|-------------|
| Newsletter retry count | `celery-tasks.md` | No mention of `NEWSLETTER_MAX_RETRY_ATTEMPTS` (default: 5) and how it affects task behavior |
| Excluded post logging | `celery-tasks.md` | No documentation of logging behavior when posts are excluded after max retry attempts |
| `send_newsletter_task` vs scheduler difference | `celery-tasks.md` | No note that APScheduler's `send_daily_newsletter` is a separate code path that directly calls `send_newsletter()`, not the Celery task |
| Email task exception handling | `celery-tasks.md` | No documentation of `SQLAlchemyError, OSError, ImportError` exception handling in email tasks |
| Lock file location variable | `scheduler.md:69` | Documents `{instance_path}` but doesn't explain how `instance_path` is determined |
| `send_daily_newsletter` condition | `scheduler.md` | Missing note that newsletter job only runs if `SMTP_HOST` is configured |
| APScheduler daemon mode | `scheduler.md` | No documentation that scheduler uses `daemon=True` BackgroundScheduler |
| Multi-worker limitation cross-reference | Both docs | Should reference DEPLOY.md for full multi-container deployment details (scheduler.py:8 hints at this but docs don't) |

---

## 5. Recommended Improvements

### High Priority

1. **Fix email task retry behavior** (`app/tasks.py:274-278, 295-299`)
   - Either remove `max_retries=3` from email tasks or implement proper retry logic with `self.retry()`
   - Current implementation silently catches exceptions and returns False, making `max_retries=3` ineffective

2. **Document newsletter retry configuration** (`celery-tasks.md`)
   - Add explicit note that `NEWSLETTER_MAX_RETRY_ATTEMPTS` (default: 5) controls retry behavior
   - Clarify that Celery task does not have the same retry-exclusion logic as APScheduler scheduler

### Medium Priority

3. **Clarify APScheduler vs Celery newsletter paths** (`scheduler.md`, `celery-tasks.md`)
   - Document that `send_daily_newsletter` (APScheduler) and `send_newsletter_task` (Celery) are separate code paths
   - APScheduler directly calls `send_newsletter()`, Celery task is for async ad-hoc sends

4. **Add multi-container deployment cross-reference** (both docs)
   - Add explicit reference to DEPLOY.md for multi-worker/deployment considerations
   - Document the Redis/etcd external coordination requirement for multi-machine setups

5. **Document SMTP_HOST condition** (`scheduler.md`)
   - Add note that `send_daily_newsletter` job is only added if `SMTP_HOST` is configured

### Low Priority

6. **Fix excluded post logging PII concern** (`app/scheduler.py:100-106`)
   - Consider logging only post IDs in production to avoid potential title leakage
   - If titles are needed for debugging, ensure log aggregation is secure

7. **Add Celery task failure visibility** (`app/tasks.py:172-175`)
   - Add logging similar to scheduler.py:100-106 when newsletter attempts fail repeatedly

8. **Document backup naming pattern source** (`celery-tasks.md:88`)
   - Clarify that `.db.gz` extension depends on `create_backup()` service implementation

9. **Document APScheduler daemon mode** (`scheduler.md`)
   - Note that scheduler runs as daemon thread and will not prevent process exit

---

## Summary

| Category | Count |
|----------|-------|
| Verified Accurate Claims | 22 |
| Inaccurate Claims | 4 |
| Bugs Identified | 4 |
| Missing Documentation | 8 |
| Improvements | 9 |

---

## Appendix: Line Number Cross-Reference

### Celery Tasks (`app/tasks.py`)
| Task | Line |
|------|------|
| `generate_image_variants` | 31 |
| `send_newsletter_task` | 130 |
| `deliver_webhook_task` | 182 |
| `send_confirmation_task` | 262 |
| `send_password_reset_task` | 283 |
| `run_backup_task` | 304 |

### APScheduler Jobs (`app/scheduler.py`)
| Job | Line |
|-----|------|
| `send_daily_newsletter` | 70 |
| `cleanup_expired_subscribers` | 165 |
| `publish_scheduled_posts` | 209 |
| `run_daily_backup` | 264 |
| `init_scheduler` | 283 |
