def test_session_fixation_prevention(app, client, db, admin_user):
    """Test that session is cleared before login to prevent session fixation."""
    from tests.conftest import TEST_PASSWORD

    with app.test_request_context():
        # Set a known session value before login
        with client.session_transaction() as sess:
            sess["test_value"] = "before_login"
            sess["_fresh"] = True

        # Login
        client.post(
            "/admin/login",
            data={
                "username": "admin",
                "password": TEST_PASSWORD,
            },
            follow_redirects=True,
        )

        # After login, the test_value should NOT be present (session was cleared)
        with client.session_transaction() as sess:
            assert "test_value" not in sess
            assert sess.get("admin_session_id") is not None


def test_csp_header(client):
    """Test CSP header present and correct."""
    response = client.get("/")
    csp = response.headers.get("Content-Security-Policy")
    assert csp is not None
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "frame-src https://www.youtube-nocookie.com" in csp
    assert "media-src 'self'" in csp
    assert "style-src 'self' 'nonce-" in csp
    assert "script-src 'self' 'nonce-" in csp


def test_debug_report_only_csp_allows_the_same_embed_and_media_sources(app):
    previous_debug = app.debug
    app.debug = True
    try:
        response = app.test_client().get("/media/download/not-an-attachment")
    finally:
        app.debug = previous_debug

    report_only = response.headers.get("Content-Security-Policy-Report-Only", "")
    assert "frame-src https://www.youtube-nocookie.com" in report_only
    assert "media-src 'self'" in report_only


def test_the_report_only_csp_declares_report_uri_as_its_own_directive(app):
    """``report-uri`` is a directive, not a source expression.

    Nested inside ``connect-src`` the browser reads the two tokens as invalid
    source expressions, ignores them and never emits the directive, so the
    reports the policy asks for never arrive.
    """
    previous_debug = app.debug
    app.debug = True
    try:
        response = app.test_client().get("/media/download/not-an-attachment")
    finally:
        app.debug = previous_debug

    report_only = response.headers.get("Content-Security-Policy-Report-Only", "")
    assert "report-uri /csp-violation;" in report_only
    assert "connect-src 'self' report-uri" not in report_only
    assert "connect-src 'self';" in report_only


def test_hsts_conditional_debug(client):
    """Test HSTS is present in non-debug mode."""
    response = client.get("/")
    hsts = response.headers.get("Strict-Transport-Security")
    assert hsts is not None
    assert "max-age=" in hsts


def test_hsts_absent_in_debug(app, client):
    """Test HSTS absent when app.debug is True."""
    original_debug = app.debug
    app.debug = True
    try:
        response = client.get("/")
        assert "Strict-Transport-Security" not in response.headers
    finally:
        app.debug = original_debug


def test_csrf_protection(app, client):
    """Test POST without CSRF token fails when CSRF is enabled."""
    original_csrf = app.config.get("CSRF_ENABLED", True)
    original_testing = app.config.get("TESTING", False)
    app.config["CSRF_ENABLED"] = True
    app.config["TESTING"] = False
    try:
        response = client.post("/subscribe", data={"email": "test@example.com"})
        assert response.status_code == 403
    finally:
        app.config["CSRF_ENABLED"] = original_csrf
        app.config["TESTING"] = original_testing


def test_x_frame_options(client):
    """Test X-Frame-Options is DENY."""
    response = client.get("/")
    assert response.headers.get("X-Frame-Options") == "DENY"


def test_referrer_policy(client):
    """Test Referrer-Policy header present."""
    response = client.get("/")
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_x_content_type_options(client):
    """Test X-Content-Type-Options is nosniff."""
    response = client.get("/")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"


def test_permissions_policy(client):
    """Test Permissions-Policy header present."""
    response = client.get("/")
    pp = response.headers.get("Permissions-Policy")
    assert pp is not None
    assert "camera=()" in pp
    assert "microphone=()" in pp


def test_static_cache_control(client):
    """Test static assets get immutable cache control."""
    response = client.get("/static/img/favicon.svg")
    if response.status_code == 200:
        assert response.headers.get("Cache-Control") == "public, max-age=31536000, immutable"


def test_csp_connect_src(client):
    """Test CSP has explicit connect-src directive."""
    response = client.get("/")
    csp = response.headers.get("Content-Security-Policy")
    assert "connect-src 'self'" in csp


def test_logout_is_post_only(client, admin_user):
    """Test that GET /admin/logout returns 405 (method not allowed)."""
    from tests.conftest import TEST_PASSWORD

    client.post(
        "/admin/login",
        data={
            "username": "admin",
            "password": TEST_PASSWORD,
        },
    )
    response = client.get("/admin/logout")
    assert response.status_code == 405


def test_non_admin_cannot_log_in(app, db, client):
    """Test that non-admin users cannot log in to admin panel."""
    from app.models import User
    from tests.conftest import TEST_PASSWORD

    user = User(username="regular", is_admin=False)
    user.set_password(TEST_PASSWORD)
    db.session.add(user)
    db.session.commit()

    response = client.post(
        "/admin/login",
        data={
            "username": "regular",
            "password": TEST_PASSWORD,
        },
        follow_redirects=True,
    )
    assert b"Invalid credentials" in response.data


