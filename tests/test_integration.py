"""Integration tests covering critical user flows end-to-end."""

import io
import os
from datetime import timedelta

import pytest
from sqlalchemy import select, func

from app.models import Post, Tag, Subscriber, User, PageView
from app.utils import utc_now


# ---------------------------------------------------------------------------
# 1. Full post lifecycle
# ---------------------------------------------------------------------------

class TestPostLifecycle:
    """Create -> edit -> publish -> view publicly -> delete."""

    def test_full_post_lifecycle(self, authenticated_client, client, db, admin_user):
        # -- Create a draft post --
        resp = authenticated_client.post('/admin/new', data={
            'title': 'Lifecycle Post',
            'body': 'Initial body content.',
            'summary': 'Lifecycle summary',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Post created' in resp.data

        post = db.session.execute(
            select(Post).filter_by(title='Lifecycle Post')
        ).scalar_one()
        assert post.slug == 'lifecycle-post'
        assert post.published is False

        # -- Edit: update title and add tags --
        resp = authenticated_client.post(f'/admin/edit/{post.id}', data={
            'title': 'Lifecycle Post Updated',
            'body': 'Updated body content.',
            'summary': 'Updated summary',
            'tags': 'integration, testing',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Post updated' in resp.data

        db.session.refresh(post)
        assert post.title == 'Lifecycle Post Updated'
        assert post.slug == 'lifecycle-post-updated'
        tag_names = {t.name for t in post.tags}
        assert tag_names == {'integration', 'testing'}

        # -- Publish --
        resp = authenticated_client.post(f'/admin/edit/{post.id}', data={
            'title': 'Lifecycle Post Updated',
            'body': 'Updated body content.',
            'summary': 'Updated summary',
            'tags': 'integration, testing',
            'published': 'on',
        }, follow_redirects=True)
        assert resp.status_code == 200
        db.session.refresh(post)
        assert post.published is True
        assert post.published_at is not None

        # -- View publicly --
        resp = client.get(f'/post/{post.slug}')
        assert resp.status_code == 200
        assert b'Lifecycle Post Updated' in resp.data
        assert b'Updated body content' in resp.data

        # -- Delete --
        resp = authenticated_client.post(f'/admin/delete/{post.id}', follow_redirects=True)
        assert resp.status_code == 200
        assert b'Post deleted' in resp.data
        assert db.session.get(Post, post.id) is None


# ---------------------------------------------------------------------------
# 2. Subscription flow
# ---------------------------------------------------------------------------

class TestSubscriptionFlow:
    """Subscribe -> confirm -> unsubscribe."""

    def test_subscribe_confirm_unsubscribe(self, client, db):
        # -- Subscribe --
        resp = client.post('/subscribe', data={'email': 'flow@example.com'}, follow_redirects=True)
        assert resp.status_code == 200

        sub = db.session.execute(
            select(Subscriber).filter_by(email='flow@example.com')
        ).scalar_one()
        assert sub.confirmed is False
        token = sub.token

        # -- Confirm --
        resp = client.get(f'/confirm/{token}', follow_redirects=True)
        assert resp.status_code == 200
        db.session.refresh(sub)
        assert sub.confirmed is True

        # -- Unsubscribe --
        resp = client.get(f'/unsubscribe/{token}', follow_redirects=True)
        assert resp.status_code == 200
        db.session.refresh(sub)
        assert sub.unsubscribed_at is not None


# ---------------------------------------------------------------------------
# 3. Search flow
# ---------------------------------------------------------------------------

class TestSearchFlow:
    """Create posts -> search -> verify results."""

    def test_search_returns_matching_posts(self, client, db, admin_user):
        posts = [
            Post(title='Flask Tips', slug='flask-tips',
                 body='Learn Flask best practices.', published=True, published_at=utc_now()),
            Post(title='Django Guide', slug='django-guide',
                 body='A guide to Django.', published=True, published_at=utc_now()),
            Post(title='Python Tricks', slug='python-tricks',
                 body='Useful Python tricks.', published=True, published_at=utc_now()),
        ]
        db.session.add_all(posts)
        db.session.commit()

        # Search for "Flask"
        resp = client.get('/search?q=Flask')
        assert resp.status_code == 200
        assert b'Flask Tips' in resp.data
        assert b'Django Guide' not in resp.data

        # Search for "Python"
        resp = client.get('/search?q=Python')
        assert resp.status_code == 200
        assert b'Python Tricks' in resp.data

    def test_search_no_results(self, client, db, admin_user):
        Post(title='Only Post', slug='only-post', body='Content', published=True)
        db.session.commit()
        resp = client.get('/search?q=nonexistentxyz')
        assert resp.status_code == 200
        assert b'No posts match your search' in resp.data


# ---------------------------------------------------------------------------
# 4. Tag flow
# ---------------------------------------------------------------------------

class TestTagFlow:
    """Create posts with tags -> browse by tag -> verify counts."""

    def test_tag_browse_and_counts(self, client, db, admin_user):
        tag_py = Tag(name='Python', slug='python')
        tag_fl = Tag(name='Flask', slug='flask')
        db.session.add_all([tag_py, tag_fl])
        db.session.flush()

        p1 = Post(title='Post A', slug='post-a', body='A', published=True, published_at=utc_now())
        p2 = Post(title='Post B', slug='post-b', body='B', published=True, published_at=utc_now())
        p1.tags.extend([tag_py, tag_fl])
        p2.tags.append(tag_py)
        db.session.add_all([p1, p2])
        db.session.commit()

        # Browse Python tag
        resp = client.get('/tag/python')
        assert resp.status_code == 200
        assert b'Post A' in resp.data
        assert b'Post B' in resp.data

        # Browse Flask tag
        resp = client.get('/tag/flask')
        assert resp.status_code == 200
        assert b'Post A' in resp.data
        assert b'Post B' not in resp.data

        # Tag counts: verify via direct DB query of the post_tags join
        from app.models import post_tags
        py_count = db.session.execute(
            select(func.count()).select_from(post_tags)
            .filter(post_tags.c.tag_id == tag_py.id)
        ).scalar_one()
        fl_count = db.session.execute(
            select(func.count()).select_from(post_tags)
            .filter(post_tags.c.tag_id == tag_fl.id)
        ).scalar_one()
        assert py_count == 2
        assert fl_count == 1


# ---------------------------------------------------------------------------
# 5. Newsletter reset flow
# ---------------------------------------------------------------------------

class TestNewsletterResetFlow:
    """Create post -> mark newsletter sent -> reset."""

    def test_newsletter_reset(self, authenticated_client, db, admin_user):
        post = Post(title='NL Post', slug='nl-post', body='Body',
                    published=True, published_at=utc_now())
        db.session.add(post)
        db.session.commit()

        # Mark newsletter as sent
        post.newsletter_sent_at = utc_now()
        post.newsletter_attempts = 2
        db.session.commit()

        # Reset
        resp = authenticated_client.post(
            f'/admin/newsletter-reset/{post.id}', follow_redirects=True)
        assert resp.status_code == 200

        db.session.refresh(post)
        assert post.newsletter_sent_at is None
        assert post.newsletter_attempts == 0


# ---------------------------------------------------------------------------
# 6. Bulk operations
# ---------------------------------------------------------------------------

class TestBulkOperations:
    """Create multiple posts -> bulk publish -> bulk delete."""

    def test_bulk_publish_then_delete(self, authenticated_client, db, admin_user):
        drafts = [
            Post(title=f'Bulk {i}', slug=f'bulk-{i}', body='Content', published=False)
            for i in range(3)
        ]
        db.session.add_all(drafts)
        db.session.commit()
        ids = [p.id for p in drafts]

        # Bulk publish
        resp = authenticated_client.post('/admin/bulk', data={
            'action': 'publish',
            'post_ids': ids,
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Published 3 post(s)' in resp.data

        for pid in ids:
            p = db.session.get(Post, pid)
            assert p.published is True
            assert p.published_at is not None

        # Bulk delete
        resp = authenticated_client.post('/admin/bulk', data={
            'action': 'delete',
            'post_ids': ids,
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Deleted 3 post(s)' in resp.data

        remaining = db.session.execute(
            select(func.count()).select_from(Post).filter(Post.id.in_(ids))
        ).scalar_one()
        assert remaining == 0


# ---------------------------------------------------------------------------
# 7. Media management
# ---------------------------------------------------------------------------

class TestMediaManagement:
    """Upload image -> view in media browser -> delete it."""

    def test_upload_browse_delete_image(self, authenticated_client, db, admin_user):
        # -- Upload image via post creation --
        png_header = b'\x89PNG\r\n\x1a\n' + b'\x00' * 64
        data = {
            'title': 'Image Post',
            'body': 'Has an image.',
            'image': (io.BytesIO(png_header), 'photo.png'),
        }
        resp = authenticated_client.post(
            '/admin/new', data=data,
            content_type='multipart/form-data', follow_redirects=True)
        assert resp.status_code == 200
        assert b'Post created' in resp.data

        post = db.session.execute(
            select(Post).filter_by(title='Image Post')
        ).scalar_one()
        filename = post.image
        assert filename is not None

        # -- Browse media --
        resp = authenticated_client.get('/admin/media')
        assert resp.status_code == 200
        assert filename.encode() in resp.data

        # -- Delete via media endpoint --
        resp = authenticated_client.post(f'/admin/media/delete/{filename}', follow_redirects=True)
        assert resp.status_code == 200

        upload_dir = authenticated_client.application.config['UPLOAD_FOLDER']
        assert not os.path.exists(os.path.join(upload_dir, filename))


# ---------------------------------------------------------------------------
# 8. User management flow
# ---------------------------------------------------------------------------

class TestUserManagement:
    """Create user -> change password -> delete user."""

    def test_create_change_password_delete_user(self, authenticated_client, db, admin_user):
        # -- Create user --
        resp = authenticated_client.post('/admin/users/create', data={
            'username': 'editor',
            'password': 'Editorpass123!',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'User' in resp.data and b'created' in resp.data

        new_user = db.session.execute(
            select(User).filter_by(username='editor')
        ).scalar_one()
        assert new_user.is_admin is False

        # -- Change password --
        resp = authenticated_client.post(
            f'/admin/users/password/{new_user.id}',
            data={'password': 'Newpassword456!'},
            follow_redirects=True)
        assert resp.status_code == 200
        assert b'Password changed' in resp.data

        db.session.refresh(new_user)
        assert new_user.check_password('Newpassword456!')
        assert not new_user.check_password('Editorpass123!')

        # -- Delete user --
        resp = authenticated_client.post(
            f'/admin/users/delete/{new_user.id}', follow_redirects=True)
        assert resp.status_code == 200
        assert b'deleted' in resp.data
        assert db.session.get(User, new_user.id) is None

    def test_cannot_delete_self(self, authenticated_client, db, admin_user):
        resp = authenticated_client.post(
            f'/admin/users/delete/{admin_user.id}', follow_redirects=True)
        assert resp.status_code == 200
        assert b'Cannot delete your own account' in resp.data
        assert db.session.get(User, admin_user.id) is not None

    def test_cannot_delete_last_admin(self, authenticated_client, db, admin_user):
        # Try to delete the only admin — should fail
        resp = authenticated_client.post(
            f'/admin/users/delete/{admin_user.id}', follow_redirects=True)
        assert resp.status_code == 200
        # Admin must still exist
        assert db.session.get(User, admin_user.id) is not None

        # Also verify via a second admin scenario
        other_admin = User(username='otheradmin', is_admin=True)
        other_admin.set_password('pass1234')
        db.session.add(other_admin)
        db.session.commit()

        # Delete other_admin — fine, admin_user still exists
        resp = authenticated_client.post(
            f'/admin/users/delete/{other_admin.id}', follow_redirects=True)
        assert resp.status_code == 200
        assert db.session.get(User, other_admin.id) is None

        # Now admin_user is the only admin — cannot delete
        resp = authenticated_client.post(
            f'/admin/users/delete/{admin_user.id}', follow_redirects=True)
        assert db.session.get(User, admin_user.id) is not None
