# Search Provider

The search system uses an abstraction layer to support multiple backends.

## SearchProvider Abstract Class

Location: `app/services/search/__init__.py`

```python
class SearchProvider(ABC):
    """Abstract base class for search providers."""

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

## Implementations

### SQLiteSearchProvider

Uses SQLite FTS5 (Full-Text Search) for indexing and ranking.

Location: `app/services/search/sqlite.py`

### PostgreSQLSearchProvider

Stub implementation for future PostgreSQL full-text search support.

Location: `app/services/search/postgresql.py`

## Factory Function

```python
def get_search_provider() -> SearchProvider:
    """Get the configured search provider based on SEARCH_PROVIDER config."""
```

## Configuration

| Provider | SEARCH_PROVIDER value |
|----------|----------------------|
| SQLite FTS5 | `sqlite` (default) |
| PostgreSQL | `postgresql` |

## Methods

| Method | Description |
|--------|-------------|
| `search(query, limit)` | Returns list of (post_id, rank) tuples ordered by relevance |
| `index_post(...)` | Index a post; returns True on success |
| `remove_post(post_id)` | Remove a post from index |
| `rebuild_index()` | Rebuild entire search index |
| `get_snippets(post_ids, query)` | Returns dict mapping post_id to highlighted snippet |