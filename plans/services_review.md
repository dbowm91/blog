# Services Module Architecture Review

**Reviewed:** 2026-05-31
**Architecture Docs:** overview.md, backup.md, search.md, slug.md, tag.md, tag_cache.md, serialization.md
**Source Files:** app/services/, app/tag_cache.py, app/backup_encryption.py, app/webhook_encryption.py

## Findings

### Verified Claims (Correct)

- overview.md service table: all file paths and module descriptions match actual code
- backup.md `create_backup()` signature: `(db_path, backup_dir, compress=False, keep=7, encrypt=False) -> Optional[str]` matches code at `app/services/backup.py:24-30`
- backup.md `cleanup_old_backups()` signature: `(backup_dir, keep) -> None` matches code at `app/services/backup.py:142`
- backup.md `run_daily_backup()` signature: `(app: Any) -> None` matches code at `app/services/backup.py:159`
- backup.md `decrypt_backup_file()` signature: `(input_path, output_path=None) -> bool` matches code at `app/services/backup.py:118`
- backup.md PBKDF2 parameters: 600,000 iterations, 16-byte salt, 32-byte key, 12-byte nonce all match `app/backup_encryption.py:43-46`
- backup.md min password 12 characters matches `app/backup_encryption.py:68`
- backup.md file format `salt(16) + nonce(12) + ciphertext + tag(16)` matches `app/backup_encryption.py:131`
- backup.md encryption modules list (TOTP, backup, webhook) all exist at stated paths
- backup.md `.gpg` extension note is accurate — actual encryption is AES-256-GCM, not GPG
- backup.md `create_backup()` returns path even when encryption fails — confirmed at `app/services/backup.py:68-71`
- search.md `SearchProvider` ABC abstract methods match `app/services/search/__init__.py:13-83`
- search.md SQLiteSearchProvider wraps module-level functions — confirmed in `app/services/search/sqlite.py`
- search.md FTS5 `prefix='2 3 4'` confirmed at `app/search.py:70`
- search.md BM25 ranking (lower = better) confirmed
- search.md `_FTS_CHECK_TTL = 300` confirmed at `app/search.py:30`
- search.md all 13 module-level function line numbers are correct (`app/search.py`)
- slug.md `generate_unique_slug()` signature matches `app/services/slug.py:12-13`
- slug.md 100 collision attempts then UUID fallback confirmed at `app/services/slug.py:32,41`
- slug.md UUID format `{base_slug}-{8_char_hex_uuid}` confirmed at `app/services/slug.py:42`
- tag.md `get_or_create_tags()` at line 12 confirmed
- tag.md `get_tag_post_count()` only counts published posts confirmed at `app/services/tag.py:49`
- serialization.md all 5 serialization function signatures match `app/services/serialization.py`
- serialization.md no `deserialize_*` functions confirmed
- tag_cache.md `_build_tag_counts_query()` at line 16 confirmed
- tag_cache.md `flask_cache.memoize(timeout=TAG_CACHE_TTL_SECONDS)` confirmed at `app/tag_cache.py:32`
- tag_cache.md `_invalidate_all_caches()` at `app/routes/admin/__init__.py:62` confirmed
- webhook_encryption.py accepts 32-byte raw or 64-char hex key — confirmed at `app/webhook_encryption.py:44-53`

### Discrepancies (Doc vs Code)

1. **backup.md:108 — Internal contradiction on "Silent fallback"**
   The "Key Configuration" section states: *"No error or warning is logged"* when encryption is silently skipped.
   But the "Encryption Behavior" section (line 54) states: *"a warning is logged and the unencrypted backup is retained"*.
   **Code reality**: TWO warnings are logged:
   - `app/services/backup.py:107-110` (`_encrypt_backup_file`): `WARNING "BACKUP_ENCRYPTION_KEY is set but encryption is not available..."`
   - `app/services/backup.py:69-71` (`create_backup`): `WARNING "Backup encryption failed, proceeding without encryption"`
   The "Silent fallback" claim is factually wrong and contradicts the document's own earlier section.

