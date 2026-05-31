# Infrastructure Module Architecture Review

**Reviewed:** 2026-05-31
**Architecture Docs:** overview.md, search.md, email.md, storage.md, webhooks.md
**Source Files:** app/search.py, app/email.py, app/storage.py, app/webhooks.py, app/utils.py

## Findings

### Verified Claims (Correct)

- FTS5 virtual table uses `prefix='2 3 4'` and `fts5vocab` — confirmed in `app/search.py:69-77`
- FTS availability caching TTL is 300 seconds (`_FTS_CHECK_TTL = 300`) — confirmed in `app/search.py:30`
- `FTS_RESULT_LIMIT` default is 100 — confirmed in `app/config.py:128`
- `sync_fts()` handles both published (INSERT OR REPLACE) and unpublished (DELETE) — confirmed in `app/search.py:118-126`
- `sync_fts_batch()` splits published and unpublished items — confirmed in `app/search.py:133-171`
- `_SQLITE_MAX_VARS = 500` for batching — confirmed in `app/search.py:291`
- `search()` builds OR query with prefix matching and BM25 ranking — confirmed in `app/search.py:196-216`
- `get_search_snippets()` uses FTS5 `snippet()` function with `<mark>` tags — confirmed in `app/search.py:293-308`
- `get_did_you_mean()` uses `difflib.get_close_matches` with `cutoff=0.6` — confirmed in `app/search.py:337`
- `highlight_query()` uses `html.escape()` for XSS prevention then regex substitution — confirmed in `app/search.py:349-364`
- `_check_fts_enabled()` queries `sqlite_master` with TTL caching — confirmed in `app/search.py:43-55`
- `init_fts()` creates `posts_fts` and `posts_fts_vocab`, then populates with published posts — confirmed in `app/search.py:58-98`
- `rebuild_fts()` uses `INSERT INTO posts_fts(posts_fts) VALUES('rebuild')` — confirmed in `app/search.py:104`
- Search provider abstraction: `SearchProvider` ABC, `SQLiteSearchProvider`, `PostgreSQLSearchProvider` stub — confirmed in `app/services/search/`
- `get_search_provider()` factory reads `SEARCH_PROVIDER` config — confirmed in `app/services/search/__init__.py:86-101`
- `PostgreSQLSearchProvider` raises `ConfigurationError` on all methods — confirmed in `app/services/search/postgresql.py`
- `_connect_smtp()` returns `None` on failure — confirmed in `app/email.py:78-103`
- `_send_email_with_retry()` reconnects on `SMTPServerDisconnected` — confirmed in `app/email.py:126-144`
- `_send_email_with_retry()` default `max_retries=3` — confirmed in `app/email.py:111`
- `NEWSLETTER_MAX_RETRY_ATTEMPTS` default is 5 — confirmed in `app/config.py:119`
- `send_newsletter()` logs progress every 50 emails — confirmed in `app/email.py:220`
- `send_newsletter()` uses placeholder-based unsubscribe URL injection — confirmed in `app/email.py:174-194`
- `send_newsletter()` adds `List-Unsubscribe` and `List-Unsubscribe-Post` headers — confirmed in `app/email.py:199-200`
- `SMTP_TIMEOUT` default is 30 — confirmed in `app/config.py:160`
- `WEBHOOK_TIMEOUT` default is 10 — confirmed in `app/config.py:156`
- `StorageBackend` abstract base class with `save/load/delete/exists/url/list_files/path` — confirmed in `app/storage.py:63-93`
- `LocalStorageBackend` returns `/static/uploads/{filename}` URLs — confirmed in `app/storage.py:127`
- `S3StorageBackend` uses lazy client initialization with `threading.Lock` double-checked locking — confirmed in `app/storage.py:164-180`
- `get_storage()` singleton uses double-checked locking — confirmed in `app/storage.py:270-277`
- `S3StorageBackend.load/delete/exists/list_files` return False/None/[] on failure — confirmed in `app/storage.py:186-234`
- `upload_with_processing()` calls `_delete_existing_variants()` then queues `generate_image_variants` — confirmed in `app/storage.py:337-378`
- `sign_webhook_payload()` uses HMAC-SHA256 with `json.dumps(sort_keys=True)` — confirmed in `app/webhooks.py:32-36`
- `deliver_webhook()` is deprecated — confirmed in `app/webhooks.py:39-84` with `warnings.warn`
- `deliver_webhook()` sets `allow_redirects=False` — confirmed in `app/webhooks.py:80`
- Two-level dispatch: `deliver_webhook_task` dispatches per-webhook `deliver_single_webhook_task` — confirmed in `app/tasks.py:194-309`
- SSRF protection in `is_safe_webhook_url()` checks scheme, hostname, userinfo, loopback, private, link-local, reserved, multicast, IPv4-mapped, cloud metadata, and global routability — confirmed in `app/utils.py:383-485`
- `deliver_single_webhook_task` performs SSRF validation before each request — confirmed in `app/tasks.py:251`
- `create_webhook_event()` creates `WebhookEvent` record and queues `deliver_webhook_task` — confirmed in `app/webhooks.py:87-115`
- `Webhook.secret` property decrypts via `app.webhook_encryption.py` AES-256-GCM — confirmed in `app/models.py:496-506` and `app/webhook_encryption.py`
- `WEBHOOK_ENCRYPTION_KEY` accepts hex-encoded (64 chars) or raw 32-byte string — confirmed in `app/webhook_encryption.py:22-54`
- Delivery status tracking: `delivered`, `partial_failure`, `failed` — confirmed in `app/tasks.py:312-341`
- Webhook queue is named `webhooks` — confirmed in `app/tasks.py:194`
- Newsletter queue is named `newsletter` — confirmed in `app/tasks.py:135`
- Email queue is named `email` — confirmed in `app/tasks.py:344,365`
- Event types: `post.published`, `post.unpublished`, `subscriber.confirmed` — confirmed in `app/routes/api/posts.py:309`, `app/routes/public/subscribe.py:148`
- Health endpoint at `GET /health` with `?detailed=true` and `?secret=` parameters — confirmed in `app/routes/public/meta.py:188-321`
- Critical health checks: database, scheduler, search, disk_space, db_integrity — confirmed in `app/routes/public/meta.py:289-292`
- Status logic: `ok` if all critical checks are "ok", "running", or "disabled"; else `degraded` — confirmed in `app/routes/public/meta.py:294-301`
- `reset_fts_available()` resets the FTS availability cache — confirmed in `app/search.py:36-40`
- `extract_snippet()` extracts context around first query match — confirmed in `app/search.py:246-272`
- `get_indexed_terms()` tries `posts_fts_vocab` first, falls back to extracting from post titles — confirmed in `app/search.py:219-243`
- All module-level FTS functions catch `OperationalError`, `ProgrammingError`, `DatabaseError` (except `get_indexed_terms` which omits `DatabaseError`) — confirmed in `app/search.py`
- Silent FTS initialization at `app/__init__.py:430-433` catches `OperationalError` — confirmed
- `S3StorageBackend` falls back to `LocalStorageBackend` when credentials are missing — confirmed in `app/storage.py:240-249`

