"""Tests for API authentication and authorization."""

import os
import hashlib

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")
os.environ["API_KEY"] = "test-api-key-12345"
os.environ["PAGE_VIEW_BUFFER_SIZE"] = "0"

from unittest.mock import patch

import pytest
from app.models import ApiToken, Post
from app.utils import utc_now


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


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
def make_scoped_token(db):
    def _create(raw_token: str, scopes: list[str], name: str = "test-token"):
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
def expired_token(db):
    token = ApiToken(
        name="expired-token",
        token_hash=_hash_token("expired-token-abc"),
        scopes=["posts:read"],
        expires_at=utc_now(),
    )
    db.session.add(token)
    db.session.commit()
    return "expired-token-abc"


@pytest.fixture()
def revoked_token(db):
    token = ApiToken(
        name="revoked-token",
        token_hash=_hash_token("revoked-token-abc"),
        scopes=["posts:read"],
        revoked_at=utc_now(),
    )
    db.session.add(token)
    db.session.commit()
    return "revoked-token-abc"


class TestNoApiKey:
    def test_returns_401(self, client):
        resp = client.get("/api/posts")
        assert resp.status_code == 401
        assert "Invalid or missing API key" in resp.get_json()["error"]


class TestInvalidApiKey:
    @patch("app.routes.api.auth.API_KEY", "test-api-key-12345")
    def test_wrong_key_returns_401(self, client):
        resp = client.get("/api/posts", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401


class TestLegacyApiKey:
    @patch("app.routes.api.auth.API_KEY", "test-api-key-12345")
    def test_grants_all_scopes(self, client, sample_published_post):
        resp = client.get("/api/posts", headers={"X-API-Key": "test-api-key-12345"})
        assert resp.status_code == 200

    @patch("app.routes.api.auth.API_KEY", "test-api-key-12345")
    def test_can_write_posts(self, client):
        resp = client.post(
            "/api/posts",
            headers={"X-API-Key": "test-api-key-12345"},
            json={"title": "New", "body": "Content"},
        )
        assert resp.status_code == 201

    @patch("app.routes.api.auth.API_KEY", "test-api-key-12345")
    def test_can_read_subscribers(self, client):
        resp = client.get("/api/subscribers", headers={"X-API-Key": "test-api-key-12345"})
        assert resp.status_code == 200


class TestScopedTokenExactMatch:
    def test_matching_scope_succeeds(self, client, make_scoped_token, sample_published_post):
        token = make_scoped_token("exact-match-token", ["posts:read"])
        resp = client.get("/api/posts", headers={"X-API-Key": token})
        assert resp.status_code == 200

    def test_missing_scope_returns_403(self, client, make_scoped_token):
        token = make_scoped_token("no-scope-token", ["posts:read"])
        resp = client.get("/api/subscribers", headers={"X-API-Key": token})
        assert resp.status_code == 403
        assert "Missing scope" in resp.get_json()["error"]

    def test_wrong_action_returns_403(self, client, make_scoped_token):
        token = make_scoped_token("write-only-token", ["posts:write"])
        resp = client.get("/api/posts", headers={"X-API-Key": token})
        assert resp.status_code == 403


class TestScopedTokenAdminWildcard:
    def test_admin_star_grants_posts_read(self, client, make_scoped_token, sample_published_post):
        token = make_scoped_token("admin-star-token", ["admin:*"])
        resp = client.get("/api/posts", headers={"X-API-Key": token})
        assert resp.status_code == 200

    def test_admin_star_grants_posts_write(self, client, make_scoped_token):
        token = make_scoped_token("admin-star-w-token", ["admin:*"])
        resp = client.post(
            "/api/posts",
            headers={"X-API-Key": token},
            json={"title": "X", "body": "Y"},
        )
        assert resp.status_code == 201

    def test_admin_star_grants_subscribers(self, client, make_scoped_token):
        token = make_scoped_token("admin-star-s-token", ["admin:*"])
        resp = client.get("/api/subscribers", headers={"X-API-Key": token})
        assert resp.status_code == 200

    def test_admin_star_grants_analytics(self, client, make_scoped_token):
        token = make_scoped_token("admin-star-a-token", ["admin:*"])
        resp = client.get("/api/stats", headers={"X-API-Key": token})
        assert resp.status_code == 200

    def test_admin_star_grants_tags(self, client, make_scoped_token):
        token = make_scoped_token("admin-star-t-token", ["admin:*"])
        resp = client.get("/api/tags", headers={"X-API-Key": token})
        assert resp.status_code == 200

    def test_admin_star_grants_pages(self, client, make_scoped_token):
        token = make_scoped_token("admin-star-p-token", ["admin:*"])
        resp = client.get("/api/pages", headers={"X-API-Key": token})
        assert resp.status_code == 200

    def test_admin_star_grants_series(self, client, make_scoped_token):
        token = make_scoped_token("admin-star-sr-token", ["admin:*"])
        resp = client.get("/api/series", headers={"X-API-Key": token})
        assert resp.status_code == 200


class TestCategoryWildcardToken:
    def test_posts_wildcard_grants_read(self, client, make_scoped_token, sample_published_post):
        token = make_scoped_token("posts-wildcard-token", ["posts:*"])
        resp = client.get("/api/posts", headers={"X-API-Key": token})
        assert resp.status_code == 200

    def test_posts_wildcard_grants_write(self, client, make_scoped_token):
        token = make_scoped_token("posts-wildcard-w-token", ["posts:*"])
        resp = client.post(
            "/api/posts",
            headers={"X-API-Key": token},
            json={"title": "X", "body": "Y"},
        )
        assert resp.status_code == 201

    def test_posts_wildcard_rejects_subscribers(self, client, make_scoped_token):
        token = make_scoped_token("posts-wildcard-s-token", ["posts:*"])
        resp = client.get("/api/subscribers", headers={"X-API-Key": token})
        assert resp.status_code == 403

    def test_posts_wildcard_rejects_analytics(self, client, make_scoped_token):
        token = make_scoped_token("posts-wildcard-a-token", ["posts:*"])
        resp = client.get("/api/stats", headers={"X-API-Key": token})
        assert resp.status_code == 403

    def test_subscribers_wildcard_grants_read(self, client, make_scoped_token):
        token = make_scoped_token("sub-wildcard-token", ["subscribers:*"])
        resp = client.get("/api/subscribers", headers={"X-API-Key": token})
        assert resp.status_code == 200

    def test_tags_wildcard_grants_read(self, client, make_scoped_token):
        token = make_scoped_token("tags-wildcard-token", ["tags:*"])
        resp = client.get("/api/tags", headers={"X-API-Key": token})
        assert resp.status_code == 200

    def test_pages_wildcard_grants_read(self, client, make_scoped_token):
        token = make_scoped_token("pages-wildcard-token", ["pages:*"])
        resp = client.get("/api/pages", headers={"X-API-Key": token})
        assert resp.status_code == 200

    def test_series_wildcard_grants_read(self, client, make_scoped_token):
        token = make_scoped_token("series-wildcard-token", ["series:*"])
        resp = client.get("/api/series", headers={"X-API-Key": token})
        assert resp.status_code == 200


class TestTokenExpiryAndRevocation:
    def test_expired_token_returns_401(self, client, expired_token):
        resp = client.get("/api/posts", headers={"X-API-Key": expired_token})
        assert resp.status_code == 401

    def test_revoked_token_returns_401(self, client, revoked_token):
        resp = client.get("/api/posts", headers={"X-API-Key": revoked_token})
        assert resp.status_code == 401


class TestTokenLastUsedAt:
    def test_updates_on_use(self, client, make_scoped_token, db):
        raw_token = "last-used-token"
        token = ApiToken(
            name="last-used-test",
            token_hash=_hash_token(raw_token),
            scopes=["posts:read"],
        )
        db.session.add(token)
        db.session.commit()

        assert token.last_used_at is None

        client.get("/api/posts", headers={"X-API-Key": raw_token})

        db.session.refresh(token)
        assert token.last_used_at is not None
