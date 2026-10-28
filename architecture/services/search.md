# Search Provider (`app/services/search/`)

Search abstraction layer supporting multiple full-text search backends.

## Architecture

The search provider system uses an abstract base class pattern to allow switching between different search backends:

```
get_search_provider()
    ├── SQLiteSearchProvider (current default)
    └── PostgreSQLSearchProvider (stub for future use)
```

## SearchProvider Abstract Base Class

```python
class SearchProvider(ABC):
    def initialize(self) -> None:
        """Initialize the search provider. Called during app startup."""

    @abstractmethod
    def search(self, query: str, limit: int = 20) -> list[tuple[int, float]]:
        """Search posts and return list of (post_id, rank) tuples."""

    @abstractmethod
    def index_post(self, post_id: int, title: str, body: str, summary: str, published: bool) -> bool:
        """Index or remove a post from the search index."""

    @abstractmethod
    def remove_post(self, post_id: int) -> bool:
        """Remove a post from the search index."""

    @abstractmethod
    def rebuild_index(self) -> None:
        """Rebuild the entire search index."""

    @abstractmethod
    def get_snippets(self, post_ids: list[int], query: str) -> dict[int, str]:
        """Get search snippets for given post IDs."""
```

## SQLiteSearchProvider

Current default implementation using SQLite FTS5.

### Features

- **FTS5 Virtual Table**: `posts_fts` with `prefix='2 3 4'` for prefix matching
- **BM25 Ranking**: Results ordered by relevance score (lower = better)
- **Snippet Highlighting**: Uses FTS5 `snippet()` function with `<mark>` tags
- **Did You Mean**: Fuzzy matching via `difflib.get_close_matches` (cutoff=0.6)
  - **Case Preservation**: When an exact case-insensitive match is found in the index, the function returns the original indexed term (preserving its original case), NOT the lowercased suggestion from `get_close_matches`. See `app/search.py:342-344`.
- **Caching**: 5-minute TTL for FTS table checks

## Module-Level Functions (`app/search.py`)

**Important**: The SearchProvider abstraction in `app/services/search/__init__.py` is **separate from** the module-level functions in `app/search.py`. The `SQLiteSearchProvider` class **wraps these functions** - it does NOT reimplement them. The abstraction provides a consistent interface, but the actual FTS5 operations are performed by these standalone functions.

| Function | Location | Description |
|----------|----------|-------------|
| `reset_fts_available()` | `app/search.py:36` | Reset FTS availability cache (for testing and cache invalidation) |
| `rebuild_fts()` | `app/search.py:101` | Rebuild entire index |
| `sync_fts()` | `app/search.py:111` | Index/update a single post |
| `sync_fts_batch()` | `app/search.py:133` | Batch index multiple posts |
| `remove_fts()` | `app/search.py:174` | Remove post from index |
| `search()` | `app/search.py:196` | FTS5 search with bm25 ranking |
| `get_indexed_terms()` | `app/search.py:219` | Get all indexed terms via fts5vocab |
| `get_indexed_terms_fallback()` | `app/search.py:230` | Fallback when fts5vocab unavailable; extracts terms from published post titles |
| `_escape_fts_term()` | `app/search.py:188` | Escapes FTS5 special characters (`()*+:<>"-`) and whitespace for safe query construction |
| `extract_snippet()` | `app/search.py:246` | Extract text snippet around match |
| `get_search_snippets()` | `app/search.py:275` | Get highlighted snippets |

**Note**: `extract_snippet`, `get_search_snippets`, `_escape_fts_term`, and `get_indexed_terms_fallback` are **not** exported in `__all__` and are internal implementation details not intended for external use.
| `get_did_you_mean()` | `app/search.py:320` | Fuzzy suggestion for failed queries |
| `highlight_query()` | `app/search.py:349` | Add `<mark>` tags around query terms |

### Exception Handling

All module-level functions in `app/search.py` catch `OperationalError`, `ProgrammingError`, and `DatabaseError` exceptions from SQLAlchemy. When these exceptions occur during search operations (e.g., FTS5 table not ready), functions return empty results or `False` rather than propagating the exception.

### Search Configuration

```python
# app/config_legacy.py (re-exported via app/config/__init__.py)
SEARCH_PROVIDER = "sqlite"  # or "postgresql"
FTS_RESULT_LIMIT = 100  # max FTS5 search results (configurable)
```

```python
# app/search.py (local constants)
_FTS_CHECK_TTL = 300  # 5 minutes cache TTL
_SQLITE_MAX_VARS = 500  # batching limit for SQLite parameters
```

## PostgreSQLSearchProvider

Stub implementation for future PostgreSQL full-text search support.

Current status: **Not implemented** - placeholder for future development.

## Configuration

The search provider is selected via the `SEARCH_PROVIDER` environment variable:

| Value | Provider | Status |
|-------|----------|--------|
| `sqlite` | SQLiteSearchProvider | Current default |
| `postgresql` | PostgreSQLSearchProvider | Stub (not implemented) |

## Indexing

Posts are indexed automatically via signals:

1. **Post creation**: `index_post()` called with `published=False`
2. **Post publish**: `index_post()` called with `published=True`
3. **Post update**: `index_post()` called to update FTS index
4. **Post delete**: `remove_post()` removes from index

## See Also
- [Search Infrastructure](../infrastructure/search.md) - Search functionality details
- [Search Configuration](../infrastructure/search.md) - Configuration options