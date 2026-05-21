# Services Layer Architecture Review

## Summary

Reviewed 6 architecture documents in `architecture/services/` and verified against actual implementation in `app/services/` (backup.py, serialization.py, tag.py, slug.py) and `app/tag_cache.py`.

## Verified Claims

### Overview (`overview.md`)
- All services listed exist in correct locations
- Tag Cache correctly noted as `app/tag_cache.py` (separate from services folder)

### Backup Service (`backup.md`)
- `create_backup()` function exists with correct signature: `(db_path, backup_dir, compress=False, keep=7, encrypt=False) -> Optional[str]`
- `cleanup_old_backups()` exists: `(backup_dir, keep) -> None`
- `run_daily_backup()` exists: `(app) -> None`
- AES-256-GCM encryption documented correctly (not GPG)
- Uses SQLite's native `backup()` API for consistency
- Both `create_backup()` and `run_daily_backup()` create `blog_YYYYMMDD_HHMMSS.db` files
- `decrypt_backup_file()` exists with correct signature

### Serialization Service (`serialization.md`)
- All 5 functions exist: `serialize_post`, `serialize_subscriber`, `serialize_page`, `serialize_tag`, `export_data_to_dict`
- Function signatures match documentation
- Import handled via CLI command `import-data` in `app/cli.py`

### Tag Service (`tag.md`)
- CRUD functions exist: `get_or_create_tags`, `get_tag_by_slug`, `get_all_tags`, `delete_tag_if_unused`
- `get_tag_post_count()` exists for post count queries
- Tag caching functions documented (in `app/tag_cache.py`)

### Tag Cache (`tag_cache.md`)
- Functions documented exist: `_get_tag_counts_cached()`, `_get_tag_counts()`, `_get_tag_counts_uncached()`, `invalidate_tag_cache()`
- Implementation uses `flask_cache.memoize` correctly
- Cache invalidation triggers correctly documented

### Slug Service (`slug.md`)
- `generate_unique_slug()` function exists
- Collision detection with suffix enumeration works correctly
- Maximum 100 collision attempts before UUID fallback
- UUID fallback format: `{base_slug}-{8_char_hex_uuid}` after 100 attempts

## Discrepancies

### 1. `TAG_CACHE_TTL_SECONDS` Default Mismatch (tag_cache.md:11)
- **Documentation**: "default: 300 seconds / 5 minutes"
- **Actual code** (`app/config.py:115`): `TAG_CACHE_TTL_SECONDS = int(_config["app"].get("tag_cache_ttl_seconds", 60))`
- **Default is 60 seconds, not 300**

### 2. `run_daily_backup()` Retention Pattern Documentation Error (backup.md:53-56)
- **Documentation claims**: "Manages `backup_*.db` files separately from `cleanup_old_backups()`"
- **Actual code** (`app/services/backup.py:179`): `backup_pattern = os.path.join(backup_dir, "blog_*.db")`
- Both `run_daily_backup()` and `cleanup_old_backups()` use `blog_*.db` pattern
- **This is a documentation bug, not a code bug**

### 3. Slug Service Parameter Names Mismatch (slug.md:15-21 vs slug.py:12-13)
- **Documentation signature**: `generate_unique_slug(base_slug: str, model_class: type, exclude_id: Optional[int] = None) -> str`
- **Actual implementation**: `generate_unique_slug(model: Type, title: str, exclude_id: Optional[int] = None, slug: Optional[str] = None) -> str`
- Parameters differ: `base_slug` vs `title`, `model_class` vs `model`, extra `slug` parameter

### 4. Celery `run_backup_task` Hardcoded Parameters (backup.md:61-70 vs tasks.py:309)
- **Documentation implies**: `run_backup_task` passes through parameters to `create_backup()`
- **Actual code** (`app/tasks.py:309`): `result = create_backup(db_path, backup_dir, compress=True, keep=7, encrypt=False)`
- `encrypt` is hardcoded to `False`, not passed through
- **Documentation should clarify that `run_backup_task` hardcodes these values**

