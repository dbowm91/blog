# Services Layer Architecture Review

Cross-reference of documentation in `architecture/services/` against actual implementation in `app/services/`.

---

## backup.md vs `app/services/backup.py`

### Verified Claims
- **Compression**: Gzip support via `shutil.copyfileobj` with gzip.open (lines 69-78) ✓
- **Encryption**: AES-256-GCM with PBKDF2 key derivation via `backup_encryption.py` (lines 62-67, 93-103) ✓
- **Retention**: Configurable via `keep` parameter, defaults to 7 (line 22, 82) ✓
- **SQLite backup API**: Uses `source.backup(dest)` (line 57) ✓
- **`create_backup()` signature**: Matches docs - `db_path`, `backup_dir`, `compress`, `keep`, `encrypt` (lines 24-25) ✓
- **`cleanup_old_backups()`**: Removes old backups keeping most recent `keep` (lines 129-141) ✓
- **`run_daily_backup()`**: Scheduler-friendly function with no encryption/compression (lines 144-191) ✓
- **`decrypt_backup_file()`**: Decrypts AES-256-GCM backups (lines 106-126) ✓
- **Naming pattern**: Both use `blog_*.db` pattern (lines 45, 167) ✓

### Discrepancies
- None significant

### Bugs Found
- **`run_daily_backup()` uses deprecated `datetime.utcnow()`** (line 166): Python 3.12 deprecated `datetime.utcnow()`. Should use `datetime.now(timezone.utc)` instead.

### Improvement Opportunities
- **High**: Fix `datetime.utcnow()` deprecation warning in `run_daily_backup()`

---

## search.md vs `app/services/search/`

### Verified Claims
- **SearchProvider ABC**: Abstract base class with `search()`, `index_post()`, `remove_post()`, `rebuild_index()`, `get_snippets()` (lines 7-67 in `__init__.py`) ✓
- **SQLiteSearchProvider as default**: `get_search_provider()` returns SQLiteSearchProvider when SEARCH_PROVIDER != "postgresql" (lines 70-83) ✓
- **PostgreSQLSearchProvider stub**: Exists at `app/services/search/postgresql.py` as placeholder ✓
- **FTS5 with BM25 ranking**: `app/search.py` uses bm25 ranking ✓
- **5-minute cache TTL**: `_FTS_CHECK_TTL = 300` in `app/search.py:30` ✓
- **Batching limit 500**: `_SQLITE_MAX_VARS = 500` in `app/search.py:298` ✓
- **SQLiteSearchProvider delegates to app.search**: All methods call corresponding functions in `app/search.py` (lines 18-42 in `sqlite.py`) ✓

### Discrepancies
- **Documentation claims configuration options are in `app/config.py`** (lines 65-68): `_FTS_CHECK_TTL` and `_SQLITE_MAX_VARS` are hardcoded in `app/search.py`, not in config. Only `SEARCH_PROVIDER` is in config.
- **"Indexing via signals" is misleading** (lines 88-93): Posts are indexed via direct function calls (e.g., `sync_fts()` in routes), not Flask signals. The doc describes automatic indexing but actual implementation requires explicit calls.

### Bugs Found
- None

### Improvement Opportunities
- **Medium**: Document that `_FTS_CHECK_TTL` and `_SQLITE_MAX_VARS` are hardcoded constants, not environment variables
- **Medium**: Clarify indexing is triggered manually in routes, not via automatic signals

---

## serialization.md vs `app/services/serialization.py`

### Verified Claims
- **`serialize_post(post)`**: Serializes to dict with title, slug, body, summary, image, dates, tags (lines 9-27) ✓
- **`serialize_subscriber(subscriber, include_email=False)`**: Returns id, confirmed, dates, optional email (lines 30-54) ✓
- **`serialize_page(page)`**: Serializes to dict (lines 57-66) ✓
- **`serialize_tag(tag)`**: Serializes to dict with name, slug (lines 69-74) ✓
- **`export_data_to_dict()`**: Exports all data with version and timestamp (lines 77-86) ✓

