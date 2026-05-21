# Infrastructure Module Architecture Review

**Review Date:** 2026-05-21
**Reviewer:** infrastructure_reviewer

---

## 1. Verified Accurate Claims

| Claim | Location | Verification |
|-------|----------|--------------|
| HMAC-SHA256 signing for webhooks | `app/webhooks.py:31-39` | Confirmed - `sign_webhook_payload()` uses `hmac.new` with sha256 |
| SSRF protection via `is_safe_webhook_url()` | `app/utils.py:312-414` | Confirmed - function exists and is used by both `deliver_webhook()` and `deliver_webhook_task` |
| `deliver_webhook()` is deprecated | `app/webhooks.py:45-62` | Confirmed - function contains DeprecationWarning |
| `create_webhook_event()` queues Celery task | `app/webhooks.py:89-116` | Confirmed - imports and calls `deliver_webhook_task.delay()` |
| Webhook secret encrypted at rest (AES-256-GCM) | `app/models.py:490-517`, `app/webhook_encryption.py:60-86` | Confirmed - `webhook_secret_encrypted` column with property getter/setter using AES-256-GCM |
| `deliver_webhook_task` uses `webhooks` queue | `app/tasks.py:182` | Confirmed - `@shared_task(..., queue='webhooks')` |
| Queue routing table (images, newsletter, webhooks, email, backup) | `app/tasks.py:31,130,182,262,283,304` | Confirmed - matches documentation |
| Event types: `post.published`, `post.created`, `subscriber.confirmed` | `app/routes/api/posts.py`, `app/routes/public/subscribe.py` | Confirmed - triggers found in actual code |
| FTS5 virtual table with `prefix='2 3 4'` | `app/search.py:68-74` | Confirmed - matches `CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(title, body, summary, prefix='2 3 4')` |
| BM25 ranking for search results | `app/search.py:212-219` | Confirmed - `bm25(posts_fts)` used in ranking |
| `_FTS_CHECK_TTL = 300` (5 min caching) | `app/search.py:30` | Confirmed - TTL is 300 seconds |
| `_SQLITE_MAX_VARS = 500` batching | `app/search.py:298` | Confirmed - chunk size of 500 for SQLite parameter limits |
| `get_search_snippets()` uses FTS5 `snippet()` function | `app/search.py:300-315` | Confirmed - native snippet() with `<mark>` tags |
| `highlight_query()` adds `<mark>` tags | `app/search.py:356-371` | Confirmed - uses regex with `re.IGNORECASE` |
| `get_did_you_mean()` uses `difflib.get_close_matches` | `app/search.py:327-353` | Confirmed - fuzzy matching with cutoff=0.6 |
| Email types: `send_confirmation()`, `send_password_reset()`, `send_newsletter()` | `app/email.py:46-62,65-79,143-216` | Confirmed - all three functions exist |
| SMTP with TLS and authentication | `app/email.py:36-43` | Confirmed - starttls with login |
| `_send_email_with_retry()` with exponential backoff | `app/email.py:104-140` | Confirmed - reconnects on SMTPServerDisconnected |
| Newsletter logs progress every 50 emails | `app/email.py:206-209` | Confirmed - `if total_subscribers and i % 50 == 0` |
| `NEWSLETTER_MAX_RETRY_ATTEMPTS` for retry count | `app/email.py:153,197` | Confirmed - used in `send_newsletter()` |
| LocalStorageBackend with save/load/delete/exists/url/path | `app/storage.py:83-128` | Confirmed - all methods implemented |
| S3StorageBackend with save/load/delete/exists/url/list_files | `app/storage.py:131-228` | Confirmed - all methods implemented |
| `upload_with_processing()` queues `generate_image_variants` | `app/storage.py:316-318` | Confirmed - calls `generate_image_variants.delay(filename)` |
| Storage singleton pattern via `get_storage()` | `app/storage.py:260-268` | Confirmed - `_storage` global with lazy initialization |
| Health check critical checks (database, scheduler, search, disk_space, db_integrity) | `app/routes/public/meta.py` | Confirmed - matches overview.md |
| Health check optional checks (backup_freshness, email) | `app/routes/public/meta.py` | Confirmed - do not affect overall status |