### Discrepancies (Doc vs Code)

1. **overview.md:17-18 => "Optional Checks" table lists `email` check ("SMTP connectivity (if configured)")**
   - Actual code in `app/routes/public/meta.py:188-321` has **no email connectivity check**. The health endpoint checks database, scheduler, search, disk_space, db_integrity, redis, celery, and backup_freshness. There is no SMTP/email check anywhere in the health endpoint.
   - **Affects:** overview.md

2. **overview.md:88-98 => `is_safe_webhook_url()` code snippet is drastically simplified**
   - The doc shows a ~10-line version with only basic checks (`ip.is_private`, `ip.is_loopback`, `ip.is_link_local`, `not ip.is_global`). The actual implementation in `app/utils.py:383-485` is ~100 lines with additional checks for: userinfo blocking, loopback hostname blocking, reserved IPs, multicast IPs, IPv4-mapped IPv6 addresses, hardcoded cloud metadata endpoints (AWS `169.254.169.254` and GCP `metadata.google.internal`), and proper error handling.
   - **Affects:** overview.md

3. **email.md:84-86 => "Exponential backoff" claim in retry logic**
   - The doc says `_send_email_with_retry()` uses "Exponential backoff". The actual code in `app/email.py:106-149` has **NO sleep/delay between retries**. The function retries immediately in a tight loop. The docstring at `app/email.py:113` also claims "exponential backoff" but this is not implemented. Only `SMTPServerDisconnected` triggers a reconnection attempt; other exceptions retry with no delay.
   - **Affects:** email.md, source code (misleading docstring)

