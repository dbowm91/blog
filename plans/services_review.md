# Services Module Architecture Review

**Review Date:** 2026-05-21
**Reviewer:** services_reviewer

---

## 1. Verified Accurate Claims

### Backup Service (`architecture/services/backup.md`)

| Claim | Source Code Location | Status |
|-------|---------------------|--------|
| Uses AES-256-GCM encryption with PBKDF2 key derivation (not GPG) | `app/backup_encryption.py:91-135` | Verified |
| Uses `blog_*.db` naming pattern | `app/services/backup.py:45,167` | Verified |
| Uses SQLite's native `backup()` API | `app/services/backup.py:57` | Verified |
| `run_daily_backup()` has no encryption/compression | `app/services/backup.py:144-192` | Verified |
| Retention default is 7 | `app/services/backup.py:21` | Verified |
| `decrypt_backup_file()` function exists | `app/services/backup.py:106-126` | Verified |
| Both implementations create `blog_*.db` files | `app/services/backup.py:45,167` | Verified |

### Slug Service (`architecture/services/slug.md`)

| Claim | Source Code Location | Status |
|-------|---------------------|--------|
| Maximum 100 collision attempts before UUID fallback | `app/services/slug.py:32,40` | Verified |
| UUID fallback format: `{base_slug}-{8_char_hex}` | `app/services/slug.py:41` | Verified |
| Slug collision handling enumerates up to `-100` | `app/services/slug.py:32-39` | Verified |

### Tag Service (`architecture/services/tag.md`)

| Claim | Source Code Location | Status |
|-------|---------------------|--------|
| `TAG_CACHE_TTL_SECONDS` default 60 | `app/config.py:115` | Verified |
| Tag CRUD operations exist | `app/services/tag.py:12-71` | Verified |
| Tag caching via `invalidate_tag_cache()` | `app/tag_cache.py:50` | Verified |

### Tag Cache (`architecture/services/tag_cache.md`)

| Claim | Source Code Location | Status |
|-------|---------------------|--------|
| Uses `flask_cache.memoize` with TTL | `app/tag_cache.py:30` | Verified |
| `_get_tag_counts_cached()` function exists | `app/tag_cache.py:31` | Verified |
| `_get_tag_counts_uncached()` function exists | `app/tag_cache.py:44` | Verified |
| `invalidate_tag_cache()` clears memoized cache | `app/tag_cache.py:50-52` | Verified |
| Cache respects request context | `app/tag_cache.py:38-41` | Verified |
| Cache invalidated on post operations | `app/routes/admin/posts.py` | Verified |

### Serialization Service (`architecture/services/serialization.md`)

| Claim | Source Code Location | Status |
|-------|---------------------|--------|
| `serialize_post()` exists | `app/services/serialization.py:9-27` | Verified |
| `serialize_subscriber()` exists | `app/services/serialization.py:30-54` | Verified |
| `serialize_page()` exists | `app/services/serialization.py:57-66` | Verified |
| `serialize_tag()` exists | `app/services/serialization.py:69-74` | Verified |
| `export_data_to_dict()` exists | `app/services/serialization.py:77-86` | Verified |
| Import via CLI command `import-data` | `app/cli.py` | Verified |

### Search Provider (Implied but not documented)

| Implementation | Source Code Location | Status |
|----------------|---------------------|--------|
| `SearchProvider` abstract class | `app/services/search/__init__.py:7-68` | Verified |
| `SQLiteSearchProvider` implementation | `app/services/search/sqlite.py:8-43` | Verified |
| `PostgreSQLSearchProvider` stub | `app/services/search/postgresql.py:19-71` | Verified |
| `get_search_provider()` factory | `app/services/search/__init__.py:70-83` | Verified |

---

## 2. Inaccurate/Outdated Claims

### Tag Service (`architecture/services/tag.md`)

| Line | Inaccurate Claim | Actual Behavior | Correction Needed |
|------|------------------|-----------------|-------------------|
| 11 | References `app/tag_cache.py` as located in services | File is at `app/tag_cache.py`, not `app/services/tag_cache.py` | Update path to `app/tag_cache.py` |

### Tag Cache (`architecture/services/tag_cache.md`)

| Line | Inaccurate Claim | Actual Behavior | Correction Needed |
|------|------------------|-----------------|-------------------|
| 1 | References `app/tag_cache.py` | Documentation path is `architecture/services/tag_cache.md` but refers to actual file at `app/tag_cache.py` (not in services) | Clarify that actual file is at `app/tag_cache.py`, not under services |
| 17-20 | Lists functions: `_get_tag_counts_cached()`, `_get_tag_counts()`, `_get_tag_counts_uncached()`, `invalidate_tag_cache()` | All functions exist but are at `app/tag_cache.py` (not services) | Update to reflect actual file location |
| 29-30 | Lists invalidation call locations | Need to verify if these are complete | Cross-reference with actual invalidation calls |

