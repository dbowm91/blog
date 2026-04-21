"""Tests for REST API endpoints."""

import os
import pytest

os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-chars-long-for-testing"
os.environ["ADMIN_PASSWORD"] = "test-password"
os.environ["API_KEY"] = "test-api-key-12345"

from app import create_app
from app.extensions import db as _db
from app.models import User, Post, Tag, Subscriber, PageView, ShareEvent
from app.utils import utc_now


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    """Create application for the test session."""
    db_dir = tmp_path_factory.mktemp("blog_api_test")
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
    existing = db.session.execute(
        _db.select(User).filter_by(username="admin")
    ).scalar_one_or_none()
    if existing:
        return existing
    user = User(username="admin", is_admin=True)
    user.set_password("testpassword")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture(scope="function")
def api_client(client, admin_user):
    """Create test client with valid API key."""
    client.post(
        "/admin/login",
        data={
            "username": "admin",
            "password": "testpassword",
        },
    )
    return client


def test_api_requires_key(client):
    """Test that API endpoints require API key."""
    response = client.get("/api/posts")
    assert response.status_code == 401
    assert b"Invalid or missing API key" in response.data


def test_api_rejects_wrong_key(client):
    """Test that API endpoints reject wrong API key."""
    response = client.get("/api/posts", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401
    assert b"Invalid or missing API key" in response.data


def test_list_posts_empty(api_client):
    """Test listing posts when none exist."""
    response = api_client.get("/api/posts", headers={"X-API-Key": "test-api-key-12345"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["posts"] == []
    assert data["total"] == 0
    assert data["page"] == 1


def test_list_posts_with_data(api_client, db, admin_user):
    """Test listing posts with existing data."""
    post = Post(
        title="Test Post",
        slug="test-post",
        body="# Hello\n\nTest content",
        summary="A test post",
        published=True,
        published_at=utc_now(),
    )
    db.session.add(post)
    db.session.commit()

    response = api_client.get("/api/posts", headers={"X-API-Key": "test-api-key-12345"})
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["posts"]) == 1
    assert data["posts"][0]["title"] == "Test Post"
    assert data["total"] == 1


def test_list_posts_pagination(api_client, db, admin_user):
    """Test posts pagination."""
    for i in range(25):
        post = Post(
            title=f"Post {i}",
            slug=f"post-{i}",
            body=f"Body {i}",
            published=True,
        )
        db.session.add(post)
    db.session.commit()

    response = api_client.get(
        "/api/posts?page=1&per_page=10",
        headers={"X-API-Key": "test-api-key-12345"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["posts"]) == 10
    assert data["total"] == 25
    assert data["pages"] == 3
    assert data["page"] == 1


def test_list_posts_filter_published(api_client, db, admin_user):
    """Test filtering posts by published status."""
    published = Post(
        title="Published",
        slug="published",
        body="Body",
        published=True,
    )
    draft = Post(
        title="Draft",
        slug="draft",
        body="Body",
        published=False,
    )
    db.session.add_all([published, draft])
    db.session.commit()

    response = api_client.get(
        "/api/posts?published=true",
        headers={"X-API-Key": "test-api-key-12345"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["posts"]) == 1
    assert data["posts"][0]["title"] == "Published"


def test_get_post(api_client, db, admin_user):
    """Test getting a single post."""
    post = Post(
        title="Test Post",
        slug="test-post",
        body="# Hello\n\nTest content",
        summary="A test post",
        published=True,
        published_at=utc_now(),
    )
    db.session.add(post)
    db.session.commit()

    response = api_client.get(
        f"/api/posts/{post.id}",
        headers={"X-API-Key": "test-api-key-12345"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["title"] == "Test Post"
    assert data["slug"] == "test-post"
    assert data["body"] == "# Hello\n\nTest content"
    assert data["summary"] == "A test post"
    assert data["published"] is True


def test_get_post_not_found(api_client):
    """Test getting a non-existent post."""
    response = api_client.get(
        "/api/posts/9999",
        headers={"X-API-Key": "test-api-key-12345"},
    )
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "Post not found"


def test_create_post(api_client, db, admin_user):
    """Test creating a post."""
    response = api_client.post(
        "/api/posts",
        headers={"X-API-Key": "test-api-key-12345"},
        json={
            "title": "New Post",
            "body": "# New Content\n\nSome content",
            "summary": "A new post",
            "published": True,
        },
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["title"] == "New Post"
    assert data["body"] == "# New Content\n\nSome content"
    assert data["summary"] == "A new post"
    assert data["published"] is True
    assert "id" in data


def test_create_post_with_tags(api_client, db, admin_user):
    """Test creating a post with tags."""
    tag = Tag(name="Python", slug="python")
    db.session.add(tag)
    db.session.commit()

    response = api_client.post(
        "/api/posts",
        headers={"X-API-Key": "test-api-key-12345"},
        json={
            "title": "Tagged Post",
            "body": "Content",
            "tags": ["Python", "NewTag"],
        },
    )
    assert response.status_code == 201
    data = response.get_json()
    assert "Python" in data["tags"]
    assert "NewTag" in data["tags"]


def test_create_post_missing_title(api_client):
    """Test creating a post without title."""
    response = api_client.post(
        "/api/posts",
        headers={"X-API-Key": "test-api-key-12345"},
        json={
            "body": "Content without title",
        },
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "title is required" in data["error"]


def test_create_post_missing_body(api_client):
    """Test creating a post without body."""
    response = api_client.post(
        "/api/posts",
        headers={"X-API-Key": "test-api-key-12345"},
        json={
            "title": "Title only",
        },
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "body is required" in data["error"]


def test_update_post(api_client, db, admin_user):
    """Test updating a post."""
    post = Post(
        title="Original Title",
        slug="original",
        body="Original body",
        summary="Original summary",
        published=False,
    )
    db.session.add(post)
    db.session.commit()

    response = api_client.put(
        f"/api/posts/{post.id}",
        headers={"X-API-Key": "test-api-key-12345"},
        json={
            "title": "Updated Title",
            "body": "Updated body",
            "published": True,
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["title"] == "Updated Title"
    assert data["body"] == "Updated body"
    assert data["published"] is True
    assert data["slug"] == "original"


def test_update_post_not_found(api_client):
    """Test updating a non-existent post."""
    response = api_client.put(
        "/api/posts/9999",
        headers={"X-API-Key": "test-api-key-12345"},
        json={
            "title": "Updated",
        },
    )
    assert response.status_code == 404


def test_delete_post(api_client, db, admin_user):
    """Test deleting a post."""
    post = Post(
        title="To Delete",
        slug="to-delete",
        body="Body",
        published=True,
    )
    db.session.add(post)
    db.session.commit()
    post_id = post.id

    response = api_client.delete(
        f"/api/posts/{post_id}",
        headers={"X-API-Key": "test-api-key-12345"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Post deleted successfully"

    deleted = db.session.get(Post, post_id)
    assert deleted is None


def test_delete_post_not_found(api_client):
    """Test deleting a non-existent post."""
    response = api_client.delete(
        "/api/posts/9999",
        headers={"X-API-Key": "test-api-key-12345"},
    )
    assert response.status_code == 404


def test_list_subscribers_empty(api_client):
    """Test listing subscribers when none exist."""
    response = api_client.get(
        "/api/subscribers",
        headers={"X-API-Key": "test-api-key-12345"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["subscribers"] == []
    assert data["total"] == 0


def test_list_subscribers_with_data(api_client, db, admin_user):
    """Test listing subscribers with existing data."""
    sub = Subscriber(
        email="test@example.com",
        confirmed=True,
    )
    db.session.add(sub)
    db.session.commit()

    response = api_client.get(
        "/api/subscribers",
        headers={"X-API-Key": "test-api-key-12345"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["subscribers"]) == 1
    assert data["subscribers"][0]["email"] == "test@example.com"


def test_list_subscribers_filter_confirmed(api_client, db, admin_user):
    """Test filtering subscribers by confirmed status."""
    confirmed = Subscriber(
        email="confirmed@example.com",
        confirmed=True,
    )
    unconfirmed = Subscriber(
        email="unconfirmed@example.com",
        confirmed=False,
    )
    db.session.add_all([confirmed, unconfirmed])
    db.session.commit()

    response = api_client.get(
        "/api/subscribers?confirmed=true",
        headers={"X-API-Key": "test-api-key-12345"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["subscribers"]) == 1
    assert data["subscribers"][0]["email"] == "confirmed@example.com"


def test_create_subscriber(api_client, db, admin_user):
    """Test creating a subscriber."""
    response = api_client.post(
        "/api/subscribers",
        headers={"X-API-Key": "test-api-key-12345"},
        json={
            "email": "new@example.com",
        },
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["email"] == "new@example.com"
    assert data["confirmed"] is False


def test_create_subscriber_duplicate(api_client, db, admin_user):
    """Test creating a duplicate subscriber returns existing."""
    existing = Subscriber(
        email="existing@example.com",
        confirmed=True,
    )
    db.session.add(existing)
    db.session.commit()

    response = api_client.post(
        "/api/subscribers",
        headers={"X-API-Key": "test-api-key-12345"},
        json={
            "email": "existing@example.com",
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["email"] == "existing@example.com"


def test_create_subscriber_invalid_email(api_client):
    """Test creating a subscriber with invalid email."""
    response = api_client.post(
        "/api/subscribers",
        headers={"X-API-Key": "test-api-key-12345"},
        json={
            "email": "not-an-email",
        },
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "Invalid email format" in data["error"]


def test_create_subscriber_missing_email(api_client, admin_user):
    """Test creating a subscriber without email."""
    response = api_client.post(
        "/api/subscribers",
        headers={"X-API-Key": "test-api-key-12345"},
        json={},
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "email is required" in data["error"]


def test_delete_subscriber(api_client, db, admin_user):
    """Test deleting a subscriber."""
    sub = Subscriber(
        email="to-delete@example.com",
        confirmed=True,
    )
    db.session.add(sub)
    db.session.commit()
    sub_id = sub.id

    response = api_client.delete(
        f"/api/subscribers/{sub_id}",
        headers={"X-API-Key": "test-api-key-12345"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Subscriber deleted successfully"

    deleted = db.session.get(Subscriber, sub_id)
    assert deleted is None


def test_delete_subscriber_not_found(api_client):
    """Test deleting a non-existent subscriber."""
    response = api_client.delete(
        "/api/subscribers/9999",
        headers={"X-API-Key": "test-api-key-12345"},
    )
    assert response.status_code == 404


def test_get_stats(api_client, db, admin_user):
    """Test getting dashboard stats."""
    post = Post(
        title="Test",
        slug="test",
        body="Body",
        published=True,
    )
    db.session.add(post)
    db.session.commit()

    view = PageView(post_id=post.id)
    db.session.add(view)

    share = ShareEvent(post_id=post.id, platform="twitter")
    db.session.add(share)

    sub = Subscriber(email="sub@example.com", confirmed=True)
    db.session.add(sub)
    db.session.commit()

    response = api_client.get(
        "/api/stats",
        headers={"X-API-Key": "test-api-key-12345"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["total_views"] == 1
    assert data["total_posts"] == 1
    assert data["total_shares"] == 1
    assert data["total_subscribers"] == 1


def test_get_stats_empty(api_client):
    """Test getting stats with no data."""
    response = api_client.get(
        "/api/stats",
        headers={"X-API-Key": "test-api-key-12345"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["total_views"] == 0
    assert data["total_posts"] == 0
    assert data["total_shares"] == 0
    assert data["total_subscribers"] == 0
