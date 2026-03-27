import os
import pytest
from app import create_app
from app.extensions import db as _db
from app.models import User, Post, Tag
from app.utils import utc_now


def _datetime_now():
    """Get current UTC datetime."""
    return utc_now()


@pytest.fixture(scope='session')
def app(tmp_path_factory):
    """Create application for the test session."""
    db_dir = tmp_path_factory.mktemp("blog_test")
    db_path = db_dir / "test.db"

    os.environ['SECRET_KEY'] = 'test-secret-key'
    os.environ['ADMIN_PASSWORD'] = 'test-password'

    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'CSRF_ENABLED': False,
    })

    with app.app_context():
        _db.create_all()
        yield app


@pytest.fixture(scope='function')
def db(app):
    """Create database tables for each test."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture(scope='function')
def client(app, db):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def admin_user(db):
    """Create an admin user."""
    user = User(username='admin')
    user.set_password('testpassword')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture(scope='function')
def authenticated_client(client, admin_user):
    """Create authenticated test client."""
    client.post('/admin/login', data={
        'username': 'admin',
        'password': 'testpassword',
    })
    return client


@pytest.fixture(scope='function')
def sample_post(db, admin_user):
    """Create a sample published post."""
    post = Post(
        title='Test Post',
        slug='test-post',
        body='# Hello World\n\nThis is a test post.',
        summary='A test post summary',
        published=True,
        published_at=_datetime_now()
    )
    db.session.add(post)
    db.session.commit()
    return post


@pytest.fixture(scope='function')
def sample_tag(db):
    """Create a sample tag."""
    tag = Tag(name='Python', slug='python')
    db.session.add(tag)
    db.session.commit()
    return tag
