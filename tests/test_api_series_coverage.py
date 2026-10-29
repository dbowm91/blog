"""Coverage tests for the scoped Series REST API."""

import hashlib
import os
import time

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")
os.environ["PAGE_VIEW_BUFFER_SIZE"] = "0"

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.extensions import db
from app.models import ApiToken, Post, PostSeries, Series
from app.utils import utc_now


@pytest.fixture(autouse=True)
def _disable_legacy_api_key(monkeypatch):
    from app.routes.api import auth as api_auth

    monkeypatch.setattr(api_auth, "API_KEY", "")


@pytest.fixture()
def token_factory(db):
    from app.routes.api import auth as api_auth

    primed = []

    def _create(scopes, raw="series-api-token"):
        token = ApiToken(
            name="series-token",
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            scopes=list(scopes),
        )
        db.session.add(token)
        db.session.commit()
        primed.append((token.id, api_auth._token_last_used_cache.get(token.id)))
        api_auth._token_last_used_cache[token.id] = time.monotonic()
        return raw

    yield _create

    for token_id, previous in primed:
        if previous is None:
            api_auth._token_last_used_cache.pop(token_id, None)
        else:
            api_auth._token_last_used_cache[token_id] = previous


@pytest.fixture()
def read_token(token_factory):
    return token_factory(["series:read"])


@pytest.fixture()
def write_token(token_factory):
    return token_factory(["series:write"])


@pytest.fixture()
def failing_commit(monkeypatch):
    def _install(exc):
        def _commit():
            raise exc

        monkeypatch.setattr(db.session, "commit", _commit)

    return _install


@pytest.fixture()
def series(db, admin_user):
    item = Series(name="Existing Series", slug="existing-series", description="Existing")
    db.session.add(item)
    db.session.commit()
    return item


@pytest.fixture()
def post(db, admin_user):
    item = Post(
        title="API Post",
        slug="api-post",
        body="Body of the API post",
        published=True,
        published_at=utc_now(),
    )
    db.session.add(item)
    db.session.commit()
    return item


@pytest.fixture()
def series_with_posts(db, admin_user):
    item = Series(name="Ordered Series", slug="ordered-series")
    first = Post(title="First Post", slug="first-post", body="First", published=True)
    second = Post(title="Second Post", slug="second-post", body="Second", published=True)
    db.session.add_all([item, first, second])
    db.session.flush()
    db.session.add_all(
        [
            PostSeries(series_id=item.id, post_id=first.id, order_index=0),
            PostSeries(series_id=item.id, post_id=second.id, order_index=1),
        ]
    )
    db.session.commit()
    return item, first, second


class TestSeriesScopes:
    def test_list_requires_api_key(self, client, db, admin_user):
        response = client.get("/api/series")
        assert response.status_code == 401
        assert "API key" in response.get_json()["error"]

    def test_read_scope_cannot_write(self, client, read_token):
        response = client.post(
            "/api/series",
            headers={"X-API-Key": read_token},
            json={"name": "Denied"},
        )
        assert response.status_code == 403
        assert "series:write" in response.get_json()["error"]

    def test_write_scope_cannot_read(self, client, write_token):
        response = client.get("/api/series", headers={"X-API-Key": write_token})
        assert response.status_code == 403
        assert "series:read" in response.get_json()["error"]

    def test_series_wildcard_grants_read_and_write(self, client, token_factory):
        token = token_factory(["series:*"])
        headers = {"X-API-Key": token}
        assert client.get("/api/series", headers=headers).status_code == 200
        created = client.post("/api/series", headers=headers, json={"name": "Wildcard Series"})
        assert created.status_code == 201

    def test_unrelated_scope_is_rejected(self, client, token_factory):
        token = token_factory(["posts:read"])
        response = client.get("/api/series", headers={"X-API-Key": token})
        assert response.status_code == 403


