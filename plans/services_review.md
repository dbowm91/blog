# Services Module Architecture Review

**Reviewed:** May 29, 2026
**Architecture Docs:** overview.md, backup.md, search.md, slug.md, tag.md, tag_cache.md, serialization.md
**Source Files:** app/services/, app/tag_cache.py, app/backup_encryption.py, app/webhook_encryption.py, app/search.py

## Findings

### Verified Claims (Correct)

- **overview.md**: Service table correctly lists all 6 services with accurate file paths
- **backup.md**: `create_backup()` signature matches source (`app/services/backup.py:24-26`)
- **backup.md**: `cleanup_old_backups()` signature matches (`app/services/backup.py:133`)
- **backup.md**: `decrypt_backup_file()` signature matches (`app/services/backup.py:109`)
- **backup.md**: AES-256-GCM with PBKDF2-HMAC-SHA256, 600,000 iterations confirmed (`app/backup_encryption.py:43`)
- **backup.md**: Salt 16 bytes, key 32 bytes, nonce 12 bytes confirmed (`app/backup_encryption.py:44-46`)
- **backup.md**: Min password 12 characters confirmed (`app/backup_encryption.py:68`)
- **backup.md**: File format `salt(16) + nonce(12) + ciphertext + tag(16)` confirmed (`app/backup_encryption.py:127`)
- **backup.md**: TOTP encryption module at `app/services/encryption.py` confirmed (AES-256-GCM via AESGCM, SECRET_KEY key)
- **backup.md**: Webhook encryption module at `app/webhook_encryption.py` confirmed (AES-256-GCM via AESGCM, WEBHOOK_ENCRYPTION_KEY)
- **search.md**: `SearchProvider` abstract class with all 5 abstract methods confirmed (`app/services/search/__init__.py:13-83`)
- **search.md**: `get_search_provider()` factory function confirmed (`app/services/search/__init__.py:86-101`)
- **search.md**: `SQLiteSearchProvider` wraps module-level functions (does NOT reimplement) confirmed (`app/services/search/sqlite.py`)
- **search.md**: `PostgreSQLSearchProvider` stub confirmed — all methods raise `ConfigurationError` (`app/services/search/postgresql.py`)
- **search.md**: FTS5 virtual table with `prefix='2 3 4'` confirmed (`app/search.py:70`)
- **search.md**: Case preservation in `get_did_you_mean()` confirmed — returns original indexed term when case-insensitive match found (`app/search.py:342-344`)
- **search.md**: `SEARCH_PROVIDER` config key with default `"sqlite"` confirmed (`app/config.py:173`)
- **slug.md**: `generate_unique_slug()` signature matches source (`app/services/slug.py:12-14`)
- **slug.md**: Max 100 collision attempts, then UUID fallback confirmed (`app/services/slug.py:32,42`)
- **slug.md**: UUID format `{base_slug}-{8_char_hex_uuid}` confirmed (`app/services/slug.py:42`)
- **tag.md**: All 5 function locations confirmed accurate
- **tag.md**: `get_tag_post_count()` only counts published posts confirmed (`app/services/tag.py:49`)
- **tag_cache.md**: `_get_tag_counts()` is the main entry point confirmed (`app/tag_cache.py:39`)
- **tag_cache.md**: `flask_cache.memoize` with TTL confirmed (`app/tag_cache.py:32`)
- **tag_cache.md**: `_get_tag_counts_cached()` takes no arguments confirmed (`app/tag_cache.py:33`)
- **tag_cache.md**: Non-request context falls back to uncached query confirmed (`app/tag_cache.py:41-43`)
- **serialization.md**: All 5 serialize functions confirmed with correct field lists
- **serialization.md**: No `deserialize_*` functions exist — import handled inline in CLI confirmed (`app/cli.py:133`)
- **backup.md**: Root-level `backup.py` CLI script exists and delegates to `app/services.backup` confirmed

### Discrepancies (Doc vs Code)

#### search.md — Line Number Drift (>5 lines in multiple cases)

| Doc Location | Doc Line | Actual Line | Drift |
|---|---|---|---|
| `reset_fts_available()` | 36 | 36 | 0 |
| `rebuild_fts()` | 102 | 101 | -1 |
| `sync_fts()` | 112 | 111 | -1 |
| `sync_fts_batch()` | 136 | 133 | -3 |
| `remove_fts()` | 177 | 174 | -3 |
| `search()` | 201 | 196 | -5 |
| `get_indexed_terms()` | 224 | 219 | -5 |
| `extract_snippet()` | 253 | 246 | -7 |
| `get_search_snippets()` | 282 | 275 | -7 |
| `get_did_you_mean()` | 327 | 320 | -7 |
| `highlight_query()` | 356 | 349 | -7 |

#### search.md — `_SQLITE_MAX_VARS` Misrepresented as Config Key

Doc (`search.md:84`) lists `_SQLITE_MAX_VARS = 500` as a config key alongside `SEARCH_PROVIDER` and `_FTS_CHECK_TTL`. In source, `_SQLITE_MAX_VARS` is a **local variable** hardcoded inside `get_search_snippets()` at `app/search.py:291`. It is not defined in `app/config.py` and is not configurable. Only `FTS_RESULT_LIMIT` is a true config key (default: 100, at `app/config.py:128`).

#### tag_cache.md — Line Number Drift on Invalidation Calls

