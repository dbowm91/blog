# Infrastructure Review: Search, Email, Storage, Webhooks

## Summary

Reviewed architecture documents against actual implementation in `app/search.py`, `app/email.py`, `app/storage.py`, and `app/webhooks.py`. Found several discrepancies, three high-risk exception handlers, and missing async wrapper documentation.

---

## Verified Claims

### Search (`app/search.py`)

| Claim | Status | Evidence |
|-------|--------|----------|
| FTS5 virtual table with prefix='2 3 4' | ✅ Verified | `app/search.py:68-73` |
| BM25 ranking | ✅ Verified | `app/search.py:214` |
| `posts_fts_vocab` table | ✅ Verified | `app/search.py:75-78` |
| `_SQLITE_MAX_VARS = 500` batching | ✅ Verified | `app/search.py:298` |
| `_FTS_CHECK_TTL = 300` caching | ✅ Verified | `app/search.py:30` |
| `sync_fts()` callable before commit | ✅ Verified | `app/search.py:112` |
| `rebuild_fts()` using rebuild command | ✅ Verified | `app/search.py:105` |
| LIKE fallback on FTS failure | ✅ Implied | Returns `[]` on exception (`app/search.py:220-221`) |

### Email (`app/email.py`)

| Claim | Status | Evidence |
|-------|--------|----------|
| TLS SMTP connection | ✅ Verified | `app/email.py:38-40` |
| `_send_email()` low-level send | ✅ Verified | `app/email.py:24-43` |
| `_connect_smtp()` returns None on failure | ✅ Verified | `app/email.py:82-101` |
| Exponential backoff retry | ✅ Verified | `app/email.py:118` |
| 5 max retries (`NEWSLETTER_MAX_RETRY_ATTEMPTS`) | ✅ Verified | `app/email.py:197` |
| Progress logging every 50 emails | ✅ Verified | `app/email.py:206-209` |

### Storage (`app/storage.py`)

| Claim | Status | Evidence |
|-------|--------|----------|
| Local and S3 backends | ✅ Verified | `app/storage.py:83-228` |
| `get_storage_backend()` factory | ✅ Verified | `app/storage.py:231-257` |
| Singleton `get_storage()` | ✅ Verified | `app/storage.py:260-268` |
| `upload_with_processing()` queues Celery task | ✅ Verified | `app/storage.py:316-318` |
| Responsive variants: 400/800/1200 webp + original | ✅ Verified | `app/tasks.py:55-70` |

### Webhooks (`app/webhooks.py`)

| Claim | Status | Evidence |
|-------|--------|----------|
| HMAC-SHA256 signing with `sha256=` prefix | ✅ Verified | `app/webhooks.py:28-36` |
| SSRF protection via `is_safe_webhook_url()` | ✅ Verified | `app/webhooks.py:51-55`, `app/utils.py:312-414` |
| 10 second timeout | ✅ Verified | `app/webhooks.py:20`, `app/tasks.py:247` |
| `allow_redirects=False` | ✅ Verified | `app/tasks.py:248` |
| `deliver_webhook_task` in `webhooks` queue | ✅ Verified | `app/tasks.py:192` |

---

## Discrepancies

### 1. Email: Confirmation/Reset not async

**Documentation** (`architecture/infrastructure/email.md:88-93`) states:
| Task | Queue | Purpose |
|-----|-------|---------|
| `send_confirmation_task` | `email` | Subscriber confirmation emails |

**Reality**: `send_confirmation()` and `send_password_reset()` in `app/email.py` are **synchronous** direct calls. The `_send_email()` function at `app/email.py:24` makes a direct SMTP connection.

The Celery tasks `send_confirmation_task` (`app/tasks.py:264`) and `send_password_reset_task` (`app/tasks.py:285`) wrap these functions, but the core email functions themselves are not inherently async.

**Impact**: Low - callers can still use async tasks. Documentation could be clearer about the wrapper pattern.

### 2. Search: Missing functions in docs

`app/search.py` exports these functions not documented in `architecture/infrastructure/search.md`:

- `remove_fts()` - `app/search.py:177` - Removes a post from FTS index
- `sync_fts_batch()` - `app/search.py:136` - Batch sync multiple posts
- `reset_fts_available()` - `app/search.py:36` - Cache invalidation
- `get_indexed_terms()` - `app/search.py:224` - Gets indexed terms from vocab table
- `highlight_query()` - `app/search.py:356` - Adds `<mark>` tags

### 3. Webhooks: Duplicate signing function

`app/webhooks.py:28` defines `sign_webhook_payload()` but `app/tasks.py:181` duplicates it as `_sign_webhook_payload()`. The Celery task `deliver_webhook_task` imports from `tasks.py` local function instead of `webhooks.py`.

