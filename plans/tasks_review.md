# Tasks Architecture Review

## Summary

Reviewed architecture documents in `architecture/tasks/` and verified against actual implementation in `app/tasks.py`, `app/scheduler.py`, and related code. Found several discrepancies between documentation and code, including one Critical bug.

---

## Verified Claims

### Celery Tasks (`app/tasks.py`)

| Claim | Status | Location |
|-------|--------|----------|
| Queue names (images, newsletter, webhooks, email, backup) | VERIFIED | tasks.py:31,130,182,255,277,297 |
| `generate_image_variants` task signature | VERIFIED | tasks.py:31 |
| `send_newsletter_task` with time_limit=600, soft_time_limit=540 | VERIFIED | tasks.py:130 |
| `deliver_webhook_task` with SSRF/HMAC signing | VERIFIED | tasks.py:182 |
| `send_confirmation_task` and `send_password_reset_task` | VERIFIED | tasks.py:255,277 |
| `run_backup_task` with max_retries=2, compress=True, keep=7 | VERIFIED | tasks.py:297,309 |
| `retry_backoff=True` on all tasks | VERIFIED | All task decorators |
| `max_retries=3` (2 for backup) | VERIFIED | tasks.py:297 |

### APScheduler (`app/scheduler.py`)

| Claim | Status | Location |
|-------|--------|----------|
| `send_daily_newsletter` runs at NEWSLETTER_SEND_TIME | VERIFIED | scheduler.py:70-141,276-282 |
| `send_daily_newsletter` uses FileLock with timeout=0 | VERIFIED | scheduler.py:72 |
| `cleanup_expired_subscribers` runs every 5 minutes | VERIFIED | scheduler.py:144-185,284-289 |
| `publish_scheduled_posts` runs every 5 minutes | VERIFIED | scheduler.py:188-237,291-296 |
| `publish_scheduled_posts` syncs FTS and invalidates cache | VERIFIED | scheduler.py:228,234 |
| Multi-worker FileLock limitation documented | VERIFIED | scheduler.py:65-69 |
| Lock file pattern: `{instance_path}/{job_name}.lock` | VERIFIED | scheduler.py:71,146,190,247 |

---

## Discrepancies

### 1. Backup Naming Pattern Documentation Error

**File:** `architecture/tasks/scheduler.md:49`

**Documentation claims:**
> **Naming Convention:** This scheduler job uses `blog_*.db` naming pattern... For encrypted/compressed backups, use the Celery task `run_backup_task` which also uses `blog_*.db` naming but supports compression and encryption via `create_backup()`.

**Problem:** The phrase "For encrypted/compressed backups, use the Celery task `run_backup_task` which also uses `blog_*.db` naming but supports compression and encryption" is misleading. The Celery task at `app/tasks.py:309` passes `encrypt=False`, so it does NOT support encryption despite the documentation suggesting it does.

**Code reference:** `app/tasks.py:309`
```python
result = create_backup(db_path, backup_dir, compress=True, keep=7, encrypt=False)
```

### 2. Queue Routing Table Line Numbers Inaccurate

**File:** `architecture/tasks/scheduler.md:55-61`

**Documentation claims:**
| Queue | Tasks | Location |
|-------|-------|----------|
| `images` | Image processing | `app/tasks.py:29` |
| `newsletter` | Newsletter delivery | `app/tasks.py:129` |
| `webhooks` | Webhook delivery | `app/tasks.py:192` |
| `email` | Transactional email | `app/tasks.py:264,285` |
| `backup` | Backup tasks | `app/tasks.py:306` |

**Actual line numbers:**
| Queue | Actual Location |
|-------|-----------------|
| `images` | `app/tasks.py:31` |
| `newsletter` | `app/tasks.py:130` |
| `webhooks` | `app/tasks.py:182` |
| `email` | `app/tasks.py:255,276` (not 264,285) |
| `backup` | `app/tasks.py:297` (not 306) |

---

## Bugs Identified

### CRITICAL: Newsletter Can Silence Retry Logic

**File:** `app/scheduler.py:70-141` (`send_daily_newsletter`)

**Issue:** When `send_newsletter()` fails, posts have `newsletter_attempts` incremented, but these posts remain in the query results for the next run (since `newsletter_sent_at` is still NULL). The scheduler will retry indefinitely unless `newsletter_attempts >= NEWSLETTER_MAX_RETRY_ATTEMPTS`.

**Code reference:** `app/scheduler.py:87-100`
```python
posts = (
    db.session.execute(
        select(Post)
        .filter(
            Post.published,
            Post.published_at.isnot(None),
            Post.newsletter_sent_at.is_(None),
            Post.newsletter_attempts < NEWSLETTER_MAX_RETRY_ATTEMPTS,
        )
        .order_by(Post.published_at.desc())
    )
    .scalars()
    .all()
)
```

