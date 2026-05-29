import pytest
from app.models import Comment


def test_add_comment_success(client, db, sample_post):
    """Test submitting a comment successfully."""
    response = client.post(
        f"/post/{sample_post.slug}/comment",
        data={
            "author_name": "Test Author",
            "author_email": "test@example.com",
            "content": "Great post!"
        },
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Comment submitted" in response.data
    # Check comment was created (unapproved)
    comment = db.session.execute(
        db.select(Comment).filter_by(post_id=sample_post.id)
    ).scalar_one_or_none()
    assert comment is not None
    assert comment.author_name == "Test Author"
    assert comment.approved is False


def test_add_comment_missing_fields(client, db, sample_post):
    """Test submitting comment with missing fields."""
    response = client.post(
        f"/post/{sample_post.slug}/comment",
        data={
            "author_name": "",
            "author_email": "test@example.com",
            "content": "Great post!"
        },
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"All fields are required" in response.data


def test_add_comment_invalid_post(client):
    """Test submitting comment to non-existent post."""
    response = client.post(
        "/post/nonexistent/comment",
        data={
            "author_name": "Test Author",
            "author_email": "test@example.com",
            "content": "Great post!"
        },
        follow_redirects=True
    )
    assert response.status_code == 404


def test_add_comment_honeypot(client, db, sample_post):
    """Honeypot submissions should be silently rejected without error."""
    response = client.post(
        f"/post/{sample_post.slug}/comment",
        data={
            "author_name": "Spam Bot",
            "author_email": "spam@example.com",
            "content": "Buy now! Click here! http://spam.com",
            "website_url": "http://spammersite.com"
        },
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Comment submitted" in response.data
    comment = db.session.execute(
        db.select(Comment).filter_by(post_id=sample_post.id)
    ).scalar_one_or_none()
    assert comment is None


def test_add_comment_too_short(client, db, sample_post):
    """Comments below minimum length should be rejected."""
    response = client.post(
        f"/post/{sample_post.slug}/comment",
        data={
            "author_name": "Test Author",
            "author_email": "test@example.com",
            "content": "AB"
        },
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"at least" in response.data


def test_add_comment_too_long(client, db, sample_post):
    """Comments above maximum length should be rejected."""
    response = client.post(
        f"/post/{sample_post.slug}/comment",
        data={
            "author_name": "Test Author",
            "author_email": "test@example.com",
            "content": "A" * 10000
        },
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"no more than" in response.data