2. **backup.md:96 — config.toml encryption key claim is false**
   Doc states the key can come from: *"config.toml under [backup] section as encryption_key"*.
   **Code reality**: `app/backup_encryption.py:40` reads ONLY from `os.environ.get("BACKUP_ENCRYPTION_KEY", "")`. The `app/config.py:155` reads only `data_backup_dir` from `[backup]` section — no `encryption_key` field. The actual `config.toml` file has no `[backup]` section at all.

3. **search.md:53 — Wrong line reference for Case Preservation**
   Doc says: *"See `app/search.py:349-351`"* for the case preservation behavior in `get_did_you_mean()`.
   **Code reality**: Lines 349-351 are the `highlight_query()` function. The case preservation logic is at `app/search.py:342-344` in `get_did_you_mean()`.

4. **search.md:78 — Exception handling claim is incomplete**
   Doc states: *"All module-level functions in `app/search.py` catch `OperationalError`, `ProgrammingError`, and `DatabaseError`"*.
   **Code reality**: `get_indexed_terms()` at `app/search.py:226` catches only `(OperationalError, ProgrammingError)` — it does NOT catch `DatabaseError`.

5. **search.md:91-92 — `_SQLITE_MAX_VARS` scope misrepresentation**
   Doc presents `_SQLITE_MAX_VARS = 500` as a module-level constant in a code block alongside `_FTS_CHECK_TTL = 300`.
   **Code reality**: `_SQLITE_MAX_VARS` is a local variable inside `get_search_snippets()` at `app/search.py:291`, not a module-level constant.

6. **tag.md — Wrong line numbers for 4 of 5 functions**
   | Function | Doc Line | Actual Line |
   |----------|----------|-------------|
   | `get_or_create_tags()` | :12 | :12 (correct) |
   | `get_tag_by_slug()` | :34 | :32 |
   | `get_all_tags()` | :41 | :37 |
   | `delete_tag_if_unused()` | :58 | :55 |
   | `get_tag_post_count()` | :48 | :42 |

7. **tag_cache.md — Wrong line numbers for 4 of 5 functions**
   | Function | Doc Line | Actual Line |
   |----------|----------|-------------|
   | `_build_tag_counts_query()` | :16 | :16 (correct) |
   | `_get_tag_counts_cached()` | :30 | :32 |
   | `_get_tag_counts()` | :37 | :39 |
   | `_get_tag_counts_uncached()` | :44 | :46 |
   | `invalidate_tag_cache()` | :50 | :52 |

8. **overview.md — Duplicate table entries**
   "Encryption" and "Encryption (TOTP)" both point to `app/services/encryption.py` with nearly identical descriptions.

### Missing Documentation

1. **search.md — `init_fts()` not in module-level functions table**
   `init_fts()` at `app/search.py:58` is called by `SQLiteSearchProvider.initialize()` but is absent from the functions table in search.md.

2. **search.md — `_check_fts_enabled()` undocumented**
   `_check_fts_enabled()` at `app/search.py:43` is the caching gatekeeper for FTS operations and is not documented anywhere in the architecture docs.

3. **backup_encryption.py — Legacy `_has_gnupg()` function**
   Function at `app/backup_encryption.py:86-88` just returns `CRYPTOGRAPHY_AVAILABLE`. Name is misleading (references GnuPG). Not documented and appears unused.

4. **encryption.py — `EncryptionError` exception class**
   Custom exception at `app/services/encryption.py:16-19` is not documented in architecture docs.

5. **webhook_encryption.py — `WebhookEncryptionError` exception class**
   Custom exception at `app/webhook_encryption.py:16-19` is not documented in architecture docs.

6. **search/__init__.py — `ConfigurationError` exception class**
   Custom exception at `app/services/search/__init__.py:7-10` is not documented in architecture docs.

