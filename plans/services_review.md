# Services Architecture Review - Improvement Plan

## Executive Summary

Reviewed 7 architecture documents in `architecture/services/` and cross-referenced against actual code in `app/services/`, `app/tag_cache.py`, and `app/search.py`. Found several discrepancies, outdated references, and missing coverage.

---

## 1. Backup Service (`architecture/services/backup.md`)

### Discrepancies Found

| Issue | Documentation | Actual Code | Impact |
|-------|---------------|--------------|--------|
| **Duplicated constant** | `BACKUP_RETENTION_COUNT = 7` shown as documentation | Defined in both `app/services/backup.py:21` AND `app/scheduler.py:261` | Maintenance risk - two sources of truth |
| **Module path for encryption** | References `app.backup_encryption` implicitly | `app/services/backup.py:99` imports from `app.backup_encryption` (root level, not services/) | Documentation should reflect actual module location |
| **Missing `decrypt_backup_file` signature detail** | Documents return `bool` | Actual returns `True` on success, `False` on failure - but `app/backup_encryption.py:219` returns `bool` which is correct | Minor - accurate |

### Potential Bugs

1. **`decrypt_backup_file` in backup.py:106-126** - The `output_path` default logic appends `.decrypted` for non-`.gpg` files, but the `backup_encryption.py` module has its own `decrypt_backup_file` that writes to output_path. If input is `blog_20260101.db.gpg`, output becomes `blog_20260101.db`. This is correct but undocumented.

2. **Error handling gap in `create_backup`** - Lines 85-90 catch `sqlite3.Error, OSError` but `gzip` compression failure (lines 68-78) can leave a corrupted state if `os.replace()` fails after writing to `.tmp`. The `tmp_path` cleanup is incomplete.

### Missing from Documentation

- `_encrypt_backup_file()` helper - not documented
- `BACKUP_RETENTION_COUNT` constant existence (only mentioned in passing)
- The interaction between `create_backup()` calling `cleanup_old_backups()` every time vs. `run_daily_backup()` doing its own retention within itself

### Recommendations

1. Remove duplicate `BACKUP_RETENTION_COUNT` from `app/scheduler.py:261` - import from `app.services.backup`
2. Document `_encrypt_backup_file()` as internal
3. Clarify that `create_backup()` calls `cleanup_old_backups()` automatically, while `run_daily_backup()` handles retention internally

---

## 2. Search Service (`architecture/services/search.md`)

### Discrepancies Found

| Issue | Documentation | Actual Code | Impact |
|-------|---------------|--------------|--------|
| **Function locations** | Table shows functions in `app/search.py` | Correct - all actual implementations are in `app/search.py` | No discrepancy |
| **Key Functions table** | Lists 5 functions | `app/search.py` has 7 functions in `__all__` plus additional helpers | Missing `sync_fts_batch`, `reset_fts_available`, `get_did_you_mean`, `highlight_query`, `get_indexed_terms`, `extract_snippet` |
| **Did You Mean** | Mentions `difflib.get_close_matches` with `cutoff=0.6` | `app/search.py:344` uses `cutoff=0.6` correctly | Accurate |

### Potential Bugs

1. **`sync_fts_batch` not documented** - This function (lines 136-174 in `app/search.py`) handles batch indexing and is used but never documented. Critical for bulk operations.

2. **`reset_fts_available()` missing from docs** - Important for testing and cache invalidation but not documented.

3. **PostgreSQL stub falls back to SQLite in all methods** - `app/services/search/postgresql.py` lines 31-33, 42-44, 48-50, 60-61, 69-70 all fall back to SQLiteSearchProvider. This means if someone configures `SEARCH_PROVIDER=postgresql`, they actually get SQLite behavior silently. This is a silent fallback pattern that could cause confusion.

### Missing from Documentation

- `sync_fts_batch()` - batch indexing function
- `reset_fts_available()` - FTS availability reset for testing
- `get_did_you_mean()` - fuzzy suggestion function
- `highlight_query()` - query highlighting function
- `get_indexed_terms()` - indexed term enumeration
- `extract_snippet()` - snippet extraction utility
- `_escape_fts_term()` - query escaping function (internal)
- `_check_fts_enabled()` - FTS availability check with caching

