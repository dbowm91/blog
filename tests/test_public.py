import pytest
from sqlalchemy import select, func
from app.utils import utc_now


def test_index(client, db, sample_post):
    """Test homepage returns 200."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Test Post" in response.data


def test_post_page(client, db, sample_post):
    """Test individual post page."""
    response = client.get("/post/test-post")
    assert response.status_code == 200
    assert b"Test Post" in response.data


def test_post_not_found(client, db):
    """Test 404 for non-existent post."""
    response = client.get("/post/non-existent")
    assert response.status_code == 404


def test_tag_page(client, db, sample_post, sample_tag):
    """Test tag page."""
    sample_post.tags.append(sample_tag)
    db.session.commit()
    response = client.get("/tag/python")
    assert response.status_code == 200


def test_search(client, db, sample_post):
    """Test search functionality."""
    response = client.get("/search?q=test")
    assert response.status_code == 200
    assert b"Test Post" in response.data


def test_search_empty_query(client, db):
    """Test search with empty query redirects."""
    response = client.get("/search?q=")
    assert response.status_code == 302


def test_search_no_results(client, db, sample_post):
    """Test search with no results."""
    response = client.get("/search?q=nonexistent")
    assert response.status_code == 200
    assert b"No posts match your search" in response.data


def test_search_escapes_like_wildcards(client, db):
    """Test that % and _ in search are escaped and treated literally."""
    from app.models import Post

    post = Post(title="100% complete", slug="100-pct", body="Done", published=True)
    db.session.add(post)
    db.session.commit()
    # Searching for "100%" should only match the literal "100%", not "100" + anything
    response = client.get("/search?q=100%25")
    assert response.status_code == 200


def test_robots_txt(client):
    """Test robots.txt returns text."""
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert b"Sitemap:" in response.data


def test_sitemap_xml(client, db, sample_post):
    """Test sitemap.xml returns valid XML."""
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert b"<?xml" in response.data
    assert b"test-post" in response.data


def test_rss_feed(client, db, sample_post):
    """Test Atom feed."""
    response = client.get("/atom")
    assert response.status_code == 200
    assert b"<?xml" in response.data
    assert b"Test Post" in response.data


def test_favicon(client):
    """Test favicon redirects to SVG."""
    response = client.get("/favicon.ico")
    assert response.status_code == 302


def test_subscribe_valid_email(client, db):
    """Test subscribing with a valid email."""
    response = client.post(
        "/subscribe", data={"email": "test@example.com"}, follow_redirects=True
    )
    assert response.status_code == 200


def test_subscribe_invalid_email(client, db):
    """Test subscribing with an invalid email."""
    response = client.post(
        "/subscribe", data={"email": "invalid"}, follow_redirects=True
    )
    assert b"valid email" in response.data


def test_subscribe_duplicate(client, db):
    """Test subscribing with an already-subscribed email returns unified message."""
    from app.models import Subscriber

    sub = Subscriber(email="test@example.com", confirmed=True)
    db.session.add(sub)
    db.session.commit()
    response = client.post(
        "/subscribe", data={"email": "test@example.com"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"already subscribed" in response.data


def test_confirm_subscription(client, db):
    """Test confirming a subscription."""
    from app.models import Subscriber

    sub = Subscriber(email="test@example.com")
    db.session.add(sub)
    db.session.commit()
    response = client.get(f"/confirm/{sub.token}", follow_redirects=True)
    assert response.status_code == 200


def test_confirm_already_confirmed(client, db):
    """Test confirming an already-confirmed subscription."""
    from app.models import Subscriber

    sub = Subscriber(email="test@example.com", confirmed=True)
    db.session.add(sub)
    db.session.commit()
    response = client.get(f"/confirm/{sub.token}", follow_redirects=True)
    assert response.status_code == 200
    assert b"Already confirmed" in response.data


def test_confirm_expired_token(client, db):
    """Test confirming a subscription with expired token."""
    from app.models import Subscriber
    from datetime import timedelta

    sub = Subscriber(email="test@example.com", expires_at=utc_now() - timedelta(days=1))
    db.session.add(sub)
    db.session.commit()
    response = client.get(f"/confirm/{sub.token}", follow_redirects=True)
    assert response.status_code == 200
    assert b"expired" in response.data.lower()


def test_health_check(client, db):
    """Test health check endpoint returns OK."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["checks"]["database"] == "ok"
    assert "timestamp" in data


