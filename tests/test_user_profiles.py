"""Tests for the admin user profile editor.

Covers the profile fields, the avatar lifecycle in storage, the access
control on the editor and the audit trail of a profile edit.
"""

from __future__ import annotations

import base64
import io
import os
import re
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models import AdminAuditLog, Post, User
from app.services.profile import validate_profile_payload
from app.utils import utc_now
from tests.conftest import TEST_PASSWORD

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture
def upload_dir(tmp_path):
    """Point the storage backend at a temporary directory for the test."""
    import app.storage as storage_module

    original_storage = storage_module._storage
    with patch.dict(os.environ, {"UPLOAD_FOLDER": str(tmp_path)}):
        storage_module._storage = None
        yield tmp_path
    storage_module._storage = original_storage


def _profile(target: User, **data: str):
    return f"/admin/users/{target.id}/profile"


def test_profile_name_falls_back_to_username(db):
    """An empty display name resolves to the username."""
    user = User(username="plainuser", is_admin=False)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()

    assert user.display_name == ""
    assert user.profile_name == "plainuser"

    user.display_name = "  Ada Lovelace  "
    assert user.profile_name == "Ada Lovelace"


def test_avatar_url_is_none_without_avatar(db):
    """A user without an avatar has no avatar URL."""
    user = User(username="noavatar", is_admin=False)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()

    assert user.avatar_path is None
    assert user.avatar_url is None


def test_validate_profile_payload_truncates_fields():
    """The display name and the short bio are truncated to their limits."""
    payload = validate_profile_payload(
        {
            "display_name": "D" * 200,
            "bio_short": "B" * 500,
            "bio_full": "# Heading\n\nBody",
            "unknown": "ignored",
        }
    )

    assert len(payload.display_name) == 120
    assert len(payload.bio_short) == 300
    assert payload.bio_full == "# Heading\n\nBody"


def test_validate_profile_payload_trims_text_fields():
    """The display name and the short bio are trimmed."""
    payload = validate_profile_payload(
        {"display_name": "  Ada  ", "bio_short": "  Short  ", "bio_full": "  Full  "}
    )

    assert payload.display_name == "Ada"
    assert payload.bio_short == "Short"
    assert payload.bio_full == "  Full  "


