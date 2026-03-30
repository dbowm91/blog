import pytest


def test_csp_header(client):
    """Test CSP header present and correct."""
    response = client.get('/')
    csp = response.headers.get('Content-Security-Policy')
    assert csp is not None
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


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
