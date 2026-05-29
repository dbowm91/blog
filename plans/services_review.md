# Services Architecture Review

**Reviewed:** 2026-05-29
**Architecture Docs:** overview.md, backup.md, search.md, slug.md, tag.md, tag_cache.md, serialization.md
**Source Files:** app/services/, app/tag_cache.py, app/backup_encryption.py, app/webhook_encryption.py

## Findings

### Verified Claims (Correct)

- **backup.py `create_backup()` signature**: Matches doc - `db_path`, `backup_dir`, `compress`, `keep`, `encrypt` params with correct defaults.
- **backup.py `cleanup_old_backups()`**: Signature `cleanup_old_backups(backup_dir: str, keep: int) -> None` - matches doc.
- **backup.py `run_daily_backup()`**: Exists at `app/services/backup.py:150` with correct behavior (no encryption/compression, uses sqlite3.backup()).
- **backup.py `decrypt_backup_file()`**: Signature `decrypt_backup_file(input_path: str, output_path: Optional[str] = None) -> bool` - matches doc.
- **backup_encryption.py**: PBKDF2 iterations = 600,000, salt = 16 bytes, nonce = 12 bytes, key = 32 bytes, AES-256-GCM - matches doc exactly.
- **webhook_encryption.py**: AES-256-GCM with 32-byte key or 64-char hex, nonce=12 bytes, Base64 output - matches doc.
- **services/encryption.py**: AES-256-GCM with direct key from SECRET_KEY (padded/truncated to 32 bytes) - matches doc for TOTP secret encryption.
- **slug.py `generate_unique_slug()`**: Function signature and collision handling (100 tries then UUID8 fallback) - matches doc.
- **tag.py functions**: `get_or_create_tags()`, `get_tag_by_slug()`, `get_all_tags()`, `delete_tag_if_unused()`, `get_tag_post_count()` - all exist with correct signatures. `get_tag_post_count()` correctly counts only published posts.
- **serialization.py functions**: All serialize functions (`serialize_post`, `serialize_subscriber`, `serialize_page`, `serialize_tag`, `export_data_to_dict`) match doc. Import is correctly documented as inline in CLI.
- **tag_cache.py functions**: `_build_tag_counts_query()` (line 16), `_get_tag_counts_cached()` (line 30), `_get_tag_counts()` (line 37), `_get_tag_counts_uncached()` (line 44), `invalidate_tag_cache()` (line 50) - all line numbers match doc.
- **tag_cache.md Cache Invalidation Lines**: All line number references are correct:
  - `app/routes/admin/posts/editor.py:89,204`
  - `app/routes/admin/posts/revisions.py:97`
  - `app/routes/admin/posts/manage.py:82`
  - `app/routes/admin/tags.py:76,104,142`
  - `app/routes/admin/posts/__init__.py:158,179,198,216`
  - `app/scheduler.py:224,256`
  - `app/routes/api/tags.py:130,189,219`
- **search.py function line numbers**: All correct:
  - `reset_fts_available()`:36, `rebuild_fts()`:101, `sync_fts()`:111, `sync_fts_batch()`:133, `remove_fts()`:174, `search()`:196, `get_indexed_terms()`:219, `get_indexed_terms_fallback()`:230, `_escape_fts_term()`:188, `extract_snippet()`:246, `get_search_snippets()`:275, `get_did_you_mean()`:320, `highlight_query()`:349
- **search.md FTS5 table**: Uses `prefix='2 3 4'` matching doc.
- **search.md "Case Preservation"**: Code at `app/search.py:342-344` correctly implements case-preserving suggestion return.
- **search.md SQLiteSearchProvider**: Wraps `app/search.py` functions rather than reimplementing - matches doc.

### Discrepancies (Doc vs Code)

- **overview.md line 10**: Claims `Encryption` (AES-256-GCM for TOTP) is at `app/services/encryption.py`. This is correct, but the file also exports `EncryptionError` class not mentioned in overview.
- **backup.md line 140**: References `run_daily_backup()` at `app/scheduler.py:261`, but the actual function is at `app/scheduler.py:262`. The wrapper is at line 262 and the actual implementation is at `app/services/backup.py:150`. Minor off-by-one error.
- **tag_cache.md line 30**: The doc says `invalidate_tag_cache()` at line 50, but the description says "Clears the memoized cache via `delete_memoized`" which is correct. However, the doc does not clarify that `_get_tag_counts_cached()` is the function that gets deleted.
- **search.md**: The doc does not list `init_fts()` function in the module-level functions table, though it exists at `app/search.py:58` and is used by `SQLiteSearchProvider.initialize()`.