4. **email.md:33-35 => `_send_email()` described as returning `None` on failure**
   - The function signature in `app/email.py:24` is `def _send_email(...) -> None` but it does **not** return `None` on failure — it **raises** exceptions (SMTPException, OSError, etc.) on any SMTP failure. There is no try/except in `_send_email()`. The doc's claim is ambiguous — it says "Low-level SMTP send with TLS" without clarifying that errors propagate.
   - **Affects:** email.md

5. **search.md:30-33 => Features list says "Fallback: LIKE-based search when FTS unavailable"**
   - When FTS is unavailable, `search()` in `app/search.py:199-200` returns an **empty list**. There is **no LIKE-based fallback** implemented in `app/search.py`. The LIKE fallback is mentioned but does not exist in the code.
   - **Affects:** search.md

6. **search.md:26-27 => "When set to `"postgresql"`, falls back to SQLite until full PostgreSQL implementation is complete"**
   - The actual code in `app/services/search/__init__.py:94-97` returns `PostgreSQLSearchProvider()` when `SEARCH_PROVIDER == "postgresql"`. The PostgreSQL provider **raises `ConfigurationError`** on all methods rather than falling back to SQLite. There is no fallback mechanism.
   - **Affects:** search.md

7. **search.md:164 => Escape characters listed as `()*+":<>`**
   - The actual regex in `app/search.py:32` is `[()*+:+"<>\-]` which also escapes the **hyphen** (`-`). The doc omits this character.
   - **Affects:** search.md

8. **webhooks.md:118 => `deliver_single_webhook_task` described at line 231**
   - The `@shared_task` decorator for `deliver_single_webhook_task` is at `app/tasks.py:230`, and the `def` is at line 231. The task queue declaration on line 194 (`@shared_task(bind=True, max_retries=3, retry_backoff=True, queue="webhooks")`) is for `deliver_webhook_task`. The doc says line 231 for the single webhook task which is the `def` line, but this is off by one from the decorator.
   - **Affects:** webhooks.md

9. **webhooks.md:200 => Email queue tasks listed at `app/tasks.py:333,354`**
   - The actual line numbers are `app/tasks.py:344` (`send_confirmation_task`) and `app/tasks.py:365` (`send_password_reset_task`). The doc is off by 11 and 19 lines respectively.
   - **Affects:** webhooks.md

10. **storage.md:73 => "S3 methods return `False` or empty lists on failure"**
    - `S3StorageBackend.save()` in `app/storage.py:182-184` has **no try/except** and will **raise** on failure (e.g., `ClientError` from `put_object`). Only `load()`, `delete()`, `exists()`, and `list_files()` have error handling that returns False/None/[].
    - **Affects:** storage.md

11. **webhooks.md:94 => "`WEBHOOK_TIMEOUT` second timeout (configurable via `webhook.timeout` in config)"**
    - The deprecated `deliver_webhook()` function in `app/webhooks.py:23` uses a **hardcoded** `WEBHOOK_TIMEOUT = 10` imported from `app/webhooks.py` (line 23), NOT from `app/config.py`. Only `deliver_single_webhook_task` in `app/tasks.py:240-281` imports `WEBHOOK_TIMEOUT` from `app/config.py`. The doc implies the deprecated function also uses the config value.
    - **Affects:** webhooks.md

