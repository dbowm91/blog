"""Unit tests for admin service functions."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")

import pytest

from app.models import User
from app.services.operations.admin import (
    create_admin,
    promote_admin,
    reset_admin_password,
    list_admins,
    _check_password_complexity,
    ConflictError,
)


@pytest.fixture()
def _app_context(app):
    with app.app_context():
        yield


class TestPasswordComplexity:
    def test_valid_password(self):
        assert _check_password_complexity("Abcdef1!") is True

    def test_too_short(self):
        assert _check_password_complexity("Ab1!") is False

    def test_only_lowercase_and_digits(self):
        assert _check_password_complexity("abcdef12") is False

    def test_only_lowercase(self):
        assert _check_password_complexity("abcdefgh") is False

    def test_only_uppercase(self):
        assert _check_password_complexity("ABCDEFGH") is False

    def test_only_digits(self):
        assert _check_password_complexity("12345678") is False

    def test_mixed_with_special(self):
        assert _check_password_complexity("abcdef1!") is True

    def test_exactly_eight_chars_three_classes(self):
        assert _check_password_complexity("Abcdef1!") is True

    def test_seven_chars_fails(self):
        assert _check_password_complexity("Abcde1!") is False


class TestCreateAdmin:
    def test_create_new_admin(self, db, _app_context):
        result = create_admin("newadmin", "SecurePass1!")

        assert result.ok is True
        assert result.code == "admin.created"
        assert result.username == "newadmin"
        assert result.details["action"] == "created"

        user = db.session.execute(db.select(User).filter_by(username="newadmin")).scalar_one()
        assert user.is_admin is True
        assert user.check_password("SecurePass1!")

    def test_create_existing_user_conflict(self, db, admin_user, _app_context):
        with pytest.raises(ConflictError, match="already exists"):
            create_admin("admin", "SecurePass1!", update_existing=False)

    def test_create_existing_user_update(self, db, admin_user, _app_context):
        result = create_admin("admin", "NewPassword1!", update_existing=True)

        assert result.ok is True
        assert result.details["existing_user"] is True
        assert result.details["action"] == "promoted"

        refreshed = db.session.execute(db.select(User).filter_by(username="admin")).scalar_one()
        assert refreshed.check_password("NewPassword1!")

    def test_password_complexity_failure(self, db, _app_context):
        with pytest.raises(ValueError, match="at least 8 characters"):
            create_admin("newadmin", "weak")

    def test_integrity_error_rollback(self, db, _app_context):
        create_admin("newadmin", "SecurePass1!")

        with pytest.raises(ConflictError):
            create_admin("newadmin", "SecurePass1!", update_existing=False)

        db.session.rollback()
        user = db.session.execute(
            db.select(User).filter_by(username="newadmin")
        ).scalar_one_or_none()
        assert user is not None

    def test_password_not_in_result(self, db, _app_context):
        result = create_admin("newadmin", "SecurePass1!")
        result_str = str(result)
        assert "SecurePass1!" not in result_str
        assert "password" not in result_str.lower() or "password_reset" in result_str.lower()


class TestPromoteAdmin:
    def test_promote_non_admin(self, db, _app_context):
        user = User(username="regularuser", is_admin=False)
        user.set_password("SecurePass1!")
        db.session.add(user)
        db.session.commit()

        result = promote_admin("regularuser")

        assert result.ok is True
        assert result.code == "admin.promoted"
        assert result.username == "regularuser"

        refreshed = db.session.execute(
            db.select(User).filter_by(username="regularuser")
        ).scalar_one()
        assert refreshed.is_admin is True

    def test_promote_missing_user(self, db, _app_context):
        with pytest.raises(ValueError, match="not found"):
            promote_admin("nonexistent")

    def test_promote_already_admin(self, db, admin_user, _app_context):
        with pytest.raises(ConflictError, match="already an admin"):
            promote_admin("admin")


class TestResetAdminPassword:
    def test_reset_password(self, db, admin_user, _app_context):
        result = reset_admin_password("admin", "NewPassword1!")

        assert result.ok is True
        assert result.code == "admin.password_reset"
        assert result.username == "admin"

        refreshed = db.session.execute(db.select(User).filter_by(username="admin")).scalar_one()
        assert refreshed.check_password("NewPassword1!")

    def test_reset_password_missing_user(self, db, _app_context):
        with pytest.raises(ValueError, match="not found"):
            reset_admin_password("nonexistent", "SecurePass1!")

    def test_reset_password_complexity_failure(self, db, admin_user, _app_context):
        with pytest.raises(ValueError, match="at least 8 characters"):
            reset_admin_password("admin", "weak")


class TestListAdmins:
    def test_list_admins_empty(self, db, _app_context):
        result = list_admins()

        assert result.ok is True
        assert result.code == "admin.list"
        assert result.admins == []
        assert result.details["count"] == 0

    def test_list_admins_with_users(self, db, admin_user, _app_context):
        user2 = User(username="admin2", is_admin=True)
        user2.set_password("SecurePass1!")
        db.session.add(user2)
        db.session.commit()

        result = list_admins()

        assert result.ok is True
        assert result.details["count"] == 2
        usernames = {a["username"] for a in result.admins}
        assert usernames == {"admin", "admin2"}

    def test_list_only_admins(self, db, _app_context):
        regular = User(username="regular", is_admin=False)
        regular.set_password("SecurePass1!")
        admin_u = User(username="adm", is_admin=True)
        admin_u.set_password("SecurePass1!")
        db.session.add_all([regular, admin_u])
        db.session.commit()

        result = list_admins()

        assert result.details["count"] == 1
        assert result.admins[0]["username"] == "adm"