### Recommendations

1. Document all public functions in `app/search.py`
2. Add warning that PostgreSQL provider is currently a full fallback to SQLite
3. Consider marking PostgreSQL stub as "non-functional" or implementing basic PostgreSQL-specific behavior

---

## 3. Serialization Service (`architecture/services/serialization.md`)

### Discrepancies Found

| Issue | Documentation | Actual Code | Impact |
|-------|---------------|--------------|--------|
| **Import function location** | Says `app/cli.py:import_data_command` | Correct - `app/cli.py:136` | Accurate |
| **CLI command name** | `import-data` | `app/cli.py:136` defines it as `import-data` via `@app.cli.command("import-data")` | Accurate |

### Missing from Documentation

- `export_data_to_dict()` has `version=1` parameter but no mention of export version handling
- No mention of error handling when serializing non-existent relations
- `serialize_post()` returns `tags` as list of tag names, not tag objects - this is correct but could be clearer

### Potential Bugs

1. **No validation on imported data** - `import_data_command` in `app/cli.py:140-169` loads JSON and imports directly without schema validation. Malformed JSON could cause crashes.

2. **`serialize_post` doesn't handle optional fields safely** - `app/services/serialization.py:26` does `post.tags` with a cast but if `post.tags` is None (shouldn't happen with SQLAlchemy but possible with malformed data), it will fail.

### Recommendations

1. Document the JSON import process more thoroughly
2. Add data validation before import
3. Document that `serialize_post` only includes tag names, not full tag objects

---

## 4. Slug Service (`architecture/services/slug.md`)

### Discrepancies Found

| Issue | Documentation | Actual Code | Impact |
|-------|---------------|--------------|--------|
| **Model types** | Says "Post, Page, Tag, Series" | `app/services/slug.py:18` comment says "Post or Page" but actual code allows any model | Documentation is more inclusive than implementation comment |
| **Collision limit** | "Maximum 100 collision attempts" | `app/services/slug.py:32` checks `counter <= 100` - correct | Accurate |

### Potential Bugs

1. **No slug uniqueness check at database level** - The collision check at lines 33-38 uses `db.session.execute(q).scalar_one_or_none()`. In a high-concurrency environment, two requests could generate the same slug simultaneously. Race condition exists.

2. **Slug generation doesn't use transaction** - If two requests generate the same slug and both try to insert, one will fail with a database integrity error. No retry logic.

3. **No length limit on resulting slug** - If title is very long and lots of collisions occur, slug could exceed reasonable URL lengths (>200 chars).

### Missing from Documentation

- No mention of potential race conditions in concurrent environments
- No mention of slug length limits

### Recommendations

1. Add unique constraint on model.slug at database level as safety net
2. Document potential race condition and that application-level locking is expected
3. Consider adding maximum slug length enforcement

---

## 5. Tag Service (`architecture/services/tag.md`)

### Discrepancies Found

| Issue | Documentation | Actual Code | Impact |
|-------|---------------|--------------|--------|
| **Cache location** | References `app/tag_cache.py` separately | Correct - `app/tag_cache.py` exists and is separate from `app/services/tag.py` | Accurate |
| **Cache invalidation** | Lists triggers | Actual triggers found in multiple places | Documentation incomplete |

### Potential Bugs

1. **`get_tag_post_count` only counts published posts** - `app/services/tag.py:54` filters `Post.published`. This means unpublished posts don't contribute to tag counts. This is likely intentional but undocumented.

2. **`delete_tag_if_unused` checks `tag.posts`** - `app/services/tag.py:68` checks if `tag.posts` is truthy. With SQLAlchemy lazy loading, this could trigger N+1 queries if accessing `tag.posts` lazily. However, since it's checking truthiness and not iterating, it's probably okay.

### Missing from Documentation