12. **webhooks.md:33-35 => WebhookEvent model docs missing `successful_deliveries` and `failed_deliveries` fields**
    - The doc shows `delivery_attempts` but omits `successful_deliveries` and `failed_deliveries` fields that exist in the actual model at `app/models.py:534-535`.
    - **Affects:** webhooks.md

13. **email.md:77 => "Base email template (standalone, not extending `base.html`)"**
    - This claim is about templates which are outside the scope of the infrastructure review, but worth noting as unverifiable without reading the template files.
    - **Affects:** email.md (unverified)

### Missing Documentation

1. **`extract_snippet()` function in `app/search.py:246-272`** — A public utility function that extracts text snippets around query matches. Not documented in search.md and not in `__all__` but is a useful standalone utility.

2. **`_delete_existing_variants()` in `app/storage.py:293-334`** — Internal function that handles cleanup of old image variants before re-upload. Has different behavior for LocalStorageBackend (direct file deletion) vs S3StorageBackend (list + delete by prefix). Important for understanding variant lifecycle but not documented.

3. **`_generate_responsive_variants_local()` in `app/storage.py:381-387`** — Deprecated function that wraps `generate_image_variants` Celery task. Marked deprecated in code but not in docs.

4. **`_escape_fts_term()` in `app/search.py:188-193`** — Private function for FTS5 term escaping. Important for understanding query processing security but not documented.

5. **`get_indexed_terms_fallback()` in `app/search.py:230-243`** — Fallback path for term extraction from post titles when vocabulary table is unavailable. Not documented.

6. **`init_storage()` in `app/storage.py:280-284`** — Function exists and is documented in storage.md but is **never called** anywhere in the codebase. Storage is always accessed via `get_storage()` singleton.

7. **`S3StorageBackend.save()` missing error handling** — Unlike other S3 methods, `save()` has no try/except block. Should be documented as a known behavior difference.

8. **`get_search_snippets()` not in `__all__`** — The function is documented in search.md and is public (no underscore prefix) but is excluded from `__all__` in `app/search.py:6-17`.

9. **`WEBHOOK_TIMEOUT` dual definition** — Hardcoded in `app/webhooks.py:23` (used by deprecated function) and configurable in `app/config.py:156` (used by Celery task). The relationship between these two is not documented.

10. **`init_fts()` destructive error handling** — On failure, `init_fts()` attempts to DROP the `posts_fts` table (`app/search.py:91`), which could destroy an existing working FTS index if the failure was transient. This behavior is not documented.

11. **`_send_email_with_retry()` reconnection scope** — Reconnection only triggers on `SMTPServerDisconnected`. Other SMTP exceptions (`SMTPException`, `OSError`) retry without reconnection. This distinction is not documented.

12. **`create_webhook_event()` silently swallows Celery queue failures** — `app/webhooks.py:112` catches `(RequestException, ValueError, OSError)` when queuing the task, logging only an error. The event record is already committed, so it exists but will never be delivered. This silent failure mode is not documented.

13. **Health check email connectivity** — Listed as an optional check in overview.md but does not exist in code. This is both a missing doc and a missing feature.

### Potential Bugs / Concerns

1. **Race condition in `_check_fts_enabled()` (`app/search.py:43-55`)** — Module-level globals `_fts_enabled` and `_fts_check_time` are read and written without any locking. In a multi-threaded WSGI server (e.g., gunicorn with threads), two threads could both see `_fts_enabled is None` and both execute the database check simultaneously. While benign (no data corruption), it defeats the caching optimization under concurrent load.

