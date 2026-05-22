# Infrastructure Documents Review

Reviewed: `architecture/infrastructure/email.md`, `overview.md`, `search.md`, `storage.md`, `webhooks.md`
Verified against: `app/email.py`, `app/webhooks.py`, `app/webhook_encryption.py`, `app/storage.py`, `app/search.py`, `app/services/search/`, `app/tasks.py`

---

## email.md

### Verified Claims

| Claim | Status |
|-------|--------|
| `_send_email()` function with TLS | Verified (`app/email.py:24-43`) |
| `_connect_smtp()` returns None on failure | Verified (`app/email.py:82-101`) |
| `_send_email_with_retry()` with exponential backoff | Verified (`app/email.py:104-140`) |
| `send_newsletter()` function | Verified (`app/email.py:143-216`) |
| Max retries: 5 via `NEWSLETTER_MAX_RETRY_ATTEMPTS` | Verified (`app/config.py:114`) |
| Reconnects on `SMTPServerDisconnected` | Verified (`app/email.py:124-135`) |
| Queue routing: newsletter→`newsletter` queue | Verified (`app/tasks.py`) |
| Queue routing: confirmation→`email` queue | Verified (`app/tasks.py:267`) |
| Queue routing: password reset→`email` queue | Verified (`app/tasks.py:289`) |

### Discrepancies

**"Wrapper Pattern" description is inaccurate** (`email.md:95`):
> `send_confirmation()` and `send_password_reset()` are synchronous functions that are called by their respective Celery tasks.

The doc implies a wrapper pattern where tasks call wrapper functions. In reality, the tasks (`send_confirmation_task`, `send_password_reset_task`) directly call `send_confirmation()` and `send_password_reset()` from `app/email.py`. There is no separate wrapper function - the email module's functions ARE the implementation.

### Bugs Found

**Bug 1: Email tasks silently swallow exceptions and never retry** (`app/tasks.py:268-286, 289-308`)

Both `send_confirmation_task` and `send_password_reset_task` catch exceptions and return `False`:
```python
try:
    send_confirmation(subscriber)
    return True
except Exception as e:
    current_app.logger.error(f"Confirmation email failed: {e}")
    return False
```

Despite having `retry_backoff=True`, these tasks will NOT automatically retry because exceptions are swallowed. With `retry_backoff=True`, Celery expects the task to raise an exception to trigger retry. Either remove `retry_backoff` or implement proper `self.retry()`.

### Improvement Opportunities

| Priority | Issue |
|----------|-------|
| Medium | Fix the "wrapper pattern" language to reflect actual implementation |
| Medium | Document the retry behavior issue for email tasks |

---

## search.md

### Verified Claims

| Claim | Status |
|-------|--------|
| `app/search.py` contains FTS5 implementation | Verified |
| Search provider abstraction in `app/services/search/` | Verified |
| `SearchProvider` abstract base class | Verified (`app/services/search/__init__.py:7-68`) |
| `SQLiteSearchProvider` wraps FTS5 | Verified (`app/services/search/sqlite.py`) |
| `PostgreSQLSearchProvider` stub | Verified (`app/services/search/postgresql.py`) |
| `get_search_provider()` factory | Verified (`app/services/search/__init__.py:70-83`) |
| `SEARCH_PROVIDER` config (default: "sqlite") | Verified (`app/config.py`) |
| FTS5 virtual table with prefix='2 3 4' | Verified (`app/search.py:70-72`) |
| FTS5 vocabulary table | Verified (`app/search.py:75-78`) |
| BM25 ranking | Verified (`app/search.py:214`) |
| Prefix matching with `term*` | Verified (`app/search.py:209`) |
| Snippets via FTS5 `snippet()` | Verified (`app/search.py:303-310`) |
| "Did You Mean" fuzzy suggestions | Verified (`app/search.py:327-353`) |
| LIKE fallback when FTS unavailable | Verified (implicit via `_check_fts_enabled()`) |
| `_FTS_CHECK_TTL = 300` | Verified (`app/search.py:30`) |
| `_SQLITE_MAX_VARS = 500` | Verified (`app/search.py:298`) |
| `FTS_RESULT_LIMIT` config | Verified (`app/config.py`) |
| All core functions: `init_fts`, `rebuild_fts`, `sync_fts`, `sync_fts_batch`, `remove_fts`, `reset_fts_available`, `get_indexed_terms`, `highlight_query`, `search`, `get_search_snippets`, `get_did_you_mean` | All verified |

### Discrepancies

None significant. The document accurately describes the search implementation.

### Bugs Found

No bugs found.

### Improvement Opportunities