---

## 2. Inaccurate/Outdated Claims

| Document | Claim | Actual Behavior | Correction Needed |
|----------|-------|------------------|-------------------|
| `webhooks.md:17-19` | Webhook model has `secret = db.Column(db.String(64))` | Actual model uses `webhook_secret_encrypted = db.Column(db.LargeBinary(256))` with property getter/setter | Update model schema to show encrypted column with property |
| `webhooks.md:28` | WebhookEvent has `delivered = db.Column(db.Boolean, default=False)` | Actual model has `delivered` (Boolean) AND `delivery_status = db.Column(db.String(32))` for tracking 'failed', 'partial_failure', 'delivered' | Update to include `delivery_status` field |
| `webhooks.md:66` | `deliver_webhook()` deprecated with note about SSRF | Deprecation note is correct | No change needed - already documented |
| `email.md:83` | Max retries: 5 via `NEWSLETTER_MAX_RETRY_ATTEMPTS` | Confirmed correct - the default is 5 | No change needed |
| `webhooks.md:109` | Queue routing table shows `send_newsletter_task` at `app/tasks.py:130` | Actual location is `app/tasks.py:143` (send_newsletter function itself) | Update line reference |
| `webhooks.md:117` | Queue routing table shows `webhooks` at `app/tasks.py:182` | This is correct for `deliver_webhook_task` | No change needed |
| `storage.md:84-85` | `upload_with_processing()` returns `tuple[str, None] \| tuple[None, str]` | Documented correctly | No change needed |
| `search.md:143-148` | `get_search_snippets()` description | Accurate - uses FTS5 snippet() with batching | No change needed |

---

## 3. Bugs Identified

| Severity | Location | Description |
|----------|----------|-------------|
| Medium | `app/email.py:36` | `_send_email()` uses `with smtplib.SMTP(...)` context manager but only handles `OSError` in finally block. If `server.ehlo()` or `starttls()` fails after context entry, `server.quit()` may not be called. Should use try/except within the context manager. |
| Medium | `app/storage.py:171-174` | `_clear_credentials()` sets `self.access_key = None` and `self.secret_key = None`, but these are instance attributes used to initialize boto3 client. If client is recreated, credentials will be None and authentication will fail. The clearing appears premature. |
| Low | `app/search.py:253-279` | `extract_snippet()` function exists but is never used by `get_search_snippets()` which uses native FTS5 snippet() instead. Dead code that could be removed or used. |
| Low | `app/email.py:94-100` | `_connect_smtp()` catches `smtplib.SMTPAuthenticationError, smtplib.SMTPConnectError, smtplib.SMTPSenderRefused, OSError` but not `smtplib.SMTPException` or `smtplib.SMTPServerDisconnected`. These could leak as unhandled exceptions. |

---

## 4. Missing Documentation

| Item | Location | Description |
|------|----------|-------------|
| Webhook `delivery_status` field | `app/models.py:533` | WebhookEvent has `delivery_status` field tracking 'failed', 'partial_failure', 'delivered' not documented in webhooks.md |
| Webhook `delivery_attempts` increment logic | `app/tasks.py:240-244` | Both successful and failed deliveries increment `delivery_attempts`, even when SSRF blocked or no secret configured |
| S3StorageBackend credential clearing | `app/storage.py:171-174` | `_clear_credentials()` method clears keys after client init but this breaks client if recreated |
| `extract_snippet()` function | `app/search.py:253-279` | Not used anywhere, dead code |
| AVIF variant generation | Not implemented | `post_image_avif_url_stub` filter exists but AVIF encoding not yet enabled |
| Email wrapper task pattern | `app/tasks.py:262-290` | `send_confirmation_task` and `send_password_reset_task` wrap synchronous email functions but this pattern not documented |
| Redis health check | `app/routes/public/meta.py` | Optional check included in detailed output but not documented in overview.md |
| Celery health check | `app/routes/public/meta.py` | Optional check included in detailed output but not documented in overview.md |