def test_unsubscribe(client, db):
    """Test unsubscribing."""
    from app.models import Subscriber

    sub = Subscriber(email="test@example.com", confirmed=True)
    db.session.add(sub)
    db.session.commit()
    response = client.get(f"/unsubscribe/{sub.token}", follow_redirects=True)
    assert response.status_code == 200


def test_unsubscribe_timing_constant(client, db):
    """Test that unsubscribe always sleeps 0.1 seconds regardless of token validity."""
    from app.models import Subscriber
    from app.utils import utc_now
    from datetime import timedelta
    from unittest.mock import patch

    # Create a valid subscriber
    sub = Subscriber(email="valid@example.com", confirmed=True)
    db.session.add(sub)
    db.session.commit()
    valid_token = sub.token

    # Create an expired subscriber (expires_at in past)
    expired_sub = Subscriber(
        email="expired@example.com",
        confirmed=True,
        expires_at=utc_now() - timedelta(days=1),
    )
    db.session.add(expired_sub)
    db.session.commit()
    expired_token = expired_sub.token

    invalid_token = "invalid-token-12345"

    with patch("app.routes.public.subscribe.time.sleep") as mock_sleep:
        # Valid token
        response = client.get(f"/unsubscribe/{valid_token}")
        assert response.status_code == 302  # redirect
        mock_sleep.assert_called_once_with(0.1)
        mock_sleep.reset_mock()

        # Expired token
        response = client.get(f"/unsubscribe/{expired_token}")
        assert response.status_code == 302
        mock_sleep.assert_called_once_with(0.1)
        mock_sleep.reset_mock()

        # Invalid token
        response = client.get(f"/unsubscribe/{invalid_token}")
        assert response.status_code == 302
        mock_sleep.assert_called_once_with(0.1)


def test_short_url_redirect(client, db, sample_post):
    """Test short URL redirects to post."""
    from app.base62 import encode

    code = encode(sample_post.id)
    response = client.get(f"/s/{code}")
    assert response.status_code == 302
    assert f"/post/{sample_post.slug}" in response.headers["Location"]


def test_short_url_records_share_event(client, db, sample_post):
    """Test short URL records a share event."""
    from app.base62 import encode
    from app.models import ShareEvent

    code = encode(sample_post.id)
    client.get(f"/s/{code}")
    event = db.session.execute(
        select(ShareEvent).filter_by(post_id=sample_post.id, platform="link")
    ).scalar_one_or_none()
    assert event is not None


def test_short_url_invalid_code(client):
    """Test short URL with invalid code redirects home."""
    response = client.get("/s/invalid")
    assert response.status_code == 302


def test_page_view_deduplication(client, db, sample_post):
    """Test that same session, same post = 1 view only."""
    from app.models import PageView
    from sqlalchemy import func

    # First visit - should create a page view
    client.get(f"/post/{sample_post.slug}")
    count_after_first = db.session.execute(
        select(func.count()).select_from(PageView).filter_by(post_id=sample_post.id)
    ).scalar_one()
    assert count_after_first == 1

    # Second visit from same session - should NOT create another
    client.get(f"/post/{sample_post.slug}")
    count_after_second = db.session.execute(
        select(func.count()).select_from(PageView).filter_by(post_id=sample_post.id)
    ).scalar_one()
    assert count_after_second == 1


def test_max_viewed_posts_cap(client, db, admin_user):
    """Test session capped at MAX_VIEWED_POSTS."""
    from app.models import Post, PageView
    from app.config import MAX_VIEWED_POSTS

    # Create more posts than the cap
    posts = []
    for i in range(MAX_VIEWED_POSTS + 3):
        post = Post(
            title=f"Post {i}",
            slug=f"post-{i}",
            body=f"Content {i}",
            published=True,
            published_at=utc_now(),
        )
        posts.append(post)
    db.session.add_all(posts)
    db.session.commit()

    # Visit all posts
    for post in posts:
        client.get(f"/post/{post.slug}")

    # Should have created views for all posts
    total_views = db.session.execute(
        select(func.count()).select_from(PageView)
    ).scalar_one()
    assert total_views == MAX_VIEWED_POSTS + 3

    # Check session has at most MAX_VIEWED_POSTS entries
    with client.session_transaction() as sess:
        viewed = sess.get("viewed_posts", [])
        assert len(viewed) <= MAX_VIEWED_POSTS


