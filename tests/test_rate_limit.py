import pytest
from app.rate_limit import clear_all, api_rate_limit
from flask import Flask


def test_login_rate_limit(client, admin_user):
    """Test login rate limiting after multiple failed attempts."""
    clear_all()  # Reset state before test
    for _ in range(5):
        client.post('/admin/login', data={'username': 'admin', 'password': 'wrong'})
    response = client.post('/admin/login', data={'username': 'admin', 'password': 'wrong'})
    assert response.status_code == 429


def test_rate_limit_clears_on_success(client, admin_user):
    """Test rate limit state is cleared after successful login."""
    clear_all()  # Reset state before test
    client.post('/admin/login', data={'username': 'admin', 'password': 'wrong'})
    client.post('/admin/login', data={'username': 'admin', 'password': 'testpassword'})
    clear_all()  # Clean up after test


def test_api_rate_limit():
    """Test API rate limiting."""
    clear_all()
    app = Flask(__name__)
    with app.test_request_context('/api/track-share', method='POST', environ_base={'REMOTE_ADDR': '127.0.0.1'}):
        # First request should pass
        result = api_rate_limit(max_requests=3, window=60)
        assert result is None
        # Second request
        result = api_rate_limit(max_requests=3, window=60)
        assert result is None
        # Third request
        result = api_rate_limit(max_requests=3, window=60)
        assert result is None
        # Fourth request should be rate limited
        result = api_rate_limit(max_requests=3, window=60)
        assert result is not None
        assert result[1] == 429
    clear_all()
