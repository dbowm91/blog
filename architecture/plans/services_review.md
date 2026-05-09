# Services Module Architecture Review

**Review Date:** 2026-05-09
**Reviewer:** services_reviewer

## Verified Accurate Claims

### 1. Two Separate Backup Implementations
- **`create_backup()`** (`app/services/backup.py:24`): Used by Celery task, supports encryption/compression, uses `blog_*.db` naming
- **`run_daily_backup()`** (`app/services/backup.py:144`): Used by APScheduler, no encryption/compression, uses `backup_*.db` naming

The documentation correctly identifies both functions with their distinct naming conventions.

### 2. AES-256-GCM Encryption with PBKDF2
- Documentation (`backup.md`) correctly states: "AES-256-GCM encryption with PBKDF2 key derivation (not GPG)"
- Implementation confirms this in `app/backup_encryption.py`:
  - PBKDF2-HMAC-SHA256 with 600,000 iterations (line 43)
  - 16-byte salt, 12-byte nonce, 16-byte tag
  - AES-256-GCM authenticated encryption

### 3. Slug Collision Limit: 100 Tries
- `app/services/slug.py:32-41`: Loop iterates `while counter <= 100`, then falls back to UUID suffix with 8 characters from `uuid.uuid4().hex[:8]`

### 4. Newsletter Retry Count: 5
- `app/config.py:114`: `NEWSLETTER_MAX_RETRY_ATTEMPTS = int(_config["newsletter"].get("max_retry_attempts", 5))`
- AGENTS.md line 137 correctly states: "Newsletter retry count default is 5 (not 3 as some documentation may claim)"

### 5. Tag Caching with TAG_CACHE_TTL_SECONDS
- `app/config.py:115`: `TAG_CACHE_TTL_SECONDS = int(_config["app"].get("tag_cache_ttl_seconds", 60))`
- `app/tag_cache.py:30`: Uses `@flask_cache.memoize(timeout=TAG_CACHE_TTL_SECONDS)`

---

## Inaccurate/Outdated Claims

### 1. Backup Documentation - GPG Reference Confusion

**Issue:** `backup.md` line 33 says `encrypt: bool = False` with description "GPG encryption" but line 8 says "AES-256-GCM encryption with PBKDF2 key derivation (not GPG)".

The `create_backup()` function's docstring at line 33 says "GPG encryption" which is incorrect - it uses AES-256-GCM as implemented in `app/backup_encryption.py`.

**Correction needed:** Update the `encrypt` parameter description in `create_backup()` docstring to reflect AES-256-GCM encryption, not GPG.

### 2. Backup Documentation - Inconsistent Naming Description

**Issue:** `backup.md` line 69-75 shows naming pattern:
```
blog_YYYYMMDD_HHMMSS.db       # Plain
blog_YYYYMMDD_HHMMSS.db.gz     # Compressed
blog_YYYYMMDD_HHMMSS.db.gpg    # Encrypted
```

But `run_daily_backup()` uses `backup_*.db` naming (not `blog_*.db`). The documentation doesn't clearly distinguish between the two backup implementations' naming conventions.

**Correction needed:** Add clear distinction between `create_backup()` (blog_*.db) and `run_daily_backup()` (backup_*.db) naming patterns.

### 3. Backup Documentation - Decryption Output Path Default

**Issue:** `backup.md` line 65 says: "defaults to input_path without `.gpg`"

However, `app/services/backup.py:119-122` shows the actual logic:
```python
if output_path is None:
    if input_path.endswith(".gpg"):
        output_path = input_path[:-4]
    else:
        output_path = input_path + ".decrypted"
```

If the file doesn't end with `.gpg`, it appends `.decrypted` instead of removing an extension.

**Correction needed:** Update documentation to reflect that `.decrypted` is appended for files without `.gpg` extension.

### 4. Serialization Service - Import Handling

**Issue:** `serialization.md` line 10 says "Import functionality is handled via `app/cli.py` (CLI commands), not in the service itself."

This is incomplete. Looking at `app/cli.py`, import is handled via `import_data` command. However, the serialization service does not have corresponding deserialization functions to match the export functions. There's no `deserialize_post()`, `deserialize_subscriber()`, etc.

**Correction needed:** Either add deserialization functions to `app/services/serialization.py` or document the import flow more completely.

---

## Missing Documentation

### 1. Tag Cache Module Not Documented

**Issue:** There is no documentation for `app/tag_cache.py` which is a critical service for tag count caching with TTL support.

**Missing:**
- `app/architecture/services/tag.md` does not mention the caching mechanism
- `app/architecture/services/overview.md` does not list tag_cache as a service
- No dedicated `tag_cache.md` documentation

**Recommendation:** Create `architecture/services/tag_cache.md` documenting:
- `_get_tag_counts()` - main function returning tag_id to count mapping
- `invalidate_tag_cache()` - cache invalidation function
- `TAG_CACHE_TTL_SECONDS` configuration (default 60 seconds)
- Cache invalidation triggers (post create/update/delete, tag changes)

### 2. Encryption Module Not Documented