def test_profile_post_persists_fields(authenticated_client, db, admin_user):
    """A valid profile submission stores the three text fields."""
    response = authenticated_client.post(
        _profile(admin_user),
        data={
            "display_name": "Ada Lovelace",
            "bio_short": "A short bio",
            "bio_full": "# Full bio\n\nBody",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    db.session.expire_all()
    user = db.session.get(User, admin_user.id)
    assert user.display_name == "Ada Lovelace"
    assert user.bio_short == "A short bio"
    assert user.bio_full == "# Full bio\n\nBody"


def test_profile_post_truncates_persisted_fields(authenticated_client, db, admin_user):
    """Over-long values are truncated before they are stored."""
    authenticated_client.post(
        _profile(admin_user),
        data={"display_name": "D" * 200, "bio_short": "B" * 500},
        follow_redirects=True,
    )

    db.session.expire_all()
    user = db.session.get(User, admin_user.id)
    assert len(user.display_name) == 120
    assert len(user.bio_short) == 300


def test_profile_avatar_upload(authenticated_client, db, admin_user, upload_dir):
    """An uploaded PNG is stored and referenced by the avatar path."""
    response = authenticated_client.post(
        _profile(admin_user),
        data={
            "display_name": "Ada Lovelace",
            "avatar": (io.BytesIO(PNG_1X1), "avatar.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    db.session.expire_all()
    user = db.session.get(User, admin_user.id)
    assert user.avatar_path is not None
    assert user.avatar_path.endswith(".png")
    assert (upload_dir / user.avatar_path).exists()
    assert user.avatar_url == f"/static/uploads/{user.avatar_path}"


def test_profile_avatar_rejects_non_image(authenticated_client, db, admin_user, upload_dir):
    """A non-image upload is rejected and leaves the profile untouched."""
    response = authenticated_client.post(
        _profile(admin_user),
        data={
            "display_name": "Ada Lovelace",
            "avatar": (io.BytesIO(b"not an image"), "avatar.txt"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"unsupported file type" in response.data.lower()
    db.session.expire_all()
    user = db.session.get(User, admin_user.id)
    assert user.avatar_path is None
    assert user.display_name == ""
    assert list(upload_dir.glob("*.txt")) == []


def test_profile_avatar_rejects_fake_image_header(authenticated_client, db, admin_user, upload_dir):
    """A file with an image name but a non-image header is rejected."""
    response = authenticated_client.post(
        _profile(admin_user),
        data={"avatar": (io.BytesIO(b"not an image"), "avatar.png")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"not a valid image" in response.data.lower()
    db.session.expire_all()
    user = db.session.get(User, admin_user.id)
    assert user.avatar_path is None


def test_profile_avatar_replacement_deletes_previous_file(
    authenticated_client, db, admin_user, upload_dir
):
    """Replacing an avatar deletes the file that was stored before."""
    authenticated_client.post(
        _profile(admin_user),
        data={"avatar": (io.BytesIO(PNG_1X1), "first.png")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    db.session.expire_all()
    first_path = db.session.get(User, admin_user.id).avatar_path
    assert first_path is not None
    assert (upload_dir / first_path).exists()

    authenticated_client.post(
        _profile(admin_user),
        data={"avatar": (io.BytesIO(PNG_1X1), "second.png")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    db.session.expire_all()
    second_path = db.session.get(User, admin_user.id).avatar_path
    assert second_path is not None
    assert second_path != first_path
    assert (upload_dir / second_path).exists()
    assert not (upload_dir / first_path).exists()


def test_profile_avatar_removal_deletes_file(authenticated_client, db, admin_user, upload_dir):
    """The remove flag clears the avatar path and deletes the stored file."""
    authenticated_client.post(
        _profile(admin_user),
        data={"avatar": (io.BytesIO(PNG_1X1), "avatar.png")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    db.session.expire_all()
    stored_path = db.session.get(User, admin_user.id).avatar_path
    assert stored_path is not None
    assert (upload_dir / stored_path).exists()

    authenticated_client.post(
        _profile(admin_user),
        data={"remove_avatar": "on"},
        follow_redirects=True,
    )

    db.session.expire_all()
    user = db.session.get(User, admin_user.id)
    assert user.avatar_path is None
    assert user.avatar_url is None
    assert not (upload_dir / stored_path).exists()


def test_profile_empty_file_input_keeps_avatar(authenticated_client, db, admin_user, upload_dir):
    """A form submission without a file leaves the stored avatar alone."""
    authenticated_client.post(
        _profile(admin_user),
        data={"avatar": (io.BytesIO(PNG_1X1), "avatar.png")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    db.session.expire_all()
    stored_path = db.session.get(User, admin_user.id).avatar_path

    authenticated_client.post(
        _profile(admin_user),
        data={"display_name": "Ada Lovelace", "avatar": (io.BytesIO(b""), "")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    db.session.expire_all()
    user = db.session.get(User, admin_user.id)
    assert user.avatar_path == stored_path
    assert (upload_dir / stored_path).exists()


def test_avatar_path_is_never_taken_from_the_request(authenticated_client, db, admin_user):
    """A client-supplied avatar path or URL is ignored."""
    response = authenticated_client.post(
        _profile(admin_user),
        data={
            "display_name": "Ada Lovelace",
            "avatar_path": "https://evil.example/picture.png",
            "avatar_url": "https://evil.example/picture.png",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"evil.example" not in response.data
    db.session.expire_all()
    user = db.session.get(User, admin_user.id)
    assert user.avatar_path is None


def test_non_admin_cannot_reach_profile_editor(app, db, client):
    """An authenticated non-admin is refused by the profile editor."""
    admin = User(username="tempadmin", is_admin=True)
    admin.set_password(TEST_PASSWORD)
    db.session.add(admin)
    db.session.commit()

    client.post(
        "/admin/login",
        data={"username": "tempadmin", "password": TEST_PASSWORD},
    )

    admin.is_admin = False
    db.session.commit()

    response = client.get(f"/admin/users/{admin.id}/profile")
    assert response.status_code == 403

    response = client.post(f"/admin/users/{admin.id}/profile", data={"display_name": "Nope"})
    assert response.status_code == 403


def test_anonymous_cannot_reach_profile_editor(client, admin_user):
    """An unauthenticated visitor is redirected to the login page."""
    response = client.get(f"/admin/users/{admin_user.id}/profile")
    assert response.status_code in (302, 401, 403)


def test_profile_editor_missing_user_returns_404(app, db, admin_user):
    """An unknown user id is a 404."""
    from flask_login import login_user
    from werkzeug.exceptions import NotFound

    from app.routes.admin.users import user_profile

    with app.test_request_context("/admin/users/999999/profile"):
        login_user(admin_user)
        with pytest.raises(NotFound):
            user_profile(999999)


def test_own_profile_redirects_to_canonical_editor(authenticated_client, admin_user):
    """The own-profile shortcut points at the canonical editor."""
    response = authenticated_client.get("/admin/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/admin/users/{admin_user.id}/profile")


def test_own_profile_post_reaches_the_canonical_editor(authenticated_client, db, admin_user):
    """A post to the own-profile shortcut is handled by the canonical editor."""
    response = authenticated_client.post(
        "/admin/profile",
        data={"display_name": "Ada Lovelace"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    db.session.expire_all()
    user = db.session.get(User, admin_user.id)
    assert user.display_name == "Ada Lovelace"


def test_profile_edit_writes_audit_log(authenticated_client, db, admin_user):
    """Every profile edit is recorded in the admin audit log."""
    authenticated_client.post(
        _profile(admin_user),
        data={
            "display_name": "Ada Lovelace",
            "bio_short": "A short bio",
            "bio_full": "# Full bio",
        },
        follow_redirects=True,
    )

    db.session.expire_all()
    entry = db.session.execute(
        select(AdminAuditLog).where(AdminAuditLog.action == "user.profile_update")
    ).scalar_one()

    assert entry.actor_id == admin_user.id
    assert entry.target_id == admin_user.id
    assert entry.target_type == "user"
    assert "Ada Lovelace" not in (entry.details or "")
    assert "A short bio" not in (entry.details or "")


def test_delete_user_nulls_post_author(authenticated_client, db):
    """Deleting a user clears the author of their posts."""
    author = User(username="author", is_admin=False)
    author.set_password("Password123!")
    db.session.add(author)
    db.session.commit()

    post = Post(
        title="Owned Post",
        slug="owned-post",
        body="Body",
        published=True,
        published_at=utc_now(),
        author_id=author.id,
    )
    db.session.add(post)
    db.session.commit()
    post_id = post.id

    response = authenticated_client.post(f"/admin/users/delete/{author.id}", follow_redirects=True)
    assert response.status_code == 200

    db.session.expire_all()
    remaining = db.session.execute(select(Post).where(Post.id == post_id)).scalar_one()
    assert remaining.author_id is None


def test_admin_nav_and_users_list_link_to_the_profile_editor(authenticated_client, admin_user):
    """The admin nav and the user list both link to the profile editor."""
    response = authenticated_client.get("/admin/users")
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    assert f"/admin/users/{admin_user.id}/profile" in body
    assert "Profile</a>" in body


def test_profile_bio_is_rendered_as_sanitised_markdown(authenticated_client, db, admin_user):
    """The full bio renders through the shared markdown sanitiser."""
    authenticated_client.post(
        _profile(admin_user),
        data={
            "bio_full": (
                '<script>alert(1)</script>\n\n<img src="x" onerror="alert(2)">\n\n**bold**'
            )
        },
        follow_redirects=True,
    )

    response = authenticated_client.get(_profile(admin_user))
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    assert "<script>alert(1)</script>" not in body
    assert 'onerror="' not in body

    preview = re.search(r'<div class="post-body prose">(.*?)</div>', body, re.S)
    assert preview is not None
    rendered = preview.group(1)
    assert "<script" not in rendered
    assert "onerror" not in rendered
    assert "<strong>bold</strong>" in rendered
