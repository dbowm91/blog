"""Shared fixtures for benchmark tests."""

import os
import pytest
from tests.shared_fixtures import *  # noqa: F401, F403
from tests.conftest import TEST_PASSWORD

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")
os.environ["PAGE_VIEW_BUFFER_SIZE"] = "0"


from app import create_app
from app.extensions import db as _db
from app.models import User, Post, Subscriber
from app.utils import utc_now
from app.search import init_fts, sync_fts


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    """Create application for the benchmark session."""
    db_dir = tmp_path_factory.mktemp("blog_bench")
    db_path = db_dir / "bench.db"

    os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "CSRF_ENABLED": False,
        }
    )

    from celery import current_app as celery_app

    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )

    yield app


@pytest.fixture(scope="module")
def db(app):
    """Create database tables for benchmarks.

    The scope is module, not session: the fixture yields inside
    ``app.app_context()``, so a session-scoped fixture would leave that
    context pushed for every test that follows, in every other directory.
    """
    with app.app_context():
        _db.session.remove()
        _db.create_all()
        init_fts()
        yield _db
        _db.engine.dispose()
        _db.session.remove()
        _db.drop_all()
        _db.session.remove()


@pytest.fixture(scope="function")
def clean_db(db):
    """Clean up data after each test function, keeping user."""
    yield db
    db.session.rollback()
    with db.session.begin_nested():
        for table in reversed(db.metadata.sorted_tables):
            if table.name not in ("users", "alembic_version"):
                db.session.execute(table.delete())
        db.session.commit()


@pytest.fixture(scope="function")
def admin_user(clean_db):
    """Create an admin user (function scoped, fresh each test)."""
    existing = clean_db.session.execute(
        clean_db.select(User).filter_by(username="admin")
    ).scalar_one_or_none()
    if existing:
        return existing
    user = User(username="admin", email="admin@example.com", is_admin=True)
    user.set_password(TEST_PASSWORD)
    clean_db.session.add(user)
    clean_db.session.commit()
    return user


@pytest.fixture(scope="function")
def authenticated_client(app, admin_user, clean_db):
    """Create authenticated test client."""
    with app.test_client() as client:
        client.post(
            "/admin/login",
            data={
                "username": "admin",
                "password": TEST_PASSWORD,
            },
        )
        yield client


def create_posts_bulk(db, count=50):
    """Helper to create multiple posts for benchmarking."""
    timestamp = utc_now().timestamp()
    titles = [f"Test Post {i} - Flask Web Development Guide" for i in range(count)]
    slugs = [f"bench-post-{i}-{timestamp}-{i}" for i in range(count)]
    bodies = [
        f"# Article {i}\n\nThis is the body content for post {i}. "
        f"It contains useful information about Flask and Python programming. "
        f"This text is intentionally longer to simulate real content."
        for i in range(count)
    ]
    summaries = [f"Summary for post {i} about Flask web development" for i in range(count)]

    for i in range(count):
        post = Post(
            title=titles[i],
            slug=slugs[i],
            body=bodies[i],
            summary=summaries[i],
            published=True,
            published_at=utc_now(),
        )
        db.session.add(post)
    db.session.commit()

    posts = db.session.execute(db.select(Post).filter(Post.slug.in_(slugs))).scalars().all()

    for post in posts:
        sync_fts(post.id, post.title, post.body, post.summary, post.published)
    db.session.commit()

    return list(posts)


def create_subscribers_bulk(db, count=100):
    """Helper to create multiple subscribers for benchmarking."""
    subscribers = []
    timestamp = utc_now().timestamp()
    for i in range(count):
        sub = Subscriber(
            email=f"bench{i}-{timestamp}@example.com",
            token=f"bench-token-{timestamp}-{i}",
            confirmed=True,
            created_at=utc_now(),
        )
        subscribers.append(sub)
    db.session.add_all(subscribers)
    db.session.commit()
    return subscribers