### Discrepancies
- **Doc omits additional fields**: `serialize_post()` includes `published` and `scheduled_publish_at` fields not mentioned in docs. `serialize_subscriber()` includes `id`, `expires_at`, `unsubscribed_at` not documented.

### Bugs Found
- None

### Improvement Opportunities
- **Low**: Document all fields returned by each serialization function

---

## slug.md vs `app/services/slug.py`

### Verified Claims
- **URL-safe slug generation**: Uses `generate_slug()` from utils ✓
- **Collision detection with suffix enumeration**: Tries `base_slug-2`, `base_slug-3`, etc. (lines 31-39) ✓
- **Maximum 100 collision attempts**: Loop `while counter <= 100` (line 32), counter > 100 triggers fallback (line 40) ✓
- **UUID fallback format `{base_slug}-{8_char_hex}`**: Line 41 uses `uuid.uuid4().hex[:8]` ✓
- **`exclude_id` parameter**: Excludes current post from collision check for edit operations (lines 34-35) ✓
- **`slug` parameter**: Allows pre-defined slug (lines 26-27) ✓

### Discrepancies
- **Documentation lists supported models as "Post, Page, Tag, Series"** but only describes Post and Page in parameter table. The actual code accepts any model with a `slug` attribute.

### Bugs Found
- None

### Improvement Opportunities
- **Low**: Update parameter table to clarify model can be any SQLAlchemy model with `slug` attribute, not just Post/Page/Tag/Series

---

## tag_cache.md vs `app/tag_cache.py`

### Verified Claims
- **File location**: `app/tag_cache.py` (not `app/services/tag_cache.py`) ✓
- **`_get_tag_counts_cached()`**: Uses `flask_cache.memoize` with TTL (line 30) ✓
- **`_get_tag_counts()`**: Respects request context, falls back to uncached for non-request contexts (lines 37-41) ✓
- **`_get_tag_counts_uncached()`**: Direct database query for non-request contexts (lines 44-47) ✓
- **`invalidate_tag_cache()`**: Clears memoized cache (lines 50-51) ✓
- **Configuration**: Uses `TAG_CACHE_TTL_SECONDS` from config (line 11) ✓

### Discrepancies
- None

### Bugs Found
- None

### Improvement Opportunities
- **Low**: Add reference to actual invalidation locations in code for verification

---

## tag.md vs `app/services/tag.py`

### Verified Claims
- **`get_or_create_tags(tag_names)`**: Creates or retrieves tags (lines 12-31) ✓
- **`get_tag_by_slug(slug)`**: Retrieves tag by slug (lines 34-38) ✓
- **`get_all_tags()`**: Returns all tags ordered by name (lines 41-45) ✓
- **`get_tag_post_count(tag_id)`**: Returns count of published posts for tag (lines 48-55) ✓
- **`delete_tag_if_unused(tag)`**: Deletes tag if no posts (lines 58-72) ✓
- **Slug generation**: Uses `generate_slug()` from app.utils (line 23) ✓
- **Note about slug collision limit**: Correctly references 100-try limit with UUID fallback (lines 64-66) ✓

### Discrepancies
- **Documentation mentions "app/tag_cache.py" in caching section** but this file is actually at `app/tag_cache.py` not `app/services/tag_cache.py`. This is correctly noted in the tag_cache.md file.

### Bugs Found
- None

### Improvement Opportunities
- **Low**: Update to clarify tag_cache location is `app/tag_cache.py` (root app, not services)

---

## Summary

| Document | Status | Issues |
|----------|--------|--------|
| backup.md | Mostly Accurate | 1 bug (datetime.utcnow deprecation) |
| search.md | Needs Update | Config location wrong, indexing description misleading |
| serialization.md | Needs Update | Missing fields in documentation |
| slug.md | Accurate | Minor doc update needed |
| tag_cache.md | Accurate | Minor |
| tag.md | Accurate | Minor |

### Priority List
1. **High**: Fix `datetime.utcnow()` deprecation in `backup.py:166`
2. **Medium**: Update `search.md` to reflect actual configuration locations and indexing mechanism
3. **Low**: Update `serialization.md` to document all fields
4. **Low**: Update `slug.md` parameter table to clarify model flexibility