**Problem:** After `NEWSLETTER_MAX_RETRY_ATTEMPTS` (default: 5) failures, posts are excluded from selection. However, there's no mechanism to reset `newsletter_attempts` or surface these stuck posts to the admin. Posts can become permanently stuck in a "failed" state.

**Impact:** Posts that consistently fail newsletter delivery (e.g., due to SMTP issues) become orphaned in the newsletter queue after 5 attempts.

---

### HIGH: Cleanup Lock Uses Different Pattern

**File:** `app/scheduler.py:146`

**Issue:** The cleanup job uses `cleanup.lock` but documentation only mentions `newsletter.lock`. Other jobs use `{instance_path}/{job_name}.lock` pattern:

| Job | Lock File |
|-----|-----------|
| send_daily_newsletter | newsletter.lock |
| cleanup_expired_subscribers | cleanup.lock |
| publish_scheduled_posts | scheduled.lock |
| run_daily_backup | backup.lock |

**Code reference:** `app/scheduler.py:71,146,190,247`

**Documentation reference:** `scheduler.md:69` only mentions `newsletter.lock`.

---

### MEDIUM: APScheduler Disabled When SMTP Not Configured

**File:** `app/scheduler.py:269-271`

```python
if not SMTP_HOST:
    app.logger.info("SMTP_HOST not configured; newsletter scheduler disabled")
    return None
```

**Issue:** When `SMTP_HOST` is not configured, the entire scheduler is disabled, including `cleanup_expired_subscribers`, `publish_scheduled_posts`, and `run_daily_backup`. These jobs don't require SMTP.

**Impact:** Scheduled cleanup and backup jobs won't run if email isn't configured, even though they don't need SMTP.

---

## Improvement Recommendations

### 1. Fix Backup Task Documentation (Low Priority)

**File:** `architecture/tasks/scheduler.md:49`

**Change:** Clarify that `run_backup_task` (Celery) does NOT support encryption:
```
OLD: "...which also uses `blog_*.db` naming but supports compression and encryption via `create_backup()`."
NEW: "...which also uses `blog_*.db` naming but supports compression via `create_backup()` (encryption is disabled)."
```

### 2. Fix Queue Routing Line Numbers (Low Priority)

**File:** `architecture/tasks/scheduler.md:55-61`

**Change:** Update line numbers to match actual code:
```markdown
| `images` | Image processing | `app/tasks.py:31` |
| `newsletter` | Newsletter delivery | `app/tasks.py:130` |
| `webhooks` | Webhook delivery | `app/tasks.py:182` |
| `email` | Transactional email | `app/tasks.py:255,276` |
| `backup` | Backup tasks | `app/tasks.py:297` |
```

### 3. Fix Scheduler Disable Logic (Medium Priority)

**File:** `app/scheduler.py:269-271`

**Change:** Only disable newsletter job when SMTP is unavailable, not the entire scheduler:
```python
def init_scheduler(app: Any) -> Optional["BackgroundScheduler"]:
    # ... existing code ...
    if not SMTP_HOST:
        app.logger.info("SMTP_HOST not configured; daily newsletter disabled")
    else:
        scheduler.add_job(
            send_daily_newsletter,
            CronTrigger(hour=hour, minute=minute),
            args=[app],
            id="daily_newsletter",
            replace_existing=True,
        )
    # Always add other jobs...
```

### 4. Document All Lock Files (Low Priority)

**File:** `architecture/tasks/scheduler.md:69`

**Change:** Document all lock files:
```markdown
OLD: Lock file locations: `{instance_path}/{job_name}.lock` (e.g., `newsletter.lock`)
NEW: Lock file locations: `{instance_path}/{job_name}.lock`
     - `newsletter.lock` - Daily newsletter sending
     - `cleanup.lock` - Expired subscriber cleanup
     - `scheduled.lock` - Scheduled post publishing
     - `backup.lock` - Daily backup
```

### 5. Consider Newsletter Retry Admin Visibility (Low Priority)

**File:** `app/scheduler.py:130-139`

**Issue:** Posts that hit `NEWSLETTER_MAX_RETRY_ATTEMPTS` are silently excluded with no admin visibility.

**Recommendation:** Consider logging a warning when posts are excluded, or add admin dashboard visibility for posts stuck in retry state.

---

## Related Files Reviewed

- `app/tasks.py` - 313 lines (Celery task definitions)
- `app/scheduler.py` - 314 lines (APScheduler jobs)
- `app/services/backup.py` - 192 lines (Backup service with `create_backup` and `run_daily_backup`)
- `app/email.py` - 216 lines (Email sending with newsletter support)
- `app/webhooks.py` - 118 lines (Webhook delivery)
- `app/config.py` - 243 lines (Configuration including `NEWSLETTER_MAX_RETRY_ATTEMPTS=5`)