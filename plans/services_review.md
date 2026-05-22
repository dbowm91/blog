# Architecture Review: Services Layer

## Summary

Reviewed 7 architecture documents in `architecture/services/` and cross-referenced with actual implementation files in `app/services/` and `app/tag_cache.py`. The review identified several inaccurate line number references, a documentation/source mapping issue with search, and a few minor discrepancies.

---

## Verified Accurate Claims

### Tag Service (`app/services/tag.py`)

| Claim | Status |
|-------|--------|
| `get_or_create_tags()` at line 12 | **ACCURATE** - Signature: `tag_names: List[str]) -> List[Tag]` |
| `get_tag_by_slug()` at line 34 | **ACCURATE** - Signature: `(slug: str) -> Optional[Tag]` |
| `get_all_tags()` at line 41 | **ACCURATE** - Returns list ordered by `Tag.name` |
| `delete_tag_if_unused()` at line 58 | **ACCURATE** - Returns `bool`, deletes only if `tag.posts` is empty |
| `get_tag_post_count()` at line 48 | **ACCURATE** - Only counts **published** posts (filter: `Post.published`) |
| Slug collision limit of 100 then UUID suffix | **ACCURATE** - Documented in `delete_tag_if_unused()` docstring line 65-66 |

### Tag Cache (`app/tag_cache.py`)

| Claim | Status |
|-------|--------|
| `TAG_CACHE_TTL_SECONDS` default 60 | **ACCURATE** - `app/config.py:117` |
| Cache uses `flask_cache.memoize` with TTL | **ACCURATE** - Line 30 |
| `_get_tag_counts_uncached()` for non-request contexts | **ACCURATE** - Lines 44-47 |
| `invalidate_tag_cache()` clears memoized cache | **ACCURATE** - Lines 50-52 |
| Cache invalidation on post create/update/delete/publish/unpublish | **ACCURATE** - Various routes call `invalidate_tag_cache()` |

### Search Provider (`app/services/search/`)

| Claim | Status |
|-------|--------|
| `SearchProvider` abstract base class pattern | **ACCURATE** - `__init__.py:12-80` |
| `SQLiteSearchProvider` wraps `app/search.py` functions | **ACCURATE** - `sqlite.py` |
| `PostgreSQLSearchProvider` is a stub raising `ConfigurationError` | **ACCURATE** - `postgresql.py` |
| `get_search_provider()` factory selects by `SEARCH_PROVIDER` config | **ACCURATE** - `__init__.py:83-96` |
| FTS5 virtual table with `prefix='2 3 4'` | **ACCURATE** - `search.py:70-72` |
| BM25 ranking (lower = better) | **ACCURATE** - `search.py:214` |
| Snippet highlighting with `<mark>` tags | **ACCURATE** - `search.py:303-304` |
| "Did You Mean" via `difflib.get_close_matches` cutoff=0.6 | **ACCURATE** - `search.py:344` |
| 5-minute TTL for FTS check caching (`_FTS_CHECK_TTL = 300`) | **ACCURATE** - `search.py:30` |
| `get_did_you_mean()` signature with `max_suggestions` param | **ACCURATE** - `search.py:327` |
| `highlight_query()` adds `<mark>` tags | **ACCURATE** - `search.py:356` |

### Backup Service (`app/services/backup.py`)

| Claim | Status |
|-------|--------|
| `create_backup()` at line 24 with `compress` and `encrypt` params | **ACCURATE** |
| `cleanup_old_backups()` removes old backups keeping `keep` recent | **ACCURATE** - Line 130 |
| `run_daily_backup()` uses `blog_*.db` naming | **ACCURATE** - Line 168 |
| AES-256-GCM encryption with PBKDF2 (600,000 iterations) | **ACCURATE** - `backup_encryption.py:43` |
| Default retention of 7 | **ACCURATE** - `BACKUP_RETENTION_COUNT = 7` at line 21 |
| `decrypt_backup_file()` at line 107 | **ACCURATE** |
| Both `create_backup()` and `run_daily_backup()` use `blog_*.db` naming | **ACCURATE** |

### Serialization Service (`app/services/serialization.py`)