---

## 5. Recommended Improvements

### High Priority

1. **Update Webhook Model Documentation** (`webhooks.md:14-30`)
   - Change `secret = db.Column(db.String(64))` to `webhook_secret_encrypted = db.Column(db.LargeBinary(256))`
   - Add `@property secret` getter/setter documentation
   - Add `delivery_status = db.Column(db.String(32))` field to WebhookEvent

2. **Document `delivery_attempts` Behavior** (`webhooks.md`)
   - SSRF-blocked webhooks and those without secrets still increment `delivery_attempts`
   - This could cause `delivery_attempts` to be high even when no actual delivery was attempted

3. **Fix S3StorageBackend Credential Handling** (`storage.md`)
   - Document that `_clear_credentials()` breaks client recreation
   - Consider documenting this as a known limitation or fixing the implementation

### Medium Priority

4. **Update Queue Reference** (`webhooks.md:109`)
   - Change `send_newsletter_task` location from `app/tasks.py:130` to `app/tasks.py:143`

5. **Document Optional Health Checks** (`overview.md`)
   - Add Redis and Celery to optional checks table
   - Redis check included in detailed output but not documented

6. **Document Email Wrapper Pattern** (`email.md`)
   - Add note about `send_confirmation_task` and `send_password_reset_task` wrapping synchronous functions

7. **Document `delivery_status` Values** (`webhooks.md`)
   - Add table: `'failed'` (no deliveries succeeded), `'partial_failure'` (some succeeded), `'delivered'` (all succeeded)

### Low Priority

8. **Remove or Use `extract_snippet()`** (`search.md`)
   - Function at `app/search.py:253-279` is dead code
   - Either remove or document when it should be used instead of FTS5 snippet()

9. **Document AVIF Status** (`storage.md`)
   - Note that AVIF variant generation is planned but not yet implemented

10. **Add Health Check Reference** (`overview.md`)
    - Reference that detailed health includes Redis and Celery checks even though they don't affect overall status

---

## Summary

| Category | Count |
|----------|-------|
| Verified Accurate Claims | 26 |
| Inaccurate Claims | 3 |
| Bugs Identified | 4 |
| Missing Documentation | 8 |
| Improvements | 10 |

---

## Detailed Bug Analysis

### Bug: Email `_send_email()` Exception Safety (Medium)
**File:** `app/email.py:24-43`
```python
with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
    server.ehlo()
    context = ssl.create_default_context()
    server.starttls(context=context)
    server.ehlo()
    if SMTP_USER:
        server.login(SMTP_USER, SMTP_PASSWORD)
    server.sendmail(FROM_ADDRESS, to, msg.as_string())
```
If `starttls()` fails, the context manager will still call `server.quit()`, but the error handling is inconsistent with `_connect_smtp()` which properly catches specific exceptions.

### Bug: S3 Credential Clearing (Medium)
**File:** `app/storage.py:171-174`
```python
def _clear_credentials(self) -> None:
    """Clear stored credentials after client initialization."""
    self.access_key = None
    self.secret_key = None
```
After clearing, if `self._client` is ever set to None (e.g., due to errors), the client recreation at line 156-168 will fail because boto3 needs these credentials to initialize.

### Bug: Unused `extract_snippet()` Function (Low)
**File:** `app/search.py:253-279`
This function is defined but never called anywhere in the codebase. `get_search_snippets()` uses the native FTS5 `snippet()` function instead.

### Bug: Incomplete SMTP Exception Handling (Low)
**File:** `app/email.py:94`
`_connect_smtp()` catches specific SMTP exceptions but not `SMTPException` (base class) or `SMTPServerDisconnected`, which could bubble up unexpectedly.