"""Performance benchmark tests for catching regressions."""
import time
from unittest.mock import patch, MagicMock
from sqlalchemy import event

import pytest

from app.search import search, sync_fts
from app.models import Tag
from app.utils import utc_now


class TestSearchPerformance:
    """Benchmark search query time (FTS5 vs LIKE fallback)."""

    def test_fts_search_single_term(self, app, clean_db, admin_user):
        """Benchmark FTS5 single-term search."""
        from tests.benchmarks.conftest import create_posts_bulk

        create_posts_bulk(clean_db, count=50)

        start = time.perf_counter()
        for _ in range(10):
            results = search("Flask")
        elapsed = (time.perf_counter() - start) / 10

        assert len(results) > 0, "Should find some results"
        assert elapsed < 0.1, f"FTS search took {elapsed:.4f}s, expected < 0.1s"

    def test_fts_search_multi_term(self, app, clean_db, admin_user):
        """Benchmark FTS5 multi-term search."""
        from tests.benchmarks.conftest import create_posts_bulk

        create_posts_bulk(clean_db, count=50)

        start = time.perf_counter()
        for _ in range(10):
            results = search("Flask Python")
        elapsed = (time.perf_counter() - start) / 10

        assert elapsed < 0.15, f"FTS multi-term search took {elapsed:.4f}s, expected < 0.15s"

    def test_fts_search_no_match(self, app, clean_db, admin_user):
        """Benchmark FTS5 search with no matches."""
        from tests.benchmarks.conftest import create_posts_bulk

        create_posts_bulk(clean_db, count=50)

        start = time.perf_counter()
        for _ in range(10):
            results = search("NONEXISTENTTERM123")
        elapsed = (time.perf_counter() - start) / 10

        assert len(results) == 0
        assert elapsed < 0.1, f"FTS no-match search took {elapsed:.4f}s, expected < 0.1s"

    def test_fts_search_with_special_chars(self, app, clean_db, admin_user):
        """Benchmark FTS5 search handling special characters."""
        from tests.benchmarks.conftest import create_posts_bulk

        create_posts_bulk(clean_db, count=50)

        start = time.perf_counter()
        for _ in range(5):
            results = search("Flask (Python)")
        elapsed = (time.perf_counter() - start) / 5

        assert elapsed < 0.2, f"FTS special char search took {elapsed:.4f}s, expected < 0.2s"


class TestLIKEFallbackPerformance:
    """Benchmark LIKE fallback search performance."""

    def test_like_search_performance(self, app, clean_db, admin_user):
        """Benchmark LIKE-based search as fallback."""
        from tests.benchmarks.conftest import create_posts_bulk
        from app.models import Post

        create_posts_bulk(clean_db, count=50)

        query = "Flask"

        start = time.perf_counter()
        for _ in range(10):
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            search_term = f"%{escaped}%"

            results = clean_db.session.execute(
                clean_db.select(Post.id).filter(
                    Post.published == True,
                    (Post.title.ilike(search_term, escape="\\")) |
                    (Post.body.ilike(search_term, escape="\\")) |
                    (Post.summary.ilike(search_term, escape="\\"))
                )
            ).scalars().all()
        elapsed = (time.perf_counter() - start) / 10

        assert len(results) > 0
        assert elapsed < 0.5, f"LIKE search took {elapsed:.4f}s, expected < 0.5s for 50 posts"


class TestDashboardPerformance:
    """Benchmark dashboard page load time."""

    def test_dashboard_load_empty(self, app, clean_db, admin_user, clean_analytics_cache, authenticated_client):
        """Benchmark dashboard with no posts."""
        start = time.perf_counter()
        response = authenticated_client.get("/admin/")
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 1.0, f"Empty dashboard took {elapsed:.4f}s, expected < 1.0s"

    def test_dashboard_load_with_posts(self, app, clean_db, admin_user, clean_analytics_cache, authenticated_client):
        """Benchmark dashboard with 50 posts."""
        from tests.benchmarks.conftest import create_posts_bulk

        create_posts_bulk(clean_db, count=50)

        start = time.perf_counter()
        response = authenticated_client.get("/admin/")
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 2.0, f"Dashboard with 50 posts took {elapsed:.4f}s, expected < 2.0s"

    def test_dashboard_load_with_search(self, app, clean_db, admin_user, clean_analytics_cache, authenticated_client):
        """Benchmark dashboard with search filter."""
        from tests.benchmarks.conftest import create_posts_bulk

        create_posts_bulk(clean_db, count=30)

        start = time.perf_counter()
        response = authenticated_client.get("/admin/?q=Flask")
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 2.0, f"Dashboard search took {elapsed:.4f}s, expected < 2.0s"


