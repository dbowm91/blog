# Services Architecture Review

**Reviewed:** 2026-06-02
**Architecture Docs:** architecture/services/overview.md, backup.md, encryption.md, search.md, slug.md, tag.md, tag_cache.md, serialization.md
**Source Files:** app/services/backup.py, app/services/encryption.py, app/backup_encryption.py, app/webhook_encryption.py, app/tag_cache.py, app/services/serialization.py, app/services/slug.py, app/services/tag.py, app/search.py, app/services/search/__init__.py, app/services/search/sqlite.py, app/services/search/postgresql.py

---

## Findings

### Verified Claims (Correct)

#### overview.md
- All service file locations and purposes are correctly mapped (backup, encryption, backup_encryption, webhook_encryption, serialization, slug, tag, tag_cache, search/search.py)

#### backup.md
- `create_backup()` function signature (lines 17-24) matches exactly
- Mutual exclusivity of `compress` and `encrypt` is correctly documented (line 70: `elif compress:` — encrypt takes precedence)
- `cleanup_old_backups()` signature and behavior are correct
- `run_daily_backup()` correctly described as NOT supporting encryption/compression
- Encryption failure behavior documented correctly (unencrypted backup retained, warning logged)
- `decrypt_backup_file()` signature matches (line 122)
- Default backup naming pattern (`blog_YYYYMMDD_HHMMSS.db`, `.db.gz`, `.db.gpg`) is correct
- Default retention of 7 is correct (`BACKUP_RETENTION_COUNT = 7` at backup.py:21)
- Key configuration from `BACKUP_ENCRYPTION_KEY` env var is correct
- TOTP encryption uses SECRET_KEY with no key derivation (correct)
- Webhook encryption uses WEBHOOK_ENCRYPTION_KEY with no key derivation (correct)
- Backup encryption uses PBKDF2 with 600,000 iterations (correct at backup_encryption.py:43)

#### encryption.md
- `EncryptionError` at encryption.py:16-19 matches
- `WebhookEncryptionError` at webhook_encryption.py:16-19 matches
- `ConfigurationError` at search/__init__.py:7-10 matches
- Three encryption modules table is accurate

#### search.md
- `SearchProvider` abstract base class interface (lines 13-83) matches
- `SQLiteSearchProvider` wrapping module-level functions (not reimplementing) is correctly documented
- FTS5 features (BM25 ranking, prefix='2 3 4', snippet highlighting, did-you-mean with cutoff=0.6) are correct
- `get_did_you_mean()` case preservation at lines 342-344 is correctly documented
- Line number references for module-level functions in app/search.py:
  - reset_fts_available(): 36 (correct)
  - rebuild_fts(): 101 (correct)
  - sync_fts(): 111 (correct)
  - sync_fts_batch(): 133 (correct)
  - remove_fts(): 174 (correct)
  - search(): 196 (correct)
  - get_indexed_terms(): 219 (correct)
  - get_indexed_terms_fallback(): 230 (correct)
  - _escape_fts_term(): 188 (correct)
  - extract_snippet(): 246 (correct)
  - get_search_snippets(): 275 (correct)
  - get_did_you_mean(): 320 (correct)
  - highlight_query(): 349 (correct)
- _FTS_CHECK_TTL = 300 (5 minutes) at search.py:32 is correct
- Configuration values SEARCH_PROVIDER, FTS_RESULT_LIMIT default 100 are correct

#### slug.md
- `generate_unique_slug()` signature at slug.py:12 matches
- Collision handling (100 tries, then UUID suffix) is correct
- UUID fallback format `{base_slug}-{8_char_hex_uuid}` is correct (slug.py:42)

#### tag.md
- Function line numbers all match:
  - get_or_create_tags(): 12
  - get_tag_by_slug(): 32
  - get_all_tags(): 37
  - get_tag_post_count(): 42
  - delete_tag_if_unused(): 55
