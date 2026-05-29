# Infrastructure Architecture Review

**Reviewed:** 2026-05-29
**Architecture Docs:** overview.md, search.md, email.md, storage.md, webhooks.md
**Source Files:** app/search.py, app/email.py, app/storage.py, app/webhooks.py, app/utils.py

## Findings

### Verified Claims (Correct)

**Search (`app/search.py` and `app/services/search/`):**
- FTS5 virtual table structure with `prefix='2 3 4'` is correctly documented
- BM25 ranking for relevance results
- Prefix matching with `term*` wildcards
- `sync_fts()`, `sync_fts_batch()`, `remove_fts()` return True/False with rollback guidance
- `_FTS_CHECK_TTL = 300` caching (5 minutes) for FTS availability check
- `get_indexed_terms()` uses FTS5 vocabulary table with fallback to post titles
- `highlight_query()` adds `<mark>` tags around matched terms
- `get_did_you_mean()` fuzzy matching with `difflib.get_close_matches`
- `_SQLITE_MAX_VARS = 500` batching for snippet queries
- Query escaping for special FTS5 characters: `()*+":<>`

**Search Provider Abstraction (`app/services/search/`):**
- `SearchProvider` abstract base class with `search()`, `index_post()`, `remove_post()`, `rebuild_index()`, `get_snippets()` methods
- `SQLiteSearchProvider` wraps `app/search.py` FTS5 functions
- `PostgreSQLSearchProvider` is a stub that raises `ConfigurationError`
- Factory function `get_search_provider()` returns configured provider based on `SEARCH_PROVIDER` config

**Email (`app/email.py`):**
- `_send_email()` low-level SMTP with TLS (lines 24-41)
- `_connect_smtp()` returns `None` on failure (lines 78-103)
- `_send_email_with_retry()` has default `max_retries=3` (line 111)
- Newsletter uses `NEWSLETTER_MAX_RETRY_ATTEMPTS` from config (line 209), default 5 (config.py:119)
- Exponential backoff retry logic with `SMTPServerDisconnected` reconnection handling
- `send_newsletter()` logs progress every 50 emails (line 220)

**Storage (`app/storage.py`):**
- `StorageBackend` abstract base class with all documented methods
- `LocalStorageBackend` stores files in `base_dir` with `/static/uploads/{filename}` URL
- `S3StorageBackend` uses boto3 with lazy client initialization via `threading.Lock`
- Singleton pattern for `get_storage()` (module-level `_storage` variable)
- `init_storage()` for local backend initialization
- `storage_delete_file()` convenience function

**Webhooks (`app/webhooks.py` and `app/tasks.py`):**
- Two-level dispatch pattern correctly documented:
  - `deliver_webhook_task` (tasks.py:~195) dispatches per-webhook tasks
  - `deliver_single_webhook_task` (tasks.py:~234) handles individual delivery with retry
- `sign_webhook_payload()` generates HMAC-SHA256 with `sha256=` prefix (lines 32-36)
- `deliver_webhook()` is deprecated (warns at line 56-60)
- SSRF protection via `is_safe_webhook_url()` in `app/utils.py:383-485`
- `allow_redirects=False` prevents redirect-based SSRF bypass (tasks.py:283)
- Webhook encryption via `app/webhook_encryption.py` (AES-256-GCM, 12-byte nonce, 32-byte key)
- `Webhook.secret` property decrypts on demand

**Webhook SSRF Protection (`app/utils.py:383-485`):**
- Blocks loopback: `127.0.0.0/8`, `::1`
- Blocks private: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
- Blocks link-local: `169.254.0.0/16`, `fe80::/10`
- Blocks reserved, multicast, non-global IPs
- Blocks AWS metadata endpoint `169.254.169.254`
- Blocks GCP metadata endpoint `metadata.google.internal`
- Blocks IPv4-mapped IPv6 to private/loopback
- Returns `tuple[bool, str]` with reason

### Discrepancies (Doc vs Code)

1. **webhooks.md:116-118 - Task line numbers are potentially stale:**
   - Doc says `deliver_webhook_task` at `app/tasks.py:194` - code shows at line 194 (correct)
   - Doc says `deliver_single_webhook_task` at `app/tasks.py:233` - code shows at line 234 (off by 1)
   - Line numbers in documentation can become stale as code changes

2. **webhooks.md - Delivery status tracking has incorrect logic:**
   - Doc states: `'delivered'` when all webhooks succeed, `'partial_failure'` when some succeed, `'failed'` when all fail
   - Code at `_update_delivery_status()` (tasks.py:311-330) has flawed logic:
     ```python
     event.delivery_status = "delivered" if event.delivered else "failed"
     ```
   - This does not properly track per-webhook success; it just checks if `event.delivered` is True

3. **overview.md:67 - Thread safety description:**
   - Doc says "Lazy client initialization for S3 uses `threading.Lock`"
   - This is correct (storage.py:153 shows `self._lock = threading.Lock()`)
   - However, the singleton `get_storage()` itself (storage.py:260-265) is NOT thread-safe

### Missing Documentation

1. **Webhook Delivery Status Race Condition:**
   - The `_update_delivery_status()` function (tasks.py:311-330) queries all webhooks to determine status but this creates a race condition
   - The function doesn't properly track per-webhook success/failure state

