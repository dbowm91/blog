"""CSRF and API authentication regression tests.

Tests verify:
- Browser form POSTs require CSRF tokens when CSRF is enabled
- API POST/PUT/DELETE succeed without CSRF tokens (API key auth only)
- No double-validation: routes covered by global hook don't validate again
- Login, logout, comment, and subscribe flows are CSRF-protected for browsers
"""

import os
from unittest.mock import patch

os.environ.setdefault("API_KEY", "test-api-key-12345")


def _enable_csrf(app):
    """Temporarily enable CSRF for testing."""
    app.config["CSRF_ENABLED"] = True
    app.config["TESTING"] = False


def _disable_csrf(app):
    """Restore default test CSRF config."""
    app.config["CSRF_ENABLED"] = False
    app.config["TESTING"] = True


def _get_csrf_token(client):
    """Establish a session and return a valid CSRF token.

    Makes a GET request to populate the session, then reads the token
    from the session cookie via session_transaction.
    """
    client.get("/")
    with client.session_transaction() as sess:
        tokens = sess.get("csrf_tokens", [])
        if tokens:
            return tokens[-1]
    return None


class TestBrowserCSRFProtection:
    """Browser form POSTs must require valid CSRF tokens."""

    def test_browser_post_without_csrf_returns_403(self, app, client):
        """POST to a browser route without CSRF token returns 403."""
        _enable_csrf(app)
        try:
            response = client.post("/subscribe", data={"email": "test@example.com"})
            assert response.status_code == 403
        finally:
            _disable_csrf(app)

    def test_browser_post_with_invalid_csrf_returns_403(self, app, client):
        """POST with a fake/invalid CSRF token returns 403."""
        _enable_csrf(app)
        try:
            response = client.post(
                "/subscribe",
                data={"email": "test@example.com", "csrf_token": "fake-token-abc"},
            )
            assert response.status_code == 403
        finally:
            _disable_csrf(app)

    def test_browser_logout_without_csrf_returns_403(self, app, client, admin_user):
        """POST /admin/logout without CSRF token returns 403."""
        from tests.conftest import TEST_PASSWORD

        _enable_csrf(app)
        try:
            client.post(
                "/admin/login",
                data={"username": "admin", "password": TEST_PASSWORD},
            )
            response = client.post("/admin/logout")
            assert response.status_code == 403
        finally:
            _disable_csrf(app)

    def test_browser_comment_without_csrf_returns_403(self, app, client, sample_post):
        """POST comment without CSRF token returns 403."""
        _enable_csrf(app)
        try:
            response = client.post(
                f"/post/{sample_post.slug}/comment",
                data={
                    "author_name": "Tester",
                    "author_email": "test@example.com",
                    "content": "A valid comment body here.",
                },
            )
            assert response.status_code == 403
        finally:
            _disable_csrf(app)

    def test_browser_subscribe_without_csrf_returns_403(self, app, client):
        """POST /subscribe without CSRF token returns 403."""
        _enable_csrf(app)
        try:
            response = client.post("/subscribe", data={"email": "new@example.com"})
            assert response.status_code == 403
        finally:
            _disable_csrf(app)

    def test_browser_admin_mutation_without_csrf_returns_403(self, app, client, admin_user):
        """POST admin mutation route without CSRF returns 403."""
        from tests.conftest import TEST_PASSWORD

        _enable_csrf(app)
        try:
            client.post(
                "/admin/login",
                data={"username": "admin", "password": TEST_PASSWORD},
            )
            response = client.post(
                "/admin/users/create",
                data={"username": "newuser", "password": "Password123!"},
            )
            assert response.status_code == 403
        finally:
            _disable_csrf(app)