**Issue:** `app/backup_encryption.py` is not documented in the services architecture.

**Missing:**
- No documentation for backup encryption implementation
- No documentation for key derivation (PBKDF2, 600,000 iterations)
- No documentation for the encrypted file format (salt + nonce + ciphertext + tag)

**Recommendation:** Either create `architecture/services/encryption.md` or add a section to `backup.md`.

### 3. Slug Service - UUID Suffix Details

**Issue:** `slug.md` mentions "Collision detection" and "Suffix enumeration" but doesn't document the fallback to UUID suffix after 100 tries.

**Missing from `slug.md`:**
- The 100 try limit before UUID fallback
- The UUID format (8 characters from hex): `f"{base_slug}-{uuid.uuid4().hex[:8]}"`
- The `exclude_id` parameter purpose for edit operations

### 4. Run Daily Backup - Lock Mechanism Not Documented

**Issue:** `run_daily_backup()` in `app/scheduler.py:240-255` uses a `FileLock` that is not mentioned in documentation.

**Missing:**
- File lock mechanism prevents concurrent backup runs
- Lock file location: `{instance_path}/backup.lock`
- Lock timeout behavior

---

## Potential Issues

### 1. Two `run_daily_backup` Functions

**Issue:** There are two `run_daily_backup` functions:
- `app/services/backup.py:144` - The actual implementation
- `app/scheduler.py:240` - A wrapper that acquires a lock and calls the service version

The wrapper in scheduler.py imports and calls the service version, but this creates a confusing import pattern. The scheduler's version should be documented to avoid confusion.

**Severity:** Medium - Code is functional but the dual function pattern could confuse developers.

### 2. Backup Encryption Comment Inconsistency

**Issue:** `app/services/backup.py:94-97` says:
```python
def _encrypt_backup_file(filepath: str) -> bool:
    """Encrypt a backup file using GPG.
```

This comment says "GPG" but the implementation uses the AES-based `encrypt_backup_file` from `app/backup_encryption.py`. The docstring is outdated.

**Severity:** Low - Code is correct but comments are misleading.

### 3. Tag Cache Invalidation - Missing Invalidation on Series Changes

**Issue:** Based on code search, tag cache is invalidated on:
- Post create/update/delete (`app/routes/admin/posts/editor.py`)
- Post publish/unpublish (`app/routes/admin/posts/manage.py`)
- Tag create/delete/update (`app/routes/admin/tags.py`)
- Post revisions (`app/routes/admin/posts/revisions.py`)

But if a Series is modified (adding/removing posts), the tag cache may not be invalidated since tag counts would change.

**Severity:** Low - Likely a rare edge case but worth noting for future investigation.

### 4. Backup File Cleanup - Only Handles Known Extensions

**Issue:** `cleanup_old_backups()` in `app/services/backup.py:133` only recognizes `blog_*.db`, `blog_*.db.gz`, and `blog_*.db.gpg` patterns. If `run_daily_backup()` creates `backup_*.db` files, `cleanup_old_backups()` won't clean them up.

This means `create_backup()` retention doesn't apply to scheduler backups and vice versa.

**Severity:** Medium - Could lead to orphaned backup files consuming disk space if different retention settings are used.

---

## Recommended Improvements

### High Priority

1. **Update `backup.md` Encryption Documentation**
   - Fix docstring for `create_backup()` encrypt parameter to say "AES-256-GCM encryption" not "GPG encryption"
   - Clarify that `.gpg` extension is historical/naming only, actual encryption is AES-256-GCM

2. **Document Two Naming Conventions**
   - Clearly distinguish between `blog_*.db` (create_backup) and `backup_*.db` (run_daily_backup)
   - Document that `cleanup_old_backups()` only handles `blog_*` files

3. **Create `tag_cache.md` Documentation**
   - Document the caching mechanism and TTL configuration
   - List all cache invalidation triggers

### Medium Priority

4. **Update Slug Service Documentation**
   - Document 100 try limit and UUID fallback behavior
   - Document `exclude_id` parameter for edit operations

5. **Update Decryption Output Path Documentation**
   - Fix documentation to reflect `.decrypted` fallback for non-`.gpg` files

6. **Fix Backup Encryption Docstring**
   - Update `_encrypt_backup_file()` docstring to say "AES-256-GCM encryption" not "GPG"

### Low Priority

7. **Document FileLock in Scheduler**
   - Add note about lock mechanism for `run_daily_backup`

8. **Consider Adding Deserialization Functions**
   - Either add `deserialize_*` functions to serialization.py or document the full import flow

---

## Summary

The services module documentation is largely accurate for the core functionality. Key verification points all pass:

- Two backup implementations confirmed with correct naming conventions
- AES-256-GCM encryption properly documented and implemented
- Slug collision limit of 100 confirmed
- Newsletter retry count of 5 confirmed  
- Tag caching with TAG_CACHE_TTL_SECONDS confirmed

Main issues are documentation inconsistencies around encryption naming (GPG vs AES) and missing documentation for the tag_cache module. The backup service documentation also needs clarification on the dual naming conventions.
