import pytest
from click.testing import CliRunner
from app import create_app
from app.models import User, Post, Tag, Subscriber, Page
from app.utils import utc_now
import json
import tempfile
import os


@pytest.fixture
def cli_app(db):
    """Create app with CLI commands registered."""
    app = create_app()
    return app


@pytest.fixture
def runner(cli_app):
    """Click CLI test runner."""
    return CliRunner()


def test_rebuild_search_command(runner, cli_app, db, sample_post):
    """Test rebuild-search CLI command."""
    result = runner.invoke(cli_app.cli, ["rebuild-search"])
    assert result.exit_code == 0
    assert "Search index rebuilt" in result.output


def test_cleanup_orphaned_images_command(runner, cli_app, db):
    """Test cleanup-orphaned-images CLI command."""
    result = runner.invoke(cli_app.cli, ["cleanup-orphaned-images"])
    assert result.exit_code == 0
    assert "Cleaned up" in result.output


def test_create_admin_command_success(runner, cli_app, db):
    """Test create-admin CLI command."""
    result = runner.invoke(
        cli_app.cli, ["create-admin"],
        input="testadmin\nPassword123!\nPassword123!\n"
    )
    assert result.exit_code == 0
    assert "Admin user 'testadmin' created" in result.output
    user = db.session.execute(
        db.select(User).filter_by(username="testadmin")
    ).scalar_one_or_none()
    assert user is not None
    assert user.is_admin is True


def test_create_admin_command_weak_password(runner, cli_app, db):
    """Test create-admin rejects weak passwords."""
    result = runner.invoke(
        cli_app.cli, ["create-admin"],
        input="testadmin\nweak\nweak\n"
    )
    assert result.exit_code == 0
    assert "Password must be at least" in result.output


def test_promote_admin_command_success(runner, cli_app, db, admin_user):
    """Test promote-admin CLI command."""
    user = User(username="regular", is_admin=False)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    result = runner.invoke(cli_app.cli, ["promote-admin", "regular"])
    assert result.exit_code == 0
    assert "User 'regular' promoted to admin" in result.output
    db.session.expire(user)
    user = db.session.get(User, user.id)
    assert user.is_admin is True


def test_promote_admin_command_user_not_found(runner, cli_app, db):
    """Test promote-admin with non-existent user."""
    result = runner.invoke(cli_app.cli, ["promote-admin", "nonexistent"])
    assert result.exit_code == 0
    assert "User 'nonexistent' not found" in result.output


def test_check_integrity_command(runner, cli_app, db):
    """Test check-integrity CLI command."""
    result = runner.invoke(cli_app.cli, ["check-integrity"])
    assert result.exit_code == 0
    assert "Database integrity check passed" in result.output


def test_export_data_command(runner, cli_app, db, sample_post, sample_tag, sample_subscriber):
    """Test export-data CLI command."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        tmp_path = f.name
    try:
        result = runner.invoke(cli_app.cli, ["export-data", tmp_path])
        assert result.exit_code == 0
        assert "Exported" in result.output
        with open(tmp_path, "r") as f:
            data = json.load(f)
        assert "posts" in data
        assert "subscribers" in data
        assert "tags" in data
        assert "pages" in data
    finally:
        os.unlink(tmp_path)


def test_import_data_command(runner, cli_app, db):
    """Test import-data CLI command."""
    sample_data = {
        "version": 1,
        "tags": [{"name": "imported-tag", "slug": "imported-tag"}],
        "posts": [],
        "subscribers": [],
        "pages": []
    }
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(sample_data, f)
        tmp_path = f.name
    try:
        result = runner.invoke(cli_app.cli, ["import-data", tmp_path])
        assert result.exit_code == 0
        assert "Imported" in result.output
        tag = db.session.execute(
            db.select(Tag).filter_by(slug="imported-tag")
        ).scalar_one_or_none()
        assert tag is not None
    finally:
        os.unlink(tmp_path)


def test_seed_command(runner, cli_app, db):
    """Test seed CLI command."""
    result = runner.invoke(cli_app.cli, ["seed", "--posts", "2", "--subscribers", "3", "--published"])
    assert result.exit_code == 0
    assert "Seed complete" in result.output
    posts = db.session.execute(db.select(Post)).scalars().all()
    assert len(posts) == 2
    subscribers = db.session.execute(db.select(Subscriber)).scalars().all()
    assert len(subscribers) == 3
