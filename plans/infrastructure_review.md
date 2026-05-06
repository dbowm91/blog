# Infrastructure Review

**Date:** May 2026  
**Reviewer:** Architecture Review Agent  
**Documents Reviewed:**
- `/home/sugarwookie/projects/blog/architecture/infrastructure/email.md`
- `/home/sugarwookie/projects/blog/architecture/infrastructure/search.md`
- `/home/sugarwookie/projects/blog/architecture/infrastructure/storage.md`
- `/home/sugarwookie/projects/blog/architecture/infrastructure/webhooks.md`
- `/home/sugarwookie/projects/blog/architecture/infrastructure/overview.md`

## Summary

This review examined 5 infrastructure architecture documents and verified their claims against actual implementations. Overall, the documentation is accurate and well-structured. However, several discrepancies were found between documented defaults and actual configuration values, and one significant bug was identified regarding webhook event triggering.

---

## Verified Claims

### Email (`app/email.py`)

| Claim | Status | Location |
|-------|--------|----------|
| `_send_email()` low-level SMTP send with TLS | VERIFIED | `app/email.py:24-43` |
| `_connect_smtp()` returns None on failure | VERIFIED | `app/email.py:82-101` |
| `_send_email_with_retry()` with exponential backoff | VERIFIED | `app/email.py:104-140` |
| Handles `SMTPServerDisconnected` by reconnecting | VERIFIED | `app/email.py:124-135` |
| `send_newsletter()` bulk delivery with progress logging every 50 | VERIFIED | `app/email.py:143-216` (line 206-209) |
| Email templates exist | VERIFIED | `app/templates/email/` (confirm.html, password_reset.html, newsletter.html) |
| Retry logic implemented | VERIFIED | `app/email.py:116-140` |

### Search (`app/search.py`)

| Claim | Status | Location |
|-------|--------|----------|
| FTS5 Virtual Table creation | VERIFIED | `app/search.py:68-73` |
| BM25 ranking in search | VERIFIED | `app/search.py:214-215` |
| Prefix matching with `term*` | VERIFIED | `app/search.py:209` |
| FTS5 `snippet()` function for highlights | VERIFIED | `app/search.py:282-324` |
| `get_did_you_mean()` fuzzy suggestions | VERIFIED | `app/search.py:327-353` |
| LIKE fallback when FTS unavailable | VERIFIED | `app/search.py:204-205` returns empty list |
| `posts_fts_vocab` vocabulary table | VERIFIED | `app/search.py:75-79` |
| `_FTS_CHECK_TTL = 300` (5 min cache) | VERIFIED | `app/search.py:30` |
| `FTS_RESULT_LIMIT` configuration | VERIFIED | `app/search.py:217`, `app/config.py:123` |
| Query escaping for special FTS5 characters | VERIFIED | `app/search.py:32`, `193-198` |

### Storage (`app/storage.py`)

| Claim | Status | Location |
|-------|--------|----------|
| Local and S3 backend support | VERIFIED | `app/storage.py:41-48` |
| `LocalStorageBackend` class | VERIFIED | `app/storage.py:83-128` |
| `S3StorageBackend` class | VERIFIED | `app/storage.py:131-228` |
| Factory function `get_storage_backend()` | VERIFIED | `app/storage.py:231-257` |
| Singleton pattern via `get_storage()` | VERIFIED | `app/storage.py:260-268` |
| `upload_with_processing()` with Celery task | VERIFIED | `app/storage.py:284-320` |
| Responsive variants: 400w, 800w, 1200w WebP | VERIFIED | `app/tasks.py:55-70` |

### Webhooks (`app/webhooks.py`)

| Claim | Status | Location |
|-------|--------|----------|
| HMAC-SHA256 signing | VERIFIED | `app/webhooks.py:28-36` |
| SSRF protection via `is_safe_webhook_url()` | VERIFIED | `app/webhooks.py:53-55`, `app/utils.py:312-414` |
| 10 second timeout | VERIFIED | `app/webhooks.py:20` (WEBHOOK_TIMEOUT = 10) |
| No redirects allowed | VERIFIED | `app/webhooks.py:69` (allow_redirects=False) |
| `Webhook` model structure | VERIFIED | `app/models.py:430-446` |
| `WebhookEvent` model structure | VERIFIED | `app/models.py:449-470` |
| Event types documented | VERIFIED | `app/models.py:437` (event_type column) |
| Celery async delivery | VERIFIED | `app/tasks.py:193-262` |

---

## Discrepancies Found

### 1. Newsletter Default Retry Count

**Document:** `email.md` line 83 - "Max retries: 3 (configurable via `NEWSLETTER_MAX_RETRY_ATTEMPTS`)"

**Actual:** `app/config.py:114` - Default is **5**, not 3:
```python
NEWSLETTER_MAX_RETRY_ATTEMPTS = int(_config["newsletter"].get("max_retry_attempts", 5))
```

**Impact:** Low - Documentation is outdated but the feature works correctly with the configurable value.

---

## Bugs Identified

### 1. Webhook Events Are Never Triggered (High Priority)

**Bug:** The `create_webhook_event()` function exists in `app/webhooks.py:76-103` and is properly implemented with Celery task queuing. However, **no code in the codebase actually calls this function**.

**Evidence:**
- `grep` search for `create_webhook_event` only finds the definition and export in `app/webhooks.py`
- There are no calls to `create_webhook_event` anywhere in the routes, models, or services
- The documented event types (`post.published`, `post.created`, `subscriber.confirmed`) are never fired

