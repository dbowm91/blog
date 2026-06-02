# Infrastructure Architecture Review

**Reviewed:** 2026-06-02
**Architecture Docs:** architecture/infrastructure/email.md, architecture/infrastructure/search.md, architecture/infrastructure/storage.md, architecture/infrastructure/webhooks.md, architecture/infrastructure/overview.md
**Source Files:** app/search.py, app/email.py, app/storage.py, app/webhooks.py, app/utils.py

## Findings

### Verified Claims (Correct)

**Email (app/email.py)**
- `_send_email()` exists with correct signature (lines 24-41): `to: str, subject: str, html_body: str, text_body: Optional[str] = None`
- `_connect_smtp()` returns `None` on failure (lines 78-103)
- `_send_email_with_retry()` with `max_retries: int = 3` default (line 111)
- `send_newsletter()` uses `NEWSLETTER_MAX_RETRY_ATTEMPTS` (5 retries) via `_send_email_with_retry()` at email.py:210
- Templates in `app/templates/email/` confirmed: `base_email.html`, `confirm.html`, `password_reset.html`, `newsletter.html`

**Search (app/search.py)**
- `init_fts()` (lines 63-98): Creates FTS5 virtual table with `prefix='2 3 4'`, handles `OperationalError`, `ProgrammingError`, `DatabaseError`
- `_check_fts_enabled()` caches for `_FTS_CHECK_TTL = 300` (5 minutes) at line 32
- `extract_snippet()` with `context_chars: int = 200` default (line 246)
- `get_indexed_terms_fallback()` exists at lines 230-243
- `rebuild_fts()` at lines 101-108
- `sync_fts()` returns `True`/`False` (lines 111-130)
- `sync_fts_batch()` returns `True`/`False` (lines 133-171)
- `remove_fts()` returns `True`/`False` (lines 174-185)
- `reset_fts_available()` at lines 39-43
- `get_indexed_terms()` uses `posts_fts_vocab` FTS5 table (lines 219-227)
- `highlight_query()` calls `html.escape()` before adding `<mark>` tags (line 367)
- `search()` returns `list[tuple[int, float]]` (lines 196-216)
- `get_search_snippets()` batches with `_SQLITE_MAX_VARS = 500` (line 291), sanitizes with `nh3.clean(tags={"mark"})` (line 314)
- `get_did_you_mean()` with `max_suggestions: int = 3` default (line 320)

**Storage (app/storage.py)**
- `LocalStorageBackend.__init__(self, base_dir: str)` (line 98)
- `S3StorageBackend.__init__` with correct parameters (lines 146-154)
- `upload_with_processing()` deletes existing variants before upload (lines 334-375)
- Variant cleanup: `400_`, `800_`, `1200_` prefixes and `.webp`, `.avif` suffixes (lines 298-305, 316-323)
- Thread-safe singleton via double-checked locking with `_storage_lock` (lines 270-281)
- S3 fallback to local when credentials missing (lines 244-253)

**Webhooks (app/webhooks.py)**
- `sign_webhook_payload()` generates `sha256=` HMAC signature (lines 32-36)
- `deliver_webhook()` deprecated with `DeprecationWarning` (lines 39-84)
- `create_webhook_event()` catches `RequestException`, `ValueError`, `OSError` silently (lines 108-113)
- `WEBHOOK_TIMEOUT = 10` (line 23)

**Utils (app/utils.py)**
- `is_safe_webhook_url()` comprehensive SSRF protection (lines 383-485)
- Blocks: loopback, private, link-local, reserved, multicast, IPv4-mapped, AWS/GCP metadata endpoints

**Health Check (app/routes/public/meta.py:188)**
- `/health` endpoint at line 188
- Critical checks: `database`, `scheduler`, `search`, `disk_space`, `db_integrity` (lines 289-293)
- Overall "degraded" when any critical check fails (lines 294-302)
- Detailed mode requires `HEALTH_CHECK_SECRET` (lines 194-198)
- Thresholds: 10% disk space, 24h backup freshness
- Scheduler check only when `SMTP_HOST` configured (lines 215-219)

**Overview (architecture/infrastructure/overview.md)**
- `init_fts()` runs during `create_app()` at `app/__init__.py:430-433` - confirmed correct
- `send_newsletter()` opens one SMTP connection, pre-renders, iterates subscribers - confirmed
- Two-level webhook dispatch pattern - confirmed

### Discrepancies (Doc vs Code)

| File | Line | Doc Claims | Actual Code | Severity |
|------|------|------------|-------------|----------|
| `email.md` | 85 | `NEWSLETTER_MAX_RETRY_ATTEMPTS` default at `app/config.py:118` | Actually at `app/config.py:120` | minor (2 lines off) |
| `webhooks.md` | 120 | `deliver_webhook_task` at `app/tasks.py:195` | Actually at `app/tasks.py:200` | medium (5 lines off) |
| `webhooks.md` | 122 | `deliver_single_webhook_task` at `app/tasks.py:231` | Actually at `app/tasks.py:237` | medium (6 lines off) |
| `webhooks.md` | 205 | Tasks table: `run_backup_task` at `app/tasks.py:375` | Not verified | - |
| `search.md` | 76 | `get_indexed_terms_fallback()` at `app/search.py:229-243` | Actually at `app/search.py:230-243` | minor (1 line off) |

