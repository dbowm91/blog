# Infrastructure Architecture Review

**Reviewed:** 2026-05-31
**Architecture Docs:** search.md, email.md, storage.md, webhooks.md (overview.md does not exist)
**Source Files:** app/search.py, app/email.py, app/storage.py, app/webhooks.py, app/utils.py

## Findings

### Verified Claims (Correct)

1. **FTS5 table structure** — `search.md:39-45` matches `app/search.py:72-78` exactly: `fts5(title, body, summary, prefix='2 3 4')` with `posts_fts_vocab` companion table.
2. **`init_fts()` idempotent and called during app init** — Confirmed at `app/__init__.py:430-433`. Uses `CREATE VIRTUAL TABLE IF NOT EXISTS` and `INSERT OR IGNORE`.
3. **FTS availability caching** — `_FTS_CHECK_TTL = 300` confirmed at `app/search.py:32`. Double-checked locking pattern with `threading.Lock()` at line 53-54.
4. **Snippet batching** — `_SQLITE_MAX_VARS = 500` at `app/search.py:291` for SQLite parameter limit. Matches doc claim at `search.md:169`.
5. **`highlight_query()` HTML escaping** — `html.escape()` called before `<mark>` tagging at `app/search.py:367`. Prevents XSS from user content.
6. **Webhook two-level dispatch** — `deliver_webhook_task` (`app/tasks.py:198`) dispatches to `deliver_single_webhook_task` (`app/tasks.py:234`), one per webhook. Matches `webhooks.md:118-135`.
7. **`deliver_webhook()` deprecated** — Confirmed at `app/webhooks.py:42-60` with `DeprecationWarning`.
8. **SSRF protection** — `is_safe_webhook_url()` at `app/utils.py:383-485` covers scheme, userinfo, loopback, private, link-local, reserved, multicast, IPv4-mapped, cloud metadata, and global routability checks.
9. **Storage singleton with double-checked locking** — `get_storage()` at `app/storage.py:274-281` uses `threading.Lock()` with two `if _storage is None` checks.
10. **S3 client lazy init with lock** — `S3StorageBackend.client` property at `app/storage.py:164-180` uses double-checked locking.
11. **Email retry defaults** — Transactional: 3 retries (`app/email.py:111`), Newsletter: 5 retries via `NEWSLETTER_MAX_RETRY_ATTEMPTS` (`app/config.py:118`). Matches `email.md:84-85`.
12. **HMAC-SHA256 signing** — `sign_webhook_payload()` at `app/webhooks.py:32-36` produces `sha256={hexdigest}` format.
13. **Search provider abstraction** — `SearchProvider` ABC at `app/services/search/__init__.py:13-83`, `SQLiteSearchProvider` at `app/services/search/sqlite.py:6-50`, `PostgreSQLSearchProvider` stub exists.
14. **Delivery status tracking** — `_update_delivery_status()` at `app/tasks.py:316-345` computes `delivered`/`partial_failure`/`failed` from `successful_deliveries + failed_deliveries`.
15. **Redirect blocking** — Both `deliver_webhook()` and `deliver_single_webhook_task` set `allow_redirects=False`.
16. **DNS rebinding gap documented** — `webhooks.md:162-173` correctly identifies the TOCTOU window between DNS resolution and HTTP request.

### Discrepancies (Doc vs Code)

1. **`WEBHOOK_TIMEOUT` duplication and inconsistency** — `app/webhooks.py:23` hardcodes `WEBHOOK_TIMEOUT = 10`. `app/config.py:155` loads from config (default 10). The deprecated `deliver_webhook()` uses the hardcoded constant (line 79). `deliver_single_webhook_task()` imports from `app.config` (line 244). Currently both default to 10, but if a user configures `webhook.timeout` in `config.toml`, the deprecated path ignores it. **Severity: Low** — deprecated function is not used for new code.

2. **`__init__.py` outer try/except is redundant** — `app/__init__.py:430-433` catches `OperationalError` around `init_fts()`, but `init_fts()` already catches `OperationalError`, `ProgrammingError`, and `DatabaseError` internally (`app/search.py:93-98`). The outer catch is unreachable for those exception types. It would only trigger if `init_fts()` raised something not caught internally (e.g., a `RuntimeError` from a bug). **Severity: Informational** — dead code, not harmful.

