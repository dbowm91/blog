"""Search provider abstraction for full-text search backends."""

from abc import ABC, abstractmethod
from typing import Optional


class ConfigurationError(Exception):
    """Raised when search provider is misconfigured."""

    pass


class SearchProvider(ABC):
    """Abstract base class for search providers."""

    def initialize(self) -> None:
        """Initialize the search provider. Called during app startup.

        Override in subclass to perform provider-specific initialization.
        Default implementation does nothing.
        """
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 20) -> list[tuple[int, float]]:
        """Search posts and return list of (post_id, rank) tuples.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of (post_id, rank) tuples ordered by relevance (lower rank = better match)
        """
        pass

    @abstractmethod
    def index_post(
        self, post_id: int, title: str, body: str, summary: str, published: bool
    ) -> bool:
        """Index or remove a post from the search index.

        Args:
            post_id: Post ID
            title: Post title
            body: Post body content
            summary: Post summary
            published: Whether post is published

        Returns:
            True on success, False on failure
        """
        pass

    @abstractmethod
    def remove_post(self, post_id: int) -> bool:
        """Remove a post from the search index.

        Args:
            post_id: Post ID to remove

        Returns:
            True on success, False on failure
        """
        pass

    @abstractmethod
    def rebuild_index(self) -> None:
        """Rebuild the entire search index."""
        pass

    @abstractmethod
    def get_snippets(self, post_ids: list[int], query: str) -> dict[int, str]:
        """Get search snippets for given post IDs.

        Args:
            post_ids: List of post IDs
            query: Search query

        Returns:
            Dict mapping post_id to highlighted snippet
        """
        pass


def get_search_provider() -> SearchProvider:
    """Get the configured search provider.

    Returns:
        SearchProvider instance based on SEARCH_PROVIDER config
    """
    from app.config import SEARCH_PROVIDER

    if SEARCH_PROVIDER == "postgresql":
        from app.services.search.postgresql import PostgreSQLSearchProvider

        return PostgreSQLSearchProvider()

    from app.services.search.sqlite import SQLiteSearchProvider

    return SQLiteSearchProvider()