- `get_tag_post_count()` only counts published posts (correct, filters on Post.published)

#### tag_cache.md
- Function line numbers match (16, 32, 39, 46, 52)
- TAG_CACHE_TTL_SECONDS default 60 is correct (config.py:121)
- Cache invalidation call locations mostly accurate (see discrepancies below)
- `_build_tag_counts_query()` joins post_tags with Post filtered by published=True (correct)

#### serialization.md
- All serialize functions correctly described with their fields
- No deserialize_* functions in module (import handled inline in CLI) is correct
- `export_data_to_dict()` signature and version default correct

---

### Discrepancies (Doc vs Code)

#### tag_cache.md:37 — Scheduler invalidation call line numbers
**Doc claims:** `app/scheduler.py:224,256`
**Actual:** 
- Line 224: `from app.tag_cache import invalidate_tag_cache` (import statement)
- Line 256: `invalidate_tag_cache()` (actual call)

**Assessment:** The import at line 224 is not an invalidation call. The actual invalidation call is at line 256. The documentation conflates the import location with the call location. The call location (256) is accurate; the import line (224) is not an invalidation call.

#### tag_cache.md:36 — API tags invalidation call line numbers
**Doc claims:** `app/routes/api/tags.py:130,189,219`
**Actual:** Verified correct for all three locations (lines 130, 189, 219).

#### tag_cache.md:34 — Posts __init__ invalidation call line numbers
**Doc claims:** `app/routes/admin/posts/__init__.py:158,179,198,216`
**Actual:** Verified correct for all four locations (lines 158, 179, 198, 216).

#### backup.md:156 — run_daily_backup reference
**Doc claims:** `run_daily_backup()` at `app/scheduler.py:262`
**Actual:** `app/scheduler.py:262` defines a wrapper function `run_daily_backup` that imports and calls the service function from `app/services/backup.py`. The service-level function is at `app/services/backup.py:163`. The documentation references the scheduler wrapper location, which is technically accurate but may cause confusion when tracing the actual implementation.

---

### Missing Documentation

1. **`__all__` exports in app/search.py**: Several documented functions (`extract_snippet`, `get_search_snippets`, `get_indexed_terms_fallback`, `_escape_fts_term`) are not exported in `__all__` and are effectively internal/private.

2. **Thread-safety mechanism**: `_fts_lock` (threading.Lock) at search.py:33 provides thread-safety for `_check_fts_enabled()` caching, but this is not documented.

3. **Two backup mechanisms exist**: `run_daily_backup()` in scheduler creates plain unencrypted backups, while `create_backup()` in the service supports encryption. This distinction (plain backup vs encrypted backup) and when to use each is not clearly highlighted.

4. **Error handling patterns for encryption modules**:
   - `app/services/encryption.py:get_encryption_key()` silently pads keys < 32 bytes with null bytes rather than raising an error
   - `app/webhook_encryption.py:_get_encryption_key()` accepts raw strings that are not 32 bytes (only validates for 64-char hex)
   - These behaviors have security implications that should be documented

5. **PostgreSQLSearchProvider stub status**: The postgresql.py file contains only stub methods that raise ConfigurationError. This is correctly noted as "not implemented" in search.md, but the implications (configure SEARCH_PROVIDER=sqlite only) could be more prominently documented.

6. **FTS5 fallback behavior**: When FTS5 is unavailable, search operations return empty results, and `get_did_you_mean` may return results from `get_indexed_terms_fallback`. This graceful degradation behavior is not documented.

---

### Potential Bugs / Concerns

#### 1. Key padding behavior in TOTP encryption (medium concern)
**File:** `app/services/encryption.py:36-38`
```python
if len(key) < KEY_SIZE:
    key = key.ljust(KEY_SIZE, b"\x00")[:KEY_SIZE]
```
Keys shorter than 32 bytes are null-padded rather than rejected. If a SECRET_KEY shorter than 32 characters is used, encryption will succeed but with weakened key entropy. This should either:
- Raise `EncryptionError` for keys < 32 bytes, or
- Be clearly documented as intentional behavior

