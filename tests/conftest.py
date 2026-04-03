import os
import pytest
from unittest.mock import patch
from app import create_app
from app.extensions import db as _db
from app.models import User, Post, Tag
from app.utils import utc_now


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    """Create application for the test session."""
    db_dir = tmp_path_factory.mktemp("blog_test")
    db_path = db_dir / "test.db"

    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["ADMIN_PASSWORD"] = "test-password"
    os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "CSRF_ENABLED": False,
        }
    )

    yield app


@pytest.fixture(scope="function")
def db(app):
    """Create database tables for each test."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app, db):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def admin_user(db):
    """Create an admin user."""
    existing = db.session.execute(
        db.select(User).filter_by(username="admin")
    ).scalar_one_or_none()
    if existing:
        return existing
    user = User(username="admin", is_admin=True)
    user.set_password("testpassword")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture(scope="function")
def authenticated_client(client, admin_user):
    """Create authenticated test client."""
    client.post(
        "/admin/login",
        data={
            "username": "admin",
            "password": "testpassword",
        },
    )
    return client


@pytest.fixture(scope="function")
def sample_post(db, admin_user):
    """Create a sample published post."""
    post = Post(
        title="Test Post",
        slug="test-post",
        body="# Hello World\n\nThis is a test post.",
        summary="A test post summary",
        published=True,
        published_at=utc_now(),
    )
    db.session.add(post)
    db.session.commit()
    return post


@pytest.fixture(scope="function")
def sample_tag(db):
    """Create a sample tag."""
    tag = Tag(name="Python", slug="python")
    db.session.add(tag)
    db.session.commit()
    return tag


@pytest.fixture(scope="function")
def mock_render():
    """Mock for email template rendering."""
    with patch("app.email.render_template") as mock:
        mock.return_value = "<html>Mock</html>"
        yield mock


@pytest.fixture(scope="function")
def clean_analytics_cache():
    """Clear analytics cache before each test to prevent cross-test pollution."""
    from app.routes.admin import _analytics_cache

    _analytics_cache.clear()
    yield
    _analytics_cache.clear()
