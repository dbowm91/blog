import hashlib
import secrets
import time
import pyotp
import qrcode
import io
import base64
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from flask import redirect, url_for, request, flash, session, abort, render_template
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.extensions import db
from app.models import User, AdminSession, Post
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import logger

from app.tasks import send_password_reset_task
from app.routes.admin.helpers import _check_password_complexity
from app.config import MAX_FAILED_ATTEMPTS, LOCKOUT_DURATION_MINUTES, LOGIN_FAILURE_DELAY
from app import limiter


def _hash_token(token: str) -> str:
    """Hash a reset token with SHA-256 for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


@admin.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login() -> Any:
    """
    Admin login page.

    Methods: GET, POST
    GET: Renders the login form. Redirects if already authenticated.
    POST: Authenticates user with username/password. If 2FA is enabled,
          redirects to TOTP verification. Creates AdminSession on success.
    Requires: Admin user with valid credentials.

    SECURITY (SEC-7): Session Fixation Protection
    - session.clear() is called before login_user() to mitigate session fixation attacks
    - This effectively creates a new session ID by clearing the old session data
    - Alternative would be Flask-Session with Redis and session.regenerate_id()
    - IP binding is implemented via AdminSession.ip_address field
    - Limitation: IP binding may cause issues for users behind NAT/proxies/VPNs
    """
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = db.session.execute(select(User).filter_by(username=username)).scalar_one_or_none()
        if user and user.is_locked():
            flash("Account is locked due to too many failed attempts. Try again later.", "error")
            return redirect(url_for("admin.login"))
        if user and user.check_password(password) and user.is_admin:
            if user.totp_enabled and user.totp_secret:
                session["pending_2fa_user_id"] = user.id
                return redirect(url_for("admin.login_2fa"))

            # SEC-7: Session Fixation Protection
            # Clear the session before logging in to regenerate session ID
            # This prevents session fixation attacks where an attacker sets
            # a known session ID before the user authenticates
            session.clear()

            login_user(user)
            user.reset_failed_login()
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
        if user:
            user.record_failed_login(MAX_FAILED_ATTEMPTS, LOCKOUT_DURATION_MINUTES)
            db.session.commit()
        flash("Invalid credentials.", "error")
        time.sleep(LOGIN_FAILURE_DELAY)

    from flask import render_template

    return render_template("admin/login.html")


@admin.route("/logout", methods=["POST"])
@login_required
def logout() -> Any:
    """
    Log out the current admin user.

    Methods: POST
    POST: Clears admin session, deletes AdminSession record, and redirects to home.
    Requires: Login (any authenticated user, not just admin).
    """
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
def newsletter_reset(post_id: int) -> Any:
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


@admin.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def forgot_password() -> Any:
    """
    Request a password reset.

    Methods: GET, POST
    GET: Renders the forgot password form.
    POST: Generates a reset token and sends password reset email.
    """
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        if not identifier:
            flash("Please enter your username or email address.", "error")
            return redirect(url_for("admin.forgot_password"))

        user = db.session.execute(select(User).filter_by(username=identifier)).scalar_one_or_none()

        if user and user.is_admin:
            token = secrets.token_hex(32)
            user.reset_token = _hash_token(token)
            user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            try:
                db.session.commit()
                send_password_reset_task.delay(user.id, token)
                flash("If that account exists, a password reset email has been sent.", "success")
            except (IntegrityError, OperationalError):
                db.session.rollback()
                flash("An error occurred. Please try again.", "error")
        else:
            flash("If that account exists, a password reset email has been sent.", "success")
            time.sleep(0.1)

        return redirect(url_for("admin.login"))

    return render_template("admin/forgot-password.html")


@admin.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token: str) -> Any:
    """
    Reset password using a token.

    Methods: GET, POST
    GET: Renders the reset password form if token is valid.
    POST: Updates password and invalidates all admin sessions for the user.
    """
    hashed_token = _hash_token(token)
    user = db.session.execute(select(User).filter_by(reset_token=hashed_token)).scalar_one_or_none()

    if not user or not user.reset_token_expires_at:
        flash("Invalid or expired reset token.", "error")
        return redirect(url_for("admin.forgot_password"))

    if user.reset_token_expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        flash("Reset token has expired. Please request a new one.", "error")
        return redirect(url_for("admin.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        if not _check_password_complexity(password):
            flash(
                "Password must be at least 8 characters and contain at least 3 of 4: lowercase, uppercase, digit, special.",
                "error",
            )
            return redirect(url_for("admin.reset_password", token=token))
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("admin.reset_password", token=token))

        user.set_password(password)
        user.reset_token = None
        user.reset_token_expires_at = None

        for admin_session in cast(list[AdminSession], user.admin_sessions):
            db.session.delete(admin_session)

        try:
            db.session.commit()
        except (IntegrityError, OperationalError):
            db.session.rollback()
            flash("An error occurred. Please try again.", "error")
            return redirect(url_for("admin.reset_password", token=token))

        # SEC-7: Session Fixation Protection
        # Clear session after password reset to force re-authentication
        # This ensures any old sessions are invalidated
        session.clear()

        logger.info(
            "Password reset completed: user_id=%d",
            user.id,
        )
        flash("Your password has been reset. Please sign in with your new password.", "success")
        return redirect(url_for("admin.login"))

    return render_template("admin/reset-password.html", token=token)


@admin.route("/2fa/setup", methods=["GET", "POST"])
@login_required
@admin_required
def setup_2fa() -> Any:
    """
    2FA setup - generate secret and verify.

    Methods: GET, POST
    GET: Generates TOTP secret, renders setup page with QR code.
    POST: Verifies TOTP code and enables 2FA.
    Requires: Admin authentication.
    """
    user = db.session.get(User, current_user.id)
    if not user:
        abort(404)

    if request.method == "POST":
        if user.totp_enabled:
            flash("2FA is already enabled.", "info")
            return redirect(url_for("admin.dashboard"))

        secret = pyotp.random_base32()
        user.set_totp_secret(secret)
        try:
            db.session.commit()
        except (IntegrityError, OperationalError):
            db.session.rollback()
            flash("Database error occurred.", "error")
            return redirect(url_for("admin.setup_2fa"))

        logger.info("2FA secret generated: user_id=%d", user.id)
        flash("2FA secret generated. Scan the QR code with your authenticator app.", "success")
        return redirect(url_for("admin.verify_2fa"))

    qr_code = None
    existing_secret = user.totp_secret
    if existing_secret:
        uri = user.get_totp_uri()
        if uri:
            img = qrcode.make(uri)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            qr_code = base64.b64encode(buf.getvalue()).decode()

    return render_template("admin/2fa_setup.html", secret=existing_secret, qr_code=qr_code)


@admin.route("/2fa/verify", methods=["GET", "POST"])
@login_required
@admin_required
def verify_2fa() -> Any:
    """
    Verify 2FA token and enable 2FA.

    Methods: GET, POST
    GET: Renders verification page.
    POST: Verifies TOTP code and enables 2FA.
    Requires: Admin authentication and 2FA secret generated.
    """
    user = db.session.get(User, current_user.id)
    if not user or not user.totp_secret:
        flash("Please set up 2FA first.", "error")
        return redirect(url_for("admin.setup_2fa"))

    if request.method == "POST":
        token = request.form.get("token", "").strip()
        if pyotp.TOTP(user.totp_secret).verify(token):
            user.totp_enabled = True
            backup_codes = user.generate_backup_codes()
            try:
                db.session.commit()
            except (IntegrityError, OperationalError):
                db.session.rollback()
                flash("Database error occurred.", "error")
                return redirect(url_for("admin.verify_2fa"))
            logger.info("2FA enabled: user_id=%d", user.id)
            session["backup_codes"] = backup_codes
            flash("2FA has been enabled. Save your backup codes!", "success")
            return redirect(url_for("admin.backup_codes"))
        flash("Invalid code. Please try again.", "error")

    return render_template("admin/2fa_verify.html")


@admin.route("/login-2fa", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login_2fa() -> Any:
    """
    TOTP verification during login.

    Methods: GET, POST
    GET: Renders TOTP verification form.
    POST: Verifies TOTP code and completes login if valid.
    """
    user_id = session.get("pending_2fa_user_id")
    if not user_id:
        return redirect(url_for("admin.login"))

    user = db.session.get(User, user_id)
    if not user or not user.totp_enabled or not user.totp_secret:
        session.pop("pending_2fa_user_id", None)
        return redirect(url_for("admin.login"))

    if request.method == "POST":
        token = request.form.get("token", "").strip()
        secret = user.totp_secret
        if secret and pyotp.TOTP(secret).verify(token):
            session.pop("pending_2fa_user_id", None)
            session.clear()

            login_user(user)
            user.reset_failed_login()
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

        if user.verify_backup_code(token):
            try:
                db.session.commit()
            except (IntegrityError, OperationalError):
                db.session.rollback()
            session.pop("pending_2fa_user_id", None)
            session.clear()

            login_user(user)
            user.reset_failed_login()
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
            logger.info("Login via backup code: user_id=%d", user.id)
            return redirect(url_for("admin.dashboard"))

        flash("Invalid code. Please try again.", "error")
        time.sleep(LOGIN_FAILURE_DELAY)

    return render_template("admin/login_2fa.html")


@admin.route("/2fa/backup-codes", methods=["GET"])
@login_required
@admin_required
def backup_codes() -> Any:
    """Display backup codes after 2FA enablement."""
    codes = session.pop("backup_codes", None)
    if not codes:
        flash("No backup codes to display.", "info")
        return redirect(url_for("admin.dashboard"))
    user = db.session.get(User, current_user.id)
    if not user:
        abort(404)
    remaining = len(user.backup_codes_hashed) if user.backup_codes_hashed else 0
    return render_template("admin/backup_codes.html", codes=codes, remaining=remaining)


@admin.route("/2fa/disable", methods=["GET", "POST"])
@login_required
@admin_required
def disable_2fa() -> Any:
    """Disable 2FA for the current user."""
    user = db.session.get(User, current_user.id)
    if not user:
        abort(404)

    if not user.totp_enabled:
        flash("2FA is not enabled.", "info")
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        token = request.form.get("token", "").strip()
        secret = user.totp_secret
        if secret and pyotp.TOTP(secret).verify(token):
            user.totp_enabled = False
            user.totp_secret_encrypted = None
            user.backup_codes_hashed = None
            try:
                db.session.commit()
            except (IntegrityError, OperationalError):
                db.session.rollback()
                flash("Database error occurred.", "error")
                return redirect(url_for("admin.disable_2fa"))
            logger.info("2FA disabled: user_id=%d", user.id)
        flash("Invalid code. Please try again.", "error")
        flash("Invalid code. Please try again.", "error")

    return render_template("admin/disable_2fa.html")