class TestAPINoCSRFRequired:
    """API POST/PUT/DELETE should succeed without CSRF tokens."""

    def test_api_post_without_csrf_succeeds(self, app, client, admin_user):
        """POST /api/posts with valid API key but no CSRF token succeeds."""
        _enable_csrf(app)
        try:
            response = client.post(
                "/api/posts",
                json={"title": "API Test", "body": "Hello world", "published": False},
                headers={"X-API-Key": os.environ.get("API_KEY", "")},
            )
            assert response.status_code == 201
        finally:
            _disable_csrf(app)

    def test_api_put_without_csrf_succeeds(self, app, client, admin_user, sample_post):
        """PUT /api/posts/<id> with valid API key but no CSRF token succeeds."""
        _enable_csrf(app)
        try:
            response = client.put(
                f"/api/posts/{sample_post.id}",
                json={"title": "Updated via API"},
                headers={"X-API-Key": os.environ.get("API_KEY", "")},
            )
            assert response.status_code == 200
        finally:
            _disable_csrf(app)

    def test_api_delete_without_csrf_succeeds(self, app, client, admin_user, sample_post):
        """DELETE /api/posts/<id> with valid API key but no CSRF token succeeds."""
        _enable_csrf(app)
        try:
            response = client.delete(
                f"/api/posts/{sample_post.id}",
                headers={"X-API-Key": os.environ.get("API_KEY", "")},
            )
            assert response.status_code == 200
        finally:
            _disable_csrf(app)

    def test_api_post_without_api_key_returns_401(self, app, client, admin_user):
        """POST /api/posts without API key returns 401 (not 403 CSRF)."""
        _enable_csrf(app)
        try:
            response = client.post(
                "/api/posts",
                json={"title": "API Test", "body": "Hello world", "published": False},
            )
            assert response.status_code == 401
        finally:
            _disable_csrf(app)

    def test_api_post_with_wrong_api_key_returns_401(self, app, client, admin_user):
        """POST /api/posts with wrong API key returns 401 (not 403 CSRF)."""
        _enable_csrf(app)
        try:
            response = client.post(
                "/api/posts",
                json={"title": "API Test", "body": "Hello world", "published": False},
                headers={"X-API-Key": "wrong-api-key-12345"},
            )
            assert response.status_code == 401
        finally:
            _disable_csrf(app)

    def test_api_subscribers_post_without_csrf_succeeds(self, app, client, admin_user):
        """POST /api/subscribers with valid API key but no CSRF token succeeds."""
        _enable_csrf(app)
        try:
            response = client.post(
                "/api/subscribers",
                json={"email": "api-test@example.com"},
                headers={"X-API-Key": os.environ.get("API_KEY", "")},
            )
            assert response.status_code == 201
        finally:
            _disable_csrf(app)

    def test_api_tags_post_without_csrf_succeeds(self, app, client, admin_user):
        """POST /api/tags with valid API key but no CSRF token succeeds."""
        _enable_csrf(app)
        try:
            response = client.post(
                "/api/tags",
                json={"name": "API-Tag"},
                headers={"X-API-Key": os.environ.get("API_KEY", "")},
            )
            assert response.status_code == 201
        finally:
            _disable_csrf(app)

    def test_api_pages_post_without_csrf_succeeds(self, app, client, admin_user):
        """POST /api/pages with valid API key but no CSRF token succeeds."""
        _enable_csrf(app)
        try:
            response = client.post(
                "/api/pages",
                json={"title": "API Page", "body": "Page content", "published": False},
                headers={"X-API-Key": os.environ.get("API_KEY", "")},
            )
            assert response.status_code == 201
        finally:
            _disable_csrf(app)

    def test_api_series_post_without_csrf_succeeds(self, app, client, admin_user):
        """POST /api/series with valid API key but no CSRF token succeeds."""
        _enable_csrf(app)
        try:
            response = client.post(
                "/api/series",
                json={"name": "API-Series", "description": "A test series"},
                headers={"X-API-Key": os.environ.get("API_KEY", "")},
            )
            assert response.status_code == 201
        finally:
            _disable_csrf(app)


class TestDoubleValidationPrevention:
    """Routes must not validate CSRF twice (global + route-level)."""

    def test_logout_no_double_validation(self, app, client, admin_user):
        """Logout route should not fail from token consumption after global hook.

        With CSRF enabled and a valid token, logout should succeed. Before
        the fix, the global hook consumed the token, then the route-level
        call would fail. Now the route-level call is removed.
        """
        from tests.conftest import TEST_PASSWORD

        _enable_csrf(app)
        try:
            client.post(
                "/admin/login",
                data={"username": "admin", "password": TEST_PASSWORD},
            )
            token = _get_csrf_token(client)
            assert token is not None, "Failed to obtain CSRF token from session"
            response = client.post(
                "/admin/logout",
                headers={"X-CSRF-Token": token},
            )
            assert response.status_code == 302
        finally:
            _disable_csrf(app)

    def test_comment_no_double_validation(self, app, client, sample_post):
        """Comment route should not fail from double CSRF validation."""
        _enable_csrf(app)
        try:
            token = _get_csrf_token(client)
            assert token is not None, "Failed to obtain CSRF token from session"
            response = client.post(
                f"/post/{sample_post.slug}/comment",
                data={
                    "author_name": "Tester",
                    "author_email": "test@example.com",
                    "content": "A valid comment with enough length to pass validation.",
                    "csrf_token": token,
                },
            )
            assert response.status_code == 302
        finally:
            _disable_csrf(app)

    def test_subscribe_no_double_validation(self, app, client):
        """Subscribe route should not fail from double CSRF validation."""
        _enable_csrf(app)
        try:
            token = _get_csrf_token(client)
            assert token is not None, "Failed to obtain CSRF token from session"
            with patch("app.routes.public.subscribe.send_confirmation_task"):
                response = client.post(
                    "/subscribe",
                    data={"email": "valid@example.com", "csrf_token": token},
                )
            assert response.status_code == 302
        finally:
            _disable_csrf(app)


class TestShouldSkipCSRF:
    """Test the should_skip_csrf predicate via HTTP behavior."""

    def test_api_posts_skips_csrf_when_enabled(self, app, client, admin_user):
        """API POST route is not blocked by CSRF when CSRF is enabled."""
        _enable_csrf(app)
        try:
            response = client.post(
                "/api/posts",
                json={"title": "CSRF Skip Test", "body": "Body", "published": False},
                headers={"X-API-Key": os.environ.get("API_KEY", "")},
            )
            assert response.status_code == 201
        finally:
            _disable_csrf(app)

    def test_admin_route_requires_csrf_when_enabled(self, app, client, admin_user):
        """Admin POST route is blocked by CSRF when CSRF is enabled."""
        from tests.conftest import TEST_PASSWORD

        _enable_csrf(app)
        try:
            client.post(
                "/admin/login",
                data={"username": "admin", "password": TEST_PASSWORD},
            )
            response = client.post("/admin/logout")
            assert response.status_code == 403
        finally:
            _disable_csrf(app)

    def test_public_route_requires_csrf_when_enabled(self, app, client):
        """Public POST route is blocked by CSRF when CSRF is enabled."""
        _enable_csrf(app)
        try:
            response = client.post("/subscribe", data={"email": "test@example.com"})
            assert response.status_code == 403
        finally:
            _disable_csrf(app)