2. **`init_fts()` drops existing FTS table on failure (`app/search.py:88-98`)** — When `init_fts()` encounters a database error, it rolls back and then attempts to `DROP TABLE IF EXISTS posts_fts`. If the error was transient (e.g., database locked), this destroys the existing working FTS index. The subsequent population from published posts would need to recreate it, but the DROP happens first. This is aggressive and could cause data loss in edge cases.

3. **`_send_email_with_retry()` returns disconnected server on reconnection failure (`app/email.py:122-149`)** — When reconnection fails after `SMTPServerDisconnected`, the function breaks out of the retry loop and returns the old disconnected `server` object. The caller (`send_newsletter()`) assigns this back to its `server` variable and passes it to the next subscriber's `_send_email_with_retry()` call. The next call will immediately fail with `SMTPServerDisconnected` again, consuming one retry attempt wastefully.

4. **`S3StorageBackend.save()` lacks error handling (`app/storage.py:182-184`)** — Unlike all other S3 methods (`load`, `delete`, `exists`, `list_files`), `save()` has no try/except. A `ClientError` from `put_object` will propagate uncaught, potentially crashing the caller. This is inconsistent with the documented behavior that "S3 methods return `False` or empty lists on failure."

5. **`_update_delivery_status()` race condition (`app/tasks.py:312-341`)** — The function re-queries all enabled webhooks to count `total_count`. Between the original dispatch and the status update, webhooks could be added or deleted, causing `total_count` to change. This could result in incorrect `delivery_status` values (e.g., marking as "delivered" when not all webhooks have been attempted).

6. **`create_webhook_event()` commits before queuing (`app/webhooks.py:97-115`)** — The `WebhookEvent` record is committed to the database at line 104 before the Celery task is queued at line 111. If the Celery queue fails, the event exists in the database but will never be delivered. The error is logged but the event's `delivered` flag remains `False` indefinitely with no retry mechanism.

7. **`get_indexed_terms()` catches different exceptions than other functions (`app/search.py:219-227`)** — Catches `(OperationalError, ProgrammingError)` but NOT `DatabaseError`, while every other FTS function catches `(OperationalError, ProgrammingError, DatabaseError)`. This means `DatabaseError` would propagate from `get_indexed_terms()` but not from `search()`, `sync_fts()`, etc.

8. **`highlight_query()` double-escapes already-escaped HTML (`app/search.py:349-364`)** — The function calls `html.escape(text)` first, then applies regex highlighting. If `text` already contains `&amp;` or `&lt;` entities, they will be double-escaped to `&amp;amp;` and `&amp;lt;`. The function name and docstring suggest it's for query highlighting, but it always HTML-escapes its input, which could be unexpected.

9. **`_delete_existing_variants()` accesses private attributes (`app/storage.py:293-334`)** — For S3 backends, the function directly accesses `storage.client` and `storage.bucket` (lines 329-331), which are public properties but tightly couple the variant cleanup to the S3 implementation. If the `S3StorageBackend` interface changes, this function would break.

10. **`init_storage()` is dead code (`app/storage.py:280-284`)** — The function is defined and documented in storage.md but never called anywhere in the codebase. Storage is always accessed via `get_storage()`. This is confusing for developers who read the docs.

### Improvement Suggestions

1. **Add actual exponential backoff to `_send_email_with_retry()`** — The function claims to implement exponential backoff in both its docstring and architecture docs, but retries immediately with no delay. Add `time.sleep(backoff_seconds)` with exponential growth (e.g., `2 ** attempt`) between retries.

2. **Document the LIKE-based search fallback or remove the claim** — search.md claims LIKE fallback exists but `search()` returns an empty list when FTS is unavailable. Either implement the fallback or update the documentation.

3. **Fix `PostgreSQLSearchProvider` to fall back to SQLite** — search.md claims PostgreSQL falls back to SQLite, but the code raises `ConfigurationError`. Either implement the fallback or correct the docs.

4. **Add error handling to `S3StorageBackend.save()`** — Wrap `put_object` in try/except consistent with other S3 methods, returning `False` or raising a custom exception.

