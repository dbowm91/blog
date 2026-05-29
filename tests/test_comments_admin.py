import pytest
from app.models import Comment, Post
from app.utils import utc_now


def test_comments_list_authenticated(authenticated_client, db, sample_post):
    """Test comments list page loads."""
    # Create a comment
    comment = Comment(
        post_id=sample_post.id,
        author_name="Test Author",
        author_email="test@example.com",
        content="Test comment",
        approved=False
    )
    db.session.add(comment)
    db.session.commit()
    response = authenticated_client.get("/admin/comments")
    assert response.status_code == 200
    assert b"Test comment" in response.data


def test_comments_list_filter_approved(authenticated_client, db, sample_post):
    """Test comments list filters approved comments."""
    # Create approved and unapproved comments
    comment1 = Comment(
        post_id=sample_post.id,
        author_name="Author1",
        author_email="a1@example.com",
        content="Approved comment",
        approved=True
    )
    comment2 = Comment(
        post_id=sample_post.id,
        author_name="Author2",
        author_email="a2@example.com",
        content="Unapproved comment",
        approved=False
    )
    db.session.add_all([comment1, comment2])
    db.session.commit()
    # Filter approved
    response = authenticated_client.get("/admin/comments?approved=yes")
    assert response.status_code == 200
    assert b"Approved comment" in response.data
    assert b"Unapproved comment" not in response.data


def test_comments_list_filter_unapproved(authenticated_client, db, sample_post):
    """Test comments list filters unapproved comments."""
    comment1 = Comment(
        post_id=sample_post.id,
        author_name="Author1",
        author_email="a1@example.com",
        content="Approved comment",
        approved=True
    )
    comment2 = Comment(
        post_id=sample_post.id,
        author_name="Author2",
        author_email="a2@example.com",
        content="Unapproved comment",
        approved=False
    )
    db.session.add_all([comment1, comment2])
    db.session.commit()
    # Filter unapproved (default)
    response = authenticated_client.get("/admin/comments?approved=no")
    assert response.status_code == 200
    assert b"Unapproved comment" in response.data
    assert b"Approved comment" not in response.data


def test_approve_comment(authenticated_client, db, sample_post):
    """Test approving a comment."""
    comment = Comment(
        post_id=sample_post.id,
        author_name="Test Author",
        author_email="test@example.com",
        content="Test comment",
        approved=False
    )
    db.session.add(comment)
    db.session.commit()
    response = authenticated_client.post(
        f"/admin/comments/{comment.id}/approve",
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Comment approved" in response.data
    db.session.expire(comment)
    comment = db.session.get(Comment, comment.id)
    assert comment.approved is True


def test_approve_comment_not_found(authenticated_client):
    """Test approving non-existent comment returns 404."""
    response = authenticated_client.post(
        "/admin/comments/999/approve",
        follow_redirects=True
    )
    assert response.status_code == 404


def test_delete_comment(authenticated_client, db, sample_post):
    """Test deleting a comment."""
    comment = Comment(
        post_id=sample_post.id,
        author_name="Test Author",
        author_email="test@example.com",
        content="Test comment",
        approved=False
    )
    db.session.add(comment)
    db.session.commit()
    response = authenticated_client.post(
        f"/admin/comments/{comment.id}/delete",
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Comment deleted" in response.data
    deleted = db.session.execute(
        db.select(Comment).filter_by(id=comment.id)
    ).scalar_one_or_none()
    assert deleted is None


def test_delete_comment_not_found(authenticated_client):
    """Test deleting non-existent comment returns 404."""
    response = authenticated_client.post(
        "/admin/comments/999/delete",
        follow_redirects=True
    )
    assert response.status_code == 404


def test_comments_list_filter_spam(authenticated_client, db, sample_post):
    """Test comments list filters spam comments."""
    comment1 = Comment(
        post_id=sample_post.id,
        author_name="Author1",
        author_email="a1@example.com",
        content="Not spam comment",
        approved=False,
        is_spam=False,
    )
    comment2 = Comment(
        post_id=sample_post.id,
        author_name="Spammer",
        author_email="spam@example.com",
        content="BUY NOW!!!!!!! CLICK HERE!!!! https://spam.com https://spam.com https://spam.com https://spam.com",
        approved=False,
        is_spam=True,
        spam_score=0.75,
    )
    db.session.add_all([comment1, comment2])
    db.session.commit()
    # Filter spam
    response = authenticated_client.get("/admin/comments?approved=all&spam=yes")
    assert response.status_code == 200
    assert b"Spammer" in response.data
    assert b"Not spam comment" not in response.data


def test_approve_spam_comment(authenticated_client, db, sample_post):
    """Test approving a spam comment marks it as not spam."""
    comment = Comment(
        post_id=sample_post.id,
        author_name="Spammer",
        author_email="spam@example.com",
        content="Spam content",
        approved=False,
        is_spam=True,
        spam_score=0.8,
    )
    db.session.add(comment)
    db.session.commit()
    response = authenticated_client.post(
        f"/admin/comments/{comment.id}/approve",
        follow_redirects=True
    )
    assert response.status_code == 200
    db.session.expire(comment)
    comment = db.session.get(Comment, comment.id)
    assert comment.approved is True
    assert comment.is_spam is False
