import pytest


def test_session_fixation_prevention(app, client, db, admin_user):
    """Test that session is cleared before login to prevent session fixation."""
    with app.test_request_context():
        from flask import session

        # Set a known session value before login
        with client.session_transaction() as sess:
            sess['test_value'] = 'before_login'
            sess['_fresh'] = True

        # Login
        response = client.post('/admin/login', data={
            'username': 'admin',
            'password': 'testpassword',
        }, follow_redirects=True)

        # After login, the test_value should NOT be present (session was cleared)
        with client.session_transaction() as sess:
            assert 'test_value' not in sess
            assert sess.get('admin_session_id') is not None


def test_csp_header(client):
    """Test CSP header present and correct."""
    response = client.get('/')
    csp = response.headers.get('Content-Security-Policy')
    assert csp is not None
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "frame-src 'none'" in csp
    assert "style-src 'self' 'nonce-" in csp
    assert "script-src 'self' 'nonce-" in csp


def test_hsts_conditional_debug(client):
    """Test HSTS is present in non-debug mode."""
    response = client.get('/')
    hsts = response.headers.get('Strict-Transport-Security')
    assert hsts is not None
    assert 'max-age=' in hsts


def test_hsts_absent_in_debug(app, client):
    """Test HSTS absent when app.debug is True."""
    original_debug = app.debug
    app.debug = True
    try:
        response = client.get('/')
        assert 'Strict-Transport-Security' not in response.headers
    finally:
        app.debug = original_debug


def test_csrf_protection(app, client):
    """Test POST without CSRF token fails when CSRF is enabled."""
    original_csrf = app.config.get('CSRF_ENABLED', True)
    original_testing = app.config.get('TESTING', False)
    app.config['CSRF_ENABLED'] = True
    app.config['TESTING'] = False
    try:
        response = client.post('/subscribe', data={'email': 'test@example.com'})
        assert response.status_code == 403
    finally:
        app.config['CSRF_ENABLED'] = original_csrf
        app.config['TESTING'] = original_testing


def test_x_frame_options(client):
    """Test X-Frame-Options is DENY."""
    response = client.get('/')
    assert response.headers.get('X-Frame-Options') == 'DENY'


def test_referrer_policy(client):
    """Test Referrer-Policy header present."""
    response = client.get('/')
    assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'


def test_x_content_type_options(client):
    """Test X-Content-Type-Options is nosniff."""
    response = client.get('/')
    assert response.headers.get('X-Content-Type-Options') == 'nosniff'


def test_permissions_policy(client):
    """Test Permissions-Policy header present."""
    response = client.get('/')
    pp = response.headers.get('Permissions-Policy')
    assert pp is not None
    assert 'camera=()' in pp
    assert 'microphone=()' in pp


def test_static_cache_control(client):
    """Test static assets get immutable cache control."""
    response = client.get('/static/img/favicon.svg')
    if response.status_code == 200:
        assert response.headers.get('Cache-Control') == 'public, max-age=31536000, immutable'


def test_csp_connect_src(client):
    """Test CSP has explicit connect-src directive."""
    response = client.get('/')
    csp = response.headers.get('Content-Security-Policy')
    assert "connect-src 'self'" in csp


def test_logout_is_post_only(client, admin_user):
    """Test that GET /admin/logout returns 405 (method not allowed)."""
    client.post('/admin/login', data={
        'username': 'admin',
        'password': 'testpassword',
    })
    response = client.get('/admin/logout')
    assert response.status_code == 405


def test_non_admin_cannot_log_in(app, db, client):
    """Test that non-admin users cannot log in to admin panel."""
    from app.models import User
    user = User(username='regular', is_admin=False)
    user.set_password('testpassword')
    db.session.add(user)
    db.session.commit()

    response = client.post('/admin/login', data={
        'username': 'regular',
        'password': 'testpassword',
    }, follow_redirects=True)
    assert b'Invalid credentials' in response.data


def test_non_admin_gets_403_on_admin_routes(app, db, client):
    """Test that authenticated non-admin users get 403 on admin routes."""
    from app.models import User
    user = User(username='regular', is_admin=False)
    user.set_password('testpassword')
    db.session.add(user)
    db.session.commit()

    # Login as admin first to create the session, then check non-admin access
    # Actually, we can't log in as non-admin (blocked by login check).
    # Instead, manually log in via login_user and test access.
    with app.test_request_context():
        from flask_login import login_user
        login_user(user)
        # This won't work outside request context for client tests.
    # We'll test via a different approach: create an admin, log in, 
    # then set is_admin=False on the user and try accessing routes.
    admin = User(username='admin2', is_admin=True)
    admin.set_password('testpassword')
    db.session.add(admin)
    db.session.commit()

    client.post('/admin/login', data={
        'username': 'admin2',
        'password': 'testpassword',
    })
    # Demote user to non-admin
    admin.is_admin = False
    db.session.commit()

    # These routes should now return 403
    for path in ['/admin/', '/admin/new', '/admin/analytics', '/admin/subscribers']:
        response = client.get(path)
        assert response.status_code == 403, f"Expected 403 for {path}, got {response.status_code}"