| Claim | Status |
|-------|--------|
| `serialize_post()` includes all listed fields | **ACCURATE** |
| `serialize_subscriber()` with `include_email` param | **ACCURATE** |
| `serialize_page()` includes all listed fields | **ACCURATE** |
| `serialize_tag()` returns `name` and `slug` | **ACCURATE** |
| `export_data_to_dict()` with `version` param | **ACCURATE** |

### Slug Service (`app/services/slug.py`)

| Claim | Status |
|-------|--------|
| `generate_unique_slug()` signature with all params | **ACCURATE** - Line 13 |
| Collision handling tries up to 100 suffixes | **ACCURATE** - Line 33 (`counter <= 100`) |
| UUID fallback format `{base_slug}-{8_char_hex_uuid}` | **ACCURATE** - Line 43 (`uuid.uuid4().hex[:8]`) |
| Works with Post, Page, Tag, Series models | **ACCURATE** - `model: Type` parameter |

### Overview (`architecture/services/overview.md`)

| Claim | Status |
|-------|--------|
| All service files and purposes listed correctly | **ACCURATE** |

---

## Discrepancies and Issues

### 1. **tag.md** - Inaccurate Line Number

| Issue | Details |
|-------|---------|
| `get_or_create_tags()` listed at line 12 | **ACTUAL: Line 12** but function signature starts at line 12, not "location". The doc implies line 12 is where function starts, which is correct but unusual phrasing. |

### 2. **tag_cache.md** - Line Numbers Do Not Match Current Code

**Issue:** The invalidation call line numbers listed do not match actual code locations:

| Location Cited | Cited Line | Actual Line(s) | Notes |
|----------------|-------------|----------------|-------|
| `app/routes/admin/__init__.py` | 67, 100 | ~67 (but different context) | `_invalidate_all_caches()` contains `invalidate_tag_cache()` at line 67, but the cited lines 100 do not match |
| `app/routes/admin/posts/editor.py` | 88, 206 | 88, 206 | **ACCURATE** |
| `app/routes/admin/posts/revisions.py` | 98 | 98 | **ACCURATE** |
| `app/routes/admin/posts/manage.py` | 83 | 83 | **ACCURATE** |
| `app/routes/admin/tags.py` | 79, 109, 147 | 79, 109, 147 | **ACCURATE** |
| `app/routes/admin/posts/__init__.py` | 155, 176, 195, 213 | 155, 176, 195, 213 | **ACCURATE** |
| `app/scheduler.py` | 225, 255 | 225, 255 | **ACCURATE** |

**Problem:** Line numbers become stale with any code modification. The documentation will become increasingly inaccurate over time.

### 3. **search.md** - Documentation Source Mismatch and Incorrect Line Numbers

**Critical Issue:** The documentation describes functions as if they belong to `app/services/search/` (SQLiteSearchProvider), but the line number citations reference `app/search.py` (module-level functions).

| Function | Doc Location | Cited Line | Actual Location |
|----------|-------------|-------------|------------------|
| `search()` | Cited as `app/search.py:201` | Line 201 | **ACCURATE** - `search()` at line 201 returns `list[tuple[int, float]]` |
| `sync_fts()` | Cited as `app/search.py:112` | Line 112 | **ACCURATE** - `sync_fts()` at line 112 |
| `sync_fts_batch()` | Cited as `app/search.py:136` | Line 136 | **ACCURATE** - `sync_fts_batch()` at line 136 |
| `remove_fts()` | Cited as `app/search.py:177` | Line 177 | **ACCURATE** - `remove_fts()` at line 177 |
| `rebuild_fts()` | Cited as `app/search.py:102` | Line 102 | **ACCURATE** - `rebuild_fts()` at line 102 |
| `get_search_snippets()` | Cited as `app/search.py:282` | Line 282 | **ACCURATE** |
| `reset_fts_available()` | Not in doc | N/A | Missing from doc |
| `get_did_you_mean()` | Cited as `app/search.py:327` | Line 327 | **ACCURATE** |
| `highlight_query()` | Cited as `app/search.py:356` | Line 356 | **ACCURATE** |
| `get_indexed_terms()` | Cited as `app/search.py:224` | Line 224 | **ACCURATE** |
| `extract_snippet()` | Cited as `app/search.py:253` | Line 253 | **ACCURATE** |

**Missing from documentation:**
- `reset_fts_available()` at line 36 - not documented at all
- `extract_snippet()` is documented but belongs to `app/search.py` not `app/services/search/`

