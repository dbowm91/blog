import pytest


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
    response = authenticated_client.get('/admin/logout', follow_redirects=True)
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
    post1 = Post.query.filter_by(title='Duplicate Title').first()
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
    post2 = Post.query.filter_by(title='Duplicate Title').order_by(Post.id.desc()).first()
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
    post = Post.query.filter_by(title='Post with Image').first()
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
