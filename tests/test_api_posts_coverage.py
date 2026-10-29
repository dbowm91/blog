"""Coverage tests for the posts REST API endpoints."""

import contextlib
import hashlib
import logging
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")
os.environ["PAGE_VIEW_BUFFER_SIZE"] = "0"

from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402
from flask import request  # noqa: E402
from sqlalchemy.exc import IntegrityError, OperationalError  # noqa: E402

from app.extensions import db  # noqa: E402
from app.models import ApiToken, Post, User  # noqa: E402
from app.routes.api.posts import _author_scope_error, _parse_author_id  # noqa: E402

RAW_TOKEN = "posts-coverage-token"
LEGACY_KEY = "poststest-key"


@pytest.fixture()
def api_token(db):
    token = ApiToken(
        name="posts-coverage",
        token_hash=hashlib.sha256(RAW_TOKEN.encode()).hexdigest(),
        scopes=["admin:*"],
    )
    db.session.add(token)
    db.session.commit()
    return RAW_TOKEN


@pytest.fixture()
def auth_headers(api_token):
    return {"X-API-Key": RAW_TOKEN}


@pytest.fixture()
def legacy_headers():
    return {"X-API-Key": LEGACY_KEY}


@contextlib.contextmanager
def legacy_api_key():
    """Authenticate with the legacy API key, which never writes to the database."""
    with patch("app.routes.api.auth.API_KEY", LEGACY_KEY):
        yield


class TestPostReading:
    def test_posts_are_listed(self, client, auth_headers, db, admin_user):
        db.session.add(Post(title="Listed", slug="listed", body="b", published=True))
        db.session.commit()

        response = client.get("/api/posts", headers=auth_headers)

        assert response.status_code == 200
        payload = response.get_json()
        assert [post["slug"] for post in payload["posts"]] == ["listed"]
        assert payload["total"] == 1

    def test_the_listing_can_be_filtered_by_publication(self, client, auth_headers, db, admin_user):
        db.session.add(Post(title="Published", slug="published", body="b", published=True))
        db.session.add(Post(title="Draft", slug="draft", body="b", published=False))
        db.session.commit()

        response = client.get("/api/posts?published=false", headers=auth_headers)

        assert response.status_code == 200
        payload = response.get_json()
        assert [post["slug"] for post in payload["posts"]] == ["draft"]

    def test_a_single_post_is_returned(self, client, auth_headers, db, admin_user):
        author = User(username="writer", email="writer@example.com")
        author.set_password(os.environ["ADMIN_PASSWORD"])
        db.session.add(author)
        db.session.flush()
        post = Post(title="Single", slug="single", body="b", published=True, author_id=author.id)
        db.session.add(post)
        db.session.commit()

        response = client.get(f"/api/posts/{post.id}", headers=auth_headers)

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["slug"] == "single"
        assert payload["author"]["username"] == "writer"

    def test_an_unknown_post_is_not_found(self, client, auth_headers):
        response = client.get("/api/posts/999999", headers=auth_headers)

        assert response.status_code == 404
        assert response.get_json()["error"] == "Post not found"


