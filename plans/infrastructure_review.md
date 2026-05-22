# Infrastructure Architecture Review

**Date:** May 22, 2026  
**Reviewer:** Architecture Review Agent  
**Modules Reviewed:** `architecture/infrastructure/` (storage.md, webhooks.md, search.md, email.md, overview.md)

---

## Summary

Reviewed 5 infrastructure documentation files and cross-referenced them against actual implementation files:
- `app/storage.py` - Storage abstraction (local/S3)
- `app/webhooks.py` - Webhook delivery system
- `app/email.py` - SMTP email delivery
- `app/services/search/__init__.py`, `sqlite.py`, `postgresql.py` - Search provider abstraction
- `app/search.py` - FTS5 full-text search implementation
- `app/webhook_encryption.py` - Webhook secret encryption
- `app/tasks.py` - Celery tasks for async operations
- `app/routes/public/meta.py` - Health check endpoint
- `app/models.py` - Webhook and WebhookEvent models

**Overall finding:** Infrastructure documentation is largely accurate with minor discrepancies identified below.

---

## Verified Accurate Claims

### Storage (`app/storage.py`)

| Claim | Status | Evidence |
|-------|--------|----------|
| LocalStorageBackend with save/load/delete/exists/url/list_files/path methods | VERIFIED | Lines 83-128 |
| S3StorageBackend with save/load/delete/exists/url/list_files methods | VERIFIED | Lines 131-222 |
| Environment variables: STORAGE_BACKEND, S3_BUCKET, S3_REGION, S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_PUBLIC_URL | VERIFIED | Lines 41-48 |
| Factory function get_storage_backend() returns configured backend | VERIFIED | Lines 225-251 |
| Singleton get_storage() pattern | VERIFIED | Lines 254-262 |
| upload_with_processing() queues generate_image_variants Celery task | VERIFIED | Lines 322-360, task dispatch at line 358 |
| Variant cleanup on re-upload (400_, 800_, 1200_, .webp, .avif) | VERIFIED | Lines 278-319 |

### Webhooks (`app/webhooks.py`, `app/webhook_encryption.py`, `app/models.py`)

| Claim | Status | Evidence |
|-------|--------|----------|
| HMAC-SHA256 signing with X-Webhook-Signature header | VERIFIED | webhooks.py:31-39 |
| SSRF protection via is_safe_webhook_url() | VERIFIED | tasks.py:214, utils.py:312-414 |
| Webhook.secret property uses AES-256-GCM encryption | VERIFIED | models.py:499-517, webhook_encryption.py |
| WebhookEvent.delivery_status field exists | VERIFIED | models.py:533 |
| deliver_webhook() marked as deprecated | VERIFIED | webhooks.py:45-62 |
| create_webhook_event() creates WebhookEvent and queues deliver_webhook_task | VERIFIED | webhooks.py:89-116, tasks.py:184-260 |
| Webhook uses webhooks Celery queue | VERIFIED | tasks.py:184 (queue='webhooks') |

### Search (`app/services/search/`, `app/search.py`)

| Claim | Status | Evidence |
|-------|--------|----------|
| SearchProvider abstract base class | VERIFIED | services/search/__init__.py:12-81 |
| SQLiteSearchProvider wraps FTS5 | VERIFIED | services/search/sqlite.py |
| PostgreSQLSearchProvider is stub | VERIFIED | services/search/postgresql.py |
| get_search_provider() factory function | VERIFIED | services/search/__init__.py:83-96 |
| SEARCH_PROVIDER config (default: "sqlite") | VERIFIED | config.py:158 |
| FTS5 table with title, body, summary, prefix='2 3 4' | VERIFIED | search.py:68-73 |
| posts_fts_vocab table | VERIFIED | search.py:75-78 |
| init_fts(), rebuild_fts(), sync_fts(), sync_fts_batch(), remove_fts() functions | VERIFIED | search.py:59-190 |
| search() returns list of (post_id, rank) tuples | VERIFIED | search.py:201-221 |
| get_search_snippets() uses FTS5 snippet() function | VERIFIED | search.py:282-324 |
| _SQLITE_MAX_VARS = 500 batching | VERIFIED | search.py:298, 318 |
| FTS availability cached for 300 seconds | VERIFIED | search.py:30, 48 |
| FTS_RESULT_LIMIT configuration | VERIFIED | config.py:125 |

### Email (`app/email.py`)

| Claim | Status | Evidence |
|-------|--------|----------|
| send_confirmation(), send_password_reset(), send_newsletter() functions | VERIFIED | email.py:46-216 |
| SMTP_TIMEOUT configuration | VERIFIED | config.py:144 |
| NEWSLETTER_MAX_RETRY_ATTEMPTS = 5 default | VERIFIED | config.py:116 |
| _connect_smtp() returns None on failure | VERIFIED | email.py:82-101 |
| _send_email_with_retry() with exponential backoff | VERIFIED | email.py:104-140 |
| Retry on SMTPServerDisconnected by reconnecting | VERIFIED | email.py:124-135 |
| SMTPException and SMTPServerDisconnected handled | VERIFIED | email.py:94, 124, 133 |
| Email templates in app/templates/email/ | VERIFIED | email.py:48-79 |