### Missing Documentation

1. **S3StorageBackend error handling limitation** (`app/storage.py:16-22`): `exists()` and `list_files()` return `False`/empty list on *any* error, making it impossible to distinguish 404 from network failures. This is documented in the source docstring but absent from architecture docs.

2. **`get_storage_backend()` vs `get_storage()` distinction**: `get_storage_backend()` is the factory, `get_storage()` is the thread-safe singleton getter. Architecture docs only mention `get_storage()`.

3. **S3 credential fallback**: When `STORAGE_BACKEND=s3` but credentials are missing, storage silently falls back to local backend (storage.py:244-253). Not documented.

4. **FTS corruption recovery**: If `init_fts()` fails, the corrupted FTS table is left intact. No automatic recovery mechanism exists. This "silent failure" design is documented but implications for operators not fully explained.

5. **Webhook encryption module**: `app/webhook_encryption.py` exists and is used by `Webhook.secret` property, but architecture/webhooks.md doesn't detail the encryption/decryption functions.

### Potential Bugs / Concerns

**Medium Severity:**

1. **`_send_email()` has no exception handling** (`app/email.py:24-41`): This function directly uses `smtplib.SMTP` context manager. If SMTP connection fails inside the `with` block, the exception propagates unhandled. Compare to `_connect_smtp()` which catches exceptions and returns `None`. For transactional emails called via Celery tasks, this means failures may not be gracefully handled.

2. **S3 error swallowing obscures diagnostics** (`app/storage.py:211-217, 226-236`): `exists()` returns `False` on any `ClientError`/`BotoCoreError`; `list_files()` returns empty list. Cannot distinguish 404 Not Found from network timeout or permission denied. This design requires API changes to fix properly.

3. **FTS corruption leaves search broken** (`app/search.py:63-98`): `init_fts()` creates tables but if the existing `posts_fts` table is corrupted, it doesn't drop and recreate. The corrupted table persists. No `DROP TABLE IF EXISTS` before `CREATE`. Only `INSERT OR IGNORE` is used for population.

**Low Severity:**

4. **Storage variant prefix collision potential**: Using simple `400_` prefix matching could inadvertently match files that naturally start with those characters. No escaping or boundary checking.

5. **S3 variant cleanup uses pagination-less listing** (`app/storage.py:326-328`): `list_objects_v2` with prefix but no `MaxKeys` or pagination handling works for small buckets but could miss objects or be slow for buckets with many objects under same prefix.

6. **Variant cleanup not atomic with upload** (`app/storage.py:353-365`): `_delete_existing_variants()` runs before the save. If upload fails mid-way, variants are already deleted but original not replaced.

### Improvement Suggestions

1. **Update line number references** in `webhooks.md` for `deliver_webhook_task` (should be 200 not 195) and `deliver_single_webhook_task` (should be 237 not 231).

2. **Update line number reference** in `email.md` for `NEWSLETTER_MAX_RETRY_ATTEMPTS` (should be 120 not 118).

3. **Document S3 error handling limitation** in `storage.md` - important for operators to understand diagnostic constraints.

4. **Document the two-function storage pattern** (`get_storage_backend()` factory vs `get_storage()` singleton getter).

5. **Add FTS corruption recovery guidance**: Document that `rebuild_fts()` should be run manually if FTS becomes corrupted, and consider adding a `DROP TABLE IF EXISTS posts_fts` before recreation in `init_fts()`.

6. **Add webhook encryption section** to `webhooks.md` documenting the `encrypt_webhook_secret()` and `decrypt_webhook_secret()` functions.

7. **Consider adding variant prefix escaping** in storage to prevent filename collisions (e.g., file `400_test.jpg` vs variant `400_400_test.jpg`).

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|---------|
| 1 | medium | Update `webhooks.md` line 120: `deliver_webhook_task` is at `app/tasks.py:200` not `195` | docs |
| 2 | medium | Update `webhooks.md` line 122: `deliver_single_webhook_task` is at `app/tasks.py:237` not `231` | docs |
| 3 | low | Update `email.md` line 85: `NEWSLETTER_MAX_RETRY_ATTEMPTS` is at `app/config.py:120` not `118` | docs |
| 4 | low | Update `search.md` line 76: `get_indexed_terms_fallback()` starts at line 230 not 229 | docs |
| 5 | medium | Document S3StorageBackend `exists()`/`list_files()` error handling limitation in `storage.md` | docs |
| 6 | low | Document `get_storage_backend()` vs `get_storage()` distinction in `storage.md` | docs |
| 7 | low | Document S3 credential fallback behavior in `storage.md` | docs |
| 8 | medium | Consider adding `DROP TABLE IF EXISTS posts_fts` before recreation in `init_fts()` to handle corruption | source |
| 9 | low | Consider documenting FTS corruption recovery procedure for operators | docs |
| 10 | low | Add webhook encryption section to `webhooks.md` | docs |