class TestCreatePostValidation:
    def test_json_body_must_not_be_null(self, client, auth_headers):
        response = client.post(
            "/api/posts",
            headers=auth_headers,
            data="null",
            content_type="application/json",
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "Invalid JSON body"

    def test_title_is_required(self, client, auth_headers):
        response = client.post("/api/posts", headers=auth_headers, json={"body": "b"})

        assert response.status_code == 400
        assert response.get_json()["error"] == "title is required"

    def test_title_exceeds_the_limit(self, client, auth_headers):
        response = client.post(
            "/api/posts",
            headers=auth_headers,
            json={"title": "t" * 201, "body": "b"},
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "title exceeds 200 chars"

    def test_body_exceeds_the_limit(self, client, auth_headers):
        response = client.post(
            "/api/posts",
            headers=auth_headers,
            json={"title": "t", "body": "b" * 50001},
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "body exceeds 50000 chars"

    def test_slug_exceeds_the_limit(self, client, auth_headers):
        response = client.post(
            "/api/posts",
            headers=auth_headers,
            json={"title": "t", "body": "b", "slug": "s" * 101},
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "slug exceeds 100 chars"

    def test_summary_exceeds_the_limit(self, client, auth_headers):
        response = client.post(
            "/api/posts",
            headers=auth_headers,
            json={"title": "t", "body": "b", "summary": "s" * 501},
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "summary exceeds 500 chars"

    def test_image_exceeds_the_limit(self, client, auth_headers):
        response = client.post(
            "/api/posts",
            headers=auth_headers,
            json={"title": "t", "body": "b", "image": "i" * 201},
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "image exceeds 200 chars"

    def test_published_must_be_a_boolean(self, client, auth_headers):
        response = client.post(
            "/api/posts",
            headers=auth_headers,
            json={"title": "t", "body": "b", "published": "sometimes"},
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "published must be a boolean"

    def test_body_is_required(self, client, auth_headers):
        response = client.post("/api/posts", headers=auth_headers, json={"title": "t"})

        assert response.status_code == 400
        assert response.get_json()["error"] == "body is required"

    def test_a_supplied_slug_is_kept(self, client, auth_headers, db):
        response = client.post(
            "/api/posts",
            headers=auth_headers,
            json={"title": "Slugged", "body": "b", "slug": "custom-slug"},
        )

        assert response.status_code == 201
        assert response.get_json()["slug"] == "custom-slug"

    def test_a_summary_and_an_image_are_accepted(self, client, auth_headers):
        response = client.post(
            "/api/posts",
            headers=auth_headers,
            json={"title": "t", "body": "b", "summary": "s", "image": "i.png"},
        )

        assert response.status_code == 201
        payload = response.get_json()
        assert payload["summary"] == "s"
        assert payload["image"] == "i.png"


class TestCreatePostAuthor:
    def test_author_id_must_be_an_integer(self, client, auth_headers):
        response = client.post(
            "/api/posts",
            headers=auth_headers,
            json={"title": "t", "body": "b", "author_id": "abc"},
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "author_id must be an integer"

    def test_author_id_must_exist(self, client, auth_headers):
        response = client.post(
            "/api/posts",
            headers=auth_headers,
            json={"title": "t", "body": "b", "author_id": 999999},
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "Unknown author"

    def test_a_null_author_id_is_accepted(self, client, auth_headers, db):
        response = client.post(
            "/api/posts",
            headers=auth_headers,
            json={"title": "t", "body": "b", "author_id": None},
        )

        assert response.status_code == 201
        assert response.get_json()["author"]["username"] is None

    def test_the_write_scope_is_required_to_set_the_author(self, client, auth_headers):
        with patch(
            "app.routes.api.posts._author_scope_error",
            return_value="Missing scope: posts:write",
        ):
            response = client.post(
                "/api/posts",
                headers=auth_headers,
                json={"title": "t", "body": "b", "author_id": 1},
            )

        assert response.status_code == 403
        assert response.get_json()["error"] == "Missing scope: posts:write"

    def test_the_scope_helper_reports_a_read_only_token(self, app):
        with app.test_request_context("/api/posts"):
            setattr(request, "api_auth", {"scopes": ["posts:read"]})
            assert _author_scope_error() == "Missing scope: posts:write"

            setattr(request, "api_auth", {"scopes": ["posts:write"]})
            assert _author_scope_error() is None

    def test_the_scope_helper_reports_a_missing_auth_context(self, app):
        with app.test_request_context("/api/posts"):
            assert _author_scope_error() == "Missing scope: posts:write"

    def test_the_author_parser_validates_its_input(self, db):
        assert _parse_author_id(None) == (None, None)
        assert _parse_author_id(True) == (None, "author_id must be an integer")
        assert _parse_author_id("7") == (None, "author_id must be an integer")
        assert _parse_author_id(999999) == (None, "Unknown author")


class TestCreatePostFailures:
    def test_the_search_index_failure_is_reported(self, client, auth_headers):
        with patch("app.search.sync_fts", return_value=False):
            response = client.post(
                "/api/posts",
                headers=auth_headers,
                json={"title": "t", "body": "b"},
            )

        assert response.status_code == 503
        assert response.get_json()["error"] == "Search index unavailable"

    def test_a_duplicate_slug_is_a_conflict(self, client, legacy_headers):
        with legacy_api_key():
            with patch.object(
                db.session,
                "commit",
                side_effect=IntegrityError("INSERT", {}, Exception("duplicate")),
            ):
                response = client.post(
                    "/api/posts",
                    headers=legacy_headers,
                    json={"title": "t", "body": "b"},
                )

        assert response.status_code == 409
        assert response.get_json()["error"] == "Duplicate slug or database constraint violation"

    def test_a_database_failure_is_a_server_error(self, client, legacy_headers):
        with legacy_api_key():
            with patch.object(
                db.session,
                "commit",
                side_effect=OperationalError("SELECT 1", {}, Exception("locked")),
            ):
                response = client.post(
                    "/api/posts",
                    headers=legacy_headers,
                    json={"title": "t", "body": "b"},
                )

        assert response.status_code == 500
        assert response.get_json()["error"] == "Database operational error"

    def test_a_created_post_carries_its_tags(self, client, auth_headers, db):
        response = client.post(
            "/api/posts",
            headers=auth_headers,
            json={"title": "Tagged", "body": "b", "tags": ["Alpha", "Beta"]},
        )

        assert response.status_code == 201
        assert set(response.get_json()["tags"]) == {"Alpha", "Beta"}


class TestUpdatePost:
    def test_an_unknown_post_is_not_found(self, client, auth_headers):
        response = client.put("/api/posts/999999", headers=auth_headers, json={"title": "t"})

        assert response.status_code == 404
        assert response.get_json()["error"] == "Post not found"

    def test_json_body_must_not_be_null(self, client, auth_headers, sample_post):
        response = client.put(
            f"/api/posts/{sample_post.id}",
            headers=auth_headers,
            data="null",
            content_type="application/json",
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "Invalid JSON body"

    def test_title_exceeds_the_limit(self, client, auth_headers, sample_post):
        response = client.put(
            f"/api/posts/{sample_post.id}",
            headers=auth_headers,
            json={"title": "t" * 201},
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "title exceeds 200 chars"

    def test_slug_exceeds_the_limit(self, client, auth_headers, sample_post):
        response = client.put(
            f"/api/posts/{sample_post.id}",
            headers=auth_headers,
            json={"slug": "s" * 101},
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "slug exceeds 100 chars"

    def test_body_exceeds_the_limit(self, client, auth_headers, sample_post):
        response = client.put(
            f"/api/posts/{sample_post.id}",
            headers=auth_headers,
            json={"body": "b" * 50001},
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "body exceeds 50000 chars"

    def test_summary_exceeds_the_limit(self, client, auth_headers, sample_post):
        response = client.put(
            f"/api/posts/{sample_post.id}",
            headers=auth_headers,
            json={"summary": "s" * 501},
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "summary exceeds 500 chars"

    def test_image_exceeds_the_limit(self, client, auth_headers, sample_post):
        response = client.put(
            f"/api/posts/{sample_post.id}",
            headers=auth_headers,
            json={"image": "i" * 201},
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "image exceeds 200 chars"

    def test_published_must_be_a_boolean(self, client, auth_headers, sample_post):
        response = client.put(
            f"/api/posts/{sample_post.id}",
            headers=auth_headers,
            json={"published": "sometimes"},
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "published must be a boolean"

    def test_a_taken_slug_is_made_unique(self, client, auth_headers, db, sample_post):
        db.session.add(Post(title="Other", slug="taken", body="b"))
        db.session.commit()

        response = client.put(
            f"/api/posts/{sample_post.id}",
            headers=auth_headers,
            json={"slug": "taken"},
        )

        assert response.status_code == 200
        assert response.get_json()["slug"] == "taken-2"

    def test_the_same_slug_is_kept(self, client, auth_headers, sample_post):
        response = client.put(
            f"/api/posts/{sample_post.id}",
            headers=auth_headers,
            json={"slug": sample_post.slug},
        )

        assert response.status_code == 200
        assert response.get_json()["slug"] == sample_post.slug

    def test_the_body_summary_and_image_are_stored(self, client, auth_headers, sample_post):
        response = client.put(
            f"/api/posts/{sample_post.id}",
            headers=auth_headers,
            json={"body": "new body", "summary": "new summary", "image": "new.png"},
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["body"] == "new body"
        assert payload["summary"] == "new summary"
        assert payload["image"] == "new.png"

    def test_publishing_a_draft_sets_the_publication_time(self, client, auth_headers, db):
        post = Post(title="Draft", slug="draft-post", body="b", published=False)
        db.session.add(post)
        db.session.commit()

        response = client.put(
            f"/api/posts/{post.id}",
            headers=auth_headers,
            json={"published": True},
        )

        assert response.status_code == 200
        assert response.get_json()["published_at"] is not None

    def test_publishing_an_already_published_post_keeps_the_publication_time(
        self, client, auth_headers, sample_post
    ):
        response = client.put(
            f"/api/posts/{sample_post.id}",
            headers=auth_headers,
            json={"published": True},
        )

        assert response.status_code == 200
        assert response.get_json()["published_at"] is not None

    def test_tags_are_replaced(self, client, auth_headers, sample_post):
        response = client.put(
            f"/api/posts/{sample_post.id}",
            headers=auth_headers,
            json={"tags": ["Gamma"]},
        )

        assert response.status_code == 200
        assert response.get_json()["tags"] == ["Gamma"]

    def test_author_id_must_be_an_integer(self, client, auth_headers, sample_post):
        response = client.put(
            f"/api/posts/{sample_post.id}",
            headers=auth_headers,
            json={"author_id": "abc"},
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "author_id must be an integer"

    def test_author_id_must_exist(self, client, auth_headers, sample_post):
        response = client.put(
            f"/api/posts/{sample_post.id}",
            headers=auth_headers,
            json={"author_id": 999999},
        )

        assert response.status_code == 400
        assert response.get_json()["error"] == "Unknown author"

    def test_the_write_scope_is_required_to_set_the_author(self, client, auth_headers, sample_post):
        with patch(
            "app.routes.api.posts._author_scope_error",
            return_value="Missing scope: posts:write",
        ):
            response = client.put(
                f"/api/posts/{sample_post.id}",
                headers=auth_headers,
                json={"author_id": 1},
            )

        assert response.status_code == 403
        assert response.get_json()["error"] == "Missing scope: posts:write"

    def test_the_author_is_assigned(self, client, auth_headers, sample_post, admin_user, db):
        response = client.put(
            f"/api/posts/{sample_post.id}",
            headers=auth_headers,
            json={"author_id": admin_user.id},
        )

        assert response.status_code == 200
        assert db.session.get(Post, sample_post.id).author_id == admin_user.id

    def test_the_search_index_failure_is_reported(self, client, auth_headers, sample_post):
        with patch("app.search.sync_fts", return_value=False):
            response = client.put(
                f"/api/posts/{sample_post.id}",
                headers=auth_headers,
                json={"title": "Updated"},
            )

        assert response.status_code == 503
        assert response.get_json()["error"] == "Search index unavailable"

    def test_a_duplicate_slug_is_a_conflict(self, client, legacy_headers, sample_post):
        with legacy_api_key():
            with patch.object(
                db.session,
                "commit",
                side_effect=IntegrityError("UPDATE", {}, Exception("duplicate")),
            ):
                response = client.put(
                    f"/api/posts/{sample_post.id}",
                    headers=legacy_headers,
                    json={"title": "Updated"},
                )

        assert response.status_code == 409
        assert response.get_json()["error"] == "Duplicate slug or database constraint violation"

    def test_a_database_failure_is_a_server_error(self, client, legacy_headers, sample_post):
        with legacy_api_key():
            with patch.object(
                db.session,
                "commit",
                side_effect=OperationalError("UPDATE", {}, Exception("locked")),
            ):
                response = client.put(
                    f"/api/posts/{sample_post.id}",
                    headers=legacy_headers,
                    json={"title": "Updated"},
                )

        assert response.status_code == 500
        assert response.get_json()["error"] == "Database operational error"

    def test_unpublishing_emits_a_webhook_event(self, client, auth_headers, sample_post):
        with patch("app.webhooks.create_webhook_event") as create_event:
            response = client.put(
                f"/api/posts/{sample_post.id}",
                headers=auth_headers,
                json={"published": False},
            )

        assert response.status_code == 200
        create_event.assert_called_once()
        assert create_event.call_args.kwargs["event_type"] == "post.unpublished"

    def test_a_failing_webhook_does_not_break_the_update(
        self, client, auth_headers, sample_post, caplog
    ):
        with caplog.at_level(logging.WARNING):
            with patch("app.webhooks.create_webhook_event", side_effect=RuntimeError("boom")):
                response = client.put(
                    f"/api/posts/{sample_post.id}",
                    headers=auth_headers,
                    json={"published": False},
                )

        assert response.status_code == 200
        assert "Webhook event creation failed" in caplog.text


class TestDeletePost:
    def test_an_unknown_post_is_not_found(self, client, auth_headers):
        response = client.delete("/api/posts/999999", headers=auth_headers)

        assert response.status_code == 404
        assert response.get_json()["error"] == "Post not found"

    def test_the_post_is_deleted(self, client, auth_headers, db, sample_post):
        response = client.delete(f"/api/posts/{sample_post.id}", headers=auth_headers)

        assert response.status_code == 200
        assert response.get_json()["message"] == "Post deleted successfully"
        assert db.session.get(Post, sample_post.id) is None

    def test_the_image_of_the_post_is_removed(self, client, auth_headers, db):
        post = Post(title="With image", slug="with-image", body="b", image="sample.png")
        db.session.add(post)
        db.session.commit()

        with patch("app.routes.api.posts.safe_delete_file") as delete_file:
            response = client.delete(f"/api/posts/{post.id}", headers=auth_headers)

        assert response.status_code == 200
        delete_file.assert_called_once()
        assert delete_file.call_args.args[0].endswith("sample.png")

    def test_a_constraint_violation_is_a_conflict(self, client, legacy_headers, sample_post):
        with legacy_api_key():
            with patch.object(
                db.session,
                "commit",
                side_effect=IntegrityError("DELETE", {}, Exception("constraint")),
            ):
                response = client.delete(f"/api/posts/{sample_post.id}", headers=legacy_headers)

        assert response.status_code == 409
        assert response.get_json()["error"] == "Database constraint violation"

    def test_a_database_failure_is_a_server_error(self, client, legacy_headers, sample_post):
        with legacy_api_key():
            with patch.object(
                db.session,
                "commit",
                side_effect=OperationalError("DELETE", {}, Exception("locked")),
            ):
                response = client.delete(f"/api/posts/{sample_post.id}", headers=legacy_headers)

        assert response.status_code == 500
        assert response.get_json()["error"] == "Database operational error"