3. **`get_indexed_terms_fallback()` not sorted** — Doc at `search.md:76` claims "Returns a deduplicated list" but the code at `app/search.py:241` returns `list(set(terms))` which is unordered. The main `get_indexed_terms()` (`app/search.py:219-227`) returns alphabetically sorted results from the vocab table. Fallback callers get random order. **Severity: Medium** — affects autocomplete consistency.

4. **`highlight_query()` accepts pre-escaped HTML poorly** — Doc at `search.md:151` says "input `text` should be raw text, not pre-escaped HTML." But the docstring at `app/search.py:354` says "(may contain HTML)". These contradict. Passing pre-escaped HTML results in double-escaping. **Severity: Low** — documentation inconsistency.

5. **`generate_image_variants` uses string comparison for backend type** — `app/tasks.py:42` and `app/tasks.py:71` check `storage.__class__.__name__ == "LocalStorageBackend"` / `"S3StorageBackend"` instead of `isinstance()`. This is fragile if classes are renamed or subclassed. **Severity: Low** — works but brittle.

### Missing Documentation

1. **`overview.md` does not exist** — The architecture docs reference `overview.md` in the review scope, but no such file exists at `architecture/infrastructure/overview.md`. This file should provide a high-level summary of all infrastructure components and their interactions.

2. **Health check endpoint undocumented** — `app/routes/public/meta.py:188-284` implements a `/health` endpoint with database, scheduler, FTS, disk, integrity, Redis, Celery, and backup freshness checks. It supports `?detailed=true&secret=<key>` for authenticated detailed results. None of this is in the infrastructure docs.

3. **`init_webhooks()` is a no-op** — `app/webhooks.py:118-120` is `pass`. Doc at `webhooks.md` does not mention this placeholder or explain why it exists.

4. **`webhook_encryption.py` undocumented in infrastructure** — Referenced in `webhooks.md:40-62` but not in the review scope. The encryption module handles AES-256-GCM for webhook secrets. Should be cross-referenced.

5. **`upload_with_processing()` return type mismatch** — Doc at `storage.md:102` shows return type `tuple[str, None] | tuple[None, str]` which matches code at `app/storage.py:336`. But the doc doesn't explain when each variant is returned or error handling behavior.

6. **S3 `exists()` ambiguity not prominent enough** — `storage.py:15-22` documents this limitation in the module docstring, but `storage.md` doesn't mention it. Callers cannot distinguish "not found" from network/permission errors.

### Potential Bugs / Concerns