**Affected Files:**
- `app/webhooks.py:76-103` - Function exists but is never invoked
- `app/routes/api/posts.py` - Post publish logic (line 267-278) does not call `create_webhook_event`
- `app/routes/api/subscribers.py` - Subscriber confirmation does not trigger webhook
- `app/scheduler.py` - Scheduled post publishing does not trigger webhook

**Recommended Fix:**
Add webhook triggering to relevant locations. Example for post publishing in `app/routes/api/posts.py`:
```python
# After successful publish (around line 269-279)
if published and not post.published_at:
    post.published_at = utc_now()

# Trigger webhook after commit
if was_published != post.published:
    from app.webhooks import create_webhook_event
    create_webhook_event(
        event_type="post.published" if post.published else "post.unpublished",
        payload={"post_id": post.id, "title": post.title, "slug": post.slug},
        target_id=post.id,
        target_type="post"
    )
```

**Priority:** High - Webhooks are documented but completely non-functional.

---

## Improvement Recommendations

### 1. Document Default Retry Discrepancy (Low Priority)

**File:** `/home/sugarwookie/projects/blog/architecture/infrastructure/email.md` line 83

**Current:** "Max retries: 3"

**Recommended:** Change to "Max retries: 5 (default, configurable via `NEWSLETTER_MAX_RETRY_ATTEMPTS`)"

**Priority:** Low - This is a documentation-only fix.

---

### 2. Add `rebuild_fts()` to sync_fts_batch Documentation (Low Priority)

**File:** `/home/sugarwookie/projects/blog/architecture/infrastructure/search.md`

**Issue:** The document describes `sync_fts()` and `sync_fts_batch()` but does not mention `rebuild_fts()` which is used to rebuild the entire FTS index from scratch.

**Location:** `app/search.py:102-109`

**Priority:** Low - Minor documentation omission.

---

### 3. Document Snippet Batching for SQLite Limits (Medium Priority)

**File:** `/home/sugarwookie/projects/blog/architecture/infrastructure/search.md`

**Issue:** The `get_search_snippets()` function at `app/search.py:298-324` uses `_SQLITE_MAX_VARS = 500` to batch queries due to SQLite's parameter limit. This is an important implementation detail for scalability but is not documented.

**Recommended:** Add to search.md under "Query Processing" or "Implementation Notes":
```markdown
## Implementation Notes

### SQLite Parameter Limits
The `get_search_snippets()` function batches post IDs in chunks of 500 to comply with SQLite's parameter limit (`:id0, :id1, ...` placeholders).
```

**Priority:** Medium - This is a significant implementation detail that affects deployment planning.

---

### 4. Add Celery Task Queues Documentation (Medium Priority)

**Files:**
- `/home/sugarwookie/projects/blog/architecture/infrastructure/email.md`
- `/home/sugarwookie/projects/blog/architecture/infrastructure/webhooks.md`

**Issue:** The documents mention async delivery via Celery but do not document the queue names used.

**Evidence from `app/tasks.py`:**
- `generate_image_variants` - queue: 'images' (line 29)
- `send_newsletter_task` - queue: 'newsletter' (line 130)
- `deliver_webhook_task` - queue: 'webhooks' (line 193)
- `send_confirmation_task` - queue: 'email' (line 265)
- `send_password_reset_task` - queue: 'email' (line 286)
- `run_backup_task` - queue: 'backup' (line 307)

**Recommended:** Add queue configuration to each document.

**Priority:** Medium - Important for deployment and monitoring.

---

### 5. S3 Backend Credentials Cleanup Documentation (Low Priority)

**File:** `/home/sugarwookie/projects/blog/architecture/infrastructure/storage.md`

**Issue:** The S3 storage backend clears credentials after client initialization (`app/storage.py:171-174`) to minimize sensitive data lifetime. This security feature is not documented.

**Priority:** Low - Security-related detail that may be relevant for compliance documentation.

---

## Priority Summary

| Item | Type | Priority |
|------|------|----------|
| Webhook events never triggered | Bug | High |
| Newsletter retry count discrepancy | Discrepancy | Low |
| rebuild_fts() not documented | Improvement | Low |
| SQLite batching not documented | Improvement | Medium |
| Celery task queues not documented | Improvement | Medium |
| S3 credentials cleanup not documented | Improvement | Low |

---

## Files Referenced

| Component | Implementation File | Line References |
|-----------|---------------------|-----------------|
| Email | `app/email.py` | 24-43, 82-101, 104-140, 143-216 |
| Email Config | `app/config.py` | 104-107, 114, 140 |
| Search | `app/search.py` | 30, 32, 68-79, 102-109, 193-198, 201-221, 282-324, 327-353 |
| Search Config | `app/config.py` | 123 |
| Storage | `app/storage.py` | 41-48, 83-128, 131-228, 231-257, 260-268, 284-320 |
| Storage Tasks | `app/tasks.py` | 29-127 |
| Webhooks | `app/webhooks.py` | 1-108 |
| Webhook Tasks | `app/tasks.py` | 182-262 |
| Webhook SSRF | `app/utils.py` | 312-414 |
| Webhook Models | `app/models.py` | 430-470 |
| Templates | `app/templates/email/` | confirm.html, password_reset.html, newsletter.html |