### Missing Documentation

- **`app/services/__init__.py`**: Does not export `decrypt_backup_file` from backup.py, even though it's a public service function. The function exists in backup.py but isn't exposed at package level.
- **`_encrypt_backup_file()`**: Private function in backup.py (line 95) not documented. It returns `bool` and logs errors internally, used by `create_backup()` when `encrypt=True`.
- **Encryption modules error handling**: The doc describes the encryption parameters but doesn't document the exceptions that can be raised:
  - `backup_encryption.py`: `RuntimeError` (encryption unavailable), `ValueError` (key too short, invalid salt)
  - `webhook_encryption.py`: `WebhookEncryptionError`
  - `services/encryption.py`: `EncryptionError`
- **Webhook and TOTP encryption differences**: Both use AES-256-GCM but with different key handling approaches. The doc doesn't highlight this distinction clearly.
- **Search `extract_snippet()`**: Exists at `app/search.py:246` but is not listed in search.md's function table. It's used internally by `get_search_snippets()`.

### Potential Bugs / Concerns

1. **`backup_encryption.py` imports `SQLAlchemyError` but never uses it**: Line 28 imports `SQLAlchemyError` and lines 129, 178, 206, 231 catch it, but the module only uses `hashlib.pbkdf2_hmac`, `os.urandom`, and `cryptography` - no database operations. This is dead import code.

2. **`webhook_encryption.py` has redundant import**: Line 32 re-imports `binascii` inside `_get_encryption_key()` when it's already imported at line 3. This works but is unnecessary.

3. **`search.py` exception handling swallows errors silently**: Functions like `search()`, `get_indexed_terms()`, `get_search_snippets()` return empty results on `OperationalError`/`ProgrammingError` rather than propagating. While documented in search.md, this means FTS5 failures are silent and fall back gracefully - which could mask configuration issues.

4. **`invalidate_tag_cache()` uses `delete_memoized` with `flask_cache`**: The `flask_cache.delete_memoized()` API requires the cached function to be importable. This works because `_get_tag_counts_cached` is in `app.tag_cache` module scope, but if caching implementation changed to a different backend (Redis), this pattern may not work identically.

5. **Race condition in `_check_fts_enabled()`**: The `_fts_enabled` cache check at `app/search.py:43-55` uses a time-based TTL check but doesn't use application-level caching. Multiple concurrent requests could race on the `_fts_check_time` update.

### Improvement Suggestions

1. **Document the private `_encrypt_backup_file()` function** or clarify its relationship with `encrypt_backup_file()` in backup_encryption.py.

2. **Standardize exception classes**: `backup_encryption.py` raises generic `RuntimeError` and `ValueError`, while `webhook_encryption.py` and `services/encryption.py` have custom `WebhookEncryptionError` and `EncryptionError`. Consider using a common base exception or at least document the exception hierarchy.

3. **Add `decrypt_backup_file` to `app/services/__init__.py` exports** for consistency with other public backup service functions.

4. **Remove dead `SQLAlchemyError` import** from `app/backup_encryption.py:28` since it's never used.

5. **Remove redundant `binascii` re-import** inside `_get_encryption_key()` in `webhook_encryption.py`.

6. **Add `extract_snippet()` to search.md function table** since it's a public-ish function (used by tests and potentially externally).

7. **Consider adding `init_fts()` to search.md** since it's part of the public API exposed in `__all__`.

8. **Clarify the `run_daily_backup` location in backup.md**: The See Also reference to `app/scheduler.py:261` is slightly off. Could reference both `app/services/backup.py:150` (implementation) and `app/scheduler.py:262` (scheduler wrapper).

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|---------|
| 1 | low | Remove dead `SQLAlchemyError` import from `app/backup_encryption.py:28` | source |
| 2 | low | Remove redundant `binascii` re-import in `app/webhook_encryption.py:32` | source |
| 3 | medium | Export `decrypt_backup_file` from `app/services/__init__.py` for consistency | source |
| 4 | medium | Fix `app/scheduler.py` line reference in `architecture/services/backup.md:140` (261 -> 262) | docs |
| 5 | medium | Add `extract_snippet()` and `init_fts()` to search.md function table | docs |
| 6 | low | Consider standardizing encryption exception types across modules | architecture |
| 7 | low | Document `_encrypt_backup_file()` private function in backup.py or clarify its purpose | docs/source |