| Priority | Issue |
|----------|-------|
| Low | Consider documenting that `highlight_query()` is used for highlighting search terms in results, not FTS5 snippet function |

---

## storage.md

### Verified Claims

| Claim | Status |
|-------|--------|
| `app/storage.py` exists | Verified |
| `LocalStorageBackend` class | Verified (`app/storage.py:83-128`) |
| `S3StorageBackend` class | Verified (`app/storage.py:131-222`) |
| Local `url()` returns `/static/uploads/{filename}` | Verified (`app/storage.py:114-115`) |
| Factory function `get_storage_backend()` | Verified (`app/storage.py:225-251`) |
| Singleton `get_storage()` | Verified (`app/storage.py:254-262`) |
| All environment variables match | Verified |
| `upload_with_processing()` | Verified (`app/storage.py:278-314`) |
| Responsive variants: 400_, 800_, 1200_ .webp | Verified (in `generate_image_variants` task) |

### Discrepancies

**"Original format variants" claim is vague** (`storage.md:95`):
> - Original format variants

This is ambiguous. The actual code generates `.webp` variants (400w, 800w, 1200w) but "original format variants" is unclear. The actual image variants generated are `400_{basename}.webp`, `800_{basename}.webp`, `1200_{basename}.webp` - not original format.

### Bugs Found

No bugs found.

### Improvement Opportunities

| Priority | Issue |
|----------|-------|
| Low | Clarify "Original format variants" or remove if not implemented |

---

## webhooks.md

### Verified Claims

| Claim | Status |
|-------|--------|
| `app/webhooks.py` exists | Verified |
| `app/webhook_encryption.py` exists with AES-256-GCM | Verified |
| `Webhook.secret` property decrypts via AES-256-GCM | Verified (`app/models.py`, `app/webhook_encryption.py`) |
| `WebhookEvent.delivery_status` field | Verified (`app/models.py`) |
| `sign_webhook_payload()` HMAC-SHA256 | Verified (`app/webhooks.py:31-39`) |
| `deliver_webhook()` deprecated | Verified (`app/webhooks.py:42-86`) |
| `create_webhook_event()` queues Celery task | Verified (`app/webhooks.py:89-116`) |
| SSRF protection via `is_safe_webhook_url()` | Verified (`app/utils.py:312-414`) |
| Queue routing matches code | Verified (`app/tasks.py:187,267,289,311`) |
| `webhooks` queue for delivery | Verified (`app/tasks.py:187`) |
| `images` queue at line 31, `newsletter` at 130 | Verified |
| `email` queue at 262, 283, `backup` at 304 | Verified |
| Loopback/private IP blocking | Verified |
| Cloud metadata endpoint blocking (AWS 169.254.169.254, GCP metadata.google.internal) | Verified |
| `allow_redirects=False` | Verified (`app/tasks.py:243`) |

### Discrepancies

None significant. The document accurately describes the webhook system.

### Bugs Found

No bugs found.

### Improvement Opportunities

| Priority | Issue |
|----------|-------|
| Low | Document that `deliver_webhook()` raises `DeprecationWarning` when called |

---

## overview.md

### Verified Claims

| Claim | Status |
|-------|--------|
| Search: `app/search.py` | Verified |
| Email: `app/email.py` | Verified |
| Storage: `app/storage.py` | Verified |
| Webhooks: `app/webhooks.py` | Verified |
| Health check endpoint | Verified |

### Discrepancies

**Minor**: The overview references `app/search.py` for search. While correct that FTS5 implementation is in `app/search.py`, the abstraction layer in `app/services/search/` provides the public API. This is not inaccurate, just incomplete.

### Bugs Found

No bugs found.

### Improvement Opportunities

| Priority | Issue |
|----------|-------|
| Low | Consider noting that search is accessed via `app/services/search/` abstraction layer |

---

## Summary

### Priority: Medium

| Document | Verified | Discrepancies | Bugs |
|----------|----------|---------------|------|
| email.md | High | 1 | 1 (email tasks never retry) |
| search.md | High | 0 | 0 |
| storage.md | High | 1 | 0 |
| webhooks.md | High | 0 | 0 |
| overview.md | High | 1 (minor) | 0 |

### Key Findings

1. **Email task retry bug is significant** - `send_confirmation_task` and `send_password_reset_task` will not retry despite having `retry_backoff=True` because exceptions are caught and swallowed.

2. **Documentation is generally accurate** - Most claims are verified in code.

3. **Wrapper pattern description in email.md is misleading** - The actual implementation directly calls email functions from tasks without a wrapper layer.

4. **Storage "original format variants" is unclear** - Actual implementation generates only `.webp` variants.