| Doc Location | Doc Line | Actual Line | Drift |
|---|---|---|---|
| `app/routes/admin/__init__.py` | 67 | 68 | +1 |
| `app/routes/admin/__init__.py` | 100 | 103 | +3 (and doc says "call" but it's an import) |
| `app/routes/admin/posts/editor.py` | 88 | 89 | +1 |
| `app/routes/admin/posts/editor.py` | 206 | 204 | -2 |
| `app/routes/admin/posts/revisions.py` | 98 | 97 | -1 |
| `app/routes/admin/posts/manage.py` | 83 | 82 | -1 |
| `app/routes/admin/tags.py` | 79 | 76 | -3 |
| `app/routes/admin/tags.py` | 109 | 104 | -5 |
| `app/routes/admin/tags.py` | 147 | 142 | -5 |
| `app/routes/admin/posts/__init__.py` | 155 | 158 | +3 |
| `app/routes/admin/posts/__init__.py` | 176 | 179 | +3 |
| `app/routes/admin/posts/__init__.py` | 195 | 198 | +3 |
| `app/routes/admin/posts/__init__.py` | 213 | 216 | +3 |
| `app/scheduler.py` | 225 | 224 | -1 |
| `app/scheduler.py` | 255 | 256 | +1 |

#### tag_cache.md — Misidentified Line 100 as Cache Invalidation Call

`tag_cache.md:30` claims `app/routes/admin/__init__.py:100` is an `invalidate_tag_cache()` call. Actual line 103 is an **import statement** (`from app.tag_cache import invalidate_tag_cache`), not a call. The actual call is at line 68 inside `_invalidate_all_caches()`.

#### search.md — Missing Note About FTS_RESULT_LIMIT Config Default

`search.md:83-84` documents config keys but omits `FTS_RESULT_LIMIT` (default: 100, defined at `app/config.py:128`). This is the actual configurable limit used by `search()` at `app/search.py:212`. The `SearchProvider.search()` method has its own `limit` parameter (default: 20) which is separate from this config value.

### Missing Documentation

- **overview.md**: Does not list `app/services/encryption.py` (TOTP secret encryption), `app/backup_encryption.py` (backup encryption), or `app/webhook_encryption.py` (webhook encryption) in the services table. These are referenced in backup.md but absent from the overview.
- **overview.md**: Does not mention `app/search.py` (standalone FTS5 module-level functions). Only references the `app/services/search/` abstraction.
- **search.md**: Does not document `get_indexed_terms_fallback()` function (`app/search.py:230-243`), which is called when `fts5vocab` table is unavailable.
- **search.md**: Does not mention `_escape_fts_term()` helper (`app/search.py:188-193`) used by `search()` and `get_search_snippets()`.
- **tag.md**: Does not document the `_invalidate_all_caches()` function in `app/routes/admin/__init__.py:62-76` which coordinates tag cache invalidation with FTS, analytics, dashboard, and footer cache invalidation.
- **backup.md**: Does not document `run_daily_backup()` function in `app/services/backup.py:150-194` — only documents the scheduler wrapper at `app/scheduler.py:262`. The service-level function has different behavior (no encryption/compression support).

### Potential Bugs / Concerns

- **backup.py compression-after-encryption path**: In `create_backup()` (`app/services/backup.py:63-80`), when `encrypt=True`, encryption runs first and compression is skipped (line 69 `elif compress`). However, if a future code change made both `encrypt=True` and `compress=True` run sequentially, the current structure would compress the encrypted file. Currently the `elif` prevents this, but the logic could be clearer with explicit mutual exclusion documentation.
- **FTS limit inconsistency**: `search()` function uses `FTS_RESULT_LIMIT` (config default: 100) at `app/search.py:212`, while `SearchProvider.search()` has its own `limit` parameter (default: 20) at `app/services/search/__init__.py:25`. The `SQLiteSearchProvider.search()` calls `fts_search(query)` without passing a limit, then truncates to its own `limit` parameter (`app/services/search/sqlite.py:24-27`). This means FTS5 always fetches up to 100 results, then the provider truncates to 20 by default — a minor inefficiency.

### Improvement Suggestions

- **search.md**: Remove `_SQLITE_MAX_VARS` from the config keys section and note it as a hardcoded constant. Add `FTS_RESULT_LIMIT` as the configurable parameter.
- **search.md**: Update all line number references to match current source (drift ranges from -1 to -7 lines).
- **tag_cache.md**: Update all invalidation call line numbers. Correct the `app/routes/admin/__init__.py:100` claim from "call" to "import".
- **overview.md**: Add encryption modules (`app/services/encryption.py`, `app/backup_encryption.py`, `app/webhook_encryption.py`) to the services table.
- **overview.md**: Add `app/search.py` as a separate entry for standalone FTS5 functions.
- **search.md**: Document `get_indexed_terms_fallback()` and `_escape_fts_term()` functions.
- **backup.md**: Document the service-level `run_daily_backup()` function and clarify its differences from the scheduler wrapper.

## Action Items

| # | Priority | Description | Docs Affected |
|---|----------|-------------|---------------|
| 1 | high | Update `search.md` line number references (11 functions, drift -1 to -7) | search.md |
| 2 | high | Update `tag_cache.md` invalidation call line numbers (15 references) | tag_cache.md |
| 3 | high | Remove `_SQLITE_MAX_VARS` from config keys section; add `FTS_RESULT_LIMIT` | search.md |
| 4 | medium | Correct `tag_cache.md:30` — line 100 is import, not call (actual call at line 68) | tag_cache.md |
| 5 | medium | Add encryption modules to `overview.md` services table | overview.md |
| 6 | medium | Add `app/search.py` standalone functions to `overview.md` | overview.md |
| 7 | low | Document `get_indexed_terms_fallback()` and `_escape_fts_term()` in search.md | search.md |
| 8 | low | Document service-level `run_daily_backup()` in backup.md | backup.md |
| 9 | low | Document `_invalidate_all_caches()` coordination in tag.md | tag.md |
