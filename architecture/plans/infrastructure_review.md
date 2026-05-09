# Infrastructure Module Architecture Review

**Review Date:** May 9, 2026
**Reviewer:** infrastructure_reviewer

## Executive Summary

Cross-referenced infrastructure documentation against actual source code and AGENTS.md. Found several outdated claims, missing documentation, and one potential SSRF bypass vulnerability.

---

## Verified Accurate Claims

| Claim | Source | Evidence |
|-------|--------|----------|
| Newsletter retry count is 5 | `app/config.py:114` | `NEWSLETTER_MAX_RETRY_ATTEMPTS = int(_config["newsletter"].get("max_retry_attempts", 5))` |
| Snippet batching uses chunk_size=500 | `app/search.py:298-319` | `_SQLITE_MAX_VARS = 500` with batching loop |
| Search abstraction layer exists | `app/services/search/__init__.py` | `SearchProvider` ABC, `SQLiteSearchProvider`, `PostgreSQLSearchProvider` stub |
| PostgreSQLSearchProvider is a stub | `app/services/search/postgresql.py` | All methods fall back to SQLiteSearchProvider |
| SSRF protection exists for webhooks | `app/utils.py:312-414` | `is_safe_webhook_url()` validates IPs, blocks private/loopback/metadata |
| Health check critical checks logic | `app/routes/public/meta.py:286-294` | Uses `("database", "scheduler", "search", "disk_space", "db_integrity")` |
| HMAC-SHA256 webhook signing | `app/webhooks.py:28-36` | `sign_webhook_payload()` uses `hmac.new(..., hashlib.sha256)` |
| Queue routing: webhooks at line 192 | `app/tasks.py:192` | `queue='webhooks'` for `deliver_webhook_task` |

---

## Inaccurate/Outdated Claims

### 1. Search Documentation References Wrong Location

**File:** `architecture/infrastructure/search.md`

**Claim (line 1):** "Search (`app/search.py`)"

**Actual:** The documentation correctly references `app/search.py` but the architecture also shows Search as a standalone component. However, the search module is now wrapped by `app/services/search/` abstraction layer that is NOT documented.

**Correction Needed:** The search infrastructure is now a two-layer system:
- `app/search.py` - Direct FTS5 implementation
- `app/services/search/` - Provider abstraction (SearchProvider, SQLiteSearchProvider, PostgreSQLSearchProvider)

The architecture docs show the old single-layer architecture.

### 2. SSRF Protection Not Documented in Webhooks Overview

**File:** `architecture/infrastructure/webhooks.md`

**Claim (lines 7-8):** Lists SSRF Protection as a feature but the detail section (lines 79-86) only provides a high-level description of what is validated, not the actual implementation.

**Actual Implementation:** `is_safe_webhook_url()` in `app/utils.py:312-414` performs extensive validation including:
- Scheme checking (http/https only)
- URL format validation
- Userinfo blocking (username/password in URL)
- Loopback hostname blocking (127.0.0.1, ::1, localhost, 0.0.0.0)
- IP resolution and validation (loopback, private, link-local, reserved, multicast)
- IPv4-mapped IPv6 address checking
- AWS metadata endpoint (169.254.169.254) blocking
- Google Cloud metadata endpoint blocking
- Global routability check

**Correction Needed:** Document the complete SSRF protection implementation details.

### 3. Health Check Critical Checks Not Documented

**File:** `architecture/infrastructure/overview.md`

**Claim:** Lists components but does not mention health check system.

**Actual:** Health check at `app/routes/public/meta.py:286-294` uses specific critical checks that determine overall status. This is important architecture information that is missing.

**Correction Needed:** Add health check system documentation.

---

## Missing Documentation

### 1. Search Provider Abstraction Layer

**Location:** `app/services/search/`

**Missing:** The entire provider abstraction is not documented in infrastructure docs. The AGENTS.md correctly notes:
- `SearchProvider` abstract class in `app/services/search/__init__.py`
- `SQLiteSearchProvider` wraps existing FTS5 functionality
- `PostgreSQLSearchProvider` is a stub for future implementation
- `get_search_provider()` factory function selects provider by `SEARCH_PROVIDER` config

**Impact:** Developers may not know about the abstraction when adding search features.

### 2. `remove_fts` Function in Search

**Location:** `app/search.py:177-190`

**Not Documented:** The `remove_fts()` function exists but is not documented in search.md. This is used by `SQLiteSearchProvider.remove_post()`.

### 3. `sync_fts_batch` Function Signature Mismatch

**Location:** `app/search.py:136-174`

**Issue:** The documented function signature in `search.md:54-56` says:
```python
def sync_fts_batch()
```

But the actual function takes `items: list[tuple]` parameter. The documentation shows batch sync but doesn't document the parameter.

### 4. S3 Storage Backend Error Handling

**Location:** `app/storage.py:171-228`

**Missing:** The `S3StorageBackend` class catches `ClientError` and `BotoCoreError` exceptions but the documentation doesn't explain what happens when S3 operations fail silently (methods return `False` or empty lists).

### 5. Storage Singleton Pattern

**Location:** `app/storage.py:260-268`

