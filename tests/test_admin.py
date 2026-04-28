import pytest
from sqlalchemy import select, func
from app.utils import utc_now


def test_login_page(client):
    """Test login page renders."""
    response = client.get('/admin/login')
    assert response.status_code == 200


def test_login_success(client, admin_user):
    """Test successful login."""
    response = client.post('/admin/login', data={
        'username': 'admin',
        'password': 'testpassword',
    }, follow_redirects=True)
    assert response.status_code == 200


def test_login_failure(client, admin_user):
    """Test failed login."""
    response = client.post('/admin/login', data={
        'username': 'admin',
        'password': 'wrongpassword',
    }, follow_redirects=True)
    assert b'Invalid credentials' in response.data


def test_dashboard_requires_auth(client):
    """Test dashboard requires authentication."""
    response = client.get('/admin/')
    assert response.status_code == 302


def test_dashboard_authenticated(authenticated_client):
    """Test authenticated dashboard access."""
    response = authenticated_client.get('/admin/')
    assert response.status_code == 200


def test_new_post_requires_auth(client):
    """Test new post requires authentication."""
    response = client.get('/admin/new')
    assert response.status_code == 302


def test_create_post(authenticated_client, db):
    """Test creating a new post."""
    response = authenticated_client.post('/admin/new', data={
        'title': 'New Test Post',
        'body': 'This is a new test post.',
        'summary': 'A summary',
        'tags': 'python, testing',
        'published': 'on',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Post created' in response.data


def test_create_post_missing_title(authenticated_client, db):
    """Test creating post without title fails."""
    response = authenticated_client.post('/admin/new', data={
        'title': '',
        'body': 'Some content',
    }, follow_redirects=True)
    assert b'Title and body are required' in response.data


def test_edit_post(authenticated_client, db, sample_post):
    """Test editing a post."""
    response = authenticated_client.post(f'/admin/edit/{sample_post.id}', data={
        'title': 'Updated Title',
        'body': 'Updated content',
        'summary': 'Updated summary',
        'tags': 'python',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Post updated' in response.data


def test_delete_post(authenticated_client, db, sample_post):
    """Test deleting a post."""
    response = authenticated_client.post(f'/admin/delete/{sample_post.id}', follow_redirects=True)
    assert response.status_code == 200
    assert b'Post deleted' in response.data


def test_logout(authenticated_client):
    """Test logout."""
    response = authenticated_client.post('/admin/logout', follow_redirects=True)
    assert response.status_code == 200


import io


def test_upload_valid_image(authenticated_client, db):
    """Test uploading a valid image with a post."""
    data = {
        'title': 'Post with Image',
        'body': 'Content',
        'image': (io.BytesIO(b'\x89PNG\r\n\x1a\n' + b'\x00' * 50), 'test.png'),
    }
    response = authenticated_client.post('/admin/new', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200


def test_upload_invalid_extension(authenticated_client, db):
    """Test uploading a file with invalid extension."""
    data = {
        'title': 'Post',
        'body': 'Content',
        'image': (io.BytesIO(b'not an image'), 'test.exe'),
    }
    response = authenticated_client.post('/admin/new', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200


def test_analytics_requires_auth(client):
    """Test analytics page requires authentication."""
    response = client.get('/admin/analytics')
    assert response.status_code == 302


def test_analytics_authenticated(authenticated_client):
    """Test analytics page loads for authenticated users."""
    response = authenticated_client.get('/admin/analytics')
    assert response.status_code == 200
    assert b'Analytics' in response.data


def test_analytics_date_range(authenticated_client):
    """Test analytics page with different date ranges."""
    response = authenticated_client.get('/admin/analytics?days=7')
    assert response.status_code == 200
    response = authenticated_client.get('/admin/analytics?days=90')
    assert response.status_code == 200


def test_dashboard_shows_stats(authenticated_client):
    """Test dashboard displays stat cards."""
    response = authenticated_client.get('/admin/')
    assert response.status_code == 200
    assert b'Total Views' in response.data
    assert b'Published Posts' in response.data
    assert b'Subscribers' in response.data


def test_upload_gif87a_image(authenticated_client, db):
    """Test uploading a valid GIF87a image."""
    # GIF87a header + minimal valid GIF
    gif87a = b'GIF87a' + b'\x00' * 100  # fake image data
    data = {
        'title': 'Post with GIF87a',
        'body': 'Content',
        'image': (io.BytesIO(gif87a), 'test.gif'),
    }
    response = authenticated_client.post('/admin/new', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'Post created' in response.data


def test_upload_gif89a_image(authenticated_client, db):
    """Test uploading a valid GIF89a image."""
    gif89a = b'GIF89a' + b'\x00' * 100
    data = {
        'title': 'Post with GIF89a',
        'body': 'Content',
        'image': (io.BytesIO(gif89a), 'test.gif'),
    }
    response = authenticated_client.post('/admin/new', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'Post created' in response.data


def test_upload_invalid_gif_header(authenticated_client, db):
    """Test uploading a file with GIF extension but invalid header."""
    invalid = b'GIF99a' + b'\x00' * 100
    data = {
        'title': 'Post with invalid GIF',
        'body': 'Content',
        'image': (io.BytesIO(invalid), 'test.gif'),
    }
    response = authenticated_client.post('/admin/new', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    # Should flash error about invalid image type
    assert b'Uploaded file is not a valid image.' in response.data


def test_slug_collision_handling(authenticated_client, db):
    """Test that duplicate post titles generate unique slugs with counters."""
    # Create first post
    response1 = authenticated_client.post('/admin/new', data={
        'title': 'Duplicate Title',
        'body': 'First post',
        'published': 'on',
    }, follow_redirects=True)
    assert response1.status_code == 200
    assert b'Post created' in response1.data
    # Extract slug from response? Not easy. Instead query the post.
    from app.models import Post
    post1 = db.session.execute(select(Post).filter_by(title='Duplicate Title')).scalar_one_or_none()
    assert post1 is not None
    assert post1.slug == 'duplicate-title'
    
    # Create second post with same title
    response2 = authenticated_client.post('/admin/new', data={
        'title': 'Duplicate Title',
        'body': 'Second post',
        'published': 'on',
    }, follow_redirects=True)
    assert response2.status_code == 200
    assert b'Post created' in response2.data
    post2 = db.session.execute(select(Post).filter_by(title='Duplicate Title').order_by(Post.id.desc())).scalars().first()
    assert post2 is not None
    assert post2.slug == 'duplicate-title-2'
    assert post2.id != post1.id


def test_preview_markdown(authenticated_client):
    """Test markdown preview endpoint."""
    import json
    response = authenticated_client.post(
        '/admin/preview-markdown',
        data=json.dumps({"text": "# Hello\n\nThis is **bold**"}),
        content_type='application/json',
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "html" in data
    assert "<h1>Hello</h1>" in data["html"]
    assert "<strong>bold</strong>" in data["html"]


def test_preview_markdown_invalid(authenticated_client):
    """Test markdown preview with invalid JSON."""
    import json
    response = authenticated_client.post(
        '/admin/preview-markdown',
        data=json.dumps({"wrong": "field"}),
        content_type='application/json',
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_delete_media_requires_auth(client):
    """Test delete media endpoint requires authentication."""
    response = client.post('/admin/media/delete/nonexistent.png')
    assert response.status_code == 302  # redirect to login


def test_delete_media_authenticated(authenticated_client, db):
    """Test authenticated user can delete a media file."""
    import io
    import os
    from flask import current_app
    # Upload a PNG image via post creation
    data = {
        'title': 'Post with Image',
        'body': 'Content',
        'image': (io.BytesIO(b'\x89PNG\r\n\x1a\n' + b'\x00' * 50), 'test_delete.png'),
    }
    response = authenticated_client.post('/admin/new', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    # Extract the saved filename from the database (post.image)
    from app.models import Post
    post = db.session.execute(select(Post).filter_by(title='Post with Image')).scalar_one_or_none()
    assert post is not None
    assert post.image is not None
    filename = post.image
    # Delete the file via media delete endpoint
    response = authenticated_client.post(f'/admin/media/delete/{filename}', follow_redirects=True)
    assert response.status_code == 200
    # Verify file is removed from upload folder
    upload_folder = current_app.config['UPLOAD_FOLDER']
    filepath = os.path.join(upload_folder, filename)
    assert not os.path.exists(filepath)


def test_export_subscribers_requires_auth(client):
    """Test subscribers export requires authentication."""
    response = client.get('/admin/subscribers/export')
    assert response.status_code == 302  # redirect to login


def test_export_subscribers_csv(authenticated_client, db):
    """Test subscribers export returns CSV with correct data."""
    from app.models import Subscriber
    from datetime import datetime, timedelta, timezone
    sub1 = Subscriber(email='test1@example.com', confirmed=True,
                      created_at=datetime.now(timezone.utc) - timedelta(days=1))
    sub2 = Subscriber(email='test2@example.com', confirmed=False,
                      created_at=datetime.now(timezone.utc))
    db.session.add_all([sub1, sub2])
    db.session.commit()
    response = authenticated_client.get('/admin/subscribers/export')
    assert response.status_code == 200
    assert response.mimetype == 'text/csv'
    assert 'attachment; filename=subscribers.csv' in response.headers['Content-Disposition']
    # CSV uses \r\n line endings; replace them
    csv_text = response.data.decode('utf-8').replace('\r\n', '\n').strip()
    lines = csv_text.split('\n')
    # header row
    assert lines[0] == 'email,confirmed,created_at,expires_at'
    # data rows (order may be by created_at desc)
    assert len(lines) == 3  # header + 2 subscribers
    # check both emails appear in the two data rows
    emails = [lines[1], lines[2]]
    assert any('test1@example.com' in row for row in emails)
    assert any('test2@example.com' in row for row in emails)


def test_delete_subscriber_requires_auth(client):
    """Test subscriber delete requires authentication."""
    response = client.post('/admin/subscribers/delete/1')
    assert response.status_code == 302  # redirect to login


def test_delete_subscriber_authenticated(authenticated_client, db):
    """Test authenticated user can delete a subscriber."""
    from app.models import Subscriber
    sub = Subscriber(email='todelete@example.com', confirmed=True)
    db.session.add(sub)
    db.session.commit()
    sub_id = sub.id
    response = authenticated_client.post(f'/admin/subscribers/delete/{sub_id}', follow_redirects=True)
    assert response.status_code == 200
    assert b'Subscriber todelete@example.com deleted' in response.data
    # Verify subscriber is gone
    assert db.session.get(Subscriber, sub_id) is None


def test_preview_endpoint(authenticated_client, db, sample_post):
    """Test preview endpoint works for published posts."""
    response = authenticated_client.get(f'/admin/preview/{sample_post.id}')
    assert response.status_code == 200
    assert b'Test Post' in response.data
    assert b'preview-banner' in response.data


def test_bulk_delete(authenticated_client, db):
    """Test bulk delete removes posts and cleans up images."""
    from app.models import Post
    post1 = Post(title='Bulk 1', slug='bulk-1', body='Content', published=True)
    post2 = Post(title='Bulk 2', slug='bulk-2', body='Content', published=True)
    db.session.add_all([post1, post2])
    db.session.commit()
    ids = [post1.id, post2.id]

    response = authenticated_client.post('/admin/bulk', data={
        'action': 'delete',
        'post_ids': ids,
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Deleted 2 post(s)' in response.data
    assert db.session.execute(select(func.count()).select_from(Post).filter(Post.id.in_(ids))).scalar_one() == 0


def test_bulk_publish(authenticated_client, db):
    """Test bulk publish sets published flag and published_at."""
    from app.models import Post
    post = Post(title='Draft', slug='draft-bulk', body='Content', published=False)
    db.session.add(post)
    db.session.commit()

    response = authenticated_client.post('/admin/bulk', data={
        'action': 'publish',
        'post_ids': [post.id],
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Published 1 post(s)' in response.data
    post = db.session.get(Post, post.id)
    assert post.published is True
    assert post.published_at is not None


def test_bulk_invalid_post_ids(authenticated_client, db):
    """Test bulk operations rejects non-integer post IDs."""
    response = authenticated_client.post('/admin/bulk', data={
        'action': 'delete',
        'post_ids': ['abc', 'def'],
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid post ID' in response.data


def test_newsletter_reset_clears_attempts(authenticated_client, db, sample_post):
    """Test newsletter reset clears both flag and attempts."""
    sample_post.newsletter_sent_at = utc_now()
    sample_post.newsletter_attempts = 3
    db.session.commit()

    response = authenticated_client.post(
        f'/admin/newsletter-reset/{sample_post.id}',
        follow_redirects=True)
    assert response.status_code == 200
    from app.models import Post
    post = db.session.get(Post, sample_post.id)
    assert post.newsletter_sent_at is None
    assert post.newsletter_attempts == 0


def test_forgot_password_page(client):
    """Test forgot password page renders."""
    response = client.get('/admin/forgot-password')
    assert response.status_code == 200


def test_forgot_password_valid_user(client, admin_user, db, monkeypatch):
    """Test forgot password sends email for valid admin user."""
    send_called = []
    original_send = __import__('app.routes.admin.auth', fromlist=['send_password_reset']).send_password_reset
    def mock_send(user, token):
        send_called.append((user, token))
    monkeypatch.setattr('app.routes.admin.auth.send_password_reset', mock_send)
    response = client.post('/admin/forgot-password', data={
        'identifier': 'admin',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'If that account exists' in response.data
    assert len(send_called) == 1
    user = db.session.execute(db.select(admin_user.__class__).filter_by(username='admin')).scalar_one()
    assert user.reset_token is not None
    assert user.reset_token_expires_at is not None


def test_forgot_password_invalid_user(client, db, monkeypatch):
    """Test forgot password with non-existent user shows success (token enumeration prevention)."""
    send_called = []
    def mock_send(user, token):
        send_called.append((user, token))
    monkeypatch.setattr('app.routes.admin.auth.send_password_reset', mock_send)
    response = client.post('/admin/forgot-password', data={
        'identifier': 'nonexistent',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'If that account exists' in response.data
    assert len(send_called) == 0


def test_forgot_password_empty_identifier(client):
    """Test forgot password with empty identifier shows error."""
    response = client.post('/admin/forgot-password', data={
        'identifier': '',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Please enter your username or email' in response.data


def test_reset_password_valid_token(client, admin_user, db):
    """Test password reset with valid token."""
    from app.routes.admin.auth import _hash_token
    import secrets
    token = secrets.token_hex(32)
    admin_user.reset_token = _hash_token(token)
    from datetime import datetime, timezone, timedelta
    admin_user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db.session.commit()

    response = client.get(f'/admin/reset/{token}')
    assert response.status_code == 200

    response = client.post(f'/admin/reset/{token}', data={
        'password': 'NewPass123!',
        'confirm_password': 'NewPass123!',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Your password has been reset' in response.data
    user = db.session.get(admin_user.__class__, admin_user.id)
    assert user.reset_token is None
    assert user.reset_token_expires_at is None


def test_reset_password_invalid_token(client):
    """Test password reset with invalid token."""
    response = client.get('/admin/reset/invalid-token')
    assert response.status_code == 302


def test_reset_password_expired_token(client, admin_user, db):
    """Test password reset with expired token."""
    from app.routes.admin.auth import _hash_token
    import secrets
    from datetime import datetime, timezone, timedelta
    token = secrets.token_hex(32)
    admin_user.reset_token = _hash_token(token)
    admin_user.reset_token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.session.commit()

    response = client.get(f'/admin/reset/{token}', follow_redirects=True)
    assert response.status_code == 200
    assert b'expired' in response.data.lower()


def test_reset_password_mismatch(client, admin_user, db):
    """Test password reset with mismatched passwords."""
    from app.routes.admin.auth import _hash_token
    import secrets
    from datetime import datetime, timezone, timedelta
    token = secrets.token_hex(32)
    admin_user.reset_token = _hash_token(token)
    admin_user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db.session.commit()

    response = client.post(f'/admin/reset/{token}', data={
        'password': 'NewPass123!',
        'confirm_password': 'DifferentPass123!',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Passwords do not match' in response.data


def test_reset_password_weak_password(client, admin_user, db):
    """Test password reset with weak password."""
    from app.routes.admin.auth import _hash_token
    import secrets
    from datetime import datetime, timezone, timedelta
    token = secrets.token_hex(32)
    admin_user.reset_token = _hash_token(token)
    admin_user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db.session.commit()

    response = client.post(f'/admin/reset/{token}', data={
        'password': 'weak',
        'confirm_password': 'weak',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Password must be at least 8 characters' in response.data


# Settings tests
def test_settings_requires_auth(client):
    """Test settings page requires authentication."""
    response = client.get('/admin/settings')
    assert response.status_code == 302


def test_settings_page(authenticated_client, db):
    """Test settings page renders with current settings."""
    response = authenticated_client.get('/admin/settings')
    assert response.status_code == 200
    assert b'Theme Settings' in response.data or b'theme' in response.data.lower()


def test_settings_theme_update(authenticated_client, db):
    """Test updating theme settings."""
    from app.models import SiteSettings
    response = authenticated_client.post('/admin/settings/theme', data={
        'preset': 'github-light',
        'custom_css_enabled': 'on',
        'custom_css': 'body { color: red; }',
        'logo_text': 'Test Logo',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Theme settings saved' in response.data
    settings = db.session.execute(db.select(SiteSettings).limit(1)).scalar_one()
    assert settings.theme_preset == 'github-light'
    assert settings.custom_css_enabled is True
    assert settings.logo_text == 'Test Logo'


def test_settings_invalid_preset(authenticated_client, db):
    """Test settings rejects invalid theme preset."""
    response = authenticated_client.post('/admin/settings/theme', data={
        'preset': 'invalid-preset',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid theme preset' in response.data


# Pages tests
def test_pages_list_requires_auth(client):
    """Test pages list requires authentication."""
    response = client.get('/admin/pages')
    assert response.status_code == 302


def test_pages_list(authenticated_client, db):
    """Test pages list renders."""
    response = authenticated_client.get('/admin/pages')
    assert response.status_code == 200


def test_new_page_requires_auth(client):
    """Test new page requires authentication."""
    response = client.get('/admin/pages/new')
    assert response.status_code == 302


def test_new_page_get(authenticated_client):
    """Test new page form renders."""
    response = authenticated_client.get('/admin/pages/new')
    assert response.status_code == 200


def test_create_page(authenticated_client, db):
    """Test creating a new page."""
    response = authenticated_client.post('/admin/pages/new', data={
        'title': 'Test Page',
        'body': '# Test Page Content',
        'published': 'on',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Page' in response.data and b'created' in response.data
    from app.models import Page
    page = db.session.execute(db.select(Page).filter_by(title='Test Page')).scalar_one()
    assert page is not None
    assert page.published is True


def test_create_page_missing_title(authenticated_client):
    """Test creating page with missing title."""
    response = authenticated_client.post('/admin/pages/new', data={
        'body': '# Content',
    }, follow_redirects=True)
    assert response.status_code == 400
    assert b'Title is required' in response.data


def test_create_page_missing_body(authenticated_client):
    """Test creating page with missing body."""
    response = authenticated_client.post('/admin/pages/new', data={
        'title': 'Test Page',
    }, follow_redirects=True)
    assert response.status_code == 400
    assert b'Content is required' in response.data


def test_edit_page(authenticated_client, db):
    """Test editing a page."""
    from app.models import Page
    page = Page(title='Original', slug='original', body='Original body', published=False)
    db.session.add(page)
    db.session.commit()
    page_id = page.id

    response = authenticated_client.post(f'/admin/pages/edit/{page_id}', data={
        'title': 'Updated Page',
        'body': 'Updated body',
        'published': 'on',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Page' in response.data and b'updated' in response.data
    page = db.session.get(Page, page_id)
    assert page.title == 'Updated Page'
    assert page.published is True


def test_delete_page(authenticated_client, db):
    """Test deleting a page."""
    from app.models import Page
    page = Page(title='To Delete', slug='to-delete', body='Content', published=False)
    db.session.add(page)
    db.session.commit()
    page_id = page.id

    response = authenticated_client.post(f'/admin/pages/delete/{page_id}', follow_redirects=True)
    assert response.status_code == 200
    assert b'deleted' in response.data.lower()
    assert db.session.get(Page, page_id) is None