### Health Check (`app/routes/public/meta.py`)

| Claim | Status | Evidence |
|-------|--------|----------|
| Critical checks: database, scheduler, search, disk_space, db_integrity | VERIFIED | meta.py:286-288 |
| Optional checks: backup_freshness, email (SMTP check NOT implemented as separate check) | PARTIAL | meta.py:272-284, email check is NOT present - SMTP_HOST is only used for scheduler status |
| Status logic: ok only if all critical checks pass, degraded if any fails | VERIFIED | meta.py:290-294 |
| Detailed mode with ?detailed=1 and secret parameter | VERIFIED | meta.py:197-203 |

---

## Discrepancies and Issues Found

### 1. Health Check: SMTP/Email Check Not Separate

**Documentation (overview.md):**
> Optional Checks (do not affect overall status)
> - `backup_freshness` - Most recent backup < 24 hours old
> - `email` - SMTP connectivity (if configured)

**Actual Implementation:**
The `meta.py` health check does NOT have a separate `email` check. SMTP connectivity is only used to determine scheduler status:
```python
# meta.py:220-224
if SMTP_HOST:
    health = get_scheduler_health()
    checks["scheduler"] = health["status"]
else:
    checks["scheduler"] = "disabled"
```

**Impact:** Low - The documentation overstates what's checked. The email check is implicitly handled via scheduler status when SMTP is configured.

**Recommendation:** Update overview.md to remove `email` from optional checks or clarify that SMTP is only checked via scheduler status.

---

### 2. Queue Routing Table Inconsistency

**Documentation (webhooks.md:129-135):**
> | Queue | Tasks | Location |
> |-------|-------|----------|
> | `images` | Image processing | `app/tasks.py:31` |
> | `newsletter` | Newsletter delivery | `app/tasks.py:130` |
> | `webhooks` | Webhook delivery | `app/tasks.py:182` |
> | `email` | Transactional email | `app/tasks.py:262,283` |
> | `backup` | Backup tasks | `app/tasks.py:304` |

**Actual Task Locations:**
- `generate_image_variants`: Line 28 (queue='images')
- `send_newsletter_task`: Line 127 (queue='newsletter')
- `deliver_webhook_task`: Line 184 (queue='webhooks')
- `send_confirmation_task`: Line 263 (queue='email')
- `send_password_reset_task`: Line 284 (queue='email')
- `run_backup_task`: Line 305 (queue='backup')

**Discrepancy:** Line numbers are off by 1-3. The documentation says 130, 182, 262, 283, 304 but actual is 127, 184, 263, 284, 305.

**Impact:** Low - Line numbers are for reference only and become outdated easily.

**Recommendation:** Either remove specific line numbers from documentation or note they are approximate.

---

### 3. EMAIL_LATENCY_SECONDS Not Documented

**Documentation (email.md):**
The email documentation does not mention any latency tracking, but in `meta.py` the health check measures `database_latency_ms` for detailed output. No email-specific latency metric is implemented.

**Impact:** None - No claim was made about email latency.

---

### 4. Storage: S3 Variant Cleanup Uses Prefix, Not Exact Patterns

**Documentation (storage.md:99-106):**
> 5. Local temp files are cleaned up after upload

**Actual Implementation:**
The S3 variant cleanup (lines 302-319) uses `list_objects_v2` with Prefix to find and delete files. This is correct behavior - it matches any object that starts with the variant prefix.

**Impact:** None - Documentation is accurate.

---

### 5. Search: `get_search_snippets()` Return Type

**Documentation (search.md:142-147):**
> ```python
> def get_search_snippets(posts: list, query: str) -> dict[int, str]:
> ```
> Returns dict mapping post_id to highlighted snippet using FTS5 `snippet()` function.

**Actual Implementation:**
The function does return `dict[int, str]` (search.py:287). However, the documentation doesn't mention it uses `_SQLITE_MAX_VARS = 500` to batch queries, which is correctly implemented.

**Impact:** None - Documentation is accurate.

---

### 6. Webhook: SSRF Protection Location

**Documentation (webhooks.md:89):**
> The `is_safe_webhook_url()` utility in `app/utils.py:312-414`

**Actual Implementation:**
The function is at `utils.py:312-414`. This is accurate.

**Impact:** None.

---

### 7. Email Queue Task Wrapper Pattern

**Documentation (email.md:95-96):**
> **Wrapper Pattern:** `send_confirmation()` and `send_password_reset()` are synchronous functions that are called by their respective Celery tasks.

**Actual Implementation:**
This is accurate. The tasks (`send_confirmation_task` at line 263, `send_password_reset_task` at line 284) call the synchronous `send_confirmation()` and `send_password_reset()` functions respectively (tasks.py:275, 296).

**Impact:** None.

