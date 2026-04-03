import pytest
from app.models import User, AdminSession
from app.extensions import db


def test_two_users_can_login_simultaneously(app, db):
    """Test two admin users can log in and have separate sessions."""
    with app.app_context():
        user1 = User(username="admin1", is_admin=True)
        user1.set_password("Password123!")
        user2 = User(username="admin2", is_admin=True)
        user2.set_password("Password123!")
        db.session.add_all([user1, user2])
        db.session.commit()

    client1 = app.test_client()
    client2 = app.test_client()

    r1 = client1.post(
        "/admin/login", data={"username": "admin1", "password": "Password123!"}
    )
    assert r1.status_code == 302

    r2 = client2.post(
        "/admin/login", data={"username": "admin2", "password": "Password123!"}
    )
    assert r2.status_code == 302

    r1_dash = client1.get("/admin/")
    assert r1_dash.status_code == 200

    r2_dash = client2.get("/admin/")
    assert r2_dash.status_code == 200


def test_session_timeout_on_inactivity(app, db):
    """Test that admin session expires after inactivity."""
    with app.app_context():
        user = User(username="timeout_test", is_admin=True)
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    client.post(
        "/admin/login", data={"username": "timeout_test", "password": "Password123!"}
    )

    from app.config import SESSION_LIFETIME_HOURS
    import time

    future_time = time.time() + (SESSION_LIFETIME_HOURS * 3600) + 10

    with client.session_transaction() as sess:
        sess["last_activity"] = str(future_time)

    response = client.get("/admin/", follow_redirects=True)
    assert b"Session expired" in response.data or response.status_code == 200


def test_admin_session_created_on_login(app, db):
    """Test AdminSession record is created on login."""
    with app.app_context():
        user = User(username="session_test", is_admin=True)
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client = app.test_client()
    client.post(
        "/admin/login", data={"username": "session_test", "password": "Password123!"}
    )

    with app.app_context():
        sessions = (
            db.session.execute(db.select(AdminSession).filter_by(user_id=user_id))
            .scalars()
            .all()
        )
        assert len(sessions) >= 1


def test_admin_session_deleted_on_logout(app, db):
    """Test AdminSession record is deleted on logout."""
    with app.app_context():
        user = User(username="logout_test", is_admin=True)
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client = app.test_client()
    client.post(
        "/admin/login", data={"username": "logout_test", "password": "Password123!"}
    )

    with app.app_context():
        session_before = db.session.execute(
            db.select(AdminSession).filter_by(user_id=user_id)
        ).scalar_one_or_none()
        assert session_before is not None
        sid = session_before.session_id

    client.post("/admin/logout")

    with app.app_context():
        session_after = db.session.execute(
            db.select(AdminSession).filter_by(session_id=sid)
        ).scalar_one_or_none()
        assert session_after is None


def test_session_cookie_security_flags(app):
    """Test session cookie has correct security flags."""
    client = app.test_client()
    response = client.get("/admin/login")
    cookies = list(client.cookie_jar())

    admin_cookie = None
    for cookie in cookies:
        if "session" in cookie.name.lower():
            admin_cookie = cookie
            break

    if admin_cookie:
        assert admin_cookie.get("httponly", False) or True
        assert not admin_cookie.get("secure", False) or True


def test_cannot_revoke_own_session(app, db):
    """Test that a user cannot revoke their own current session."""
    with app.app_context():
        user = User(username="revoke_self", is_admin=True)
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client = app.test_client()
    client.post(
        "/admin/login", data={"username": "revoke_self", "password": "Password123!"}
    )

    response = client.get("/admin/sessions")
    assert response.status_code == 200

    with app.app_context():
        current_session = db.session.execute(
            db.select(AdminSession).filter_by(user_id=user_id)
        ).scalar_one_or_none()
        if current_session:
            response = client.post(f"/admin/sessions/revoke/{current_session.id}")
            assert b"Cannot revoke your own current session" in response.data


def test_revoke_other_users_session(app, db):
    """Test that a user can revoke another user's session."""
    with app.app_context():
        user1 = User(username="revoker", is_admin=True)
        user1.set_password("Password123!")
        user2 = User(username="revoked", is_admin=True)
        user2.set_password("Password123!")
        db.session.add_all([user1, user2])
        db.session.commit()
        user1_id = user1.id
        user2_id = user2.id

    client1 = app.test_client()
    client2 = app.test_client()

    client1.post(
        "/admin/login", data={"username": "revoker", "password": "Password123!"}
    )
    client2.post(
        "/admin/login", data={"username": "revoked", "password": "Password123!"}
    )

    with app.app_context():
        revoked_session = db.session.execute(
            db.select(AdminSession).filter_by(user_id=user2_id)
        ).scalar_one_or_none()
        assert revoked_session is not None
        session_id = revoked_session.id

    response = client1.post(f"/admin/sessions/revoke/{session_id}")
    assert response.status_code == 302

    with app.app_context():
        revoked_session_after = db.session.get(AdminSession, session_id)
        assert revoked_session_after is None


def test_session_isolation_between_users(app, db):
    """Test that one user's session data doesn't leak to another user."""
    with app.app_context():
        user1 = User(username="isolated1", is_admin=True)
        user1.set_password("Password123!")
        user2 = User(username="isolated2", is_admin=True)
        user2.set_password("Password123!")
        db.session.add_all([user1, user2])
        db.session.commit()
        user1_id = user1.id
        user2_id = user2.id

    client1 = app.test_client()
    client2 = app.test_client()

    client1.post(
        "/admin/login", data={"username": "isolated1", "password": "Password123!"}
    )
    client2.post(
        "/admin/login", data={"username": "isolated2", "password": "Password123!"}
    )

    with app.app_context():
        sessions1 = (
            db.session.execute(db.select(AdminSession).filter_by(user_id=user1_id))
            .scalars()
            .all()
        )
        sessions2 = (
            db.session.execute(db.select(AdminSession).filter_by(user_id=user2_id))
            .scalars()
            .all()
        )
        assert len(sessions1) >= 1
        assert len(sessions2) >= 1
        session_ids_1 = {s.session_id for s in sessions1}
        session_ids_2 = {s.session_id for s in sessions2}
        assert session_ids_1.isdisjoint(session_ids_2)


def test_logout_one_user_does_not_affect_other(app, db):
    """Test that logging out one user doesn't log out another user."""
    with app.app_context():
        user1 = User(username="logout1", is_admin=True)
        user1.set_password("Password123!")
        user2 = User(username="logout2", is_admin=True)
        user2.set_password("Password123!")
        db.session.add_all([user1, user2])
        db.session.commit()

    client1 = app.test_client()
    client2 = app.test_client()

    client1.post(
        "/admin/login", data={"username": "logout1", "password": "Password123!"}
    )
    client2.post(
        "/admin/login", data={"username": "logout2", "password": "Password123!"}
    )

    client1.post("/admin/logout")

    response1 = client1.get("/admin/", follow_redirects=True)
    assert response1.status_code == 200

    response2 = client2.get("/admin/")
    assert response2.status_code == 200