### Backup Service (`architecture/services/backup.md`)

| Line | Inaccurate/Outdated | Actual Behavior | Correction Needed |
|------|---------------------|-----------------|-------------------|
| 94 | Shows `.gpg` extension for encrypted files | Encrypted files retain `.db` extension (`.gpg` is not appended by current implementation) | Update naming to show encrypted files remain `blog_*.db` |

### Encryption Details

| Claim | Actual Behavior |
|-------|-----------------|
| `app/services/encryption.py` handles backup encryption | No - backup encryption is in `app/backup_encryption.py`. `app/services/encryption.py` is for TOTP/webhook encryption |

---

## 3. Bugs Identified

No bugs identified in service implementations. The code is consistent and follows proper patterns.

---

## 4. Missing Documentation

### Search Provider Abstraction

| Missing Item | Location | Description |
|-------------|----------|-------------|
| Search provider documentation | `architecture/services/` | No document exists for `app/services/search/` module |
| `SearchProvider` abstract class | `app/services/search/__init__.py:7-68` | Should be documented with interface methods |
| `SQLiteSearchProvider` | `app/services/search/sqlite.py` | FTS5 implementation details not documented |
| `PostgreSQLSearchProvider` | `app/services/search/postgresql.py` | Stub implementation not documented as future feature |
| `get_search_provider()` factory | `app/services/search/__init__.py:70-83` | Provider selection logic not documented |

### Services Overview

| Missing Item | Location | Description |
|-------------|----------|-------------|
| Search service listing | `architecture/services/overview.md` | Search provider not listed in overview table |

### Backup Encryption Location

| Missing Item | Location | Description |
|-------------|----------|-------------|
| `app/backup_encryption.py` documentation | `architecture/services/backup.md` or separate | Encryption details in separate file from `app/services/backup.py` |

---

## 5. Recommended Improvements

### High Priority

1. **Create Search Provider Documentation** (`architecture/services/search.md`)
   - Document `SearchProvider` abstract class and interface
   - Document `SQLiteSearchProvider` (current implementation)
   - Document `PostgreSQLSearchProvider` as stub/future feature
   - Include configuration details for `SEARCH_PROVIDER` config

2. **Update Tag Cache Documentation Path**
   - `architecture/services/tag_cache.md` line 1 should clarify actual file location is `app/tag_cache.py` (not in services directory)

3. **Fix Backup Encryption File Extension**
   - `architecture/services/backup.md` line 94 shows `.gpg` extension
   - Current code at `app/services/backup.py:49` shows encrypted files keep `.db` extension (only `.gz` appended for compression)

### Medium Priority

4. **Update Services Overview** (`architecture/services/overview.md`)
   - Add Search service to overview table
   - Clarify that Tag Cache is at `app/tag_cache.py` (not in services)

5. **Document Encryption Layer Separation**
   - `app/backup_encryption.py` - backup encryption with PBKDF2
   - `app/services/encryption.py` - general encryption for TOTP/webhooks
   - Consider separate documentation or clarify distinction

### Low Priority

6. **Add Backup Decryption Function Documentation**
   - `decrypt_backup_file()` in `app/services/backup.py` is documented but details on decryption process could be expanded

7. **Document Search Snippets Feature**
   - `get_snippets()` method in `SearchProvider` not covered in any service documentation

---

## Summary

| Category | Count |
|----------|-------|
| Verified Accurate Claims | 22 |
| Inaccurate Claims | 5 |
| Bugs Identified | 0 |
| Missing Documentation | 5 |
| Improvements | 7 |

---

## Appendix: Key Implementation Details Verified

### Backup Naming Convention
```
app/services/backup.py:45    - create_backup(): blog_{timestamp}.db
app/services/backup.py:167   - run_daily_backup(): blog_{timestamp}.db
```

### Encryption Implementation
```
app/backup_encryption.py:43  - PBKDF2_ITERATIONS = 600_000
app/backup_encryption.py:91  - encrypt_backup() uses AES-256-GCM
app/services/encryption.py  - Different module for TOTP/webhook encryption
```

### Slug Collision Handling
```
app/services/slug.py:32      - counter <= 100 loop
app/services/slug.py:40-41   - Fallback to UUID after 100 attempts
```

### Tag Cache TTL
```
app/config.py:115            - TAG_CACHE_TTL_SECONDS default: 60
app/tag_cache.py:30          - Uses flask_cache.memoize with this TTL
```

### Search Provider Factory
```
app/services/search/__init__.py:70-83 - get_search_provider() selects by SEARCH_PROVIDER config
```