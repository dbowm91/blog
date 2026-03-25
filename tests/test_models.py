import pytest
from app.models import User, Post, Tag, Subscriber
from app.utils import generate_slug


def test_user_password_hashing(db):
    """Test user password hashing."""
    user = User(username='testuser')
    user.set_password('mypassword')
    assert user.password_hash != 'mypassword'
    assert user.check_password('mypassword')
    assert not user.check_password('wrongpassword')


def test_post_slug_generation(db):
    """Test post slug generation."""
    slug = Post.generate_slug('Hello World!')
    assert slug == 'hello-world'


def test_post_slug_special_chars(db):
    """Test slug generation with special characters."""
    slug = Post.generate_slug('Python 3.10: What\'s New?')
    assert slug == 'python-310-whats-new'


def test_generate_slug_util():
    """Test utility slug generation."""
    assert generate_slug('Hello World') == 'hello-world'
    assert generate_slug('  Spaces  ') == 'spaces'
    assert generate_slug('Multiple   Spaces') == 'multiple-spaces'


def test_tag_creation(db):
    """Test tag creation."""
    tag = Tag(name='JavaScript', slug='javascript')
    db.session.add(tag)
    db.session.commit()
    assert tag.id is not None
    assert tag.name == 'JavaScript'
    assert tag.slug == 'javascript'


def test_post_with_tags(db):
    """Test post with tags relationship."""
    tag1 = Tag(name='Python', slug='python')
    tag2 = Tag(name='Flask', slug='flask')
    db.session.add_all([tag1, tag2])
    
    post = Post(
        title='Test Post',
        slug='test-post',
        body='Content here',
        published=True,
    )
    post.tags.extend([tag1, tag2])
    db.session.add(post)
    db.session.commit()
    
    assert len(post.tags) == 2
    assert tag1 in post.tags
    assert tag2 in post.tags


def test_subscriber_creation(db):
    """Test subscriber creation with token."""
    sub = Subscriber(email='test@example.com')
    db.session.add(sub)
    db.session.commit()
    
    assert sub.id is not None
    assert sub.email == 'test@example.com'
    assert sub.token is not None
    assert len(sub.token) == 32  # UUID hex length
    assert sub.confirmed is False


def test_subscriber_confirmation(db):
    """Test subscriber confirmation."""
    sub = Subscriber(email='test@example.com')
    db.session.add(sub)
    db.session.commit()
    
    sub.confirmed = True
    db.session.commit()
    
    assert sub.confirmed is True
