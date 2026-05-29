"""SQLite FTS5 search provider implementation."""

from app.services.search import SearchProvider


class SQLiteSearchProvider(SearchProvider):
    """SQLite FTS5 implementation of SearchProvider."""

    def __init__(self) -> None:
        self._fts_enabled: bool | None = None
        self._fts_check_time: float = 0
        self._FTS_CHECK_TTL = 300

    def initialize(self) -> None:
        """Initialize the SQLite FTS5 provider. Wraps init_fts()."""
        from app.search import init_fts

        init_fts()

    def search(self, query: str, limit: int = 20) -> list[tuple[int, float]]:
        """Search using FTS5 with bm25 ranking."""
        from app.search import search as fts_search

        results = fts_search(query)
        if limit and len(results) > limit:
            return results[:limit]
        return results

    def index_post(
        self, post_id: int, title: str, body: str, summary: str, published: bool
    ) -> bool:
        """Index a post using sync_fts."""
        from app.search import sync_fts

        return sync_fts(post_id, title, body, summary, published)

    def remove_post(self, post_id: int) -> bool:
        """Remove a post from FTS index."""
        from app.search import remove_fts

        return remove_fts(post_id)

    def rebuild_index(self) -> None:
        """Rebuild FTS5 index."""
        from app.search import rebuild_fts

        rebuild_fts()

    def get_snippets(self, post_ids: list[int], query: str) -> dict[int, str]:
        """Get search snippets using FTS5."""
        from app.search import get_search_snippets
        from app.models import Post

        posts = Post.query.filter(Post.id.in_(post_ids)).all()
        return get_search_snippets(posts, query)