def test_search_has_sidebar_tags(client, db, sample_post, sample_tag):
    """Test search page includes tags and tag_counts for sidebar."""
    sample_post.tags.append(sample_tag)
    db.session.commit()
    response = client.get("/search?q=test")
    assert response.status_code == 200
    assert b"Tags" in response.data
    assert b"#Python" in response.data


def test_subscribe_open_redirect_prevented(client, db):
    """Test subscribe does not redirect to external sites via spoofed Referer."""
    response = client.post(
        "/subscribe",
        data={"email": "test@example.com"},
        headers={"Referer": "http://evil.com/phishing"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    # Should redirect to index, not to evil.com


def test_track_share_validates_post_id(client, db):
    """Test track_share rejects non-integer post_ids."""
    response = client.post(
        "/api/track-share",
        json={"post_id": "abc", "platform": "twitter"},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_track_share_rejects_invalid_platform(client, db, sample_post):
    """Test track_share rejects platforms not in allowlist."""
    long_platform = "x" * 100
    response = client.post(
        "/api/track-share",
        json={"post_id": sample_post.id, "platform": long_platform},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json == {"error": "invalid platform"}


def test_track_share_accepts_valid_platforms(client, db, sample_post):
    """Test track_share accepts valid platform names."""
    for platform in ["twitter", "facebook", "linkedin", "reddit", "hackernews", "link"]:
        response = client.post(
            "/api/track-share",
            json={"post_id": sample_post.id, "platform": platform},
            content_type="application/json",
        )
        assert response.status_code == 200, f"Platform {platform} should be accepted"


def test_referrer_sanitized(client, db, sample_post):
    """Test referrer query params are stripped before storing."""
    response = client.get(
        f"/post/{sample_post.slug}",
        headers={"Referer": "http://example.com/page?secret=token&foo=bar"},
    )
    from app.models import PageView

    pv = db.session.execute(
        select(PageView).filter_by(post_id=sample_post.id)
    ).scalar_one_or_none()
    assert pv.referrer == "http://example.com/page"
    assert "secret" not in (pv.referrer or "")
    assert "token" not in (pv.referrer or "")


def test_search_fts5_special_characters_double_quote(client, db, sample_post):
    """Test FTS5 handles double quote in search without 500 error."""
    response = client.get('/search?q="test')
    assert response.status_code == 200


def test_search_fts5_special_characters_asterisk(client, db, sample_post):
    """Test FTS5 handles asterisk in search without 500 error."""
    response = client.get("/search?q=test*")
    assert response.status_code == 200


def test_search_fts5_special_characters_colon(client, db, sample_post):
    """Test FTS5 handles colon in search without 500 error."""
    response = client.get("/search?q=test:foo")
    assert response.status_code == 200


def test_search_fts5_special_characters_hyphen(client, db, sample_post):
    """Test FTS5 handles hyphen in search without 500 error."""
    response = client.get("/search?q=test-foo")
    assert response.status_code == 200


def test_search_special_characters_comma(client, db, sample_post):
    """Test search with comma doesn't crash."""
    response = client.get("/search?q=hello,world")
    assert response.status_code == 200


def test_search_special_characters_semicolon(client, db, sample_post):
    """Test search with semicolon doesn't crash."""
    response = client.get("/search?q=hello;world")
    assert response.status_code == 200


def test_search_special_characters_pipe(client, db, sample_post):
    """Test search with pipe doesn't crash."""
    response = client.get("/search?q=hello|world")
    assert response.status_code == 200


def test_search_special_characters_backslash(client, db, sample_post):
    """Test search with backslash doesn't crash."""
    response = client.get("/search?q=hello\\world")
    assert response.status_code == 200


def test_search_special_characters_unicode(client, db, sample_post):
    """Test search with Unicode characters doesn't crash."""
    response = client.get("/search?q=hello\u4e16\u754c")
    assert response.status_code == 200


def test_search_empty_query_returns_home(client, db):
    """Test empty search query redirects to home."""
    response = client.get("/search?q=")
    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_search_very_long_query(client, db):
    """Test search with very long query (>200 chars) is handled."""
    long_query = "a" * 300
    response = client.get(f"/search?q={long_query}")
    assert response.status_code == 200