**Architecture inconsistency:** The documentation presents search as if it is organized under `app/services/search/` with the SearchProvider abstraction, but all the actual function line numbers point to `app/search.py` which contains module-level functions. The `SQLiteSearchProvider` in `app/services/search/sqlite.py` merely wraps these module-level functions.

### 4. **slug.md** - Minor Line Number Discrepancy

| Issue | Details |
|-------|---------|
| `generate_unique_slug()` listed at `app/services/slug.py:12` | **ACTUAL: Line 13** - The function starts at line 13, not line 12 |

### 5. **backup.md** - Minor Line Number Discrepancy

| Issue | Details |
|-------|---------|
| `run_daily_backup()` listed at line 48 | **ACTUAL: Line 145** - Function starts at line 145 |
| `create_backup()` listed at line 24 | **ACCURATE** - Line 24 is correct |
| `decrypt_backup_file()` listed at line 107 | **ACCURATE** - Line 107 is correct |

---

## Recommended Improvements

### High Priority

1. **Remove line numbers from `tag_cache.md` invalidation calls**
   - Line numbers are fragile and will become stale with any code changes
   - Replace with functional descriptions or use a search-based approach in documentation generation
   - Alternatively, document the pattern: "Cache invalidation is called in post editor, tag management, and scheduler"

2. **Fix `search.md` documentation source confusion**
   - The current structure is misleading: it describes SearchProvider architecture but cites `app/search.py` line numbers
   - Either:
     - Move function documentation to `app/search.py` and update `search.md` to focus on the abstraction layer only
     - Or update line numbers to reference `app/services/search/sqlite.py` methods and remove detailed `app/search.py` function docs

3. **Add `reset_fts_available()` to `search.md`**
   - This function is missing from the documented functions list
   - It is important for cache invalidation and testing

### Medium Priority

4. **Update line numbers in `backup.md`**
   - `run_daily_backup()` is at line 145, not 48
   - Consider using function signature documentation instead of line numbers

5. **Update line number in `slug.md`**
   - `generate_unique_slug()` is at line 13, not 12

6. **Document the relationship between `app/search.py` and `app/services/search/`**
   - `app/search.py` contains the actual FTS5 implementation (module-level functions)
   - `app/services/search/sqlite.py` wraps these as class methods
   - This architectural clarity would help future developers

### Low Priority

7. **Consider documenting exception handling in search functions**
   - `app/search.py` catches `OperationalError, ProgrammingError, DatabaseError` and returns empty/false on failure
   - This behavior is not documented

8. **Document the "Did You Mean" exact match behavior**
   - `search.py:349-351` has special logic to return exact case match if found
   - This is an implementation detail worth noting

---

## Bugs and Security Concerns

### No Bugs Found

The implementations appear to be correct and match their intended behavior:

- Tag caching correctly filters by published posts only
- Slug generation correctly handles collision up to 100 attempts
- Backup encryption uses NIST SP 800-132 compliant PBKDF2 with 600,000 iterations
- Search FTS5 properly handles prefix matching and BM25 ranking
- Serialization correctly handles optional email exclusion

### Security Concerns

**No security vulnerabilities identified.** The code follows good practices:

- Backup encryption uses secure PBKDF2 with high iteration count
- Slug generation uses cryptographically random UUIDs for fallback
- Subscriber email serialization respects privacy by requiring `include_email=True`
- SQL injection is prevented via parameterized queries in FTS operations

---

## Summary Table

| Document | Issues Found | Severity |
|----------|-------------|----------|
| `tag.md` | 1 minor line number | Low |
| `tag_cache.md` | Line numbers stale, documentation fragile | Medium |
| `search.md` | Source mismatch, missing function, line number accuracy | Medium |
| `backup.md` | 1 line number off by 137 lines | Low |
| `serialization.md` | None | N/A |
| `slug.md` | 1 line number off by 1 line | Low |
| `overview.md` | None | N/A |
| `AGENTS.override.md` (architecture) | None | N/A |
| `AGENTS.override.md` (services) | Incomplete (no `update_tag` exists) | Low |

**Overall Assessment:** The documentation is mostly accurate. The main issues are fragile line number references and a documentation/source mismatch in the search service. None of the issues represent functional bugs or security vulnerabilities.
