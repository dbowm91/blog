# Services Architecture Review

**Reviewed:** 2026-05-31
**Architecture Docs:** overview.md, backup.md, encryption.md, search.md, slug.md, tag.md, tag_cache.md, serialization.md
**Source Files:** app/services/, app/tag_cache.py, app/backup_encryption.py, app/webhook_encryption.py

## Findings

### Verified Claims (Correct)

- **backup.md**: `create_backup()` signature at `app/services/backup.py:24-30` matches doc exactly
- **backup.md**: Mutual exclusivity of `compress`/`encrypt` params confirmed — `elif compress:` at `backup.py:72`
- **backup.md**: Unencrypted fallback on encryption failure confirmed — `backup.py:68-71`
- **backup.md**: Double warning on key load failure confirmed — `backup.py:107-110` and `backup.py:69-71`
- **backup.md**: Backup file naming conventions (`.db`, `.db.gz`, `.db.gpg`) match `backup.py:51-54`
- **backup.md**: Encryption modules table — all three modules exist with described parameters
- **backup.md**: `decrypt_backup_file()` default output path logic confirmed — `backup.py:131-135`
- **encryption.md**: `EncryptionError` class at `app/services/encryption.py:16-19` ✓
- **encryption.md**: `WebhookEncryptionError` class at `app/webhook_encryption.py:16-19` ✓
- **encryption.md**: `ConfigurationError` class at `app/services/search/__init__.py:7-10` ✓
- **encryption.md**: Three encryption modules with described key sources and ciphers ✓
- **search.md**: `SearchProvider` ABC methods match `app/services/search/__init__.py:13-83` ✓
- **search.md**: `SQLiteSearchProvider` wraps module-level functions from `app/search.py` ✓
- **search.md**: `PostgreSQLSearchProvider` is a stub raising `ConfigurationError` ✓
- **search.md**: FTS5 virtual table with `prefix='2 3 4'` confirmed — `search.py:74-76`
- **search.md**: BM25 ranking confirmed — `search.py:209-210`
- **search.md**: Case preservation in `get_did_you_mean()` confirmed — `search.py:342-344`
- **slug.md**: `generate_unique_slug()` signature and collision handling match `app/services/slug.py:12-43` ✓
- **slug.md**: 100-attempt limit with UUID fallback confirmed — `slug.py:32,41-42`
- **tag.md**: All five public functions exist at documented locations ✓
- **tag.md**: `get_tag_post_count()` counts only published posts — `tag.py:49` ✓
- **tag_cache.md**: `_get_tag_counts_cached()` uses `flask_cache.memoize` — `tag_cache.py:32` ✓
- **tag_cache.md**: Cache invalidation locations verified: `tags.py:76,104,142`, `posts/__init__.py:158,179,198,216`, `scheduler.py:224,256`, `api/tags.py:130,189,219` ✓
- **serialization.md**: All five serialization functions match `app/services/serialization.py` ✓
- **serialization.md**: No `deserialize_*` functions — import handled inline in CLI ✓

### Discrepancies (Doc vs Code)

| # | Doc File | Claim | Actual | Severity |
|---|----------|-------|--------|----------|
| 1 | `tag_cache.md:31` | `app/routes/admin/posts/editor.py:89,204` | Actual lines are `77,192` | Low (stale line refs) |
| 2 | `tag_cache.md:33` | `app/routes/admin/posts/manage.py:82` | Actual line is `70` | Low (stale line ref) |
| 3 | `encryption.md:17` | Functions named `encrypt_secret()`, `decrypt_secret()` | Actual names are `encrypt()` and `decrypt()` at `encryption.py:41,69` | Medium (wrong function names) |
| 4 | `search.md:62` | `reset_fts_available()` at `app/search.py:36` | Actual line is `39` | Low (stale line ref) |
| 5 | `search.md` | `init_fts()` not listed in function table | Exists at `search.py:63`, called by `SQLiteSearchProvider.initialize()` | Medium (missing from docs) |

### Missing Documentation

| # | Item | Location | Notes |
|---|------|----------|-------|
| 1 | `init_fts()` function | `app/search.py:63-98` | Creates FTS5 virtual table and populates index. Called by `SQLiteSearchProvider.initialize()`. Not listed in search.md function table. |
| 2 | `_check_fts_enabled()` | `app/search.py:46-60` | Internal caching function with double-checked locking. Not documented. |
| 3 | `_derive_key()` | `app/backup_encryption.py:49-83` | PBKDF2 key derivation. Referenced in backup.md but not its own section. |
| 4 | `is_encryption_available()` | `app/backup_encryption.py:182-184` | Mentioned in backup.md but not in encryption.md module table. |
| 5 | `_encrypt_backup_file()` | `app/services/backup.py:98-115` | Internal wrapper. Documented in backup.md behavior section but not in a dedicated API section. |