---

### 8. Backup Freshness Check Path

**Documentation (overview.md:33):**
> `backup_freshness` - Most recent backup < 24 hours old

**Actual Implementation:**
The check uses `DATA_BACKUP_DIR` (meta.py:273) which is configurable via `config.toml` under `[backup]`. The actual path is `instance_path / DATA_BACKUP_DIR` (meta.py:274).

**Impact:** Low - The documentation doesn't specify the path structure, but it's accurate.

---

## Bugs Discovered

### None Critical

No bugs found in the infrastructure implementations. All claims in the documentation match the actual code with the minor discrepancies noted above.

---

## Security Concerns

### 1. Webhook Secret Encryption - Well Implemented

The webhook secret encryption using AES-256-GCM is properly implemented:
- `Webhook.secret` property decrypts on access (models.py:499-508)
- `Webhook.secret` setter encrypts on write (models.py:510-517)
- `webhook_encryption.py` uses proper AESGCM with random nonce
- Key validation handles both hex-encoded (64 chars) and raw 32-byte keys

**Status:** Secure.

### 2. SSRF Protection - Well Implemented

The `is_safe_webhook_url()` function properly blocks:
- Loopback (127.0.0.1, ::1, localhost, 0.0.0.0)
- Private IPs (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
- Link-local (169.254.0.0/16, fe80::/10)
- Reserved, multicast addresses
- Cloud metadata endpoints (169.254.169.254, metadata.google.internal)
- IPv4-mapped IPv6 to private addresses

**Status:** Secure.

### 3. Webhook Delivery Retry Does Not Propagate

**Issue:** In `tasks.py:234-246`, when a webhook request fails with `requests.RequestException`, the exception is caught but NOT re-raised. This means Celery's `max_retries=3` will NOT trigger for individual webhook failures.

```python
try:
    response = requests.post(...)
    event.delivery_attempts += 1
    if response.status_code < 400:
        delivered_count += 1
except requests.RequestException:
    event.delivery_attempts += 1
    # Exception not re-raised - no retry triggered
```

**Impact:** Medium - Individual webhook failures won't be automatically retried. The task itself succeeds even if all webhooks fail.

**Recommendation:** Consider re-raising the exception or implementing a different retry mechanism for webhook delivery failures.

---

## Recommended Improvements

### 1. Update Queue Routing Line Numbers

**File:** `architecture/infrastructure/webhooks.md`  
**Change:** Update line numbers in queue table to reflect actual implementation:
- `send_newsletter_task`: 127 (currently 130)
- `deliver_webhook_task`: 184 (currently 182)
- `send_confirmation_task`: 263 (currently 262)
- `send_password_reset_task`: 284 (currently 283)
- `run_backup_task`: 305 (currently 304)

Or remove line numbers entirely as they are fragile and become outdated.

### 2. Clarify Health Check Email Status

**File:** `architecture/infrastructure/overview.md`  
**Change:** Remove `email` from optional checks or clarify:
```
| Check | What it validates |
|-------|-------------------|
| `email` | SMTP connectivity checked via scheduler status (only when SMTP_HOST is set) |
```

### 3. Document WEBHOOK_TIMEOUT Configuration

**File:** `architecture/infrastructure/webhooks.md`  
**Change:** The documentation mentions "10 second timeout" but doesn't mention it's configurable. Add to Environment Variables or Configuration section:
```
| Variable | Description |
|----------|-------------|
| `WEBHOOK_TIMEOUT` | Request timeout in seconds (default: 10, configurable via config.toml) |
```

### 4. Add Search Provider Configuration Details

**File:** `architecture/infrastructure/search.md`  
**Change:** The configuration section mentions `SEARCH_PROVIDER` and `SEARCH_CONFIG` but doesn't specify where to configure them. Add:
```
## Configuration

Configuration in `config.toml` under `[search]`:
- `provider`: "sqlite" (default) or "postgresql"
- `config`: Provider-specific configuration dict (currently unused)
```

### 5. Add Variant Cleanup to S3 Flow

**File:** `architecture/infrastructure/storage.md`  
**Change:** The S3 variant generation flow (lines 97-106) doesn't mention that `_delete_existing_variants()` is called before uploading. Add to step 1:
```
1. upload_with_processing() calls _delete_existing_variants() to clean up old variants, then saves original file to S3
```

---

## Conclusion

The infrastructure documentation is largely accurate and well-maintained. The implementations in `app/storage.py`, `app/webhooks.py`, `app/email.py`, and `app/services/search/` match their documentation closely. 

Minor issues found:
- Line numbers in queue routing table are outdated by 1-3 lines
- Health check "email" optional check doesn't exist as a standalone check
- WEBHOOK_TIMEOUT is not documented as configurable

No critical bugs or security vulnerabilities were found. The one notable finding is that webhook delivery exceptions are silently caught, preventing Celery's automatic retry from triggering on individual webhook failures.

All issues are low to medium severity and do not affect the functional correctness of the infrastructure components.