class TestDatabaseQueryCounts:
    """Benchmark database query counts per request."""

    @pytest.fixture
    def query_counter(self, app, clean_db):
        """Fixture that counts queries per request."""
        query_counts = []

        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            if query_counts:
                query_counts[-1] += 1

        event.listen(clean_db.engine, "after_cursor_execute", receive_after_cursor_execute)

        class Counter:
            def __enter__(self):
                query_counts.append(0)
                return self

            def __exit__(self, *args):
                event.remove(clean_db.engine, "after_cursor_execute", receive_after_cursor_execute)

            @property
            def count(self):
                return query_counts[-1] if query_counts else 0

        return Counter()

    def test_search_query_count(self, app, clean_db, admin_user, query_counter):
        """Verify search uses minimal queries."""
        from tests.benchmarks.conftest import create_posts_bulk

        create_posts_bulk(clean_db, count=20)

        with query_counter:
            results = search("Flask")

        assert query_counter.count <= 3, f"Search used {query_counter.count} queries, expected <= 3"

    def test_dashboard_query_count(self, app, clean_db, admin_user, clean_analytics_cache, query_counter, authenticated_client):
        """Verify dashboard uses reasonable query count."""
        from tests.benchmarks.conftest import create_posts_bulk

        create_posts_bulk(clean_db, count=20)

        with query_counter:
            response = authenticated_client.get("/admin/")

        assert response.status_code == 200
        assert query_counter.count <= 20, f"Dashboard used {query_counter.count} queries, expected <= 20"

    def test_public_homepage_query_count(self, app, clean_db, admin_user, query_counter):
        """Verify public homepage uses minimal queries."""
        from tests.benchmarks.conftest import create_posts_bulk

        create_posts_bulk(clean_db, count=10)

        with app.test_client() as client:
            with query_counter:
                response = client.get("/")

            assert response.status_code == 200
            assert query_counter.count <= 10, f"Homepage used {query_counter.count} queries, expected <= 10"


class TestNewsletterPerformance:
    """Benchmark newsletter send time per subscriber."""

    def test_newsletter_email_render_time(self, app, clean_db):
        """Benchmark single email render time."""
        from tests.benchmarks.conftest import create_posts_bulk, create_subscribers_bulk

        posts = create_posts_bulk(clean_db, count=5)
        subscribers = create_subscribers_bulk(clean_db, count=1)

        with patch("app.email.render_template") as mock_render:
            mock_render.return_value = "<html>Mock Newsletter</html>"

            with patch("app.email._connect_smtp") as mock_connect:
                mock_server = MagicMock()
                mock_server.sendmail = MagicMock()
                mock_server.quit = MagicMock()
                mock_connect.return_value = mock_server

                with app.test_request_context():
                    from app.email import send_newsletter

                    start = time.perf_counter()
                    result = send_newsletter(posts, subscribers, total_subscribers=len(subscribers))
                    elapsed = time.perf_counter() - start

                    assert result is True
                    assert elapsed < 5.0, f"Newsletter send for 1 subscriber took {elapsed:.4f}s, expected < 5.0s"

    def test_newsletter_batch_timing(self, app, clean_db):
        """Benchmark newsletter batch send timing."""
        from tests.benchmarks.conftest import create_posts_bulk, create_subscribers_bulk

        posts = create_posts_bulk(clean_db, count=3)

        with patch("app.email._connect_smtp") as mock_connect:
            mock_server = MagicMock()
            mock_server.sendmail = MagicMock()
            mock_server.quit = MagicMock()
            mock_connect.return_value = mock_server

            subscribers = create_subscribers_bulk(clean_db, count=10)

            with patch("app.email.render_template") as mock_render:
                mock_render.return_value = "<html>Mock Newsletter</html>"

                with app.test_request_context():
                    from app.email import send_newsletter

                    start = time.perf_counter()
                    result = send_newsletter(posts, subscribers, total_subscribers=10)
                    elapsed = time.perf_counter() - start

                    assert result is True
                    per_subscriber = elapsed / len(subscribers)
                    assert per_subscriber < 0.5, f"Per-subscriber time {per_subscriber:.4f}s, expected < 0.5s"


class TestFTSIndexingPerformance:
    """Benchmark FTS indexing operations."""

    def test_sync_fts_single_post(self, app, clean_db, admin_user):
        """Benchmark syncing a single post to FTS."""
        from tests.benchmarks.conftest import create_posts_bulk

        posts = create_posts_bulk(clean_db, count=1)
        post_id = posts[0].id
        post_body = posts[0].body
        post_summary = posts[0].summary

        start = time.perf_counter()
        for i in range(10):
            sync_fts(
                post_id,
                f"Updated Post Title {i}",
                post_body,
                post_summary,
                True
            )
            clean_db.session.commit()
        elapsed = time.perf_counter() - start

        per_sync = elapsed / 10
        assert per_sync < 0.1, f"Per-post FTS sync took {per_sync:.4f}s, expected < 0.1s"

    def test_rebuild_fts_performance(self, app, clean_db, admin_user):
        """Benchmark full FTS rebuild."""
        from tests.benchmarks.conftest import create_posts_bulk
        from app.search import rebuild_fts

        create_posts_bulk(clean_db, count=50)

        start = time.perf_counter()
        rebuild_fts()
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0, f"FTS rebuild took {elapsed:.4f}s, expected < 2.0s for 50 posts"


class TestTagCachingPerformance:
    """Benchmark tag cache operations."""

    def test_get_tag_counts_performance(self, app, clean_db, admin_user):
        """Benchmark tag counts retrieval."""
        from tests.benchmarks.conftest import create_posts_bulk
        from app.tag_cache import _get_tag_counts, invalidate_tag_cache

        posts = create_posts_bulk(clean_db, count=30)

        tag = Tag(name="Python", slug=f"python-{utc_now().timestamp()}")
        clean_db.session.add(tag)
        clean_db.session.commit()

        for post in posts[:10]:
            post.tags.append(tag)
        clean_db.session.commit()

        invalidate_tag_cache()

        start = time.perf_counter()
        for _ in range(100):
            counts = _get_tag_counts()
        elapsed = time.perf_counter() - start

        per_call = elapsed / 100
        assert per_call < 0.01, f"Tag counts per call took {per_call:.4f}s, expected < 0.01s"
