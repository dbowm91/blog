# Task Architecture Review

## Summary

Reviewed three architecture documents in `architecture/tasks/` against actual implementation in `app/tasks.py`, `app/scheduler.py`, and `app/celery_app.py`. The documents are largely accurate but contain several discrepancies, one significant bug, and some outdated information. Most concerning is a bug in the S3 image variant upload logic that causes original files to be overwritten.

## Verified Claims

### Celery Tasks (`app/tasks.py`) - Verified

| Claim | Status | Implementation |
|-------|--------|----------------|
| Queue definitions (images, newsletter, webhooks, email, backup) | VERIFIED | `app/tasks.py:29,130,193,265,286,307` |
| `generate_image_variants` - 400w/800w/1200w WebP + original | VERIFIED | `app/tasks.py:55-70` (LocalStorage), `app/tasks.py:88-103` (S3) |
| `send_newsletter_task` - time_limit=600, soft_time_limit=540 | VERIFIED | `app/tasks.py:130` |
| `deliver_webhook_task` - SSRF protection, HMAC-SHA256 signing | VERIFIED | `app/tasks.py:200-241` |
| `send_confirmation_task` / `send_password_reset_task` | VERIFIED | `app/tasks.py:265,286` |
| `run_backup_task` - max_retries=2, queue='backup' | VERIFIED | `app/tasks.py:307` |
| Retry policy (max_retries=3, retry_backoff=True) | VERIFIED | All tasks use this pattern |

### APScheduler (`app/scheduler.py`) - Verified

| Claim | Status | Implementation |
|-------|--------|----------------|
| `send_daily_newsletter` job schedule at NEWSLETTER_SEND_TIME | VERIFIED | `app/scheduler.py:269-278` |
| `cleanup_expired_subscribers` - hourly | VERIFIED | `app/scheduler.py:279-285` (runs every 5 minutes, not hourly - minor inaccuracy in doc) |
| `publish_scheduled_posts` - every 5 minutes | VERIFIED | `app/scheduler.py:286-292` |
| `run_daily_backup` - daily at midnight | VERIFIED | `app/scheduler.py:293-299` (runs at 02:00, not midnight - documented as midnight but actual is 02:00) |
| File locking mechanism described | VERIFIED | All jobs use `FileLock` with instance path locks |

### Overview (`architecture/tasks/overview.md`) - Verified

| Claim | Status | Implementation |
|-------|--------|----------------|
| Celery file location `app/celery_app.py`, `app/tasks.py` | VERIFIED | Correct file paths |
| APScheduler file location `app/scheduler.py` | VERIFIED | Correct file path |

## Discrepancies Found

### 1. `cleanup_expired_subscribers` Schedule Inconsistency
- **Doc**: "Hourly"
- **Actual**: `CronTrigger(minute="*/5")` - runs every 5 minutes
- **Location**: `app/scheduler.py:281`
- **Priority**: Medium

### 2. `run_daily_backup` Schedule Inconsistency  
- **Doc**: "Daily at midnight"
- **Actual**: `CronTrigger(hour=2, minute=0)` - runs at 02:00
- **Location**: `app/scheduler.py:295`
- **Priority**: Medium

### 3. `run_daily_backup` Service Call Inconsistency
- **Doc**: "Creates backup using `run_daily_backup()` service"
- **Actual**: `app/scheduler.py:242` imports `run_daily_backup as _run_backup` from `app.services.backup`, but the Celery task `run_backup_task` in `app/tasks.py:310` calls `create_backup` directly from `app.services.backup`
- **Note**: Two different functions exist - the scheduler version (`app/services/backup.py:144`) does NOT use `create_backup()` but has its own inline backup logic. This is a subtle inconsistency but both functions work.
- **Priority**: Low

### 4. APScheduler `cleanup_expired_subscribers` Not Hourly
- **Doc**: "Runs hourly: 1. Finds subscribers past `expires_at` without confirmation 2. Deletes unconfirmed expired records"
- **Actual**: The description is accurate but schedule is wrong (every 5 min)
- **Priority**: Medium

## Bugs Identified

### Critical: S3 Image Upload Overwrites Original File

**Location**: `app/tasks.py:106`

**Bug**: The S3 storage backend in `generate_image_variants` calls:
```python
storage.save(filename, file_data)  # Line 106 - OVERWRITES ORIGINAL
```

This re-uploads the original file (potentially overwriting it) BEFORE uploading the generated variants. This is backwards - it should only upload the variants.

**Impact**: When processing an S3 image, the original file gets overwritten with potentially corrupted data from the temp file handle that may have been read incorrectly.

**Fix**: Remove line 106 entirely. The variants should be uploaded, not the original:

```python
# Line 106 should be REMOVED - it incorrectly re-uploads the original
for width in (400, 800, 1200):
    webp_variant_name = f"{width}_{basename}.webp"
    ...
```

**Priority**: High

### Medium: S3 Original Variant Upload Uses Wrong Variable

**Location**: `app/tasks.py:106`

**Bug**: Even if the intent was to upload the original, the code uses `filename` (which is just the basename without path) and `file_data` (the original data that was loaded). But for consistency with local storage, only variants should be uploaded.

**Priority**: High (same bug as above)

## Improvement Recommendations

### High Priority

1. **Fix S3 upload bug in `generate_image_variants`**
   - File: `app/tasks.py`
   - Line: 106
   - Issue: `storage.save(filename, file_data)` incorrectly re-uploads original file
   - Recommendation: Remove line 106 as variants are uploaded in the loop below

2. **Fix APScheduler job schedules in `scheduler.md`**
   - File: `architecture/tasks/scheduler.md`
   - Lines 12, 22: Change `Hourly` to `Every 5 minutes` for cleanup
   - Lines 12, 34: Change `Daily at midnight` to `Daily at 02:00` for backup

### Medium Priority

3. **Document the two different backup paths**
   - File: `architecture/tasks/scheduler.md`
   - Issue: `run_daily_backup` in scheduler uses inline logic, while Celery's `run_backup_task` uses `create_backup()` service
   - Recommendation: Clarify both paths work but serve different use cases (scheduler for daily automated, Celery for on-demand)

4. **Add queue configuration to `celery_app.py` documentation**
   - File: `app/celery_app.py`
   - Issue: The architecture doc lists 5 queues, but actual queue routing configuration is implicit in task decorators
   - Recommendation: Add explicit queue configuration or document the queue routing

### Low Priority

5. **Update `generate_image_variants` docstring to reflect S3 behavior**
   - File: `app/tasks.py`
   - Line: 31-35
   - The docstring should clarify that for S3, the original file must already exist in storage

6. **Add `@shared_task` decorator parameters to type annotations in arch docs**
   - File: `architecture/tasks/celery-tasks.md`
   - The task signatures show decorator options (bind=True, max_retries=3, etc.) which is useful for understanding retry behavior

## Summary Table

| Issue | Type | Priority | Location |
|-------|------|----------|----------|
| S3 original file overwrite bug | Bug | High | `app/tasks.py:106` |
| Cleanup job runs every 5 min, not hourly | Discrepancy | Medium | `app/scheduler.py:281` |
| Backup runs at 02:00, not midnight | Discrepancy | Medium | `app/scheduler.py:295` |
| Scheduler doc lists "hourly" for cleanup | Discrepancy | Medium | `architecture/tasks/scheduler.md:12,22` |
| Scheduler doc lists "midnight" for backup | Discrepancy | Medium | `architecture/tasks/scheduler.md:12,34` |
| Two different backup implementations | Discrepancy | Low | `app/services/backup.py:144` vs `app/tasks.py:310` |
