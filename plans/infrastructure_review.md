# Infrastructure Module Architecture Review

**Reviewed:** May 29, 2026
**Architecture Docs:** overview.md, search.md, email.md, storage.md, webhooks.md
**Source Files:** app/search.py, app/email.py, app/storage.py, app/webhooks.py, app/utils.py, app/webhook_encryption.py, app/services/search/__init__.py, app/services/search/sqlite.py

## Findings

### Verified Claims (Correct)

- `app/search.py` functions catch `OperationalError`, `ProgrammingError`, `DatabaseError` and return empty results/False — confirmed at all relevant locations
- FTS5 table structure matches doc (`posts_fts` with `title, body, summary, prefix='2 3 4'`) — `app/search.py:69-71`
- Vocabulary table created as `posts_fts_vocab` — `app/search.py:74-77`
- `_FTS_CHECK_TTL = 300` (5 minutes) — `app/search.py:30`
- `FTS_RESULT_LIMIT` default 100 — `app/config.py:128`
- `_SQLITE_MAX_VARS = 500` for snippet batching — `app/search.py:291`
- `_send_email()` signature matches doc — `app/email.py:24`
- `_connect_smtp()` returns `None` on failure — `app/email.py:78-103`
- `send_newsletter()` pre-renders templates, logs every 50 emails — `app/email.py:176-221`
- `NEWSLETTER_MAX_RETRY_ATTEMPTS` default 5 from config — `app/config.py:119`
- `StorageBackend` ABC with `path()` raising `NotImplementedError` — `app/storage.py:54-83`
- `LocalStorageBackend` methods raise on filesystem errors (no try/except for `save`/`path`) — `app/storage.py:93-97,130-131`
- `S3StorageBackend` returns `False` or empty lists on failure — `app/storage.py:182-184,193-194,203-204,222-223`
- `S3StorageBackend` lazy client initialization with `threading.Lock` — `app/storage.py:153,158-171`
- `get_storage()` singleton pattern — `app/storage.py:257-265`
- `_delete_existing_variants()` handles 400_, 800_, 1200_ prefixes and .webp, .avif suffixes — `app/storage.py:281-322`
- `upload_with_processing()` signature and variant generation queue — `app/storage.py:325-366`
- Webhook HMAC-SHA256 signing with `sha256=` prefix — `app/webhooks.py:32-36`
- `deliver_webhook()` is deprecated — `app/webhooks.py:39-84`
- `create_webhook_event()` returns event ID and queues `deliver_webhook_task` — `app/webhooks.py:87-115`
- SSRF protection via `is_safe_webhook_url()` in `app/utils.py:383-485` — checks scheme, userinfo, loopback, private, link-local, reserved, multicast, IPv4-mapped IPv6, cloud metadata, and `is_global`
- `WEBHOOK_TIMEOUT` default 10, configurable via `webhook.timeout` — `app/config.py:155`, `app/webhooks.py:23`
- Webhook model fields match doc — `app/models.py:483-519`
- WebhookEvent model fields match doc — `app/models.py:522-544`
- `SearchProvider` ABC with `initialize()`, `search()`, `index_post()`, `remove_post()`, `rebuild_index()`, `get_snippets()` — `app/services/search/__init__.py:13-83`
- `SQLiteSearchProvider` delegates to `app/search.py` functions — `app/services/search/sqlite.py:14-55`
- `get_search_provider()` factory with postgresql fallback to sqlite — `app/services/search/__init__.py:86-101`
- `SEARCH_PROVIDER` default "sqlite" — `app/config.py:173`
- `SEARCH_CONFIG` exists — `app/config.py:174`
- `highlight_query()` applies `<mark>` tags — `app/search.py:349-364`
- `get_did_you_mean()` uses `difflib.get_close_matches` with cutoff 0.6 — `app/search.py:320-346`
- `deliver_single_webhook_task` sets `allow_redirects=False` — `app/tasks.py:283`
- Queue names match doc (`images`, `newsletter`, `webhooks`, `email`, `backup`) — `app/tasks.py`

### Discrepancies (Doc vs Code)

1. **overview.md:89 — `is_safe_url` function name wrong**
   Doc shows a code block for `def is_safe_url(url: str) -> bool:`. The actual function is `is_safe_webhook_url(url: str) -> tuple[bool, str]` at `app/utils.py:383`. The return type is also different (tuple vs bool).

2. **overview.md:89-95 — Simplified SSRF code block misleading**
   The doc shows a 5-line implementation using `socket.gethostbyname` and `ipaddress.ip_address(ip).is_private`. The actual implementation at `app/utils.py:383-485` uses `socket.getaddrinfo` with `AF_UNSPEC`, checks 10+ conditions (loopback, private, link-local, reserved, multicast, IPv4-mapped IPv6, cloud metadata, `is_global`), and returns a tuple. The doc code block is a conceptual simplification that doesn't reflect real behavior.

