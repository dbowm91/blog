# Search (`app/search.py`)

Full-text search using SQLite FTS5 with LIKE fallback.

## Search Provider Abstraction (`app/services/search/`)

The search functionality is abstracted by a provider pattern:

| Class | File | Purpose |
|-------|------|---------|
| `SearchProvider` | `__init__.py` | Abstract base class defining the interface |
| `SQLiteSearchProvider` | `sqlite.py` | Wraps `app/search.py` FTS5 functions through the `SearchProvider` interface |
| `PostgreSQLSearchProvider` | `postgresql.py` | Stub for future PostgreSQL implementation |

### Factory Function

```python
from app.services.search import get_search_provider
provider = get_search_provider()  # Returns configured provider
```

### Configuration

- `SEARCH_PROVIDER` config (default: `"sqlite"`, can be `"postgresql"`)
- `SEARCH_CONFIG` - Provider-specific configuration dict
- When set to `"postgresql"`, falls back to SQLite until full PostgreSQL implementation is complete

## Features

- **FTS5 Virtual Table**: High-performance full-text search
- **BM25 Ranking**: Relevance-based results
- **Prefix Matching**: Supports `term*` wildcards
- **Snippets**: Query highlighting in results
- **Did You Mean**: Fuzzy suggestions for misspellings
- **Fallback**: LIKE-based search when FTS unavailable

## FTS5 Table Structure

```sql
CREATE VIRTUAL TABLE posts_fts USING fts5(
    title,
    body,
    summary,
    prefix='2 3 4'
)
```

Additional vocabulary table:
```sql
CREATE VIRTUAL TABLE posts_fts_vocab USING fts5vocab(posts_fts, 'row')
```

## Core Functions

### `init_fts()`

Creates FTS5 tables and populates with existing published posts. Idempotent.

### `rebuild_fts()`

Rebuilds the FTS5 index from scratch using `INSERT INTO posts_fts(posts_fts) VALUES('rebuild')`. Use when index gets out of sync with actual data.

### `sync_fts()`

```python
def sync_fts(
    post_id: int,
    title: str,
    body: str,
    summary: str,
    published: bool
) -> bool:
```

Syncs a single post to/from FTS index. Called before `db.session.commit()`.

### `sync_fts_batch()`

```python
def sync_fts_batch(items: list[tuple]) -> bool:
```

Batch sync multiple posts to FTS index. Call before `db.session.commit()`.

**Args:**
- `items`: List of `(post_id, title, body, summary, published)` tuples.

**Returns:** True on success, False on failure. On failure, caller should rollback the transaction to maintain FTS/DB consistency.

### `remove_fts()`

```python
def remove_fts(post_id: int) -> bool:
```

Remove a post from the FTS index. Call before `db.session.commit()`.

**Returns:** True on success, False on failure. On failure, caller should rollback the transaction to maintain FTS/DB consistency.

### `reset_fts_available()`

```python
def reset_fts_available() -> None:
```

Reset FTS availability cache. For testing and cache invalidation. Forces next search to re-check FTS5 table existence.

### `get_indexed_terms()`

```python
def get_indexed_terms() -> list[str]:
```

Get all indexed terms using FTS5 vocabulary table for efficiency. Falls back to extracting terms from post titles if vocabulary table unavailable.

**Returns:** Alphabetically sorted list of unique terms in the search index.

### `highlight_query()`

```python
def highlight_query(text: str, query: str) -> str:
```

Add `<mark>` tags around query terms in text for highlighting.

**Args:**
- `text`: The text to highlight within
- `query`: The search query (may contain multiple words)

**Returns:** The text with `<mark>` tags around matched terms.

### `search()`

```python
def search(query: str) -> list[tuple[int, float]]:
```

Returns list of `(post_id, rank)` tuples ordered by BM25 relevance.

### `get_search_snippets()`

```python
def get_search_snippets(posts: list, query: str) -> dict[int, str]:
```

Returns dict mapping post_id to highlighted snippet using FTS5 `snippet()` function.

**SQLite Batching**: Uses `_SQLITE_MAX_VARS = 500` to batch queries due to SQLite's parameter limit (999). For large result sets, post_ids are chunked into groups of 500.

### `get_did_you_mean()`

```python
def get_did_you_mean(
    query: str,
    indexed_terms: list[str],
    max_suggestions: int = 3
) -> str | None:
```

Fuzzy matching suggestions for misspelled queries.

## Query Processing

1. Escape special FTS5 characters: `()*+":<>`
2. Split query into terms
3. Build OR query with prefix matching: `"term"*`
4. Execute with BM25 ranking

## Caching

- FTS availability check cached for 5 minutes (`_FTS_CHECK_TTL = 300`)

## Configuration

- `FTS_RESULT_LIMIT`: Max results (default: 100)

## See Also
- [Models](core/models.md) - Post model
- [Public Routes](../routes/public-routes.md) - Search endpoint