7. **search.md — `highlight_query()` HTML escaping behavior**
   The function at `app/search.py:362` calls `html.escape(text)` before applying `<mark>` highlights. This XSS-safety behavior is not documented.

8. **backup.md — Timezone inconsistency between backup paths**
   `create_backup()` uses `datetime.now()` (local time) at `app/services/backup.py:49`.
   `run_daily_backup()` uses `datetime.now(timezone.utc)` (UTC) at `app/services/backup.py:181`.
   This inconsistency is not documented.

### Potential Bugs / Concerns

1. **backup_encryption.py:237 — Missing `RuntimeError` catch in `decrypt_backup_file()`**
   `decrypt_backup()` raises `RuntimeError` on failure (line 184), but `decrypt_backup_file()` catches only `(OSError, ValueError, SQLAlchemyError)` — NOT `RuntimeError`. Decryption failures propagate as unhandled exceptions instead of returning `False`.
   **Compare with**: `encrypt_backup_file()` at line 212 correctly catches `RuntimeError` in its handler.
   **Impact**: Any decryption failure (wrong key, corrupted data, missing library) raises an unhandled exception rather than the documented `False` return.

2. **backup_encryption.py:133,183,237 — Missing `InvalidTag` exception catch**
   All three functions catch `(OSError, ValueError, SQLAlchemyError)` but NOT `cryptography.hazmat.primitives.exceptions.InvalidTag`. When GCM authentication fails (wrong key or corrupted data), `InvalidTag` is raised. This exception is NOT a subclass of `ValueError` in the cryptography library, so it propagates unhandled.
   **Impact**: Corrupted encrypted backups cause unhandled exceptions instead of clean error messages.

3. **backup.py:49 vs backup.py:181 — Timezone inconsistency**
   `create_backup()` uses `datetime.now()` (local/naive time) for timestamp.
   `run_daily_backup()` uses `datetime.now(timezone.utc)` (UTC-aware time) for timestamp.
   **Impact**: Backups created by different code paths have inconsistent timestamp formats. Retention cleanup that compares modification times could behave unexpectedly across DST transitions.

4. **backup_encryption.py:133,183 — Unnecessary `SQLAlchemyError` catch**
   Both `encrypt_backup()` and `decrypt_backup()` catch `SQLAlchemyError` from `sqlalchemy.exc`. A standalone encryption module should have no dependency on SQLAlchemy exception types. This is overly defensive and could mask unrelated errors if SQLAlchemy is somehow involved.

5. **tag_cache.py — Multi-worker cache invalidation race condition**
   `invalidate_tag_cache()` uses `flask_cache.delete_memoized()` which operates on the local worker's cache. In a multi-worker deployment, one worker's invalidation does not affect other workers' cached data. The TTL-based expiry is the only cross-worker consistency mechanism.

6. **encryption.py:36-38 — Null-byte key padding reduces entropy**
   `get_encryption_key()` pads short `SECRET_KEY` values with null bytes: `key.ljust(KEY_SIZE, b"\x00")[:KEY_SIZE]`. A short SECRET_KEY (e.g., 4 characters) produces a key with 28 null bytes, drastically reducing entropy.

7. **backup.py:54 — Extension ordering with mutual exclusivity**
   When both `compress=True` and `encrypt=True`, the code would produce `blog_*.db.gz.gpg` because compress appends `.gz` then encrypt appends `.gpg`. However, the `elif` at line 72 means compression is only applied when encrypt is `False`. This mutual exclusivity is not documented.

8. **backup.py:98-115 — `_encrypt_backup_file` in-place encryption risk**
   `encrypt_backup_file(filepath, filepath)` is called with the same path for input and output (`app/services/backup.py:112`). If the process crashes after truncating the output file but before writing the encrypted data, the backup is lost.

### Improvement Suggestions

1. **backup.md**: Remove or correct the "Silent fallback" section (line 108) to state that warnings ARE logged, consistent with both the code and the document's own "Encryption Behavior" section.

2. **backup.md**: Remove the config.toml encryption key claim (lines 96, 104) or add actual config.toml loading support in `app/backup_encryption.py`.

