"""PostgreSQL full-text search provider implementation.

Note: This is a stub implementation. PostgreSQL FTS requires:
1. PostgreSQL database with tsvector columns
2. Migration of existing SQLite FTS5 data
3. Configuration of SEARCH_PROVIDER='postgresql' in config

The actual implementation would use:
- tsvector for indexing
- ts_rank for relevance scoring
- <-> operator for phrase search
"""

from typing import Optional

from app.services.search import SearchProvider


class PostgreSQLSearchProvider(SearchProvider):
    """PostgreSQL tsvector implementation of SearchProvider."""

    def __init__(self) -> None:
        pass

    def search(self, query: str, limit: int = 20) -> list[tuple[int, float]]:
        """Search using PostgreSQL tsvector with ts_rank.

        This is a stub that falls back to SQLite search.
        Full implementation requires PostgreSQL schema changes.
        """
        from app.services.search.sqlite import SQLiteSearchProvider
        provider = SQLiteSearchProvider()
        return provider.search(query, limit)

    def index_post(self, post_id: int, title: str, body: str, summary: str, published: bool) -> bool:
        """Index a post using PostgreSQL tsvector.

        Full implementation would:
        1. Update posts.search_vector with setweight(to_tsvector(...), ...)
        2. Use triggers to keep search_vector in sync
        """
        from app.services.search.sqlite import SQLiteSearchProvider
        provider = SQLiteSearchProvider()
        return provider.index_post(post_id, title, body, summary, published)

    def remove_post(self, post_id: int) -> bool:
        """Remove a post from PostgreSQL FTS index."""
        from app.services.search.sqlite import SQLiteSearchProvider
        provider = SQLiteSearchProvider()
        return provider.remove_post(post_id)

    def rebuild_index(self) -> None:
        """Rebuild PostgreSQL tsvector index.

        Full implementation would:
        1. TRUNCATE search_vector column
        2. Re-populate with to_tsvector(...) for all published posts
        """
        from app.services.search.sqlite import SQLiteSearchProvider
        provider = SQLiteSearchProvider()
        return provider.rebuild_index()

    def get_snippets(self, post_ids: list[int], query: str) -> dict[int, str]:
        """Get search snippets using PostgreSQL ts_headline.

        Full implementation would use:
        ts_headline(body, plainto_tsquery(query), ...)
        """
        from app.services.search.sqlite import SQLiteSearchProvider
        provider = SQLiteSearchProvider()
        return provider.get_snippets(post_ids, query)