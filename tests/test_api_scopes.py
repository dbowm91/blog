import os
import hashlib

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")
os.environ["API_KEY"] = ""
os.environ["PAGE_VIEW_BUFFER_SIZE"] = "0"

import pytest
from app.models import ApiToken, Post
from app.utils import utc_now


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@pytest.fixture()
def scoped_token_factory(db):
    def _create(scopes, name="test-token"):
        raw_token = "test-token-abc123"
        token = ApiToken(
            name=name,
            token_hash=_hash_token(raw_token),
            scopes=scopes,
        )
        db.session.add(token)
        db.session.commit()
        return raw_token

    return _create


@pytest.fixture()
def posts_read_token(scoped_token_factory):
    return scoped_token_factory(["posts:read"])


@pytest.fixture()
def posts_write_token(scoped_token_factory):
    return scoped_token_factory(["posts:write"])


@pytest.fixture()
def subscribers_read_token(scoped_token_factory):
    return scoped_token_factory(["subscribers:read"])


@pytest.fixture()
def subscribers_write_token(scoped_token_factory):
    return scoped_token_factory(["subscribers:write"])


@pytest.fixture()
def analytics_read_token(scoped_token_factory):
    return scoped_token_factory(["analytics:read"])


@pytest.fixture()
def pages_read_token(scoped_token_factory):
    return scoped_token_factory(["pages:read"])


@pytest.fixture()
def admin_star_token(scoped_token_factory):
    return scoped_token_factory(["admin:*"])


@pytest.fixture()
def sample_published_post(db, admin_user):
    post = Post(
        title="Test Post",
        slug="test-post",
        body="# Hello\n\nContent",
        summary="Summary",
        published=True,
        published_at=utc_now(),
    )
    db.session.add(post)
    db.session.commit()
    return post


@pytest.fixture()
def sample_draft_post(db, admin_user):
    post = Post(
        title="Draft Post",
        slug="draft-post",
        body="# Draft\n\nContent",
        published=False,
    )
    db.session.add(post)
    db.session.commit()
    return post


class TestPostsReadScope:
    def test_posts_read_allowed(self, client, posts_read_token, sample_published_post):
        resp = client.get("/api/posts", headers={"X-API-Key": posts_read_token})
        assert resp.status_code == 200

    def test_subscribers_read_rejected(self, client, posts_read_token):
        resp = client.get("/api/subscribers", headers={"X-API-Key": posts_read_token})
        assert resp.status_code == 403
        assert "Missing scope" in resp.get_json()["error"]

    def test_subscribers_write_rejected(self, client, posts_read_token):
        resp = client.post(
            "/api/subscribers",
            headers={"X-API-Key": posts_read_token},
            json={"email": "x@x.com"},
        )
        assert resp.status_code == 403

    def test_analytics_read_rejected(self, client, posts_read_token):
        resp = client.get("/api/stats", headers={"X-API-Key": posts_read_token})
        assert resp.status_code == 403

    def test_posts_write_rejected(self, client, posts_read_token):
        resp = client.post(
            "/api/posts",
            headers={"X-API-Key": posts_read_token},
            json={"title": "X", "body": "Y"},
        )
        assert resp.status_code == 403


class TestPostsWriteScope:
    def test_posts_write_allowed(self, client, posts_write_token):
        resp = client.post(
            "/api/posts",
            headers={"X-API-Key": posts_write_token},
            json={"title": "New", "body": "Content"},
        )
        assert resp.status_code == 201

    def test_posts_read_rejected(self, client, posts_write_token):
        resp = client.get("/api/posts", headers={"X-API-Key": posts_write_token})
        assert resp.status_code == 403

    def test_subscribers_read_rejected(self, client, posts_write_token):
        resp = client.get("/api/subscribers", headers={"X-API-Key": posts_write_token})
        assert resp.status_code == 403

    def test_analytics_read_rejected(self, client, posts_write_token):
        resp = client.get("/api/stats", headers={"X-API-Key": posts_write_token})
        assert resp.status_code == 403


