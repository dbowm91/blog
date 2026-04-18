import secrets

from flask import redirect, url_for, request, flash, session, Response, abort
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.extensions import db
from app.models import User, AdminSession, Post
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import logger
from app.csrf import validate_csrf_token


@admin.route("/login", methods=["GET", "POST"])
def login() -> Response:
    """
    Admin login page.

    Methods: GET, POST
    GET: Renders the login form. Redirects if already authenticated.
    POST: Authenticates user with username/password. Creates AdminSession on success.
    Requires: Admin user with valid credentials.
    """
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = db.session.execute(
            select(User).filter_by(username=username)
        ).scalar_one_or_none()
        if user and user.check_password(password) and user.is_admin:
            session.clear()
            login_user(user)
            sid = secrets.token_hex(32)
            admin_session = AdminSession(
                user_id=user.id,
                session_id=sid,
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent", "")[:256],
            )
            db.session.add(admin_session)
            db.session.commit()
            session["admin_session_id"] = sid
            session["admin_session_ip"] = request.remote_addr
            return redirect(url_for("admin.dashboard"))
        flash("Invalid credentials.", "error")

    from flask import render_template

    return render_template("admin/login.html")


@admin.route("/logout", methods=["POST"])
@login_required
def logout() -> Response:
    """
    Log out the current admin user.

    Methods: POST
    POST: Clears admin session, deletes AdminSession record, and redirects to home.
    Requires: Login (any authenticated user, not just admin).
    """
    validate_csrf_token()
    sid = session.pop("admin_session_id", None)
    if sid:
        admin_session = db.session.execute(
            select(AdminSession).filter_by(session_id=sid)
        ).scalar_one_or_none()
        if admin_session:
            db.session.delete(admin_session)
            try:
                db.session.commit()
            except (IntegrityError, OperationalError):
                db.session.rollback()
    logout_user()
    return redirect(url_for("public.index"))


@admin.route("/newsletter-reset/<int:post_id>", methods=["POST"])
@admin_required
def newsletter_reset(post_id) -> Response:
    """
    Reset newsletter status for a post.

    Methods: POST
    POST: Resets newsletter_sent_at and newsletter_attempts to allow post to be
          included in the next newsletter send.
    Requires: Admin authentication.
    Path params: post_id (int) - ID of the post to reset.
    """
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)
    post.newsletter_sent_at = None
    post.newsletter_attempts = 0
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.dashboard"))
    flash(
        f"Newsletter flag reset for '{post.title}'. It will be included in the next newsletter.",
        "success",
    )
    return redirect(url_for("admin.dashboard"))
