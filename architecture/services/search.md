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
- **Caching**: 5-minute TTL for FTS table checks

### Key Functions

| Function | Location | Description |
|----------|----------|-------------|
| `search()` | `app/search.py` | FTS5 search with bm25 ranking |
| `sync_fts()` | `app/search.py` | Index/update a post |
| `remove_fts()` | `app/search.py` | Remove post from index |
| `rebuild_fts()` | `app/search.py` | Rebuild entire index |
| `get_search_snippets()` | `app/search.py` | Get highlighted snippets |

### Search Configuration

```python
# app/config.py
SEARCH_PROVIDER = "sqlite"  # or "postgresql"
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