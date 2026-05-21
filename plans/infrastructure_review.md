# Infrastructure Review Plan

## Summary

Reviewed architecture documents in `architecture/infrastructure/` against actual implementation in `app/`:
- `webhooks.md` → `app/webhooks.py`, `app/tasks.py` (deliver_webhook_task), `app/utils.py` (is_safe_webhook_url)
- `search.md` → `app/search.py`, `app/services/search/`
- `email.md` → `app/email.py`, `app/tasks.py`
- `storage.md` → `app/storage.py`, `app/tasks.py` (generate_image_variants)
- `overview.md` → `app/routes/public/meta.py` (health check)

---

## Verified Claims

### Webhooks
- HMAC-SHA256 signing via `sign_webhook_payload()` - **VERIFIED** (`app/webhooks.py:28-36`)
- SSRF Protection via `is_safe_webhook_url()` - **VERIFIED** (`app/utils.py:312-414`)
- `deliver_webhook()` deprecated - **VERIFIED** (`app/webhooks.py:42-59`)
- `deliver_webhook_task` Celery task with `webhooks` queue - **VERIFIED** (`app/tasks.py:182`)
- `WEBHOOK_TIMEOUT = 10` - **VERIFIED** (`app/webhooks.py:20`)
- `allow_redirects=False` - **VERIFIED** (`app/webhooks.py:79`, `app/tasks.py:239`)
- HMAC header `X-Webhook-Signature` - **VERIFIED** (`app/webhooks.py:70`, `app/tasks.py:230`)
- Event types (`post.published`, `post.created`, `subscriber.confirmed`) - **VERIFIED** in code

### Search
- `SearchProvider` abstract class in `app/services/search/__init__.py` - **VERIFIED**
- `SQLiteSearchProvider` wrapping `app/search.py` - **VERIFIED** (`app/services/search/sqlite.py`)
- `PostgreSQLSearchProvider` stub - **VERIFIED** (`app/services/search/postgresql.py`)
- FTS5 virtual table with `prefix='2 3 4'` - **VERIFIED** (`app/search.py:70-72`)
- BM25 ranking - **VERIFIED** (`app/search.py:214`)
- Prefix matching with `"term"*` - **VERIFIED** (`app/search.py:209`)
- SQLite batching with `_SQLITE_MAX_VARS = 500` - **VERIFIED** (`app/search.py:298`)
- FTS availability cache TTL 300 seconds - **VERIFIED** (`app/search.py:30`)
- `get_indexed_terms()` fallback to post titles - **VERIFIED** (`app/search.py:235-250`)

### Email
- SMTP TLS on port 587 - **VERIFIED** (`app/email.py:39`)
- `send_confirmation()`, `send_password_reset()`, `send_newsletter()` - **VERIFIED**
- Retry with exponential backoff - **VERIFIED** (`app/email.py:104-140`)
- `NEWSLETTER_MAX_RETRY_ATTEMPTS` used in newsletter - **VERIFIED** (`app/email.py:197`)
- Progress logging every 50 emails - **VERIFIED** (`app/email.py:206`)

### Storage
- `LocalStorageBackend` and `S3StorageBackend` classes - **VERIFIED** (`app/storage.py:83, 131`)
- Factory `get_storage_backend()` - **VERIFIED** (`app/storage.py:231`)
- Singleton `get_storage()` - **VERIFIED** (`app/storage.py:263`)
- Responsive variants `400_`, `800_`, `1200_` prefixes - **VERIFIED** (`app/tasks.py:64, 97`)
- `upload_with_processing()` queues Celery task - **VERIFIED** (`app/storage.py:318`)

### Health Check
- Critical checks: `database`, `scheduler`, `search`, `disk_space`, `db_integrity` - **VERIFIED** (`app/routes/public/meta.py:286-288`)
- Optional checks: `backup_freshness` (does not affect overall status) - **VERIFIED**
- Redis and Celery checks included but not in critical - **VERIFIED**
- Overall status logic (`ok`/`degraded`) - **VERIFIED** (`app/routes/public/meta.py:290-293`)

---

## Discrepancies

### 1. Queue Line Numbers Off in webhooks.md
**File:** `architecture/infrastructure/webhooks.md:115-118`

The documentation references outdated line numbers in `app/tasks.py`:

| Queue | Doc Line | Actual Line |
|-------|----------|-------------|
| `images` | 29 | 31 |
| `newsletter` | 129 | 130 |
| `email` | 264, 285 | 255, 276 |
| `backup` | 306 | 297 |

