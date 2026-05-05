"""Tests for admin post revision routes."""

import pytest


class TestPostRevisions:
    """Tests for post_revisions route."""

    def test_post_revisions_requires_auth(self, client):
        """Test that post revisions requires authentication."""
        response = client.get("/admin/posts/1/revisions")
        assert response.status_code == 302

    def test_post_revisions_nonexistent_post(self, authenticated_client):
        """Test viewing revisions for nonexistent post."""
        response = authenticated_client.get("/admin/posts/99999/revisions")
        assert response.status_code == 404

    def test_post_revisions_empty(self, authenticated_client, sample_post, db):
        """Test viewing revisions when no revisions exist."""
        response = authenticated_client.get(f"/admin/posts/{sample_post.id}/revisions")
        assert response.status_code == 200
        assert b"revisions" in response.data.lower()

    def test_post_revisions_with_revisions(self, authenticated_client, sample_post, db, admin_user):
        """Test viewing revisions list."""
        from app.models import PostRevision

        revision = PostRevision(
            post_id=sample_post.id,
            title="Previous Title",
            slug=sample_post.slug,
            body="Previous body",
            summary="Previous summary",
            author_id=admin_user.id
        )
        db.session.add(revision)
        db.session.commit()

        response = authenticated_client.get(f"/admin/posts/{sample_post.id}/revisions")
        assert response.status_code == 200
        assert b"Previous Title" in response.data


class TestRestoreRevision:
    """Tests for restore_revision route."""

    def test_restore_revision_requires_auth(self, client):
        """Test that restore revision requires authentication."""
        response = client.post("/admin/posts/1/revisions/1/restore")
        assert response.status_code == 302

    def test_restore_revision_nonexistent_post(self, authenticated_client):
        """Test restoring revision for nonexistent post."""
        response = authenticated_client.post("/admin/posts/99999/revisions/1/restore")
        assert response.status_code == 404

    def test_restore_revision_nonexistent_revision(self, authenticated_client, sample_post):
        """Test restoring nonexistent revision."""
        response = authenticated_client.post(
            f"/admin/posts/{sample_post.id}/revisions/99999/restore"
        )
        assert response.status_code == 404

    def test_restore_revision_wrong_post_id(self, authenticated_client, sample_post, db, admin_user):
        """Test restoring revision to wrong post."""
        from app.models import PostRevision, Post

        other_post = Post(
            title="Other Post",
            slug="other-post",
            body="Other body",
            published=True
        )
        db.session.add(other_post)
        db.session.commit()

        revision = PostRevision(
            post_id=other_post.id,
            title="Other Title",
            slug="other-slug",
            body="Other body content",
            summary="Other summary",
            author_id=admin_user.id
        )
        db.session.add(revision)
        db.session.commit()

        response = authenticated_client.post(
            f"/admin/posts/{sample_post.id}/revisions/{revision.id}/restore"
        )
        assert response.status_code == 404

    def test_restore_revision_success(self, authenticated_client, sample_post, db, admin_user):
        """Test successfully restoring a revision."""
        from app.models import PostRevision

        original_title = sample_post.title
        original_body = sample_post.body

        revision = PostRevision(
            post_id=sample_post.id,
            title="Revise Title",
            slug=sample_post.slug,
            body="Revised body content",
            summary="Revised summary",
            author_id=admin_user.id
        )
        db.session.add(revision)
        db.session.commit()
        revision_id = revision.id

        response = authenticated_client.post(
            f"/admin/posts/{sample_post.id}/revisions/{revision_id}/restore",
            follow_redirects=True
        )
        assert response.status_code == 200

        db.session.expire(sample_post)
        sample_post = db.session.get(type(sample_post), sample_post.id)
        assert sample_post.title == "Revise Title"
        assert sample_post.body == "Revised body content"