import os

os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-chars-long-for-testing"
os.environ["ADMIN_PASSWORD"] = "test-password"

import pytest
from sqlalchemy import text
from app import create_app
from app.extensions import db as _db
from app.models import User, Post
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


@pytest.fixture(scope="function")
def admin_user(db):
    """Create an admin user."""
    existing = db.session.execute(
        db.select(User).filter_by(username="admin")
    ).scalar_one_or_none()
    if existing:
        return existing
    user = User(username="admin", is_admin=True)
    user.set_password("testpassword")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture(scope="function")
def sample_post(db, admin_user):
    """Create a sample published post."""
    post = Post(
        title="Test Post",
        slug="test-post",
        body="# Hello World\n\nThis is a test post about Flask and Python.",
        summary="A test post summary about Flask and Python",
        published=True,
        published_at=utc_now(),
    )
    db.session.add(post)
    db.session.commit()
    return post


class TestInitFTS:
    def test_init_fts_creates_table(self, db):
        """Verify FTS table is created."""
        result = db.session.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'"
            )
        ).fetchone()
        assert result is not None
        assert result[0] == "posts_fts"

    def test_init_fts_idempotent(self, db):
        """Verify init_fts can be called multiple times without error."""
        init_fts()
        init_fts()
        result = db.session.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'"
            )
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

        snippets = get_search_snippets([post], "summary")
        assert isinstance(snippets, dict)
        assert post.id in snippets
        assert "summary" in snippets[post.id].lower()

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