1. **`send_newsletter_task` references `post` after loop** — `app/tasks.py:190` references `post.newsletter_attempts` outside the `for post in posts` loop. If `posts` is empty (shouldn't be due to early return at line 152), this would raise `UnboundLocalError`. The variable `post` leaks from the loop scope. **File:** `app/tasks.py:190`. **Fix:** Use `posts[0].newsletter_attempts` or track the value separately.

2. **`_send_email_with_retry` silently returns `server=None` path** — `app/email.py:124` returns `(False, "Server is None", None)` when server is None. But `send_newsletter()` at line 205 captures `server` from the return value. If `_connect_smtp()` fails mid-newsletter (returns None from retry), subsequent emails will fail with "Server is None" and the server object is lost. The newsletter loop continues processing subscribers with a None server, logging warnings for each. **File:** `app/email.py:124,205-219`. **Severity: Medium** — wastes time iterating remaining subscribers after SMTP death.

3. **`create_webhook_event()` silent failure on Celery queue** — `app/webhooks.py:108-113` catches exceptions from `deliver_webhook_task.delay()` and logs them, but the `WebhookEvent` record remains with `delivered=False` and is never retried. The function always returns the event ID regardless. **File:** `app/webhooks.py:106-115`. **Severity: Medium** — acknowledged in docs but no recovery mechanism exists.

4. **`_check_fts_enabled` stale timestamp under lock contention** — `app/search.py:51-52` captures `now = time.monotonic()` before acquiring the lock. If thread A acquires the lock and thread B is waiting, thread B's `now` is stale. When B enters the lock, it checks `now - _fts_check_time > _FTS_CHECK_TTL` using its old timestamp. This could cause a redundant check or miss a window. **Severity: Low** — TTL is 300s, lock contention is brief.

5. **SSRF DNS rebinding window** — Correctly documented in `webhooks.md:162-173`. Between `is_safe_webhook_url()` DNS resolution and `requests.post()`, a short-TTL DNS record could change to a private IP. No mitigation is implemented. **Severity: Medium** — theoretical attack, requires attacker-controlled DNS.

6. **`highlight_query()` regex matches inside words** — `app/search.py:362` uses `re.escape(query)` without word boundary anchors. Searching "cat" highlights "cat" inside "category". **File:** `app/search.py:362`. **Severity: Low** — may be intentional for partial matching.

7. **S3 `exists()` conflates errors with "not found"** — `app/storage.py:211-217` returns `False` for any `ClientError` or `BotoCoreError`. A 403 Forbidden looks identical to a 404 Not Found. **Severity: Medium** — documented but callers have no way to distinguish.

8. **`_delete_existing_variants` for S3 uses prefix matching** — `app/storage.py:324-331` does `list_objects_v2(Prefix=prefix)` for each variant pattern. If a filename like `a.jpg` is deleted, `Prefix="a.jpg"` could match `a.jpg.bak` or other unrelated objects. **File:** `app/storage.py:326`. **Severity: Low** — unlikely in practice.

9. **No `SMTP_SERVER_RECOVERABLE_ERRORS` in retry logic** — `app/email.py:146-149` catches `SMTPException` and `OSError` generically. Transient errors like `SMTPRecipientsRefused` (bad recipient, not SMTP issue) and permanent errors like `SMTPAuthenticationError` are treated the same — retried. **Severity: Low** — retry won't help auth errors but won't cause harm.

10. **`_send_email()` creates new connection per call** — `app/email.py:34` opens and closes an SMTP connection for every single email (confirmation, password reset). No connection reuse. **Severity: Low** — acceptable for low-volume transactional emails.

### Improvement Suggestions

1. **Add `overview.md`** — Create `architecture/infrastructure/overview.md` to describe how search, email, storage, and webhooks interact. Currently each doc is siloed.

2. **Document health check endpoint** — Add a `health.md` or include in `overview.md`. The `/health` endpoint is feature-rich (DB, scheduler, FTS, disk, Redis, Celery, backup freshness) and should be documented for operations.

3. **Fix `get_indexed_terms_fallback()` sorting** — Change `app/search.py:241` from `list(set(terms))` to `sorted(set(terms))` for consistent autocomplete behavior.

4. **Fix `send_newsletter_task` variable leak** — `app/tasks.py:190` should not reference `post` outside the loop. Track `newsletter_attempts` separately.

5. **Add SMTP connection reuse for newsletters** — `send_newsletter()` already reuses a single connection. `_send_email()` for transactional emails could benefit from connection pooling if volume grows.

6. **Use `isinstance()` for backend type checks** — `app/tasks.py:42,71` should use `isinstance(storage, LocalStorageBackend)` instead of string comparison.

7. **Improve `create_webhook_event()` resilience** — Consider a retry mechanism or dead-letter queue for failed Celery task queuing. At minimum, log the event ID prominently for manual recovery.

8. **SSRF mitigation: resolve DNS at request time** — Use a DNS resolver that validates IPs at the moment of connection, or pin the resolved IP and pass it to `requests` via a custom adapter.

9. **Add word boundary to `highlight_query()` regex** — Use `\b{query}\b` pattern to avoid matching inside words, unless partial matching is desired (in which case, document it).

10. **S3 `exists()` should differentiate errors** — Return a `Result` type or raise on non-404 errors. At minimum, log the error type for debugging.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | Medium | Fix `send_newsletter_task` variable leak (`post` referenced outside loop) | `app/tasks.py:190` |
| 2 | Medium | Fix `get_indexed_terms_fallback()` to return sorted list | `app/search.py:241` |
| 3 | Medium | Document health check endpoint in architecture docs | `architecture/infrastructure/` |
| 4 | Medium | Create `architecture/infrastructure/overview.md` | `architecture/infrastructure/` |
| 5 | Low | Replace string comparison with `isinstance()` in `generate_image_variants` | `app/tasks.py:42,71` |
| 6 | Low | Fix `highlight_query()` docstring to say "raw text, not HTML" | `app/search.py:354` |
| 7 | Low | Add word boundary anchors to `highlight_query()` regex | `app/search.py:362` |
| 8 | Low | Document S3 `exists()` error ambiguity in `storage.md` | `architecture/infrastructure/storage.md` |
| 9 | Low | Add `SMTPRecipientsRefused` and other non-recoverable errors to exclude list | `app/email.py:146-149` |
| 10 | Low | Consider dead-letter queue or retry mechanism for `create_webhook_event()` Celery failures | `app/webhooks.py:108-113` |