3. **overview.md:17 — Health check `detailed` parameter**
   Doc says `?detailed=1`. Actual code at `app/routes/public/meta.py:194` checks `request.args.get("detailed", "").lower() == "true"`. Should be `?detailed=true`.

4. **overview.md:26 — `disk_space` check threshold**
   Doc says "Available space > 100MB". Actual code at `app/routes/public/meta.py:234-235` checks `free_percent >= 10` (10% free), not an absolute 100MB threshold.

5. **overview.md:82-83 — SSRF blocked ranges incomplete**
   Doc lists specific CIDR ranges: `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `::1/128`, `fc00::/7`. The actual implementation uses Python's `ipaddress` properties (`is_loopback`, `is_private`, `is_link_local`, `is_reserved`, `is_multicast`, `is_global`) which cover broader ranges. Also blocks cloud metadata endpoints (169.254.169.254, metadata.google.internal) and IPv4-mapped IPv6 — not mentioned in the list.

6. **search.md:12 — SQLiteSearchProvider described as "wraps"**
   Doc says `SQLiteSearchProvider` "Wraps `app/search.py` FTS5 functions through the `SearchProvider` interface." The relationship is delegation, not wrapping. `SQLiteSearchProvider` calls `app/search.py` functions directly but has its own `_fts_enabled`/`_fts_check_time` state that is never used (dead code at `app/services/search/sqlite.py:10-12`).

7. **email.md:52 — `_send_email_with_retry` default max_retries**
   Doc says default `max_retries: int = 3`. Source at `app/email.py:111` confirms `max_retries: int = 3`. However, email.md:83 says "Max retries: 5 (configurable via `NEWSLETTER_MAX_RETRY_ATTEMPTS`)" which is the value passed by `send_newsletter()`, not the function's own default. This is technically correct but confusing — the function default is 3, the newsletter caller overrides to 5.

8. **webhooks.md:126,132-136 — Queue line numbers off**
   Doc references `app/tasks.py:184` for webhooks queue, `app/tasks.py:31` for images, `app/tasks.py:130` for newsletter, `app/tasks.py:182` for webhooks, `app/tasks.py:262,283` for email, `app/tasks.py:304` for backup. Actual line numbers:
   - images queue: line 30
   - newsletter queue: line 135
   - webhooks queue: lines 194, 233
   - email queue: lines 333, 354
   - backup queue: line 375

9. **webhooks.md:47-53 — `sign_webhook_payload` code block variable assignment**
   Doc shows `signature = hmac.new(...)` then `return f"sha256={signature}"`. Source at `app/webhooks.py:34-36` is functionally identical but assigns to `signature` variable. Minor stylistic difference, not a bug.

10. **webhooks.md — `deliver_webhook_task` retry behavior**
    Doc says "Retry Logic: Exponential backoff via Celery" (line 10). The overview.md context says "Webhook delivery does NOT retry per-webhook at the `deliver_webhook_task` level". This is correct — `deliver_webhook_task` at `app/tasks.py:194-230` dispatches to `deliver_single_webhook_task` which handles per-webhook retry. But the webhooks.md doc doesn't clarify this two-level architecture.

### Missing Documentation

1. **`app/webhook_encryption.py` — Not documented in any architecture doc**
   AES-256-GCM encryption module with `encrypt_webhook_secret()` and `decrypt_webhook_secret()`. Referenced in overview.md:99 as "Detailed implementation: architecture/infrastructure/webhooks.md" but webhooks.md only mentions it in the model description (line 25) without documenting the actual encryption functions.

2. **`app/utils.py` — Not documented as infrastructure component**
   Contains `is_safe_webhook_url()` (the SSRF protection function), `sanitize_css()`, error logging utilities (`log_storage_error`, `log_security_event`, `log_scheduler_error`, `handle_error`, `unified_error_handler`). The overview.md mentions SSRF protection but references the wrong function name.

3. **`app/services/search/postgresql.py` — Exists but not reviewed**
   Doc says it's a "Stub for future PostgreSQL implementation" — confirmed it exists at `app/services/search/postgresql.py` and raises `NotImplementedError`.

4. **`extract_snippet()` function in `app/search.py:246-272`**
   Public function (not in `__all__`) that extracts text snippets around query matches. Not documented in search.md.

5. **`init_storage()` function in `app/storage.py:268-272`**
   Allows explicit initialization with a base directory. Not documented in storage.md.

6. **`storage_delete_file()` function in `app/storage.py:275-278`**
   Convenience wrapper for deleting files. Not documented.

7. **`_generate_responsive_variants_local()` in `app/storage.py:369-375`**
   Deprecated function that just delegates to Celery task. Not mentioned in docs.

8. **`app/templates/email/base_email.html`**
   Base email template not listed in email.md templates section.

9. **Health check requires `secret` parameter for detailed mode**
   `app/routes/public/meta.py:195-198` — detailed mode requires `?secret=<HEALTH_CHECK_SECRET>` in addition to `?detailed=true`. Not documented.

### Potential Bugs / Concerns

1. **`app/services/search/sqlite.py:10-12` — Dead state variables**
   `SQLiteSearchProvider` defines `_fts_enabled`, `_fts_check_time`, and `_FTS_CHECK_TTL` instance variables that are never used. The `search()` method delegates to `app/search.py:search()` which uses its own module-level state. This is dead code that could cause confusion.

2. **overview.md:93 — SSRF code uses `socket.gethostbyname` (doc block)**
   The doc code block uses `socket.gethostbyname` which only resolves IPv4 and doesn't handle dual-stack hosts. The actual code uses `socket.getaddrinfo` with `AF_UNSPEC` which is correct. If someone implements based on the doc, they'd have a less robust SSRF check.

3. **`_delete_existing_variants()` only handles LocalStorageBackend and S3StorageBackend**
   `app/storage.py:286-322` — If a new storage backend is added, variant cleanup silently does nothing. Should use the `StorageBackend` interface or log a warning for unknown backends.

4. **`deliver_webhook_task` marks `delivered=True` before individual deliveries complete**
   `app/tasks.py:226` — The event is marked as delivered immediately after dispatching individual tasks, before any delivery actually happens. The `_update_delivery_status` function then potentially overwrites this. The `delivered` field semantics are unclear.

5. **`send_newsletter` returns `all_sent` but callers may not check it**
   `app/email.py:189-228` — The function returns a boolean, but the newsletter task at `app/tasks.py:167` captures the return value and handles it. However, `send_newsletter_task` returns the boolean to Celery which may not propagate failure status correctly for retry purposes.

6. **`highlight_query()` escapes HTML then applies regex**
   `app/search.py:362-364` — The function escapes HTML first, then applies `re.escape(query)` as a regex pattern. If the query contains special regex characters, `re.escape` handles them, but the escaped text may not match the original query terms after HTML escaping (e.g., `&` becomes `&amp;`).

### Improvement Suggestions

1. **Rename `is_safe_url` reference to `is_safe_webhook_url`** in overview.md and fix the code block to match actual implementation or clearly label it as pseudocode.

2. **Document `app/webhook_encryption.py`** as a separate section or in the webhooks architecture doc with the encryption key requirements (`WEBHOOK_ENCRYPTION_KEY` env var, 32 bytes or 64 hex chars).

3. **Document `app/utils.py`** infrastructure utilities, especially `is_safe_webhook_url()` with its full validation logic.

4. **Remove dead state variables** from `SQLiteSearchProvider.__init__()` (`app/services/search/sqlite.py:10-12`).

5. **Fix health check `detailed` parameter** in overview.md from `?detailed=1` to `?detailed=true` and document the `?secret=` requirement.

6. **Fix `disk_space` check description** in overview.md from "> 100MB" to ">= 10% free".

7. **Update queue line numbers** in webhooks.md to match current source.

8. **Document the two-level webhook delivery architecture** in webhooks.md: `deliver_webhook_task` dispatches, `deliver_single_webhook_task` handles per-webhook retry.

9. **Add `base_email.html`** to email templates list.

## Action Items

| # | Priority | Description | Docs Affected |
|---|----------|-------------|---------------|
| 1 | high | Fix `is_safe_url` → `is_safe_webhook_url` name and code block in overview.md | overview.md |
| 2 | high | Fix `?detailed=1` → `?detailed=true` and document `?secret=` requirement | overview.md |
| 3 | high | Fix `disk_space` check description (10% free, not 100MB) | overview.md |
| 4 | medium | Document `app/webhook_encryption.py` in webhooks.md | webhooks.md |
| 5 | medium | Document `is_safe_webhook_url()` full validation logic in webhooks.md or overview.md | webhooks.md, overview.md |
| 6 | medium | Update queue line numbers in webhooks.md | webhooks.md |
| 7 | medium | Document two-level webhook delivery architecture | webhooks.md |
| 8 | low | Remove dead state variables from `SQLiteSearchProvider.__init__()` | app/services/search/sqlite.py |
| 9 | low | Document `extract_snippet()`, `init_storage()`, `storage_delete_file()` | search.md, storage.md |
| 10 | low | Add `base_email.html` to email templates list | email.md |
| 11 | low | Clarify `_send_email_with_retry` default (3) vs newsletter override (5) in email.md | email.md |
