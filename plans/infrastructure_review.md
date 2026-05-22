# Infrastructure Documentation Review - Improvement Plan

## Overview

Reviewed architecture documents in `architecture/infrastructure/` against implementation code in:
- `app/webhooks.py`
- `app/email.py`
- `app/storage.py`
- `app/services/search/__init__.py`
- `app/search.py`
- `app/tasks.py`

---

## 1. Webhooks (`webhooks.md`)

### Discrepancies

| Issue | Documentation | Actual Implementation |
|-------|---------------|----------------------|
| `WebhookEvent.webhook_id` | Documented as FK to webhooks | Column exists but is nullable and unused in delivery logic. `deliver_webhook_task` queries webhooks by `event_type` not by FK relation. |

### Bugs & Issues

**1. No per-webhook retry within task (tasks.py:234-246)**
```python
except requests.RequestException:
    event.delivery_attempts += 1
```
When a single webhook fails, the task catches the exception and continues. Celery's `max_retries=3` only triggers on task-level exceptions that propagate. Since we catch `RequestException` and don't re-raise, the task succeeds but the failed webhook isn't actually retried.

**Fix needed**: Either re-raise the exception to trigger Celery retry, or implement per-webhook retry within the task with exponential backoff.

**2. No-op assertion (tasks.py:248)**
```python
assert event is not None
```
This assertion is always true at that point. Remove or replace with meaningful check.

**3. `event.delivery_status` not set when no webhooks found (tasks.py:204)**
```python
if not webhooks:
    event.delivered = True
    db.session.commit()
    return True
```
When no webhooks match, `delivery_status` is never set, leaving it `None` instead of a defined state.

**4. Silent failure on queue error (webhooks.py:110-114)**
```python
except (RequestException, ValueError, OSError) as e:
    logger.error("Failed to queue webhook event %d for delivery: %s", event_id, e)
```
The event is created and committed, but if queuing fails, the event sits in DB undelivered with no retry mechanism.

---

## 2. Email (`email.md`)

### Discrepancies

| Issue | Documentation | Actual Implementation |
|-------|---------------|----------------------|
| Confirmation/Password reset retry | Not mentioned | `send_confirmation()` and `send_password_reset()` use `_send_email()` directly with **no retry logic**. Only newsletter has retry via `_send_email_with_retry()`. |

### Bugs & Issues

**1. No retry for transactional emails**
- `send_confirmation()` (email.py:46) uses `_send_email()` directly
- `send_password_reset()` (email.py:65) uses `_send_email()` directly

If SMTP fails, these fail immediately with no retry. The Celery tasks wrapping them (tasks.py:264-282, 285-303) do have `max_retries=3`, but they only retry when an exception propagates. Since `_send_email()` can raise `smtplib.SMTPException` or `OSError`, this may work in practice, but the retry is at the task level, not the SMTP level.

**2. Inconsistent SMTP connection handling**
- `_send_email()` opens/closes connection per email (line 36-43)
- `send_newsletter()` opens one connection and reuses via `_send_email_with_retry()` (line 158-197)

Transactional emails don't benefit from connection reuse. Could be optimized.

**3. Newsletter early termination on first failure**
The newsletter task (tasks.py:158) calls `send_newsletter()` which returns `False` on any failure. If sending fails for subscriber #50 out of 100, the remaining 50 are never attempted.

---

## 3. Storage (`storage.md`)

### Discrepancies

| Issue | Documentation | Actual Implementation |
|-------|---------------|----------------------|
| S3 variant generation | Not documented | `upload_with_processing()` saves to S3, then Celery task (`generate_image_variants`) downloads from S3 to temp, processes, and re-uploads variants back to S3. This is correct but undocumented. |
| `S3StorageBackend` path() | Not applicable | Correctly raises `NotImplementedError` via base class (storage.py:78-80) |

### Bugs & Issues

**1. No cleanup of old variants on image replacement**
When a new image with the same filename is uploaded, old variants (400_, 800_, 1200_) are not deleted. They remain orphaned in storage.

**2. S3 client lazy initialization stores credentials**
`S3StorageBackend.client` property (storage.py:152-168) initializes boto3 client lazily. The credentials remain on the instance to allow recreation. This is documented as intentional in AGENTS.md ("S3 Client Initialization") but contradicts what might be expected for credential security.

**3. Exception handling in S3 operations**
Many S3 methods catch `ClientError, BotoCoreError` but also have:
```python
except (KeyboardInterrupt, SystemExit):
    raise
```
This pattern is repeated 4 times (load, delete, exists, list_files). These exceptions shouldn't be caught since they indicate the process is being terminated by external signals.

