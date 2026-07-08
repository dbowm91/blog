import os
from unittest.mock import patch

import pytest
from sqlalchemy import text
from app import create_app
from app.extensions import db as _db
from app.models import Post
from app.utils import utc_now
from app.search import (
    init_fts,
    rebuild_fts,
    sync_fts,
    remove_fts,
    search,
    extract_snippet,
    get_search_snippets,
    reset_fts_available,
)
from app.services.search import get_search_provider


@pytest.fixture(scope="function")
def app(tmp_path):
    """Create application with temp database for each test."""
    db_path = tmp_path / "test.db"

    os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "CSRF_ENABLED": False,
        }
    )

    yield app


@pytest.fixture(scope="function")
def db(app):
    """Create database tables for each test."""
    with app.app_context():
        _db.session.remove()
        _db.create_all()
        reset_fts_available()
        init_fts()
        yield _db
        _db.engine.dispose()
        _db.session.remove()
        _db.drop_all()
        _db.session.remove()


class TestGetSearchProvider:
    """Tests for get_search_provider() factory function."""

    def test_get_search_provider_sqlite(self, app):
        """Test get_search_provider returns SQLiteSearchProvider by default."""
        from app.services.search import get_search_provider
        from app.services.search.sqlite import SQLiteSearchProvider

        with app.app_context():
            provider = get_search_provider()
            assert isinstance(provider, SQLiteSearchProvider)

    def test_get_search_provider_postgresql_stub(self, app):
        """Test PostgreSQL search provider raises ConfigurationError on use."""
        from app.services.search import ConfigurationError

        with patch("app.config.SEARCH_PROVIDER", "postgresql"):
            with app.app_context():
                provider = get_search_provider()
                with pytest.raises(ConfigurationError, match="not yet implemented"):
                    provider.search("test query")

    def test_search_provider_has_initialize(self, app):
        """Test SearchProvider base class has initialize() method."""
        from app.services.search import SearchProvider

        assert hasattr(SearchProvider, "initialize")

    def test_sqlite_search_provider_initialize(self, app, db):
        """Test SQLiteSearchProvider.initialize() calls init_fts()."""
        from app.services.search.sqlite import SQLiteSearchProvider

        with app.app_context():
            provider = SQLiteSearchProvider()
            provider.initialize()
            result = db.session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'")
            ).fetchone()
            assert result is not None


class TestInitFTS:
    def test_init_fts_creates_table(self, db):
        """Verify FTS table is created."""
        result = db.session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'")
        ).fetchone()
        assert result is not None
        assert result[0] == "posts_fts"

    def test_init_fts_idempotent(self, db):
        """Verify init_fts can be called multiple times without error."""
        init_fts()
        init_fts()
        result = db.session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'")
        ).fetchone()
        assert result is not None


class TestSyncAndSearch:
    def test_sync_fts_then_search(self, db, admin_user):
        """Create a post, sync to FTS, search for it, verify it's found."""
        post = Post(
            title="Flask Web Development",
            slug="flask-web-dev",
            body="Flask is a Python web framework.",
            summary="Learn Flask web development",
            published=True,
            published_at=utc_now(),
        )
        db.session.add(post)
        db.session.commit()
        sync_fts(post.id, post.title, post.body, post.summary, post.published)
        db.session.commit()

        results = search("Flask")
        post_ids = [r[0] for r in results]
        assert post.id in post_ids

    def test_sync_fts_published_true_searchable(self, db, admin_user):
        """Verify published posts are searchable."""
        post = Post(
            title="Published Article",
            slug="published-article",
            body="This content should be searchable",
            summary="Published summary",
            published=True,
            published_at=utc_now(),
        )
        db.session.add(post)
        db.session.commit()
        sync_fts(post.id, post.title, post.body, post.summary, post.published)
        db.session.commit()

        results = search("searchable")
        post_ids = [r[0] for r in results]
        assert post.id in post_ids

    def test_sync_fts_published_false_not_searchable(self, db, admin_user):
        """Verify unpublished posts are NOT searchable."""
        post = Post(
            title="Draft Article",
            slug="draft-article",
            body="This content should NOT be searchable",
            summary="Draft summary",
            published=False,
        )
        db.session.add(post)
        db.session.commit()
        sync_fts(post.id, post.title, post.body, post.summary, post.published)
        db.session.commit()

        results = search("searchable")
        post_ids = [r[0] for r in results]
        assert post.id not in post_ids


class TestRebuildFTS:
    def test_rebuild_fts_succeeds(self, db, sample_post):
        """Verify rebuild_fts doesn't error."""
        sync_fts(
            sample_post.id,
            sample_post.title,
            sample_post.body,
            sample_post.summary,
            sample_post.published,
        )
        db.session.commit()

        rebuild_fts()

        results = search("test")
        post_ids = [r[0] for r in results]
        assert sample_post.id in post_ids


class TestExtractSnippet:
    def test_extract_snippet_finds_query(self):
        """Verify it extracts text around query match."""
        text = "This is a long article about Python programming. Python is great for beginners."
        snippet = extract_snippet(text, "Python", context_chars=50)
        assert "Python" in snippet

    def test_extract_snippet_no_match_returns_start(self):
        """When query not found, return start of text."""
        text = "This is a long article about programming."
        snippet = extract_snippet(text, "NOTFOUND", context_chars=50)
        assert snippet.startswith("This")
        assert "..." in snippet or len(snippet) <= 53

    def test_extract_snippet_empty_text(self):
        """Empty text returns empty string."""
        assert extract_snippet("", "query") == ""
        assert extract_snippet(None, "query") == ""

    def test_extract_snippet_context_bounds(self):
        """Verify snippet respects context_chars."""
        text = "A" * 500
        snippet = extract_snippet(text, "AAA", context_chars=100)
        assert len(snippet) <= 103