5. **Add thread-safety to `_check_fts_enabled()`** — Use `threading.Lock()` or `functools.lru_cache` for the FTS availability check to prevent redundant database queries under concurrent load.

6. **Make `init_fts()` less destructive on failure** — Instead of dropping the FTS table on error, log the error and leave the table intact. The rebuild can be triggered manually if needed.

7. **Add an email connectivity check to the health endpoint** — overview.md documents this as an optional check but it doesn't exist. Either implement it or remove from docs.

8. **Fix the `is_safe_webhook_url()` code snippet in overview.md** — Replace the simplified version with an accurate representation or remove the code block and reference the full implementation in `app/utils.py`.

9. **Clean up `init_storage()` or integrate it** — Either call `init_storage()` during app startup or remove it and its documentation to avoid confusion.

10. **Add `get_search_snippets()` to `__all__`** — The function is public and documented but not exported, which is inconsistent.

11. **Document the `WEBHOOK_TIMEOUT` dual definition** — Make it clear that `app/webhooks.py:23` has a hardcoded fallback while `app/config.py:156` has the configurable version.

12. **Address `create_webhook_event()` silent failure** — Consider adding a dead-letter mechanism or retry queue for events that fail to queue, rather than silently logging and leaving orphaned events.

13. **Consider making `_delete_existing_variants()` a method of `StorageBackend`** — This would eliminate the tight coupling to implementation details and allow backend-specific variant cleanup logic.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|---------|
| 1 | high | email.md:84-86 claims "Exponential backoff" but `_send_email_with_retry()` has no sleep/delay between retries — update docs or implement backoff | docs/source |
| 2 | high | search.md:30-33 claims "Fallback: LIKE-based search when FTS unavailable" but `search()` returns empty list — either implement fallback or remove claim | docs |
| 3 | high | search.md:26-27 claims PostgreSQL "falls back to SQLite" but `PostgreSQLSearchProvider` raises `ConfigurationError` — either implement fallback or correct docs | docs |
| 4 | high | overview.md:17-18 lists `email` as optional health check but it does not exist in `app/routes/public/meta.py` — either implement or remove from docs | docs/source |
| 5 | high | overview.md:88-98 `is_safe_webhook_url()` code snippet is drastically simplified and misleading — replace with accurate version or remove | docs |
| 6 | high | `S3StorageBackend.save()` has no error handling (unlike all other S3 methods) — add try/consistent with other methods | source |
| 7 | medium | webhooks.md missing `successful_deliveries` and `failed_deliveries` fields in WebhookEvent model docs | docs |
| 8 | medium | storage.md:73 claims all "S3 methods return False or empty lists on failure" but `save()` raises | docs |
| 9 | medium | webhooks.md:94 implies deprecated `deliver_webhook()` uses configurable timeout but it uses hardcoded value | docs |
| 10 | medium | `init_fts()` drops existing FTS table on transient failures — make less destructive | source |
| 11 | medium | `create_webhook_event()` commits event before queuing, with no recovery for failed queue attempts | source |
| 12 | medium | `_check_fts_enabled()` module-level globals accessed without locking in multi-threaded environments | source |
| 13 | medium | `get_indexed_terms()` catches different exceptions than other FTS functions (omits `DatabaseError`) | source |
| 14 | low | `init_storage()` is defined and documented but never called anywhere in the codebase — dead code | docs/source |
| 15 | low | `get_search_snippets()` not in `__all__` despite being public and documented | source |
| 16 | low | `extract_snippet()` function not documented in search.md | docs |
| 17 | low | `_delete_existing_variants()` accesses `storage.client` and `storage.bucket` directly — tight coupling | source |
| 18 | low | `highlight_query()` always calls `html.escape()` which could double-escape already-escaped HTML | source |
| 19 | low | `_send_email_with_retry()` returns disconnected server object on reconnection failure, causing wasted retry on next call | source |
| 20 | low | `get_indexed_terms()` fallback path (`get_indexed_terms_fallback`) not documented in search.md | docs |