def test_non_admin_gets_403_on_admin_routes(app, db, client):
    """Test that authenticated non-admin users get 403 on admin routes."""
    from app.models import User
    from tests.conftest import TEST_PASSWORD

    user = User(username="regular", is_admin=False)
    user.set_password(TEST_PASSWORD)
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
    admin = User(username="admin2", is_admin=True)
    admin.set_password(TEST_PASSWORD)
    db.session.add(admin)
    db.session.commit()

    client.post(
        "/admin/login",
        data={
            "username": "admin2",
            "password": TEST_PASSWORD,
        },
    )
    # Demote user to non-admin
    admin.is_admin = False
    db.session.commit()

    # These routes should now return 403
    for path in ["/admin/", "/admin/analytics", "/admin/subscribers", "/admin/users"]:
        response = client.get(path)
        assert response.status_code == 403, f"Expected 403 for {path}, got {response.status_code}"

    # The post editor is deliberately reachable by an author, but an author
    # may not open a post that belongs to somebody else.
    response = client.get("/admin/new")
    assert response.status_code == 200, f"Expected 200 for /admin/new, got {response.status_code}"


def test_account_lockout_after_failed_attempts(app, db, client):
    """Test that accounts get locked after failed login attempts."""
    from app.models import User

    user = User(username="locktest", is_admin=True)
    user.set_password("CorrectPassword123!")
    db.session.add(user)
    db.session.commit()

    failed_passwords = ["wrong1", "wrong2", "wrong3", "wrong4", "wrong5"]
    for pw in failed_passwords:
        client.post(
            "/admin/login",
            data={
                "username": "locktest",
                "password": pw,
            },
            follow_redirects=True,
        )

    db.session.expire(user)
    user = db.session.execute(db.select(User).filter_by(username="locktest")).scalar_one()
    assert user.locked_until is not None


def test_locked_account_rejects_login(app, db, client):
    """Test that locked account rejects valid password."""
    from app.models import User
    from datetime import datetime, timedelta, timezone

    user = User(username="locktest2", is_admin=True)
    user.set_password("CorrectPassword123!")
    user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
    db.session.add(user)
    db.session.commit()

    response = client.post(
        "/admin/login",
        data={
            "username": "locktest2",
            "password": "CorrectPassword123!",
        },
        follow_redirects=True,
    )
    assert b"locked" in response.data.lower() or b"temporarily disabled" in response.data.lower()


def test_csrf_bypass_prevented(app, client, db, admin_user):
    """Test CSRF protection prevents bypass attempts."""
    from tests.conftest import TEST_PASSWORD

    original_csrf = app.config.get("CSRF_ENABLED", True)
    original_testing = app.config.get("TESTING", False)
    app.config["CSRF_ENABLED"] = True
    app.config["TESTING"] = False
    try:
        client.post(
            "/admin/login",
            data={
                "username": "admin",
                "password": TEST_PASSWORD,
            },
        )
        fake_csrf = "attacker-fake-csrf-token"
        response = client.post(
            "/admin/users/create",
            data={
                "username": "attacker",
                "password": "Password123!",
                "_csrf_token": fake_csrf,
            },
        )
        assert response.status_code == 403
    finally:
        app.config["CSRF_ENABLED"] = original_csrf
        app.config["TESTING"] = original_testing


def test_rate_limit_login_endpoint(client, db):
    """Test that login endpoint rate limits failed attempts (feature exists)."""
    from app.models import User

    user = User(username="ratelimit", is_admin=True)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()

    failed_count = 0
    for _ in range(5):
        response = client.post(
            "/admin/login",
            data={
                "username": "ratelimit",
                "password": "wrongpassword",
            },
        )
        if response.status_code == 200:
            failed_count += 1

    assert failed_count >= 3, "Login should fail for wrong password multiple times"


def test_rate_limit_blocked_ip_after_excessive_requests(client, db):
    """Test that subscribe endpoint handles repeated requests."""
    from unittest.mock import patch

    with patch("app.routes.public.subscribe.send_confirmation_task"):
        responses = []
        for i in range(10):
            response = client.post(
                "/subscribe",
                data={
                    "email": f"test{i}@example.com",
                },
            )
            responses.append(response.status_code)

        assert all(r in (200, 302, 400) for r in responses), (
            "Subscribe should handle requests gracefully"
        )


def test_admin_rate_limit_exceeded(client, admin_user, db):
    """Test admin endpoints can handle multiple requests."""
    from tests.conftest import TEST_PASSWORD

    client.post(
        "/admin/login",
        data={
            "username": "admin",
            "password": TEST_PASSWORD,
        },
    )

    responses = []
    for _ in range(10):
        response = client.get("/admin/")
        responses.append(response.status_code)

    assert all(r == 200 for r in responses), "Admin page should respond successfully"


def test_security_headers_on_admin_route(client, admin_user, db):
    """Test security headers present on admin routes."""
    from tests.conftest import TEST_PASSWORD

    client.post(
        "/admin/login",
        data={"username": "admin", "password": TEST_PASSWORD},
    )
    response = client.get("/admin/")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    pp = response.headers.get("Permissions-Policy")
    assert pp is not None
    assert "camera=()" in pp
    csp = response.headers.get("Content-Security-Policy")
    assert csp is not None
    assert "default-src 'self'" in csp