class TestGetSearchSnippets:
    def test_get_search_snippets_returns_dict(self, db, admin_user):
        """Verify it returns dict mapping post_id to snippet."""
        post = Post(
            title="Test Post",
            slug="test-post-snippet",
            body="This is the body content",
            summary="This is the summary",
            published=True,
            published_at=utc_now(),
        )
        db.session.add(post)
        db.session.commit()
        sync_fts(post.id, post.title, post.body, post.summary, post.published)
        db.session.commit()

        snippets = get_search_snippets([post], "body")
        assert isinstance(snippets, dict)
        assert post.id in snippets
        assert "body" in snippets[post.id].lower()

    def test_get_search_snippets_falls_back_to_body(self, db, admin_user):
        """When post has no summary, falls back to body."""
        post = Post(
            title="Test Post",
            slug="test-post-body-snippet",
            body="This unique body content should be found",
            summary="",
            published=True,
            published_at=utc_now(),
        )
        db.session.add(post)
        db.session.commit()
        sync_fts(post.id, post.title, post.body, post.summary, post.published)
        db.session.commit()

        snippets = get_search_snippets([post], "unique")
        assert "unique" in snippets[post.id].lower()


class TestSearchNoResults:
    def test_search_no_results(self, db):
        """Search with no matching posts returns empty list."""
        results = search("XYZNONEXISTENTTERM123")
        assert results == []

    def test_search_empty_query(self, db):
        """Empty query returns empty list."""
        results = search("")
        assert results == []


class TestFTSPrefixSearch:
    """Test FTS5 prefix search with prefix='2 3 4' option."""

    def test_prefix_search_matches_partial_words(self, db, admin_user):
        """Prefix search should match words starting with the prefix (e.g., 'Py' matches 'Python')."""
        post = Post(
            title="Python Flask Tutorial",
            slug="python-flask-tutorial",
            body="Learn Python and Flask for web development. Python is great.",
            summary="Python Flask web development tutorial",
            published=True,
            published_at=utc_now(),
        )
        db.session.add(post)
        db.session.commit()
        sync_fts(post.id, post.title, post.body, post.summary, post.published)
        db.session.commit()

        # Search with prefix "Py" should match "Python"
        results = search("Py")
        post_ids = [r[0] for r in results]
        assert post.id in post_ids

        # Search with full word should also match
        results_full = search("Python")
        post_ids_full = [r[0] for r in results_full]
        assert post.id in post_ids_full

    def test_prefix_search_multiple_terms(self, db, admin_user):
        """Prefix search should work with multiple search terms."""
        post = Post(
            title="JavaScript React Vue Angular",
            slug="js-frameworks",
            body="Comparison of JavaScript frameworks: React, Vue, and Angular.",
            summary="JS frameworks comparison",
            published=True,
            published_at=utc_now(),
        )
        db.session.add(post)
        db.session.commit()
        sync_fts(post.id, post.title, post.body, post.summary, post.published)
        db.session.commit()

        # Search with prefix "Re" should match "React"
        results = search("Re")
        post_ids = [r[0] for r in results]
        assert post.id in post_ids

        # Search with prefix "An" should match "Angular"
        results2 = search("An")
        post_ids2 = [r[0] for r in results2]
        assert post.id in post_ids2

    def test_prefix_search_uses_fts5_prefix_index(self, db):
        """Verify FTS5 table was created with prefix index option."""
        result = db.session.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='posts_fts'")
        ).fetchone()
        assert result is not None
        # The CREATE statement should contain the prefix option
        create_sql = result[0]
        assert "prefix" in create_sql
        assert "2 3 4" in create_sql

    def test_prefix_search_exact_word_no_prefix(self, db, admin_user):
        """Search with exact word should still work (no false positives from prefix)."""
        post1 = Post(
            title="Python Programming",
            slug="python-programming",
            body="Learn Python programming.",
            summary="Python programming guide",
            published=True,
            published_at=utc_now(),
        )
        post2 = Post(
            title="PyTorch Deep Learning",
            slug="pytorch-deep-learning",
            body="Deep learning with PyTorch.",
            summary="PyTorch deep learning",
            published=True,
            published_at=utc_now(),
        )
        db.session.add_all([post1, post2])
        db.session.commit()
        sync_fts(post1.id, post1.title, post1.body, post1.summary, post1.published)
        sync_fts(post2.id, post2.title, post2.body, post2.summary, post2.published)
        db.session.commit()

        # Search for "Py" should match both (prefix match)
        results = search("Py")
        post_ids = [r[0] for r in results]
        assert post1.id in post_ids
        assert post2.id in post_ids

        # Search for "Python" should only match post1
        results_exact = search("Python")
        post_ids_exact = [r[0] for r in results_exact]
        assert post1.id in post_ids_exact
        assert post2.id not in post_ids_exact


class TestRemoveFTS:
    def test_remove_fts_removes_post(self, db, admin_user):
        """Remove a post from FTS and verify it's no longer found."""
        post = Post(
            title="Post to Remove",
            slug="post-to-remove",
            body="This post will be removed from search",
            summary="Remove me",
            published=True,
            published_at=utc_now(),
        )
        db.session.add(post)
        db.session.commit()
        sync_fts(post.id, post.title, post.body, post.summary, post.published)
        db.session.commit()

        results_before = search("Remove")
        assert post.id in [r[0] for r in results_before]

        remove_fts(post.id)
        db.session.commit()

        results_after = search("Remove")
        assert post.id not in [r[0] for r in results_after]

    def test_remove_fts_nonexistent_post_no_error(self, db):
        """Removing non-existent post doesn't error."""
        remove_fts(99999)
        db.session.commit()
