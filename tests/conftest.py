import os
import shutil
import pytest
from tests.shared_fixtures import *
from unittest.mock import patch, MagicMock
from dataclasses import dataclass, field
from datetime import datetime, timezone

os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-chars-long-for-testing"
os.environ["ADMIN_PASSWORD"] = "test-password"
os.environ["TESTING"] = "True"
os.environ["PAGE_VIEW_BUFFER_SIZE"] = "0"

from app import create_app
from app.extensions import db as _db
from app.models import User, Post, Tag
from app.utils import utc_now


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    """Create application for the test session."""
    db_dir = tmp_path_factory.mktemp("blog_test")
    db_path = db_dir / "test.db"

    os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "CSRF_ENABLED": False,
        }
    )
    # Disable page view buffer in tests
    import app.config as _app_config

    _app_config.PAGE_VIEW_BUFFER_SIZE = 0
    # Stop any running buffer
    from app.page_view_buffer import shutdown_page_view_buffer

    shutdown_page_view_buffer()

    # Configure Celery to run tasks eagerly (synchronously) in tests
    from celery import current_app as celery_app

    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )

    yield app


@dataclass
class FakeSubscriber:
    """Test fixture for newsletter testing without real subscribers."""

    email: str
    token: str = "test"
    confirmed: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    unsubscribed_at: datetime | None = None


@pytest.fixture(scope="function")
def db(app):
    """Create database tables for each test."""
    with app.app_context():
        _db.session.remove()
        _db.create_all()
        from app.search import init_fts

        init_fts()
        yield _db
        _db.session.remove()
        _db.drop_all()
        _db.session.remove()


@pytest.fixture(scope="function")
def client(app, db):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def admin_user(db):
    """Create an admin user."""
    existing = db.session.execute(db.select(User).filter_by(username="admin")).scalar_one_or_none()
    if existing:
        return existing
    user = User(username="admin", email="admin@example.com", is_admin=True)
    user.set_password(os.environ["ADMIN_PASSWORD"])
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
            "password": "test-password",
        },
    )
    return client


@pytest.fixture(scope="function")
def api_client(client, admin_user):
    """Create test client with valid API key."""
    client.post(
        "/admin/login",
        data={
            "username": "admin",
            "password": "test-password",
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
def sample_subscriber(db):
    """Create a sample confirmed subscriber."""
    from app.models import Subscriber

    sub = Subscriber(email="test@example.com", confirmed=True)
    db.session.add(sub)
    db.session.commit()
    return sub


@pytest.fixture(scope="function")
def mock_render():
    """Mock for email template rendering."""
    with patch("app.email.render_template") as mock:
        mock.return_value = "<html>Mock</html>"
        yield mock


@pytest.fixture(scope="function")
def mock_smtp():
    """Mock SMTP connection and sendmail for email tests."""
    mock_server = MagicMock()
    mock_server.sendmail = MagicMock()
    mock_server.quit = MagicMock()
    with patch("app.email._connect_smtp", return_value=mock_server):
        yield mock_server


@pytest.fixture(scope="function")
def mock_email(mock_render, mock_smtp):
    """Combined mock for email rendering and SMTP sending.

    Function-scoped fixtures that must be explicitly requested by tests,
    not autouse.
    """
    yield


@pytest.fixture(scope="session", autouse=True)
def cleanup_uploads():
    """Clean up uploads directory after all tests in session."""
    yield
    upload_folder = os.path.join(os.path.dirname(__file__), "..", "app", "static", "uploads")
    if not os.path.isdir(upload_folder):
        return
    for item in os.listdir(upload_folder):
        item_path = os.path.join(upload_folder, item)
        if os.path.isfile(item_path):
            os.remove(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