2. **S3StorageBackend Error Handling:**
   - Methods `load()`, `delete()`, `exists()`, `list_files()` return `False`/`None`/`[]` on error but don't differentiate between "not found" and actual failures
   - This could mask genuine S3 connectivity issues

3. **Search Config - SEARCH_PROVIDER defaults:**
   - Documentation doesn't mention what happens if `SEARCH_PROVIDER` is set to an invalid value
   - The code in `get_search_provider()` silently falls back to SQLite if unknown value

4. **Email Queue - Wrapper Pattern Notes:**
   - The "wrapper pattern" for `send_confirmation()` and `send_password_reset()` being called by Celery tasks is documented correctly but the retry behavior of the tasks themselves isn't documented

5. **Webhook SSRF Protection - DNS Rebinding Time-of-Check:**
   - The `is_safe_webhook_url()` resolves DNS once before the request
   - If DNS changes between validation and request, a previously safe URL could become unsafe
   - No lock or reservation mechanism to hold the resolved IP

### Potential Bugs / Concerns

1. **`_update_delivery_status()` incorrect logic (tasks.py:311-330):**
   - The function determines status by checking `event.delivered` which is set to True before individual webhooks complete
   - This means `'delivered'` could be set even when all webhooks failed
   - Per-webhook success tracking is not implemented

2. **Singleton `get_storage()` not thread-safe (storage.py:260-265):**
   - Multiple threads could simultaneously create multiple storage instances
   - Should use a lock around the `_storage is None` check

3. **S3 `list_files()` swallows all exceptions (storage.py:221-223):**
   ```python
   except (ClientError, BotoCoreError) as e:
       logger.error("S3 operation failed: %s", e)
       return []
   ```
   - Returns empty list for any S3 error, including permission issues
   - Could cause silent failures in listing operations

4. **Webhook task dispatch without error handling (tasks.py:222-223):**
   ```python
   for webhook in webhooks:
       deliver_single_webhook_task.delay(webhook_event_id, webhook.id)
   ```
   - If Celery is unavailable, `delay()` raises `RequestException` which is caught and logged
   - But the event is marked `delivered=True` at line 226 before tasks complete
   - Webhooks could be silently undelivered

5. **Email retry count discrepancy in `_send_email_with_retry()` (email.py:120):**
   - Loop uses `range(max_retries)` but with `max_retries=3`, this gives 3 attempts (indices 0,1,2)
   - The doc claims "3 retries" which is ambiguous - could mean 3 total attempts or 3 retries after initial failure
   - Newsletter code uses `NEWSLETTER_MAX_RETRY_ATTEMPTS=5` which works correctly

6. **S3 `exists()` swallows exceptions (storage.py:199-206):**
   - `head_object()` returns True if file exists, False for any error including "not found"
   - Cannot distinguish between "file doesn't exist" and "S3 error"

### Improvement Suggestions

1. **Add thread safety to storage singleton:**
   ```python
   _storage_lock = threading.Lock()
   def get_storage() -> StorageBackend:
       global _storage
       if _storage is None:
           with _storage_lock:
               if _storage is None:  # Double-check
                   _storage = get_storage_backend()
       return _storage
   ```

2. **Fix `_update_delivery_status()` to track per-webhook success:**
   - Store individual webhook delivery results
   - Update status based on actual success/failure counts

3. **Document the Celery task retry behavior:**
   - `deliver_single_webhook_task` has `max_retries=3` (line 233)
   - This means up to 4 total attempts per webhook
   - Document this in webhooks.md

4. **Add validation for `SEARCH_PROVIDER` config:**
   - Fail loudly if unknown provider configured
   - Add to `get_search_provider()` to raise `ConfigurationError` for unknown values

5. **Consider adding request ID to webhook delivery:**
   - Would help with tracing across `deliver_webhook_task` -> `deliver_single_webhook_task`
   - Currently no correlation ID

6. **Add `get_snippets()` implementation to PostgreSQL stub:**
   - Currently raises `ConfigurationError`
   - Could implement using `ts_headline()` for feature parity

7. **Document S3StorageBackend error behavior:**
   - Clarify that methods return empty/false on any error
   - Consider adding error details to return values or logging

8. **Remove or update hardcoded line numbers in documentation:**
   - Line references like `app/tasks.py:194` become stale
   - Consider using function names instead or a "as of" date

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|---------|
| 1 | high | Fix `_update_delivery_status()` - incorrect delivery status tracking | source (tasks.py:311-330) |
| 2 | high | Add thread safety to `get_storage()` singleton | source (storage.py:260-265) |
| 3 | med | Fix `deliver_webhook_task` marking event delivered before webhook tasks complete | source (tasks.py:226-227) |
| 4 | med | Add error differentiation to S3StorageBackend methods (not_found vs error) | source (storage.py) |
| 5 | med | Add validation for `SEARCH_PROVIDER` config value | source (services/search/__init__.py) |
| 6 | low | Remove hardcoded line numbers from webhooks.md | docs |
| 7 | low | Document Celery task retry behavior (max_retries=3) in webhooks.md | docs |
| 8 | low | Clarify "3 retries" vs "4 total attempts" in email.md | docs (email.md:84) |
| 9 | low | Consider adding correlation ID to webhook delivery chain | source |
