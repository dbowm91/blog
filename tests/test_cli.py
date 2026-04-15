import os
import pytest

os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-chars-long-for-testing"
os.environ["ADMIN_PASSWORD"] = "test-password"

from click.testing import CliRunner
from app import create_app
from app.extensions import db
from app.models import User


@pytest.fixture(scope="function")
def app_with_db(tmp_path):
    """Create application with a temporary database for CLI tests."""
    db_dir = tmp_path / "blog_test"
    db_dir.mkdir()
    db_path = db_dir / "test.db"

    os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "CSRF_ENABLED": False,
        }
    )

    with app.app_context():
        db.create_all()
        from app.search import init_fts

        init_fts()
        yield app
        db.session.remove()
        db.drop_all()
        db.session.remove()


@pytest.fixture
def runner(app_with_db):
    """Create a CLI test runner."""
    return app_with_db.test_cli_runner()


class TestRebuildSearch:
    def test_rebuild_search_command(self, runner):
        """Test that rebuild-search command executes without error."""
        result = runner.invoke(args=["rebuild-search"])
        assert result.exit_code == 0
        assert "Search index rebuilt" in result.output


class TestCreateAdmin:
    def test_create_admin_new_user(self, app_with_db, runner):
        """Test creating a new admin user via CLI."""
        result = runner.invoke(
            args=["create-admin"], input="newadmin\nSecurePass123!\nSecurePass123!\n"
        )
        assert result.exit_code == 0
        assert "Admin user 'newadmin' created" in result.output

        with app_with_db.app_context():
            user = db.session.execute(
                db.select(User).filter_by(username="newadmin")
            ).scalar_one_or_none()
            assert user is not None
            assert user.is_admin is True
            assert user.check_password("SecurePass123!")

    def test_create_admin_promote_existing(self, app_with_db, runner):
        """Test promoting an existing user to admin."""
        with app_with_db.app_context():
            user = User(username="existinguser", is_admin=False)
            user.set_password("OldPass123")
            db.session.add(user)
            db.session.commit()
            db.session.flush()
            user_id = user.id

        with app_with_db.app_context():
            result = runner.invoke(
                args=["create-admin"], input="existinguser\nNewPass456!\nNewPass456!\n"
            )
        assert result.exit_code == 0, result.output
        assert "promoted to admin" in result.output

        with app_with_db.app_context():
            user = db.session.get(User, user_id)
            assert user.is_admin is True
            assert user.check_password("NewPass456!")

    def test_create_admin_password_too_short(self, runner):
        """Test that password too short is rejected."""
        result = runner.invoke(
            args=["create-admin"], input="shortuser\nshort1!\nshort1!\n"
        )
        assert (
            result.exit_code != 0
            or "Password must be at least 8 characters" in result.output
        )

    def test_create_admin_password_too_simple(self, runner):
        """Test that password without enough complexity is rejected."""
        result = runner.invoke(
            args=["create-admin"], input="simpleuser\npassword\npassword\n"
        )
        assert (
            result.exit_code != 0
            or "Password must be at least 8 characters" in result.output
        )

    def test_create_admin_password_missing_uppercase(self, runner):
        """Test that password without uppercase is rejected."""
        result = runner.invoke(
            args=["create-admin"], input="noupperuser\npass1234\npass1234\n"
        )
        assert (
            result.exit_code != 0
            or "Password must be at least 8 characters" in result.output
        )

    def test_create_admin_password_missing_digit(self, runner):
        """Test that password without digit is rejected."""
        result = runner.invoke(
            args=["create-admin"], input="nodigituser\npassword!\npassword!\n"
        )
        assert (
            result.exit_code != 0
            or "Password must be at least 8 characters" in result.output
        )

    def test_create_admin_password_missing_special(self, runner):
        """Test that password without special character is rejected."""
        result = runner.invoke(
            args=["create-admin"], input="nospecialuser\nPasswordAB\nPasswordAB\n"
        )
        assert (
            result.exit_code != 0
            or "Password must be at least 8 characters" in result.output
        )