### 5. `delete_tag_if_unused()` Docstring References Wrong Slug Service (tag.py:65-66)
- **Docstring states**: "Slug generation for new tags uses a collision limit of 100 tries before falling back to UUID suffix (see `app/services/slug.py`)"
- The slug service is correctly referenced, but this function calls `generate_slug` from `app/utils.py`, not `generate_unique_slug` from the slug service
- This is potentially misleading

## Bugs Identified

### Medium - Documentation Error: `run_daily_backup()` Retention Pattern
- **File**: `architecture/services/backup.md:53-56, 66, 71`
- **Issue**: Documentation claims APScheduler `run_daily_backup()` manages `backup_*.db` files, but code uses `blog_*.db`
- **Impact**: Documentation contradicts actual behavior; could cause confusion during troubleshooting
- **Fix**: Update documentation to say both use `blog_*.db` pattern

### Low - `run_backup_task` Hardcoded Encryption Parameter
- **File**: `architecture/services/backup.md:67`, `app/tasks.py:309`
- **Issue**: Documentation implies `run_backup_task` supports `encrypt=True`, but code hardcodes `encrypt=False`
- **Impact**: Users expecting encrypted backups via Celery task may be confused
- **Fix**: Either update documentation to clarify encryption is disabled, or update code to accept configuration

### Low - TAG_CACHE_TTL_SECONDS Documentation Default Wrong
- **File**: `architecture/services/tag_cache.md:11`
- **Issue**: Documentation says 300 seconds default, actual default is 60 seconds
- **Impact**: Low - misconfiguration expectations

### Low - Slug Service Documentation Signature Mismatch
- **File**: `architecture/services/slug.md:15-21`, `app/services/slug.py:12-13`
- **Issue**: Documentation parameter names (`base_slug`, `model_class`) don't match implementation (`title`, `model`)
- **Impact**: Developers using documentation may write incorrect code

### Low - `delete_tag_if_unused()` Docstring Could Mislead
- **File**: `app/services/tag.py:65-66`
- **Issue**: References "collision limit of 100 tries" but this function uses `generate_slug`, not `generate_unique_slug`
- **Impact**: Could mislead about slug behavior

## Improvement Recommendations

### 1. Fix `backup.md` Retention Pattern Documentation
```markdown
# Change line 53-56 from:
- **Own retention**: Manages `backup_*.db` files separately from `cleanup_old_backups()`

# To:
- **Own retention**: Manages `blog_*.db` files using the same pattern as `cleanup_old_backups()`
```

### 2. Fix `tag_cache.md` TTL Default
```markdown
# Change line 11 from:
- `TAG_CACHE_TTL_SECONDS` from `app/config.py` - Cache timeout (default: 300 seconds / 5 minutes)

# To:
- `TAG_CACHE_TTL_SECONDS` from `app/config.py` - Cache timeout (default: 60 seconds)
```

### 3. Fix `slug.md` Function Signature
```markdown
# Change line 15 from:
def generate_unique_slug(base_slug: str, model_class: type, exclude_id: Optional[int] = None) -> str:

# To match actual implementation:
def generate_unique_slug(model: Type, title: str, exclude_id: Optional[int] = None, slug: Optional[str] = None) -> str:
```

### 4. Add `run_backup_task` Configuration Note to `backup.md`
```markdown
# Add note after line 69:
**Configuration Note**: The Celery task `run_backup_task` hardcodes `compress=True` and `encrypt=False`. For fully configurable encrypted backups, call `create_backup()` directly.
```

### 5. Clarify `delete_tag_if_unused()` Docstring
```python
# Change line 65-66 from:
    Note:
        Slug generation for new tags uses a collision limit of 100 tries
        before falling back to UUID suffix (see `app/services/slug.py`).

# To:
    Note:
        New tags are created with a slug from the tag name (see `app/utils.py:generate_slug`).
        The slug service in `app/services/slug.py` handles collision resolution separately.
```

### 6. Add Service Layer Type Hints
The service layer functions lack consistent type hints. Consider adding proper type hints to match documentation and improve developer experience.