3. **search.md**: Fix the Case Preservation line reference from `app/search.py:349-351` to `app/search.py:342-344`.

4. **search.md**: Correct the exception handling claim to note that `get_indexed_terms()` does NOT catch `DatabaseError`.

5. **search.md**: Move `_SQLITE_MAX_VARS` out of the module-level constants code block, or add a comment that it is local to `get_search_snippets()`.

6. **search.md**: Add `init_fts()` and `_check_fts_enabled()` to the module-level functions table.

7. **tag.md**: Update all line numbers to match current code.

8. **tag_cache.md**: Update all line numbers to match current code.

9. **overview.md**: Merge the two "Encryption" rows into one entry.

10. **All encryption modules**: Document the `EncryptionError` / `WebhookEncryptionError` / `ConfigurationError` exception classes in their respective architecture docs.

11. **backup_encryption.py**: Add `RuntimeError` and `cryptography.exceptions.InvalidTag` to the exception handlers in `decrypt_backup()` and `decrypt_backup_file()`.

12. **backup_encryption.py**: Remove the legacy `_has_gnupg()` function or rename it to reflect its actual purpose.

13. **backup_encryption.py**: Remove unnecessary `SQLAlchemyError` from exception handlers in standalone encryption functions.

14. **backup.md**: Document the timezone inconsistency between `create_backup()` (local time) and `run_daily_backup()` (UTC).

15. **search.md**: Document that `highlight_query()` HTML-escapes input text before applying `<mark>` tags.

## Action Items

| # | Priority | Description | Affects |
|---|----------|-------------|--------|
| 1 | high | Add `RuntimeError` and `InvalidTag` to `decrypt_backup_file()` exception handler in `app/backup_encryption.py:237` — currently unhandled exceptions break the documented `False` return contract | source |
| 2 | high | Add `InvalidTag` catch to `decrypt_backup()` in `app/backup_encryption.py:183` — corrupted encrypted data causes unhandled exception | source |
| 3 | high | Fix backup.md "Silent fallback" section (line 108) to match actual code behavior (warnings ARE logged) — self-contradictory documentation | docs |
| 4 | high | Remove false config.toml encryption key claim from backup.md (lines 96, 104) — key is only loaded from environment variable | docs |
| 5 | med | Fix search.md Case Preservation line reference from `349-351` to `342-344` | docs |
| 6 | med | Fix search.md exception handling claim — `get_indexed_terms()` does not catch `DatabaseError` | docs |
| 7 | med | Update tag.md line numbers for 4 functions (get_tag_by_slug, get_all_tags, delete_tag_if_unused, get_tag_post_count) | docs |
| 8 | med | Update tag_cache.md line numbers for 4 functions (_get_tag_counts_cached, _get_tag_counts, _get_tag_counts_uncached, invalidate_tag_cache) | docs |
| 9 | med | Add `init_fts()` and `_check_fts_enabled()` to search.md module-level functions table | docs |
| 10 | med | Document timezone inconsistency between `create_backup()` (local) and `run_daily_backup()` (UTC) in backup.md | docs |
| 11 | low | Remove duplicate "Encryption" row from overview.md service table | docs |
| 12 | low | Move `_SQLITE_MAX_VARS` out of module-level constants code block in search.md or clarify it is local to `get_search_snippets()` | docs |
| 13 | low | Remove legacy `_has_gnupg()` function from `app/backup_encryption.py` or rename it | source |
| 14 | low | Remove unnecessary `SQLAlchemyError` from exception handlers in `app/backup_encryption.py` standalone encryption functions | source |
| 15 | low | Document `EncryptionError`, `WebhookEncryptionError`, and `ConfigurationError` exception classes in respective architecture docs | docs |
| 16 | low | Document `highlight_query()` HTML escaping behavior in search.md | docs |
| 17 | low | Document mutual exclusivity of `compress` and `encrypt` parameters in `create_backup()` | docs |
