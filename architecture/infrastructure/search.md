# Search (`app/search.py`)

Full-text search using SQLite FTS5 with LIKE fallback.

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

Batch sync multiple posts. Uses `INSERT OR REPLACE` for efficiency.

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