### Potential Bugs / Concerns

| # | Severity | Description | Location |
|---|----------|-------------|----------|
| 1 | **CRITICAL** | **`_invalidate_all_caches()` is dead code.** Defined at `app/routes/admin/__init__.py:62` but never called anywhere in the codebase. The coordinated cache invalidation described in `tag.md:42-54` is not actually happening. Individual caches are invalidated separately in route handlers via direct `invalidate_tag_cache()` calls. | `app/routes/admin/__init__.py:62` |
| 2 | **HIGH** | **In-place encryption overwrites source file.** `backup.py:112` calls `encrypt_backup_file(filepath, filepath)` — same path for input and output. The function reads the entire file into memory, then writes encrypted content to the same path. If the process crashes or is killed between the `open(output_path, "wb")` and `f.write(encrypted)` completing, the backup file is corrupted with partial/no data. | `app/services/backup.py:112` |
| 3 | **MEDIUM** | **Weak key handling for TOTP encryption.** `app/services/encryption.py:37` pads short `SECRET_KEY` values with null bytes (`key.ljust(KEY_SIZE, b"\x00")`). If `SECRET_KEY` is shorter than 32 bytes, the effective key space is reduced. A 16-byte key would have 16 bytes of null padding, making it equivalent to a 16-byte key for AES-256. | `app/services/encryption.py:36-38` |
| 4 | **LOW** | **Unnecessary exception type caught.** `backup.py:113` catches `SQLAlchemyError` in `_encrypt_backup_file`, but the underlying `encrypt_backup_file()` only raises `OSError`, `ValueError`, `RuntimeError`. `SQLAlchemyError` will never be caught here. | `app/services/backup.py:113` |
| 5 | **LOW** | **Tag count join direction is unusual.** `get_tag_post_count()` in `tag.py:44-52` uses `outerjoin(Post.tags)` starting from `Tag`, which traverses the many-to-many relationship backwards. While it works due to the `or 0` fallback, the more conventional approach would be to join from `Post` to `Tag` via the association table. | `app/services/tag.py:44-52` |

### Improvement Suggestions

| # | Priority | Description |
|---|----------|-------------|
| 1 | High | Wire up `_invalidate_all_caches()` to be called from route handlers, or remove it and update docs to reflect the actual per-function invalidation pattern. |
| 2 | High | Use a temporary file for in-place encryption: write to `filepath + ".enc.tmp"`, then `os.replace()` to `filepath` on success. This prevents corruption on crash. |
| 3 | Medium | Remove `SQLAlchemyError` from the exception tuple in `_encrypt_backup_file()` to avoid masking unrelated errors. |
| 4 | Medium | Document `init_fts()` in the search.md function table since it's the entry point for FTS initialization. |
| 5 | Medium | Fix stale line number references in `tag_cache.md` (editor.py:89→77, manage.py:82→70). |
| 6 | Low | Consider using PBKDF2 or HKDF for TOTP key derivation instead of null-padding `SECRET_KEY`. |
| 7 | Low | Add a note in `encryption.md` that `encrypt()`/`decrypt()` are the actual function names (not `encrypt_secret()`/`decrypt_secret()`). |

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|---------|
| 1 | Critical | Investigate and fix `_invalidate_all_caches()` dead code — either wire it up or remove and update docs | `app/routes/admin/__init__.py`, `architecture/services/tag.md`, `architecture/services/tag_cache.md` |
| 2 | High | Fix in-place encryption to use temp file pattern | `app/services/backup.py:112`, `app/backup_encryption.py:187-209` |
| 3 | Medium | Fix function name references in `encryption.md` (`encrypt_secret`→`encrypt`, `decrypt_secret`→`decrypt`) | `architecture/services/encryption.md:17` |
| 4 | Medium | Add `init_fts()` to search.md function table | `architecture/services/search.md` |
| 5 | Medium | Update stale line numbers in `tag_cache.md` | `architecture/services/tag_cache.md:31,33` |
| 6 | Low | Remove unnecessary `SQLAlchemyError` catch in `_encrypt_backup_file` | `app/services/backup.py:113` |
| 7 | Low | Review TOTP key padding strategy for short SECRET_KEY values | `app/services/encryption.py:36-38` |
