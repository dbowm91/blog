"""Coverage tests for the RSS, Atom and JSON feed variants."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")
os.environ["PAGE_VIEW_BUFFER_SIZE"] = "0"

import pytest
from sqlalchemy import update

from app.models import Post, PostSeries, Series, Tag
from app.routes.rss import invalidate_rss_cache
from app.utils import utc_now


@pytest.fixture(autouse=True)
def _clear_feed_cache(app):
    with app.app_context():
        invalidate_rss_cache()
    yield
    with app.app_context():
        invalidate_rss_cache()


@pytest.fixture()
def tagged_post(db, admin_user):
    tag = Tag(name="Python", slug="python")
    post = Post(
        title="Tagged Post",
        slug="tagged-post",
        body="# Heading\n\nSome *emphasis* and a [link](https://example.com).",
        published=True,
        published_at=utc_now(),
    )
    post.tags.append(tag)
    db.session.add(post)
    db.session.commit()
    return tag, post


@pytest.fixture()
def undated_post(db, admin_user):
    post = Post(
        title="Undated Post",
        slug="undated-post",
        body="Body without publication timestamps",
        published=True,
    )
    db.session.add(post)
    db.session.commit()
    db.session.execute(
        update(Post).where(Post.id == post.id).values(updated_at=None, published_at=None)
    )
    db.session.commit()
    return post


@pytest.fixture()
def series_with_posts(db, admin_user):
    series = Series(name="Guide Series", slug="guide-series", description="A guide")
    published = Post(
        title="Chapter One",
        slug="chapter-one",
        body="First chapter body",
        published=True,
        published_at=utc_now(),
    )
    draft = Post(title="Chapter Draft", slug="chapter-draft", body="Draft body", published=False)
    db.session.add_all([series, published, draft])
    db.session.flush()
    db.session.add_all(
        [
            PostSeries(series_id=series.id, post_id=published.id, order_index=0),
            PostSeries(series_id=series.id, post_id=draft.id, order_index=1),
        ]
    )
    db.session.commit()
    return series


class TestTagFeeds:
    def test_tag_atom_feed_lists_tagged_posts(self, client, tagged_post):
        response = client.get("/tag/python/atom")
        assert response.status_code == 200
        assert response.mimetype == "application/atom+xml"
        body = response.get_data(as_text=True)
        assert "<entry>" in body
        assert "Tagged Post" in body
        assert 'term="Python"' in body
        assert response.headers["ETag"]

    def test_tag_rss_feed_lists_tagged_posts(self, client, tagged_post):
        response = client.get("/tag/python/rss")
        assert response.status_code == 200
        assert response.mimetype == "application/rss+xml"
        body = response.get_data(as_text=True)
        assert "<item>" in body
        assert "Tagged Post" in body
        assert "<category>Python</category>" in body
        assert response.headers["ETag"]

    def test_tag_json_feed_lists_tagged_posts(self, client, tagged_post):
        response = client.get("/tag/python/json")
        assert response.status_code == 200
        assert response.mimetype == "application/feed+json"
        data = response.get_json()
        assert data["title"].startswith("#Python - ")
        assert data["description"] == "Posts tagged with #Python"
        assert data["feed_url"].endswith("/tag/python/json")
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["id"] == "tagged-post"
        assert item["title"] == "Tagged Post"
        assert item["tags"] == ["Python"]
        assert "content_html" in item

    def test_tag_feeds_return_304_for_matching_etag(self, client, tagged_post):
        for path in ("/tag/python/atom", "/tag/python/rss", "/tag/python/json"):
            first = client.get(path)
            etag = first.headers["ETag"]
            second = client.get(path, headers={"If-None-Match": etag})
            assert second.status_code == 304
            assert second.get_data() == b""

    def test_tag_feeds_ignore_stale_etag(self, client, tagged_post):
        response = client.get("/tag/python/rss", headers={"If-None-Match": '"stale-etag"'})
        assert response.status_code == 200
        assert "<item>" in response.get_data(as_text=True)

    def test_tag_feeds_404_for_unknown_tag(self, client, db, admin_user):
        for path in ("/tag/missing/atom", "/tag/missing/rss", "/tag/missing/json"):
            response = client.get(path)
            assert response.status_code == 404

    def test_tag_feed_without_posts(self, client, db, admin_user):
        tag = Tag(name="Empty Tag", slug="empty-tag")
        db.session.add(tag)
        db.session.commit()

        rss_response = client.get("/tag/empty-tag/rss")
        assert rss_response.status_code == 200
        assert "<item>" not in rss_response.get_data(as_text=True)

        atom_response = client.get("/tag/empty-tag/atom")
        assert atom_response.status_code == 200
        assert "<entry>" not in atom_response.get_data(as_text=True)

        json_response = client.get("/tag/empty-tag/json")
        assert json_response.status_code == 200
        assert json_response.get_json()["items"] == []


class TestSeriesFeeds:
    def test_series_atom_feed_excludes_drafts(self, client, series_with_posts):
        response = client.get("/series/guide-series/atom")
        assert response.status_code == 200
        assert response.mimetype == "application/atom+xml"
        body = response.get_data(as_text=True)
        assert "Chapter One" in body
        assert "Chapter Draft" not in body
        assert response.headers["ETag"]

    def test_series_rss_feed_excludes_drafts(self, client, series_with_posts):
        response = client.get("/series/guide-series/rss")
        assert response.status_code == 200
        assert response.mimetype == "application/rss+xml"
        body = response.get_data(as_text=True)
        assert "<item>" in body
        assert "Chapter One" in body
        assert "Chapter Draft" not in body

    def test_series_json_feed_excludes_drafts(self, client, series_with_posts):
        response = client.get("/series/guide-series/json")
        assert response.status_code == 200
        assert response.mimetype == "application/feed+json"
        data = response.get_json()
        assert data["title"].startswith("Guide Series - ")
        assert data["description"] == "Posts in the Guide Series series"
        assert data["feed_url"].endswith("/series/guide-series/json")
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Chapter One"

    def test_series_feeds_return_304_for_matching_etag(self, client, series_with_posts):
        for path in (
            "/series/guide-series/atom",
            "/series/guide-series/rss",
            "/series/guide-series/json",
        ):
            first = client.get(path)
            etag = first.headers["ETag"]
            second = client.get(path, headers={"If-None-Match": etag})
            assert second.status_code == 304
            assert second.get_data() == b""

    def test_series_feeds_404_for_unknown_series(self, client, db, admin_user):
        for path in (
            "/series/missing/atom",
            "/series/missing/rss",
            "/series/missing/json",
        ):
            response = client.get(path)
            assert response.status_code == 404

    def test_series_feed_without_posts(self, client, db, admin_user):
        series = Series(name="Empty Series", slug="empty-series")
        db.session.add(series)
        db.session.commit()

        rss_response = client.get("/series/empty-series/rss")
        assert rss_response.status_code == 200
        assert "<item>" not in rss_response.get_data(as_text=True)

        atom_response = client.get("/series/empty-series/atom")
        assert atom_response.status_code == 200
        assert "<entry>" not in atom_response.get_data(as_text=True)

        json_response = client.get("/series/empty-series/json")
        assert json_response.status_code == 200
        assert json_response.get_json()["items"] == []


class TestMainFeeds:
    def test_json_feed_lists_published_posts(self, client, sample_post):
        response = client.get("/json")
        assert response.status_code == 200
        assert response.mimetype == "application/feed+json"
        data = response.get_json()
        assert data["version"] == "https://jsonfeed.org/version/1.1"
        assert data["feed_url"].endswith("/json")
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["id"] == "test-post"
        assert item["title"] == "Test Post"
        assert item["date_published"].endswith("Z")
        assert item["date_modified"].endswith("Z")
        assert "content_html" in item

    def test_rss_feed_returns_304_for_matching_etag(self, client, sample_post):
        first = client.get("/rss")
        second = client.get("/rss", headers={"If-None-Match": first.headers["ETag"]})
        assert second.status_code == 304
        assert second.get_data() == b""

    def test_atom_feed_returns_304_for_matching_etag(self, client, sample_post):
        first = client.get("/atom")
        second = client.get("/atom", headers={"If-None-Match": first.headers["ETag"]})
        assert second.status_code == 304
        assert second.get_data() == b""

    def test_json_feed_returns_304_for_matching_etag(self, client, sample_post):
        first = client.get("/json")
        second = client.get("/json", headers={"If-None-Match": first.headers["ETag"]})
        assert second.status_code == 304
        assert second.get_data() == b""

    def test_feeds_ignore_stale_etag(self, client, sample_post):
        for path in ("/rss", "/atom", "/json"):
            response = client.get(path, headers={"If-None-Match": '"stale-etag"'})
            assert response.status_code == 200

    def test_feeds_without_posts(self, client, db, admin_user):
        rss_response = client.get("/rss")
        assert rss_response.status_code == 200
        assert "<item>" not in rss_response.get_data(as_text=True)

        atom_response = client.get("/atom")
        assert atom_response.status_code == 200
        assert "<entry>" not in atom_response.get_data(as_text=True)

        json_response = client.get("/json")
        assert json_response.status_code == 200
        assert json_response.get_json()["items"] == []

    def test_feeds_fall_back_to_created_at_without_timestamps(self, client, undated_post):
        response = client.get("/json")
        assert response.status_code == 200
        item = response.get_json()["items"][0]
        assert item["date_published"] == undated_post.created_at.isoformat() + "Z"
        assert item["date_modified"] == undated_post.created_at.isoformat() + "Z"

    def test_rss_feed_uses_cached_posts_outside_testing(self, app, client, sample_post):
        app.config["TESTING"] = False
        try:
            response = client.get("/rss")
        finally:
            app.config["TESTING"] = True
        assert response.status_code == 200
        assert b"Test Post" in response.data

    def test_json_feed_uses_cached_posts_outside_testing(self, app, client, sample_post):
        app.config["TESTING"] = False
        try:
            response = client.get("/json")
        finally:
            app.config["TESTING"] = True
        assert response.status_code == 200
        assert response.get_json()["items"][0]["title"] == "Test Post"