**Impact**: Maintenance burden, potential for inconsistency if one is updated without the other.

---

## Bugs & High-Risk Exception Handlers

Per AGENTS.md, these files have a history of broad `except Exception` clauses:

### 1. `app/tasks.py:320` - Backup task broad exception

```python
except Exception as e:
    logger.error("Backup task failed: %s", e)
    return False
```

**Issue**: Catches all exceptions including `KeyboardInterrupt`, `SystemExit`, and `CeleryTaskError`. Should catch specific exceptions.

### 2. `app/webhooks.py:100` - Silent failure on task queuing

```python
try:
    from app.tasks import deliver_webhook_task
    deliver_webhook_task.delay(event_id)
except (RequestException, ValueError, OSError):
    pass
```

**Issue**: Swallows all failures silently. If Celery is down, `create_webhook_event()` returns an event_id but the event is never delivered without any error indication.

**Impact**: **Critical** - Webhook events can be created and committed to DB but never queued, with no warning to operators.

### 3. `app/email.py:94` - SMTP connection broad exception

```python
except (smtplib.SMTPException, OSError):
    logger.exception("Failed to connect to SMTP server")
```

**Issue**: `SMTPException` is the base class for all SMTP errors. Also catches `OSError` which is too broad. Should catch specific subclasses like `SMTPAuthenticationError`, `SMTPConnectError`, etc.

---

## Security Issues

### 1. SSRF protection exists but not enforced in `webhooks.py`

`app/webhooks.py:deliver_webhook()` performs SSRF validation at line 53, but `app/tasks.py:deliver_webhook_task` also validates at line 221. Both check `is_safe_webhook_url()`, which is correct, but the fact that `webhooks.py:deliver_webhook()` exists and is separately callable could lead to SSRF bypass if called directly bypassing the Celery task.

**Recommendation**: Deprecate `webhooks.py:deliver_webhook()` and require all deliveries go through the Celery task which enforces SSRF protection.

### 2. Webhook secret decryption failure uses secret as-is

`app/tasks.py:229-233`:
```python
if secret and not secret.startswith("sha256="):
    try:
        secret = decrypt_webhook_secret(secret)
    except WebhookEncryptionError:
        logger.warning("Failed to decrypt webhook secret for %s, using as-is", webhook.name)
```

If decryption fails, the (presumably encrypted) secret is used directly as the HMAC key, which will produce incorrect signatures.

---

## Improvement Recommendations

### HIGH PRIORITY

1. **Fix silent failure in `app/webhooks.py:97-101`**
   ```python
   except (RequestException, ValueError, OSError):
       pass
   ```
   **Recommendation**: Log a warning and store delivery status as failed:
   ```python
   except (RequestException, ValueError, OSError) as e:
       logger.error("Failed to queue webhook event %d for delivery: %s", event_id, e)
   ```

2. **Fix broad exception in `app/tasks.py:320`**
   ```python
   except Exception as e:
   ```
   **Recommendation**: Catch specific exceptions:
   ```python
   except (SQLAlchemyError, OSError, ImportError) as e:
   ```

### MEDIUM PRIORITY

3. **Unify webhook signing function** - Remove `app/tasks.py:181-189` `_sign_webhook_payload()` and have `deliver_webhook_task` import from `app/webhooks.py`.

4. **Document missing search functions** - Add `remove_fts()`, `sync_fts_batch()`, `reset_fts_available()`, `get_indexed_terms()`, `highlight_query()` to `architecture/infrastructure/search.md`.

5. **Clarify async email pattern** - Update `architecture/infrastructure/email.md` to clarify that `send_confirmation()` and `send_password_reset()` are synchronous wrappers called by async Celery tasks.

6. **Refine SMTP exception handling** - `app/email.py:94` should catch specific SMTP exceptions rather than the base `SMTPAuthenticationError`, `SMTPConnectError`, etc.

### LOW PRIORITY

7. **Consider deprecating `webhooks.py:deliver_webhook()`** - Since `deliver_webhook_task` in tasks.py handles all delivery with proper SSRF protection, the direct delivery function may be unnecessary.

---

## Files Referenced

| File | Lines | Issue |
|------|-------|-------|
| `app/webhooks.py` | 97-101 | Silent failure on task queuing |
| `app/tasks.py` | 181-189 | Duplicate signing function |
| `app/tasks.py` | 320 | Broad `except Exception` |
| `app/email.py` | 94 | Broad SMTP exception |
| `app/email.py` | 24-43 | Synchronous `_send_email()` |
| `app/tasks.py` | 264, 285 | Celery task wrappers for email |
| `app/utils.py` | 312-414 | SSRF protection implementation |