- `get_or_create_tags()` - important function not documented
- `get_tag_by_slug()` - not documented
- `get_all_tags()` - not documented
- `delete_tag_if_unused()` - partially documented (only "delete tags" mentioned in features)
- That `get_tag_post_count` only counts published posts

### Recommendations

1. Document all 5 public functions in tag service
2. Clarify that `get_tag_post_count` only counts published posts
3. Add cache invalidation trigger details

---

## 6. Tag Cache (`architecture/services/tag_cache.md`)

### Discrepancies Found

| Issue | Documentation | Actual Code | Impact |
|-------|---------------|--------------|--------|
| **Function `_get_tag_counts`** | Listed in table as "Get tag counts with caching" | `app/tag_cache.py:37` exists and checks `has_request_context()` | Accurate |
| **Invalidation triggers** | Lists `app/routes/admin/posts.py` and `app/routes/admin/tags.py` | Actually found in many more places (see below) | Incomplete |

### Actual Invalidation Locations (from grep results)

1. `app/routes/admin/__init__.py:67,100`
2. `app/routes/admin/posts/editor.py:88,206`
3. `app/routes/admin/posts/revisions.py:98`
4. `app/routes/admin/posts/manage.py:83`
5. `app/routes/admin/tags.py:79,109,147`
6. `app/routes/admin/posts/__init__.py:155,176,195,213`
7. `app/scheduler.py:225,255` (scheduled publish)
8. `tests/test_cache.py` and `tests/benchmarks/test_benchmarks.py`

### Potential Bugs

1. **`_get_tag_counts_uncached()` always queries database** - Even in request context, if cache is invalidated, subsequent calls within the same request will hit the database because `has_request_context()` only checks if we're in a request, not if cache is valid. However, `flask_cache.memoize` should handle cache state correctly within a request.

2. **Race condition in cache expiry** - Multiple concurrent requests after cache expiry could all hit the database simultaneously. This is a known trade-off of memoization.

3. **Cache key based on function args** - Since `_get_tag_counts_cached()` takes no arguments, the entire cache is a single key. Any tag change invalidates the entire cache, not just the affected tag. This is documented but worth noting for performance.

### Recommendations

1. Update invalidation triggers list to include all locations
2. Document the `has_request_context()` behavior - uncached fallback for non-request contexts
3. Consider documenting performance characteristics for high-traffic scenarios

---

## 7. Overview (`architecture/services/overview.md`)

### Issues

1. **Mentions `app/tag_cache.py` as a "service"** - While technically correct (it's in `app/`), it's inconsistent with other services which are in `app/services/`. The overview categorizes it under "Tag Cache" but the path is different from other services.

### Recommendations

1. Clarify that `app/tag_cache.py` is a separate module from `app/services/tag.py`
2. Consider either moving tag_cache into services or documenting the architectural reason for separation

---

## Priority Recommendations

### High Priority (Bugs/Risks)

1. **Slug Service Race Condition** - Add database-level unique constraint on slug columns
2. **PostgreSQL Search Provider Silent Fallback** - Either implement properly or raise an error when configured
3. **Backup Compression Error Handling** - Fix incomplete cleanup on compression failure

### Medium Priority (Documentation Gaps)

1. **Search Service** - Document all public functions, especially `sync_fts_batch`
2. **Tag Cache** - Document all invalidation locations
3. **Tag Service** - Document all public functions

### Low Priority (Improvements)

1. **Backup Service** - Remove duplicate `BACKUP_RETENTION_COUNT` constant
2. **Serialization** - Add data validation for import
3. **Slug Service** - Document slug length limits

---

## Files to Update

| File | Action |
|------|--------|
| `architecture/services/search.md` | Add missing functions, document PostgreSQL fallback |
| `architecture/services/tag_cache.md` | Add all invalidation locations |
| `architecture/services/tag.md` | Document all functions, clarify published-only counting |
| `architecture/services/slug.md` | Add race condition warning, length limits |
| `architecture/services/backup.md` | Document internal functions, clarify retention behavior |
| `app/scheduler.py:261` | Remove duplicate constant, import from backup.py |