**Recommendation:** Remove specific line number references from documentation, or use relative references like "see queue definition in tasks.py".

### 2. Email Optional Check Description Inaccurate
**File:** `architecture/infrastructure/overview.md:34`

The documentation states:
> `email` - SMTP connectivity (if configured)

**Actual implementation** (`app/routes/public/meta.py:220-224`):
```python
if SMTP_HOST:
    health = get_scheduler_health()
    checks["scheduler"] = health["status"]
else:
    checks["scheduler"] = "disabled"
```

There is no `email` key in `checks`. The code only checks if SMTP_HOST is set to determine scheduler status - it does NOT test SMTP connectivity. The scheduler check is actually in `scheduler`, not `email`.

**Recommendation:** Remove `email` from optional checks table, or clarify that the email check is implicit via scheduler health.

### 3. storage.md Missing Original Format Variant Upload for S3
**File:** `architecture/infrastructure/storage.md:94-95`

The documentation states:
> - Original format variants

**Actual implementation** (`app/tasks.py:107-119`): The S3 storage path only uploads WebP variants:
```python
for width in (400, 800, 1200):
    webp_variant_name = f"{width}_{basename}.webp"
    # ... uploads webp only
```

But local storage (`app/tasks.py:64-71`) saves both WebP AND original format variants. S3 only saves WebP variants.

**Recommendation:** Clarify documentation - S3 only generates WebP variants, not original format variants.

---

## Bugs Identified

### Critical: Missing Logger Import in webhooks.py
**File:** `app/webhooks.py:111`

```python
logger.error("Failed to queue webhook event %d for delivery: %s", event_id, e)
```

The `logger` variable is used but never imported or defined at module level. This will cause a `NameError` at runtime when `create_webhook_event()` fails to queue a webhook task.

**Fix:** Add at module level:
```python
logger = logging.getLogger(__name__)
```

**Priority:** Critical

---

## Improvement Recommendations

### 1. Add SMTP Connectivity Health Check
**File:** `app/routes/public/meta.py`

Currently the health check doesn't actually verify SMTP connectivity - it only checks if `SMTP_HOST` is configured. For a proper health check, add actual SMTP connectivity test in the email check:

```python
# Email/SMTP check
try:
    if SMTP_HOST:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=5)
        server.quit()
        checks["email"] = "ok"
    else:
        checks["email"] = "disabled"
except Exception:
    checks["email"] = "error"
```

### 2. Document SSRF Protection in deliver_webhook_task
**File:** `architecture/infrastructure/webhooks.md:66`

The documentation says SSRF protection is applied in both `deliver_webhook()` and `deliver_webhook_task`, but the primary code path for actual webhook delivery is `deliver_webhook_task`. The documentation should clarify that `deliver_webhook_task` is the **actual** delivery function with SSRF protection, while `deliver_webhook()` is deprecated.

### 3. Add Response Handling for Webhook Delivery
**File:** `app/tasks.py:247-248`

The current code sets `event.delivered = delivered_count > 0` which means if ANY webhook succeeds, the event is marked as delivered. If multiple webhooks are configured and one fails, the event is still marked delivered. Consider:
- Marking as delivered only if ALL webhooks succeed, OR
- Adding a `partial_failure` status

### 4. Document Queue Configuration Dependencies
**File:** `architecture/infrastructure/email.md:89-95`

The documentation doesn't mention that `send_confirmation()` and `send_password_reset()` are **synchronous** wrapper functions called by Celery tasks. The wrapper pattern allows async task handling while keeping SMTP logic synchronous. This is correctly noted but could be clearer.

### 5. Health Check Should Include Email in Optional Checks
**File:** `architecture/infrastructure/overview.md:29-35`

The optional checks table shows `email` but no `email` check exists in the code. Either:
- Add the email check to the code, OR
- Remove `email` from the documentation

Currently only `backup_freshness` is the actual optional check that runs.

### 6. Consistent Error Handling in create_webhook_event
**File:** `app/webhooks.py:107-111`

The error handling silently logs and continues:
```python
except (RequestException, ValueError, OSError) as e:
    logger.error("Failed to queue webhook event %d for delivery: %s", event_id, e)
```

If Celery is down, the webhook event is created in the database but never delivered, with only an error log. Consider:
- Adding a `delivery_failed` status to WebhookEvent
- Raising the exception so the task is retried
- Adding metrics/monitoring for failed queue attempts
