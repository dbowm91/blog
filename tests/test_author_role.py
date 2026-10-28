"""Tests for the author role.

An author is a signed-in user without the ``is_admin`` flag. Authors reach
the post editor and nothing else, and may only open the posts they are the
author of.
"""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import Mock

import pytest

from app.config.model import AiConfig
from app.models import Post, User
from app.services import ai_assist

TEST_PASSWORD = "test-password-123"


@pytest.fixture
def author_user(db):
    user = User(username="author1", email="author1@example.com", is_admin=False)
    user.set_password(TEST_PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def author_client(client, author_user):
    client.post(
        "/admin/login",
        data={"username": "author1", "password": TEST_PASSWORD},
    )
    return client


def _login(client, username):
    response = client.post(
        "/login",
        data={"identifier": username, "password": TEST_PASSWORD},
    )
    return response


def test_an_author_cannot_sign_in_through_the_admin_login(client, author_user):
    response = client.post(
        "/admin/login",
        data={"username": "author1", "password": TEST_PASSWORD},
    )

    assert response.status_code in (200, 302)
    assert b"Invalid" in response.data or response.status_code == 302


def test_an_author_can_sign_in_through_the_public_login(client, author_user):
    response = _login(client, "author1")

    assert response.status_code in (200, 302)


def test_an_author_can_reach_the_editor(client, author_user):
    _login(client, "author1")

    response = client.get("/admin/new")

    assert response.status_code == 200
    assert b"Title" in response.data


def test_an_author_cannot_reach_the_admin_dashboard(client, author_user):
    _login(client, "author1")

    response = client.get("/admin/")

    assert response.status_code == 403


def test_an_author_cannot_reach_the_admin_settings(client, author_user):
    _login(client, "author1")

    assert client.get("/admin/settings").status_code == 403


def test_an_author_cannot_reach_the_user_list(client, author_user):
    _login(client, "author1")

    assert client.get("/admin/users").status_code == 403


def test_an_author_new_post_is_a_draft_authored_by_them(client, db, author_user):
    _login(client, "author1")

    client.post(
        "/admin/new",
        data={
            "title": "An author post",
            "body": "The body of the post.",
            "published": "on",
        },
    )

    post = db.session.execute(db.select(Post)).scalar_one()
    assert post.author_id == author_user.id
    assert post.published is False


def test_an_author_post_is_attached_to_its_author(client, db, author_user):
    _login(client, "author1")

    client.post(
        "/admin/new",
        data={"title": "Another post", "body": "Body text."},
    )

    post = db.session.execute(db.select(Post)).scalar_one()
    assert post.author is not None
    assert post.author.username == "author1"


def test_an_author_cannot_open_a_post_they_do_not_own(client, db, author_user):
    other = User(username="author2", email="author2@example.com", is_admin=False)
    other.set_password(TEST_PASSWORD)
    db.session.add(other)
    post = Post(
        title="Someone else's post",
        slug="someone-elses-post",
        body="Body",
        summary="",
        published=True,
        author_id=other.id,
    )
    db.session.add(post)
    db.session.commit()

    _login(client, "author1")

    response = client.get(f"/admin/edit/{post.id}")

    assert response.status_code == 403


def test_an_author_can_open_their_own_post(client, db, author_user):
    post = Post(
        title="My own post",
        slug="my-own-post",
        body="Body",
        summary="",
        published=False,
        author_id=author_user.id,
    )
    db.session.add(post)
    db.session.commit()

    _login(client, "author1")

    response = client.get(f"/admin/edit/{post.id}")

    assert response.status_code == 200


def test_the_admin_shell_hides_admin_links_from_an_author(client, author_user):
    _login(client, "author1")

    response = client.get("/admin/new")
    html = response.data.decode()

    assert "Write" in html
    assert "/admin/users" not in html
    assert "/admin/settings" not in html


def test_an_administrator_still_reaches_everything(authenticated_client):
    assert authenticated_client.get("/admin/").status_code == 200
    assert authenticated_client.get("/admin/settings").status_code == 200
    assert authenticated_client.get("/admin/users").status_code == 200


def test_author_cannot_request_ai_for_another_authors_post(
    app, db, author_client, author_user, monkeypatch
):
    other = User(username="ai-other-author", email="ai-other@example.com", is_admin=False)
    other.set_password(TEST_PASSWORD)
    db.session.add(other)
    db.session.flush()
    post = Post(
        title="Another author's draft",
        slug="another-authors-ai-draft",
        body="Private body",
        summary="",
        published=False,
        author_id=other.id,
    )
    db.session.add(post)
    db.session.commit()
    original_config = app.config["DEVLOG_CONFIG"]
    app.config["DEVLOG_CONFIG"] = replace(original_config, ai=AiConfig(api_key="test-private-key"))
    provider = Mock()
    monkeypatch.setattr(ai_assist.requests, "post", provider)

    _login(author_client, "author1")
    response = author_client.post(
        "/admin/ai-assist",
        json={"action": "summary", "title": "T", "body": "Body", "post_id": post.id},
    )

    app.config["DEVLOG_CONFIG"] = original_config
    assert author_user.is_admin is False
    assert post.author_id != author_user.id
    assert response.status_code == 403
    provider.assert_not_called()
