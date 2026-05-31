import os

os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-chars-long-for-testing"
os.environ["ADMIN_PASSWORD"] = "test-password"

import pytest
from bs4 import BeautifulSoup

from app import create_app
from app.extensions import db as _db
from app.models import User, Post, Tag
from app.utils import utc_now


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

    yield app


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
    user = User(username="admin", is_admin=True)
    user.set_password("test-password")
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


class TestInjectFooterData:
    """Tests for inject_footer_data context processor."""

    def test_footer_data_not_injected_for_admin_path(self, authenticated_client):
        """Footer data should NOT be injected for /admin/* paths."""
        response = authenticated_client.get("/admin/", follow_redirects=True)
        assert response.status_code == 200
        soup = BeautifulSoup(response.data, "html.parser")
        footer = soup.find("footer")
        assert footer is not None
        assert "Recent Posts" not in str(footer)

    def test_footer_data_is_injected_for_public_home(self, client, sample_post):
        """Footer data should be injected for public home path /."""
        response = client.get("/")
        assert response.status_code == 200
        soup = BeautifulSoup(response.data, "html.parser")
        footer = soup.find("footer")
        assert footer is not None
        assert "Recent Posts" in str(footer)

    def test_footer_data_is_injected_for_archive(self, client, sample_post):
        """Footer data should be injected for /archive path."""
        response = client.get("/archive")
        assert response.status_code == 200
        soup = BeautifulSoup(response.data, "html.parser")
        footer = soup.find("footer")
        assert footer is not None
        assert "Recent Posts" in str(footer)


class TestInjectShowFooterPosts:
    """Tests for inject_show_footer_posts context processor."""

    def test_show_footer_posts_false_for_search(self, client):
        """show_footer_posts should be False for /search path."""
        response = client.get("/search?q=test")
        assert response.status_code == 200
        soup = BeautifulSoup(response.data, "html.parser")
        footer = soup.find("footer")
        assert "Recent Posts" not in str(footer)

    def test_show_footer_posts_false_for_tag(self, client, sample_tag):
        """show_footer_posts should be False for /tag/ path."""
        response = client.get("/tag/python")
        assert response.status_code == 200
        soup = BeautifulSoup(response.data, "html.parser")
        footer = soup.find("footer")
        assert "Recent Posts" not in str(footer)

    def test_show_footer_posts_true_for_home(self, client, sample_post):
        """show_footer_posts should be True for / path."""
        response = client.get("/")
        assert response.status_code == 200
        soup = BeautifulSoup(response.data, "html.parser")
        footer = soup.find("footer")
        assert "Recent Posts" in str(footer)

    def test_show_footer_posts_true_for_archive(self, client, sample_post):
        """show_footer_posts should be True for /archive path."""
        response = client.get("/archive")
        assert response.status_code == 200
        soup = BeautifulSoup(response.data, "html.parser")
        footer = soup.find("footer")
        assert "Recent Posts" in str(footer)


class TestInjectConfig:
    """Tests for inject_config context processor."""

    def test_inject_config_includes_site_title(self, client):
        """inject_config should include site_title."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"<title>" in response.data

    def test_inject_config_includes_canonical_url(self, client, sample_post):
        """inject_config should include canonical_url in the page."""
        response = client.get("/post/test-post")
        assert response.status_code == 200
        assert b"canonical" in response.data.lower()

    def test_inject_config_includes_current_year(self, client):
        """inject_config should include current_year."""
        from datetime import datetime

        response = client.get("/")
        assert response.status_code == 200
        assert str(datetime.now().year).encode() in response.data