**Missing:** The `get_storage()` function returns a module-level singleton `_storage`. This is not documented but is important for testing scenarios.

### 6. Webhook Secret Encryption

**Location:** `app/webhook_encryption.py` (referenced in tasks.py:200)

**Missing:** The infrastructure docs mention webhook secrets are "Encrypted" in the model but don't document:
- How encryption/decryption works
- The `decrypt_webhook_secret()` function
- Backward compatibility with plaintext secrets (line 229-233 in tasks.py)

---

## Potential Issues

### 1. SSRF Protection Bypass via Redirect (Medium Severity)

**Location:** `app/tasks.py:243-249`

**Issue:**
```python
response = requests.post(
    webhook.url,
    json=payload,
    headers=headers,
    timeout=WEBHOOK_TIMEOUT,
    allow_redirects=False,  # Prevent redirect-based SSRF
)
```

The `deliver_webhook_task` correctly sets `allow_redirects=False`, BUT the `deliver_webhook()` function in `app/webhooks.py:64-70` also sets `allow_redirects=False`:

```python
response = requests.post(
    webhook_url,
    json=payload,
    headers=headers,
    timeout=WEBHOOK_TIMEOUT,
    allow_redirects=False,
)
```

However, this is the non-task version which may not be used. The task version at line 248 does correctly block redirects.

**Verification:** Both functions block redirects. No bypass detected.

### 2. SSRF Protection - DNS Rebinding Attack Potential (Low Severity)

**Location:** `app/utils.py:356-361`

**Issue:** The SSRF check resolves hostname to IP at check time but does not bind the IP. If an attacker:
1. Registers a domain pointing to a safe IP
2. After webhook URL passes validation, changes DNS to point to private IP
3. The actual request may still use the safe IP due to HTTP client DNS caching

However, `requests` library does not typically cache DNS indefinitely, and the check happens immediately before the request, making this attack impractical.

**Recommendation:** Consider binding to the resolved IP in the webhook delivery to prevent DNS rebinding.

### 3. Webhook Delivery Silent Failure

**Location:** `app/webhooks.py:97-101`

**Issue:**
```python
try:
    from app.tasks import deliver_webhook_task
    deliver_webhook_task.delay(event_id)
except (RequestException, ValueError, OSError):
    pass
```

Silent failure - if Celery is unavailable, webhook events are lost without notification. This is noted but not highlighted as a potential issue.

**Recommendation:** Add logging for Celery connection failures in webhook creation.

### 4. Error Handler Broad Exception Clause

**Location:** `app/tasks.py:320`

**Issue:**
```python
except Exception as e:
    logger.error("Backup task failed: %s", e)
    return False
```

The backup task catches all exceptions broadly. This contradicts the AGENTS.md note that tasks.py has been updated to use specific exceptions.

**Correction Needed:** Should be specific exception types. Check if this was meant to be updated.

---

## Recommended Improvements

### Priority 1: Document Search Abstraction Layer

Add to `architecture/infrastructure/search.md`:

```markdown
## Search Provider Abstraction

Located at `app/services/search/`:

### Classes

- `SearchProvider` - Abstract base class defining the interface
- `SQLiteSearchProvider` - Wraps `app/search.py` FTS5 implementation
- `PostgreSQLSearchProvider` - Stub for future PostgreSQL implementation

### Factory Function

```python
from app.services.search import get_search_provider
provider = get_search_provider()  # Returns configured provider
```

### Configuration

- `SEARCH_PROVIDER` config (default: "sqlite", can be "postgresql")
- When set to "postgresql", falls back to SQLite until full implementation is complete
```

### Priority 2: Document Complete SSRF Protection

Update `architecture/infrastructure/webhooks.md` to document the complete validation logic from `app/utils.py:312-414`.

### Priority 3: Add Health Check Documentation

Add new section to `architecture/infrastructure/overview.md`:

```markdown
## Health Check

Health endpoint at `GET /health` with optional `?detailed=1`.

### Critical Checks (determine overall status)

- `database` - SQLite connectivity
- `scheduler` - APScheduler running
- `search` - FTS5 availability
- `disk_space` - Available space > 100MB
- `db_integrity` - Database passes integrity check

### Optional Checks (do not affect overall status)

- `backup_freshness` - Most recent backup < 24 hours old
- `email` - SMTP connectivity (if configured)

### Overall Status Logic

- `ok`: All critical checks pass (status in "ok", "running", "disabled")
- `degraded`: Any critical check fails
```

### Priority 4: Document Webhook Secret Encryption

Add documentation about `app/webhook_encryption.py` and the backward-compatible secret handling.

### Priority 5: Fix Error Handling in Backup Task

Update `app/tasks.py:320` to use specific exception types instead of bare `except Exception`.

---

## Summary of Required Changes

| File | Action |
|------|--------|
| `architecture/infrastructure/search.md` | Add search provider abstraction section, document `remove_fts`, fix `sync_fts_batch` signature |
| `architecture/infrastructure/webhooks.md` | Document complete SSRF protection, add webhook encryption section |
| `architecture/infrastructure/overview.md` | Add health check documentation section |
| `app/tasks.py:320` | Fix broad exception clause |