---

## 4. Search (`search.md`)

### Discrepancies

| Issue | Documentation | Actual Implementation |
|-------|---------------|----------------------|
| File location | References `app/search.py` directly | Search is now abstracted via `app/services/search/` provider layer. `app/search.py` contains the FTS5 implementation used by `SQLiteSearchProvider`. |
| `get_search_snippets` batching | Documents `_SQLITE_MAX_VARS = 500` | Correct, line 298 in search.py |
| `get_indexed_terms` fallback | Documents it returns terms from post titles | Implementation (search.py:235-250) matches this. |

### Bugs & Issues

**1. `SQLiteSearchProvider` has no error handling**
The provider methods (sqlite.py:16-43) don't wrap calls in try/except. Any FTS failure propagates to caller. This is arguably correct (let caller decide), but inconsistency with other services that log and return False.

**2. `get_indexed_terms_fallback` in wrong place**
When `fts5vocab` table fails (search.py:231), it falls back to `get_indexed_terms_fallback()`. But this fallback function queries the `posts` table directly (search.py:241), which is a different approach than using FTS vocabulary. This works but is undocumented.

**3. No `init_fts()` in provider abstraction**
The `SearchProvider` base class (services/search/__init__.py) doesn't include an `init()` method. `init_fts()` is called separately during app initialization, not via the provider. This is a gap in the abstraction.

---

## 5. Overview (`overview.md`)

### Issues

**1. References outdated file paths**
- `app/search.py` is the underlying FTS implementation, but the abstraction is `app/services/search/`

**2. Health check optional checks incomplete**
Documents only `backup_freshness` and `email` as optional. Actual health check (meta.py) includes `redis` and `celery` in detailed output but these also don't affect overall status. See AGENTS.md: "Health Check Status Logic".

---

## Recommended Improvements

### Priority 1: Webhook Delivery Reliability

1. **Add per-webhook retry logic**: Modify `deliver_webhook_task` to track failed webhooks and retry them with exponential backoff before marking as `partial_failure` or `failed`.

2. **Fix assertion removal**: Remove `assert event is not None` at tasks.py:248.

3. **Set `delivery_status` consistently**: When no webhooks match, set `delivery_status = 'delivered'` (since there's nothing to deliver) or leave `delivered=True` with explicit status.

4. **Add dead letter tracking**: When queuing fails (webhooks.py:113), update the event record to reflect delivery failure or schedule retry.

### Priority 2: Email Reliability

1. **Document transactional email retry behavior**: Clarify that confirmation/password reset emails rely on Celery task retry (max_retries=3), not SMTP-level retry.

2. **Consider adding SMTP retry to `_send_email()`**: For resilience, consider wrapping `_send_email()` with retry logic similar to `_send_email_with_retry()`.

3. **Add newsletter partial failure handling**: Currently if sending fails at subscriber #50, remaining subscribers aren't attempted. Consider either:
   - Continuing to end and log failures
   - Returning detailed failure info for monitoring

### Priority 3: Storage

1. **Add variant cleanup on image replacement**: When `upload_with_processing()` is called with an existing filename, delete old variants first.

2. **Document S3 variant generation flow**: Add note that variant generation downloads from S3, processes locally, and re-uploads.

### Priority 4: Search

1. **Update overview.md**: Reference `app/services/search/` abstraction instead of `app/search.py`.

2. **Add `init()` to SearchProvider abstraction**: For consistency, consider adding an `initialize()` method to the abstract class and implement in `SQLiteSearchProvider`.

3. **Document fallback behavior**: In search.md, note that `get_indexed_terms()` falls back to querying `posts.title` directly if `fts5vocab` is unavailable.

### Priority 5: Documentation Maintenance

1. **Add this review document to architecture docs**: Consider creating `architecture/infrastructure/REVIEW.md` to track review history.

2. **Cross-reference actual queue locations**: Queue definitions are in `app/tasks.py` but documentation should explicitly note that line numbers may drift.

3. **Add error handling matrix**: Document which operations can fail, how failures manifest, and what recovery mechanisms exist.

---

## Summary

| Component | Issues Found | Priority |
|-----------|-------------|----------|
| Webhooks | No per-webhook retry, no-op assertion, inconsistent delivery_status | High |
| Email | Transactional emails lack retry at SMTP level | Medium |
| Storage | No variant cleanup, S3 flow undocumented | Medium |
| Search | File path outdated, abstraction gap | Low |
| Overview | Incomplete health check docs | Low |