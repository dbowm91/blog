"""Tests for the public authentication routes."""

import re
from unittest.mock import patch

import pyotp
import pytest
from sqlalchemy import select

from app import limiter
from app.config import MAX_FAILED_ATTEMPTS
from app.extensions import db
from app.models import AdminSession, Post, User
from app.routes.public import public
from app.routes.public.auth import is_safe_next_url, register_auth_routes
from tests.conftest import TEST_PASSWORD

register_auth_routes(public)

FLASH_PATTERN = re.compile(rb'<span class="flash-message">(.*?)</span>')


@pytest.fixture
def author_user(db):
    """Create a non-admin account."""
    user = User(username="author1", email="author1@example.com", is_admin=False)
    user.set_password(TEST_PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user


def _reload(user):
    """Re-read a user row from the database."""
    return db.session.execute(
        select(User).filter_by(id=user.id).execution_options(populate_existing=True)
    ).scalar_one()


def _flash_messages(response):
    """Extract the flashed messages from a rendered response."""
    return FLASH_PATTERN.findall(response.data)


def _sign_in(client, identifier="author1", password=TEST_PASSWORD, **extra):
    """Post the public login form."""
    data = {"identifier": identifier, "password": password}
    data.update(extra)
    return client.post("/login", data=data)


def test_login_page_renders(client):
    """The public login page renders with a CSRF token."""
    response = client.get("/login")
    assert response.status_code == 200
    assert b'name="csrf_token"' in response.data
    assert b'name="identifier"' in response.data
    assert b'name="password"' in response.data


def test_non_admin_can_sign_in(client, author_user):
    """A non-admin account can sign in through the public login."""
    response = _sign_in(client)
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    with client.session_transaction() as sess:
        assert sess.get("_user_id") == str(author_user.id)


def test_non_admin_can_sign_in_with_email(client, author_user):
    """The identifier field accepts an email address."""
    response = _sign_in(client, identifier="author1@example.com")
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert sess.get("_user_id") == str(author_user.id)


def test_wrong_password_increments_failed_logins(client, author_user):
    """A wrong password reports a generic message and counts the failure."""
    with patch("app.routes.public.auth.time.sleep") as mock_sleep:
        response = _sign_in(client, password="wrong-password")
    assert response.status_code == 200
    assert b"Invalid credentials." in response.data
    assert mock_sleep.called
    assert _reload(author_user).failed_login_count == 1
    with client.session_transaction() as sess:
        assert "_user_id" not in sess


def test_failure_message_is_identical_for_unknown_identifier(client, author_user):
    """The failure message does not reveal whether an account exists."""
    with patch("app.routes.public.auth.time.sleep"):
        known = _sign_in(client, password="wrong-password")
        unknown = _sign_in(client, identifier="nobody-here", password="wrong-password")
    assert known.status_code == unknown.status_code == 200
    assert _flash_messages(known) == _flash_messages(unknown)
    assert b"Invalid credentials." in known.data
    assert b"Invalid credentials." in unknown.data


def test_account_locks_after_max_failed_attempts(client, author_user):
    """The account locks after the configured number of failures."""
    with patch("app.routes.public.auth.time.sleep"):
        for _ in range(MAX_FAILED_ATTEMPTS):
            _sign_in(client, password="wrong-password")
        locked = _sign_in(client)
    assert locked.status_code == 200
    assert b"locked" in locked.data.lower()

    user = _reload(author_user)
    assert user.failed_login_count == MAX_FAILED_ATTEMPTS
    assert user.is_locked()
    with client.session_transaction() as sess:
        assert "_user_id" not in sess


def test_next_rejects_external_url(client, author_user):
    """An off-site next parameter is rejected."""
    response = client.post(
        "/login?next=https://evil.example/",
        data={"identifier": "author1", "password": TEST_PASSWORD},
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_next_accepts_local_path(client, author_user):
    """A local next parameter is honoured."""
    response = client.post(
        "/login?next=/post/x",
        data={"identifier": "author1", "password": TEST_PASSWORD},
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/post/x"


def test_is_safe_next_url_rejects_off_site_targets():
    """The next parameter validator only accepts local single-slash paths."""
    assert is_safe_next_url("/post/x") is True
    assert is_safe_next_url("https://evil.example/") is False
    assert is_safe_next_url("//evil.example/") is False
    assert is_safe_next_url("http:/evil.example") is False
    assert is_safe_next_url("/\\evil.example") is False
    assert is_safe_next_url("") is False


def test_session_changes_across_login(client, author_user):
    """The session is cleared before login, so the identifier changes."""
    with client.session_transaction() as sess:
        sess["planted"] = "attacker-value"
    before = client.get_cookie("session")
    before_value = before.value if before else None

    response = _sign_in(client)
    assert response.status_code == 302

    after = client.get_cookie("session")
    assert after is not None
    assert after.value != before_value
    with client.session_transaction() as sess:
        assert "planted" not in sess
        assert sess.get("_user_id") == str(author_user.id)


def test_two_factor_account_requires_a_code(client, db, monkeypatch):
    """A two-factor account cannot be signed in without the second factor."""
    monkeypatch.setattr("app.services.encryption.encrypt", lambda plaintext: plaintext)
    monkeypatch.setattr("app.services.encryption.decrypt", lambda ciphertext: ciphertext)

    user = User(username="mfa-user", email="mfa@example.com", is_admin=False)
    user.set_password(TEST_PASSWORD)
    user.set_totp_secret(pyotp.random_base32())
    user.totp_enabled = True
    db.session.add(user)
    db.session.commit()

    with patch("app.routes.public.auth.time.sleep"):
        response = _sign_in(client, identifier="mfa-user")
    assert response.status_code == 200
    assert b'name="totp_code"' in response.data
    with client.session_transaction() as sess:
        assert "_user_id" not in sess

    code = pyotp.TOTP(user.totp_secret).now()
    accepted = _sign_in(client, identifier="mfa-user", totp_code=code)
    assert accepted.status_code == 302
    with client.session_transaction() as sess:
        assert sess.get("_user_id") == str(user.id)


def test_two_factor_account_without_secret_is_refused(client, db):
    """A two-factor account without a stored secret cannot be signed in."""
    user = User(username="mfa-broken", email="mfa-broken@example.com", is_admin=False)
    user.set_password(TEST_PASSWORD)
    user.totp_enabled = True
    db.session.add(user)
    db.session.commit()

    with patch("app.routes.public.auth.time.sleep"):
        response = _sign_in(client, identifier="mfa-broken")
    assert response.status_code == 200
    assert b"Two-factor authentication" in response.data
    with client.session_transaction() as sess:
        assert "_user_id" not in sess


def test_public_session_cannot_reach_admin_dashboard(client, author_user):
    """A public-only session does not grant access to the admin panel."""
    assert _sign_in(client).status_code == 302
    with client.session_transaction() as sess:
        assert sess.get("_user_id") == str(author_user.id)

    dashboard = client.get("/admin/")
    assert dashboard.status_code in (302, 403)
    assert dashboard.status_code != 200

    assert client.get("/admin/dashboard").status_code != 200


def test_admin_account_cannot_sign_in_through_public_login(client, admin_user):
    """An administrator must use the admin login, so a public session is never an admin session."""
    response = client.post("/login", data={"identifier": "admin", "password": TEST_PASSWORD})
    assert response.status_code == 200
    assert b"Administrator accounts must sign in" in response.data
    with client.session_transaction() as sess:
        assert "_user_id" not in sess


def test_account_counts_published_posts(client, db, author_user):
    """The account page counts the published posts of the signed-in visitor."""
    post = Post(
        title="Hello",
        slug="hello",
        body="Body",
        published=True,
        author_id=author_user.id,
    )
    db.session.add(post)
    db.session.commit()

    assert _sign_in(client).status_code == 302
    response = client.get("/account")
    assert response.status_code == 200
    assert b"1 published post" in response.data


def test_account_requires_a_session(client):
    """The account page redirects anonymous visitors to the public login."""
    response = client.get("/account")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_account_renders_profile(client, db, author_user):
    """The account page shows the signed-in user's profile."""
    author_user.display_name = "Ada Author"
    author_user.bio_short = "Writes about testing."
    db.session.commit()

    assert _sign_in(client).status_code == 302
    response = client.get("/account")
    assert response.status_code == 200
    assert b"Ada Author" in response.data
    assert b"Writes about testing." in response.data
    assert b"0 published posts" in response.data
    assert b"/account/profile" in response.data


def test_account_profile_editor_saves_profile(client, db, author_user):
    """The profile editor saves the public profile fields only."""
    assert _sign_in(client).status_code == 302
    response = client.post(
        "/account/profile",
        data={"display_name": "Ada Lovelace", "bio_short": "Analytical engines."},
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/account"

    user = _reload(author_user)
    assert user.display_name == "Ada Lovelace"
    assert user.bio_short == "Analytical engines."
    assert user.is_admin is False


def test_forgot_password_issues_token_for_non_admin(client, db, author_user, monkeypatch):
    """A non-admin account can request a password reset."""
    send_called = []

    def mock_send_task(user_id, token):
        send_called.append((user_id, token))

    monkeypatch.setattr("app.tasks.send_password_reset_task.delay", mock_send_task)
    response = client.post(
        "/admin/forgot-password",
        data={"identifier": "author1"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"If that account exists" in response.data
    assert len(send_called) == 1

    user = _reload(author_user)
    assert user.reset_token is not None
    assert user.reset_token_expires_at is not None


def test_login_endpoint_has_no_application_rate_limit(app):
    """The application does not rate limit login; the proxy is expected to.

    Rate limiting the login routes in the application costs a storage round
    trip on every attempt, and the deployment is expected to sit behind a
    reverse proxy or WAF that does it instead.
    """
    _, decorated = limiter.limit_manager.resolve_limits(app, endpoint="public.login")
    assert not any(str(item.limit).startswith("5 per") for item in decorated)


def test_login_account_lockout_is_still_enforced(app, client, db, author_user):
    """The per-account lockout stays, because it costs no extra request."""
    from app.config import MAX_FAILED_ATTEMPTS

    for _ in range(MAX_FAILED_ATTEMPTS):
        client.post(
            "/login",
            data={"identifier": author_user.username, "password": "wrong-password"},
        )

    user = _reload(author_user)
    assert user.failed_login_count >= MAX_FAILED_ATTEMPTS
    assert user.is_locked()


def test_public_logout_removes_admin_session(client, db, admin_user):
    """Signing out through the public route clears the admin session row."""
    assert (
        client.post(
            "/admin/login",
            data={"username": "admin", "password": TEST_PASSWORD},
        ).status_code
        == 302
    )
    admin_session = db.session.execute(
        select(AdminSession).filter_by(user_id=admin_user.id)
    ).scalar_one()
    assert admin_session is not None

    response = client.post("/logout")
    assert response.status_code == 302
    assert response.headers["Location"] == "/"

    remaining = (
        db.session.execute(select(AdminSession).filter_by(user_id=admin_user.id)).scalars().all()
    )
    assert remaining == []
    with client.session_transaction() as sess:
        assert "_user_id" not in sess


def test_public_logout_works_for_non_admin(client, author_user):
    """A visitor without an admin session can sign out."""
    assert _sign_in(client).status_code == 302
    response = client.post("/logout")
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    with client.session_transaction() as sess:
        assert "_user_id" not in sess
