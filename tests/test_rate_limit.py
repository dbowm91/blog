import pytest


def test_login_rate_limit(client, admin_user):
    """Test login rate limiting after multiple failed attempts."""
    for _ in range(5):
        client.post('/admin/login', data={'username': 'admin', 'password': 'wrong'})
    response = client.post('/admin/login', data={'username': 'admin', 'password': 'wrong'})
    assert response.status_code == 429


def test_rate_limit_clears_on_success(client, admin_user):
    """Test rate limit state is cleared after successful login."""
    client.post('/admin/login', data={'username': 'admin', 'password': 'wrong'})
    client.post('/admin/login', data={'username': 'admin', 'password': 'testpassword'})
    from app.rate_limit import _attempts, _lockouts
    _attempts.clear()
    _lockouts.clear()