class TestSeriesRead:
    def test_list_includes_posts(self, client, read_token, series, post):
        db.session.add(PostSeries(series_id=series.id, post_id=post.id, order_index=0))
        db.session.commit()

        response = client.get("/api/series?include_posts=true", headers={"X-API-Key": read_token})
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        posts = data["series"][0]["posts"]
        assert len(posts) == 1
        assert posts[0]["id"] == post.id
        assert posts[0]["slug"] == "api-post"
        assert posts[0]["order_index"] == 0

    def test_list_omits_posts_by_default(self, client, read_token, series):
        response = client.get("/api/series", headers={"X-API-Key": read_token})
        assert response.status_code == 200
        assert "posts" not in response.get_json()["series"][0]

    def test_list_caps_per_page(self, client, read_token, series):
        response = client.get("/api/series?per_page=500", headers={"X-API-Key": read_token})
        assert response.status_code == 200
        assert response.get_json()["per_page"] == 100

    def test_list_paginates(self, client, read_token, db, admin_user):
        for index in range(3):
            db.session.add(Series(name=f"Page Series {index}", slug=f"page-series-{index}"))
        db.session.commit()

        response = client.get("/api/series?page=2&per_page=1", headers={"X-API-Key": read_token})
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 3
        assert data["page"] == 2
        assert data["per_page"] == 1
        assert len(data["series"]) == 1

    def test_get_series_includes_posts(self, client, read_token, series, post):
        db.session.add(PostSeries(series_id=series.id, post_id=post.id, order_index=3))
        db.session.commit()

        response = client.get(
            f"/api/series/{series.id}?include_posts=1", headers={"X-API-Key": read_token}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Existing Series"
        assert data["posts"][0]["title"] == "API Post"
        assert data["posts"][0]["order_index"] == 3

    def test_get_series_without_posts(self, client, read_token, series):
        response = client.get(f"/api/series/{series.id}", headers={"X-API-Key": read_token})
        assert response.status_code == 200
        assert "posts" not in response.get_json()

    def test_get_unknown_series(self, client, read_token, db, admin_user):
        response = client.get("/api/series/999999", headers={"X-API-Key": read_token})
        assert response.status_code == 404
        assert response.get_json()["error"] == "Series not found"


class TestSeriesCreate:
    def test_create_rejects_missing_body(self, client, write_token):
        response = client.post(
            "/api/series",
            headers={"X-API-Key": write_token},
            data="null",
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "Invalid JSON body"

    def test_create_requires_name(self, client, write_token):
        response = client.post("/api/series", headers={"X-API-Key": write_token}, json={})
        assert response.status_code == 400
        assert response.get_json()["error"] == "name is required"

    def test_create_rejects_non_string_name(self, client, write_token):
        response = client.post(
            "/api/series", headers={"X-API-Key": write_token}, json={"name": 123}
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "name must be a string"

    def test_create_rejects_long_description(self, client, write_token):
        response = client.post(
            "/api/series",
            headers={"X-API-Key": write_token},
            json={"name": "Long Description", "description": "x" * 501},
        )
        assert response.status_code == 400
        assert "description" in response.get_json()["error"]

    def test_create_uses_explicit_slug(self, client, write_token):
        response = client.post(
            "/api/series",
            headers={"X-API-Key": write_token},
            json={"name": "Custom Slug", "slug": "My Custom Slug!"},
        )
        assert response.status_code == 201
        assert response.get_json()["slug"] == "my-custom-slug"

    def test_create_rejects_non_string_slug(self, client, write_token):
        response = client.post(
            "/api/series",
            headers={"X-API-Key": write_token},
            json={"name": "Bad Slug", "slug": 123},
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "slug must be a string"

    def test_create_stores_description(self, client, write_token):
        response = client.post(
            "/api/series",
            headers={"X-API-Key": write_token},
            json={"name": "Described Series", "description": "A described series"},
        )
        assert response.status_code == 201
        assert response.get_json()["description"] == "A described series"

    def test_create_rejects_duplicate_slug(self, client, write_token, series):
        response = client.post(
            "/api/series",
            headers={"X-API-Key": write_token},
            json={"name": "Existing Series"},
        )
        assert response.status_code == 409
        assert "already exists" in response.get_json()["error"]

    def test_create_handles_integrity_error(self, client, write_token, failing_commit):
        failing_commit(IntegrityError("INSERT INTO series", {}, Exception("constraint")))
        response = client.post(
            "/api/series", headers={"X-API-Key": write_token}, json={"name": "Boom"}
        )
        assert response.status_code == 409
        assert "constraint" in response.get_json()["error"]

    def test_create_handles_operational_error(self, client, write_token, failing_commit):
        failing_commit(OperationalError("INSERT INTO series", {}, Exception("offline")))
        response = client.post(
            "/api/series", headers={"X-API-Key": write_token}, json={"name": "Boom"}
        )
        assert response.status_code == 500
        assert response.get_json()["error"] == "Database operational error"


class TestSeriesUpdate:
    def test_update_unknown_series(self, client, write_token, db, admin_user):
        response = client.put(
            "/api/series/999999", headers={"X-API-Key": write_token}, json={"name": "Nope"}
        )
        assert response.status_code == 404
        assert response.get_json()["error"] == "Series not found"

    def test_update_rejects_missing_body(self, client, write_token, series):
        response = client.put(
            f"/api/series/{series.id}",
            headers={"X-API-Key": write_token},
            data="null",
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "Invalid JSON body"

    def test_update_rejects_invalid_name(self, client, write_token, series):
        response = client.put(
            f"/api/series/{series.id}", headers={"X-API-Key": write_token}, json={"name": 5}
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "name must be a string"

    def test_update_rejects_long_description(self, client, write_token, series):
        response = client.put(
            f"/api/series/{series.id}",
            headers={"X-API-Key": write_token},
            json={"description": "x" * 501},
        )
        assert response.status_code == 400
        assert "description" in response.get_json()["error"]

    def test_update_rejects_non_string_slug(self, client, write_token, series):
        response = client.put(
            f"/api/series/{series.id}", headers={"X-API-Key": write_token}, json={"slug": 12}
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "slug must be a string"

    def test_update_changes_slug(self, client, write_token, series):
        response = client.put(
            f"/api/series/{series.id}",
            headers={"X-API-Key": write_token},
            json={"slug": "Renamed Series"},
        )
        assert response.status_code == 200
        assert response.get_json()["slug"] == "renamed-series"

    def test_update_keeps_unchanged_slug(self, client, write_token, series):
        response = client.put(
            f"/api/series/{series.id}",
            headers={"X-API-Key": write_token},
            json={"slug": series.slug},
        )
        assert response.status_code == 200
        assert response.get_json()["slug"] == series.slug

    def test_update_sets_description(self, client, write_token, series):
        response = client.put(
            f"/api/series/{series.id}",
            headers={"X-API-Key": write_token},
            json={"description": "An updated description"},
        )
        assert response.status_code == 200
        assert response.get_json()["description"] == "An updated description"

    def test_update_rejects_duplicate_slug(self, client, write_token, series, db, admin_user):
        db.session.add(Series(name="Other Series", slug="other-series"))
        db.session.commit()

        response = client.put(
            f"/api/series/{series.id}",
            headers={"X-API-Key": write_token},
            json={"slug": "Other Series"},
        )
        assert response.status_code == 409
        assert "already exists" in response.get_json()["error"]

    def test_update_handles_integrity_error(self, client, write_token, series, failing_commit):
        failing_commit(IntegrityError("UPDATE series", {}, Exception("constraint")))
        response = client.put(
            f"/api/series/{series.id}", headers={"X-API-Key": write_token}, json={"name": "Boom"}
        )
        assert response.status_code == 409
        assert "constraint" in response.get_json()["error"]

    def test_update_handles_operational_error(self, client, write_token, series, failing_commit):
        failing_commit(OperationalError("UPDATE series", {}, Exception("offline")))
        response = client.put(
            f"/api/series/{series.id}", headers={"X-API-Key": write_token}, json={"name": "Boom"}
        )
        assert response.status_code == 500
        assert response.get_json()["error"] == "Database operational error"


class TestSeriesDelete:
    def test_delete_unknown_series(self, client, write_token, db, admin_user):
        response = client.delete("/api/series/999999", headers={"X-API-Key": write_token})
        assert response.status_code == 404
        assert response.get_json()["error"] == "Series not found"

    def test_delete_removes_post_links(self, client, write_token, series_with_posts):
        item, first, _ = series_with_posts
        response = client.delete(f"/api/series/{item.id}", headers={"X-API-Key": write_token})
        assert response.status_code == 200
        assert "deleted successfully" in response.get_json()["message"]

        links = (
            db.session.execute(select(PostSeries).where(PostSeries.series_id == item.id))
            .scalars()
            .all()
        )
        assert links == []

    def test_delete_handles_integrity_error(self, client, write_token, series, failing_commit):
        failing_commit(IntegrityError("DELETE FROM series", {}, Exception("constraint")))
        response = client.delete(f"/api/series/{series.id}", headers={"X-API-Key": write_token})
        assert response.status_code == 409
        assert response.get_json()["error"] == "Database constraint violation"

    def test_delete_handles_operational_error(self, client, write_token, series, failing_commit):
        failing_commit(OperationalError("DELETE FROM series", {}, Exception("offline")))
        response = client.delete(f"/api/series/{series.id}", headers={"X-API-Key": write_token})
        assert response.status_code == 500
        assert response.get_json()["error"] == "Database operational error"


class TestSeriesPosts:
    def test_add_post_to_unknown_series(self, client, write_token, db, admin_user):
        response = client.post(
            "/api/series/999999/posts", headers={"X-API-Key": write_token}, json={"post_id": 1}
        )
        assert response.status_code == 404
        assert response.get_json()["error"] == "Series not found"

    def test_add_post_rejects_missing_body(self, client, write_token, series):
        response = client.post(
            f"/api/series/{series.id}/posts",
            headers={"X-API-Key": write_token},
            data="null",
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "Invalid JSON body"

    def test_add_post_requires_post_id(self, client, write_token, series):
        response = client.post(
            f"/api/series/{series.id}/posts", headers={"X-API-Key": write_token}, json={}
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "post_id is required"

    def test_add_post_rejects_non_integer_post_id(self, client, write_token, series):
        response = client.post(
            f"/api/series/{series.id}/posts",
            headers={"X-API-Key": write_token},
            json={"post_id": "abc"},
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "post_id must be an integer"

    def test_add_post_rejects_post_id_below_one(self, client, write_token, series):
        response = client.post(
            f"/api/series/{series.id}/posts",
            headers={"X-API-Key": write_token},
            json={"post_id": -1},
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "post_id must be at least 1"

    def test_add_post_to_unknown_post(self, client, write_token, series):
        response = client.post(
            f"/api/series/{series.id}/posts",
            headers={"X-API-Key": write_token},
            json={"post_id": 999999},
        )
        assert response.status_code == 404
        assert response.get_json()["error"] == "Post not found"

    def test_add_post_rejects_duplicate_membership(self, client, write_token, series_with_posts):
        item, first, _ = series_with_posts
        response = client.post(
            f"/api/series/{item.id}/posts",
            headers={"X-API-Key": write_token},
            json={"post_id": first.id},
        )
        assert response.status_code == 409
        assert response.get_json()["error"] == "Post is already in this series"

    def test_add_post_rejects_negative_order_index(self, client, write_token, series, post):
        response = client.post(
            f"/api/series/{series.id}/posts",
            headers={"X-API-Key": write_token},
            json={"post_id": post.id, "order_index": -1},
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "order_index must be at least 0"

    def test_add_post_appends_after_existing_entries(self, client, write_token, series_with_posts):
        item, first, second = series_with_posts
        extra = Post(title="Third Post", slug="third-post", body="Third", published=True)
        db.session.add(extra)
        db.session.commit()

        response = client.post(
            f"/api/series/{item.id}/posts",
            headers={"X-API-Key": write_token},
            json={"post_id": extra.id},
        )
        assert response.status_code == 201

        link = db.session.execute(
            select(PostSeries).where(
                PostSeries.series_id == item.id, PostSeries.post_id == extra.id
            )
        ).scalar_one()
        assert link.order_index == 2

    def test_add_post_accepts_explicit_order_index(self, client, write_token, series, post):
        response = client.post(
            f"/api/series/{series.id}/posts",
            headers={"X-API-Key": write_token},
            json={"post_id": post.id, "order_index": 5},
        )
        assert response.status_code == 201

        link = db.session.execute(
            select(PostSeries).where(
                PostSeries.series_id == series.id, PostSeries.post_id == post.id
            )
        ).scalar_one()
        assert link.order_index == 5

    def test_add_post_handles_integrity_error(
        self, client, write_token, series, post, failing_commit
    ):
        failing_commit(IntegrityError("INSERT INTO post_series", {}, Exception("constraint")))
        response = client.post(
            f"/api/series/{series.id}/posts",
            headers={"X-API-Key": write_token},
            json={"post_id": post.id},
        )
        assert response.status_code == 409
        assert response.get_json()["error"] == "Database constraint violation"

    def test_add_post_handles_operational_error(
        self, client, write_token, series, post, failing_commit
    ):
        failing_commit(OperationalError("INSERT INTO post_series", {}, Exception("offline")))
        response = client.post(
            f"/api/series/{series.id}/posts",
            headers={"X-API-Key": write_token},
            json={"post_id": post.id},
        )
        assert response.status_code == 500
        assert response.get_json()["error"] == "Database error"

    def test_remove_post_from_unknown_series(self, client, write_token, db, admin_user):
        response = client.delete("/api/series/999999/posts/1", headers={"X-API-Key": write_token})
        assert response.status_code == 404
        assert response.get_json()["error"] == "Series not found"

    def test_remove_post_not_in_series(self, client, write_token, series, post):
        response = client.delete(
            f"/api/series/{series.id}/posts/{post.id}", headers={"X-API-Key": write_token}
        )
        assert response.status_code == 404
        assert response.get_json()["error"] == "Post not found in this series"

    def test_remove_post_from_series(self, client, write_token, series_with_posts):
        item, first, _ = series_with_posts
        response = client.delete(
            f"/api/series/{item.id}/posts/{first.id}", headers={"X-API-Key": write_token}
        )
        assert response.status_code == 200
        assert response.get_json()["message"] == "Post removed from series"

        link = db.session.execute(
            select(PostSeries).where(
                PostSeries.series_id == item.id, PostSeries.post_id == first.id
            )
        ).scalar_one_or_none()
        assert link is None

    def test_remove_post_handles_operational_error(
        self, client, write_token, series_with_posts, failing_commit
    ):
        item, first, _ = series_with_posts
        failing_commit(OperationalError("DELETE FROM post_series", {}, Exception("offline")))
        response = client.delete(
            f"/api/series/{item.id}/posts/{first.id}", headers={"X-API-Key": write_token}
        )
        assert response.status_code == 500
        assert response.get_json()["error"] == "Database error"


class TestSeriesReorder:
    def test_reorder_unknown_series(self, client, write_token, db, admin_user):
        response = client.post(
            "/api/series/999999/reorder",
            headers={"X-API-Key": write_token},
            json={"order": [{"post_id": 1, "order_index": 0}]},
        )
        assert response.status_code == 404
        assert response.get_json()["error"] == "Series not found"

    def test_reorder_rejects_missing_body(self, client, write_token, series):
        response = client.post(
            f"/api/series/{series.id}/reorder",
            headers={"X-API-Key": write_token},
            data="null",
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "Invalid JSON body"

    def test_reorder_requires_order(self, client, write_token, series):
        response = client.post(
            f"/api/series/{series.id}/reorder", headers={"X-API-Key": write_token}, json={}
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "order is required"

    def test_reorder_rejects_empty_order(self, client, write_token, series):
        response = client.post(
            f"/api/series/{series.id}/reorder",
            headers={"X-API-Key": write_token},
            json={"order": []},
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "order is required"

    def test_reorder_rejects_non_list_order(self, client, write_token, series):
        response = client.post(
            f"/api/series/{series.id}/reorder",
            headers={"X-API-Key": write_token},
            json={"order": "not-a-list"},
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "order must be a list"

    def test_reorder_rejects_oversized_order(self, client, write_token, series):
        order = [{"post_id": 1, "order_index": index} for index in range(501)]
        response = client.post(
            f"/api/series/{series.id}/reorder",
            headers={"X-API-Key": write_token},
            json={"order": order},
        )
        assert response.status_code == 400
        assert "order" in response.get_json()["error"]

    def test_reorder_rejects_non_object_item(self, client, write_token, series):
        response = client.post(
            f"/api/series/{series.id}/reorder",
            headers={"X-API-Key": write_token},
            json={"order": ["not-an-object"]},
        )
        assert response.status_code == 400
        assert "objects" in response.get_json()["error"]

    def test_reorder_requires_item_keys(self, client, write_token, series):
        response = client.post(
            f"/api/series/{series.id}/reorder",
            headers={"X-API-Key": write_token},
            json={"order": [{"post_id": 1}]},
        )
        assert response.status_code == 400
        assert "post_id and order_index" in response.get_json()["error"]

    def test_reorder_rejects_invalid_post_id(self, client, write_token, series):
        response = client.post(
            f"/api/series/{series.id}/reorder",
            headers={"X-API-Key": write_token},
            json={"order": [{"post_id": "abc", "order_index": 0}]},
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "post_id must be an integer"

    def test_reorder_rejects_negative_order_index(self, client, write_token, series):
        response = client.post(
            f"/api/series/{series.id}/reorder",
            headers={"X-API-Key": write_token},
            json={"order": [{"post_id": 1, "order_index": -2}]},
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "order_index must be at least 0"

    def test_reorder_updates_order_index(self, client, write_token, series_with_posts):
        item, first, second = series_with_posts
        response = client.post(
            f"/api/series/{item.id}/reorder",
            headers={"X-API-Key": write_token},
            json={
                "order": [
                    {"post_id": second.id, "order_index": 0},
                    {"post_id": first.id, "order_index": 1},
                ]
            },
        )
        assert response.status_code == 200
        assert response.get_json()["message"] == "Series posts reordered"

        links = (
            db.session.execute(
                select(PostSeries)
                .where(PostSeries.series_id == item.id)
                .order_by(PostSeries.order_index)
            )
            .scalars()
            .all()
        )
        assert [link.post_id for link in links] == [second.id, first.id]

    def test_reorder_ignores_posts_outside_the_series(self, client, write_token, series_with_posts):
        item, first, _ = series_with_posts
        response = client.post(
            f"/api/series/{item.id}/reorder",
            headers={"X-API-Key": write_token},
            json={"order": [{"post_id": 999999, "order_index": 0}]},
        )
        assert response.status_code == 200

    def test_reorder_handles_database_error(self, client, write_token, series, failing_commit):
        failing_commit(IntegrityError("UPDATE post_series", {}, Exception("constraint")))
        response = client.post(
            f"/api/series/{series.id}/reorder",
            headers={"X-API-Key": write_token},
            json={"order": [{"post_id": 1, "order_index": 0}]},
        )
        assert response.status_code == 500
        assert response.get_json()["error"] == "Database error"