class TestSubscribersReadScope:
    def test_subscribers_read_allowed(self, client, subscribers_read_token):
        resp = client.get("/api/subscribers", headers={"X-API-Key": subscribers_read_token})
        assert resp.status_code == 200

    def test_posts_read_rejected(self, client, subscribers_read_token):
        resp = client.get("/api/posts", headers={"X-API-Key": subscribers_read_token})
        assert resp.status_code == 403

    def test_posts_write_rejected(self, client, subscribers_read_token):
        resp = client.post(
            "/api/posts",
            headers={"X-API-Key": subscribers_read_token},
            json={"title": "X", "body": "Y"},
        )
        assert resp.status_code == 403

    def test_analytics_read_rejected(self, client, subscribers_read_token):
        resp = client.get("/api/stats", headers={"X-API-Key": subscribers_read_token})
        assert resp.status_code == 403


class TestSubscribersWriteScope:
    def test_subscribers_write_allowed(self, client, subscribers_write_token):
        resp = client.post(
            "/api/subscribers",
            headers={"X-API-Key": subscribers_write_token},
            json={"email": "new@x.com"},
        )
        assert resp.status_code == 201

    def test_subscribers_read_rejected(self, client, subscribers_write_token):
        resp = client.get("/api/subscribers", headers={"X-API-Key": subscribers_write_token})
        assert resp.status_code == 403

    def test_posts_read_rejected(self, client, subscribers_write_token):
        resp = client.get("/api/posts", headers={"X-API-Key": subscribers_write_token})
        assert resp.status_code == 403

    def test_analytics_read_rejected(self, client, subscribers_write_token):
        resp = client.get("/api/stats", headers={"X-API-Key": subscribers_write_token})
        assert resp.status_code == 403


class TestAnalyticsReadScope:
    def test_analytics_read_allowed(self, client, analytics_read_token):
        resp = client.get("/api/stats", headers={"X-API-Key": analytics_read_token})
        assert resp.status_code == 200

    def test_posts_read_rejected(self, client, analytics_read_token):
        resp = client.get("/api/posts", headers={"X-API-Key": analytics_read_token})
        assert resp.status_code == 403

    def test_posts_write_rejected(self, client, analytics_read_token):
        resp = client.post(
            "/api/posts",
            headers={"X-API-Key": analytics_read_token},
            json={"title": "X", "body": "Y"},
        )
        assert resp.status_code == 403

    def test_subscribers_read_rejected(self, client, analytics_read_token):
        resp = client.get("/api/subscribers", headers={"X-API-Key": analytics_read_token})
        assert resp.status_code == 403


class TestAdminStarScope:
    def test_posts_read_rejected(self, client, admin_star_token, sample_published_post):
        resp = client.get("/api/posts", headers={"X-API-Key": admin_star_token})
        assert resp.status_code == 403

    def test_posts_write_rejected(self, client, admin_star_token):
        resp = client.post(
            "/api/posts",
            headers={"X-API-Key": admin_star_token},
            json={"title": "X", "body": "Y"},
        )
        assert resp.status_code == 403

    def test_subscribers_read_rejected(self, client, admin_star_token):
        resp = client.get("/api/subscribers", headers={"X-API-Key": admin_star_token})
        assert resp.status_code == 403

    def test_subscribers_write_rejected(self, client, admin_star_token):
        resp = client.post(
            "/api/subscribers",
            headers={"X-API-Key": admin_star_token},
            json={"email": "admin@x.com"},
        )
        assert resp.status_code == 403

    def test_analytics_read_rejected(self, client, admin_star_token):
        resp = client.get("/api/stats", headers={"X-API-Key": admin_star_token})
        assert resp.status_code == 403


class TestNoToken:
    def test_posts_read_requires_auth(self, client, sample_published_post):
        resp = client.get("/api/posts")
        assert resp.status_code == 401

    def test_subscribers_read_requires_auth(self, client):
        resp = client.get("/api/subscribers")
        assert resp.status_code == 401

    def test_stats_requires_auth(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 401
