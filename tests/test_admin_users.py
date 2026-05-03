import pytest
from app.models import User
from app.utils import utc_now


def test_create_user_success(authenticated_client, db):
    """Test creating a new user."""
    response = authenticated_client.post(
        "/admin/users/create",
        data={
            "username": "newuser",
            "password": "Password123!",
            "is_admin": "on"
        },
        follow_redirects=True
    )
    assert response.status_code == 200
    # Check user exists
    user = db.session.execute(
        db.select(User).filter_by(username="newuser")
    ).scalar_one_or_none()
    assert user is not None
    assert user.is_admin is True


def test_create_user_existing(authenticated_client, admin_user):
    """Test creating user with existing username."""
    response = authenticated_client.post(
        "/admin/users/create",
        data={
            "username": "admin",
            "password": "Password123!"
        },
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"already exists" in response.data.lower()


def test_create_user_weak_password(authenticated_client):
    """Test creating user with weak password."""
    response = authenticated_client.post(
        "/admin/users/create",
        data={
            "username": "weakuser",
            "password": "weak"
        },
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"must be at least" in response.data.lower()


def test_delete_user(authenticated_client, db, admin_user):
    """Test deleting a user."""
    user = User(username="todelete", is_admin=False)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    user_id = user.id
    response = authenticated_client.post(
        f"/admin/users/delete/{user_id}",
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"deleted" in response.data.lower()
    # Check user deleted
    deleted = db.session.execute(
        db.select(User).filter_by(id=user_id)
    ).scalar_one_or_none()
    assert deleted is None


def test_delete_self(authenticated_client, admin_user):
    """Test cannot delete self."""
    response = authenticated_client.post(
        f"/admin/users/delete/{admin_user.id}",
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"cannot delete your own" in response.data.lower()


def test_promote_user(authenticated_client, db):
    """Test promoting user to admin."""
    user = User(username="tpromote", is_admin=False)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    response = authenticated_client.post(
        f"/admin/users/{user.id}/promote",
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"promoted" in response.data.lower()
    db.session.refresh(user)
    assert user.is_admin is True


def test_demote_user(authenticated_client, db, admin_user):
    """Test demoting admin to regular user."""
    # Create another admin
    other_admin = User(username="otheradmin", is_admin=True)
    other_admin.set_password("Password123!")
    db.session.add(other_admin)
    db.session.commit()
    # Demote other admin
    response = authenticated_client.post(
        f"/admin/users/{other_admin.id}/demote",
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"demoted" in response.data.lower()
    db.session.refresh(other_admin)
    assert other_admin.is_admin is False


def test_demote_self(authenticated_client, admin_user):
    """Test cannot demote self."""
    response = authenticated_client.post(
        f"/admin/users/{admin_user.id}/demote",
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"cannot demote your own" in response.data.lower()


def test_make_owner(authenticated_client, db, admin_user):
    """Test transferring ownership."""
    # Create new owner
    new_owner = User(username="newowner", is_admin=False)
    new_owner.set_password("Password123!")
    db.session.add(new_owner)
    db.session.commit()
    # Make owner (need to provide current user's password)
    response = authenticated_client.post(
        f"/admin/users/{new_owner.id}/make-owner",
        data={"password": "testpassword"},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"transferred" in response.data.lower()
    # Check new owner is admin, old is not
    db.session.refresh(admin_user)
    db.session.refresh(new_owner)
    assert new_owner.is_admin is True
    assert admin_user.is_admin is False


def test_change_password(authenticated_client, db, admin_user):
    """Test changing user's password."""
    response = authenticated_client.post(
        f"/admin/users/{admin_user.id}/password",
        data={"password": "NewPassword123!"},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"password changed" in response.data.lower()
    # Check password changed
    db.session.refresh(admin_user)
    assert admin_user.check_password("NewPassword123!") is True


def test_change_password_weak(authenticated_client, admin_user):
    """Test changing password to weak one."""
    response = authenticated_client.post(
        f"/admin/users/{admin_user.id}/password",
        data={"password": "weak"},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"must be at least" in response.data.lower()


def test_delete_user(authenticated_client, db, admin_user):
    """Test deleting a user."""
    user = User(username="todelete", is_admin=False)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    user_id = user.id
    response = authenticated_client.post(
        f"/users/delete/{user_id}",
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"deleted" in response.data.lower()
    # Check user deleted
    deleted = db.session.execute(
        db.select(User).filter_by(id=user_id)
    ).scalar_one_or_none()
    assert deleted is None


def test_delete_self(authenticated_client, admin_user):
    """Test cannot delete self."""
    response = authenticated_client.post(
        f"/users/delete/{admin_user.id}",
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"cannot delete your own" in response.data.lower()


def test_promote_user(authenticated_client, db):
    """Test promoting user to admin."""
    user = User(username="t promote", is_admin=False)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    response = authenticated_client.post(
        f"/users/{user.id}/promote",
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"promoted" in response.data.lower()
    db.session.refresh(user)
    assert user.is_admin is True


def test_demote_user(authenticated_client, db, admin_user):
    """Test demoting admin to regular user."""
    # Create another admin
    other_admin = User(username="otheradmin", is_admin=True)
    other_admin.set_password("Password123!")
    db.session.add(other_admin)
    db.session.commit()
    # Demote other admin
    response = authenticated_client.post(
        f"/users/{other_admin.id}/demote",
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"demoted" in response.data.lower()
    db.session.refresh(other_admin)
    assert other_admin.is_admin is False


def test_demote_self(authenticated_client, admin_user):
    """Test cannot demote self."""
    response = authenticated_client.post(
        f"/users/{admin_user.id}/demote",
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"cannot demote your own" in response.data.lower()


def test_make_owner(authenticated_client, db, admin_user):
    """Test transferring ownership."""
    # Create new owner
    new_owner = User(username="newowner", is_admin=False)
    new_owner.set_password("Password123!")
    db.session.add(new_owner)
    db.session.commit()
    # Make owner (need to provide current user's password)
    response = authenticated_client.post(
        f"/users/{new_owner.id}/make-owner",
        data={"password": "testpassword"},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"transferred" in response.data.lower()
    # Check new owner is admin, old is not
    db.session.refresh(admin_user)
    db.session.refresh(new_owner)
    assert new_owner.is_admin is True
    assert admin_user.is_admin is False


def test_change_password(authenticated_client, db, admin_user):
    """Test changing user's password."""
    response = authenticated_client.post(
        f"/users/{admin_user.id}/password",
        data={"password": "NewPassword123!"},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"password changed" in response.data.lower()
    # Check password changed
    db.session.refresh(admin_user)
    assert admin_user.check_password("NewPassword123!") is True


def test_change_password_weak(authenticated_client, admin_user):
    """Test changing password to weak one."""
    response = authenticated_client.post(
        f"/users/{admin_user.id}/password",
        data={"password": "weak"},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"must be at least" in response.data.lower()