#### 2. Overly broad exception catching in decrypt_backup_file (low concern)
**File:** `app/services/backup.py:141`
```python
except (OSError, ValueError, SQLAlchemyError) as e:
```
Catching `SQLAlchemyError` is unnecessary since the operation is purely file I/O. This suggests copy-paste error or defensive programming without understanding the actual failure modes.

#### 3. Missing cryptographic library handling in encryption.py (low concern)
**File:** `app/services/encryption.py`
No check for `CRYPTOGRAPHY_AVAILABLE`. If the cryptography library is not installed, functions will fail with `ImportError` rather than a meaningful error message. Compare with `backup_encryption.py` which has `CRYPTOGRAPHY_AVAILABLE` checks.

#### 4. Webhook encryption key handling allows invalid key formats (medium concern)
**File:** `app/webhook_encryption.py:42-54`
The code accepts a raw string key that is not exactly 32 bytes (after encoding to UTF-8). Only 64-character hex strings are explicitly validated. Any other non-32-byte string passes through and is used directly. This could result in encryption with incorrect key sizes.

#### 5. Undocumented encryption availability flag (low concern)
**File:** `app/backup_encryption.py:176-178`
```python
def is_encryption_available() -> bool:
    return CRYPTOGRAPHY_AVAILABLE and bool(BACKUP_ENCRYPTION_KEY)
```
This function is used by `_encrypt_backup_file()` to check if encryption can proceed, but the result is not exposed to callers to know why encryption was skipped.

---

### Improvement Suggestions

#### Documentation Improvements

1. **tag_cache.md**: Correct the scheduler line number reference to distinguish import (224) from call (256), or note both.

2. **backup.md**: Add a prominent note that `run_daily_backup()` in scheduler creates plain backups while `create_backup()` with `encrypt=True` creates encrypted backups. This architectural distinction is easy to miss.

3. **search.md**: Add a section on "Internal vs Exported Functions" clarifying that `extract_snippet`, `get_search_snippets`, `get_indexed_terms_fallback`, and `_escape_fts_term` are internal functions not part of the public API.

4. **encryption.md** or **backup.md**: Document the key padding/truncation behavior for `app/services/encryption.py` and the key format flexibility in `app/webhook_encryption.py` so operators understand the security implications.

5. **overview.md**: Consider adding a brief summary distinguishing the three encryption modules (backup_encryption.py for files, encryption.py for TOTP secrets, webhook_encryption.py for webhook secrets).

#### Code Improvements

1. **app/services/encryption.py**: Add `CRYPTOGRAPHY_AVAILABLE` check like the other encryption modules, and raise a clear `EncryptionError` for keys < 32 bytes.

2. **app/services/backup.py:141**: Remove `SQLAlchemyError` from exception handling (not relevant for file I/O operations).

3. **app/webhook_encryption.py**: Validate that raw string keys are exactly 32 bytes, similar to how hex keys are validated.

---

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|---------|
| 1 | medium | Clarify tag_cache.md scheduler line references (import at 224 vs call at 256) | docs |
| 2 | medium | Document key padding behavior in app/services/encryption.py (security implication for short SECRET_KEY) | docs, code |
| 3 | low | Add CRYPTOGRAPHY_AVAILABLE check to app/services/encryption.py for consistent error handling | code |
| 4 | low | Remove unnecessary SQLAlchemyError catch in backup.py decrypt function | code |
| 5 | low | Validate raw string key length in webhook_encryption.py (currently accepts any length) | code |
| 6 | low | Document that extract_snippet, get_search_snippets, _escape_fts_term are internal (not in __all__) | docs |
| 7 | low | Add note in backup.md distinguishing plain run_daily_backup from encrypted create_backup | docs |
