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
