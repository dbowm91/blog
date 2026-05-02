from __future__ import annotations

from flask import render_template, redirect, url_for, request, flash, abort, session, Response
from flask.typing import ResponseReturnValue
from typing import Union
from flask_login import current_user

from app.extensions import db
from app.models import User
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import _check_password_complexity, logger
from app.csrf import generate_csrf_token
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, OperationalError


@admin.route("/users")
@admin_required
def users_list() -> ResponseReturnValue:
    """
    List all admin users.

    Methods: GET
    GET: Renders user management page with paginated list of users.
    Query params: page - Page number (default 1)
    Requires: Admin authentication.
    """
    page = request.args.get("page", 1, type=int)
    per_page = 20
    pagination = db.paginate(
        select(User).order_by(User.username),
        page=page,
        per_page=per_page,
        error_out=False,
    )
    return render_template(
        "admin/users.html", users=pagination.items, pagination=pagination
    )


@admin.route("/users/create", methods=["POST"])
@admin_required
def create_user() -> ResponseReturnValue:
    """
    Create a new admin user.

    Methods: POST
    POST: Creates new user with username and hashed password. Validates password complexity.
    Requires: Admin authentication.
    Form params: username (max 80 chars), password, is_admin (checkbox)
    Password requirements: 8+ chars with at least 3 of 4: lowercase, uppercase, digit, special.
    """
    username = request.form.get("username", "").strip()[:80]
    password = request.form.get("password", "").strip()
    is_admin = "is_admin" in request.form

    if not username or not password:
        flash("Username and password are required.", "error")
        return redirect(url_for("admin.users_list"))

    if not _check_password_complexity(password):
        flash(
            "Password must be at least 8 characters and contain at least 3 of 4: lowercase, uppercase, digit, special.",
            "error",
        )
        return redirect(url_for("admin.users_list"))

    existing = db.session.execute(
        select(User).filter_by(username=username)
    ).scalar_one_or_none()
    if existing:
        flash(f"User '{username}' already exists.", "error")
        return redirect(url_for("admin.users_list"))

    user = User(username=username, is_admin=is_admin)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.users_list"))
    logger.info(
        "User created: id=%d username=%s is_admin=%s", user.id, username, is_admin
    )
    flash(f"User '{username}' created.", "success")
    return redirect(url_for("admin.users_list"))


@admin.route("/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id: int) -> ResponseReturnValue:
    """
    Delete a user.

    Methods: POST
    POST: Deletes the user and their AdminSession records (cascade).
    Requires: Admin authentication.
    Guards: Cannot delete own account, cannot delete last admin.
    Path params: user_id (int) - ID of the user to delete.
    """
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.id == current_user.id:
        flash("Cannot delete your own account.", "error")
        return redirect(url_for("admin.users_list"))
    username = user.username
    is_admin = user.is_admin
    db.session.delete(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Cannot delete the last admin user.", "error")
        return redirect(url_for("admin.users_list"))
    logger.info(
        "User deleted: id=%d username=%s is_admin=%s", user_id, username, is_admin
    )
    flash(f"User '{username}' deleted.", "success")
    return redirect(url_for("admin.users_list"))


@admin.route("/users/<int:user_id>/promote", methods=["POST"])
@admin_required
def promote_user(user_id: int) -> ResponseReturnValue:
    """
    Promote a user to admin.

    Methods: POST
    POST: Sets user.is_admin = True.
    Requires: Admin authentication.
    Path params: user_id (int) - ID of the user to promote.
    """
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.is_admin:
        flash(f"'{user.username}' is already an admin.", "error")
        return redirect(url_for("admin.users_list"))
    user.is_admin = True
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.users_list"))
    session["csrf_tokens"] = [generate_csrf_token()]
    logger.info("User promoted to admin: user_id=%d username=%s", user_id, user.username)
    flash(f"'{user.username}' promoted to admin.", "success")
    return redirect(url_for("admin.users_list"))


@admin.route("/users/<int:user_id>/demote", methods=["POST"])
@admin_required
def demote_user(user_id: int) -> ResponseReturnValue:
    """
    Demote an admin to regular user.

    Methods: POST
    POST: Sets user.is_admin = False.
    Requires: Admin authentication.
    Guards: Cannot demote self, cannot demote if would leave no admins.
    Path params: user_id (int) - ID of the user to demote.
    """
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.id == current_user.id:
        flash("Cannot demote your own account.", "error")
        return redirect(url_for("admin.users_list"))
    admin_count = db.session.execute(
        select(func.count(User.id)).filter(User.is_admin)
    ).scalar()
    if (admin_count or 0) <= 1:
        flash("Cannot demote the last admin user.", "error")
        return redirect(url_for("admin.users_list"))
    user.is_admin = False
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.users_list"))
    session["csrf_tokens"] = [generate_csrf_token()]
    logger.info("User demoted from admin: user_id=%d username=%s", user_id, user.username)
    flash(f"'{user.username}' demoted from admin.", "success")
    return redirect(url_for("admin.users_list"))


@admin.route("/users/<int:user_id>/make-owner", methods=["POST"])
@admin_required
def make_owner(user_id: int) -> ResponseReturnValue:
    """
    Transfer ownership to another admin.

    Methods: POST
    POST: Transfers owner status by setting all admins is_admin=True except target user,
          then setting target user as the only admin.
    Requires: Admin authentication + current user password confirmation.
    Guards: Cannot transfer to self.
    Path params: user_id (int) - ID of the user to make owner.
    Form params: password (current user's password for confirmation)
    """
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.id == current_user.id:
        flash("Cannot transfer ownership to yourself.", "error")
        return redirect(url_for("admin.users_list"))
    password = request.form.get("password", "").strip()
    if not password or not current_user.check_password(password):
        flash("Invalid password. Ownership transfer requires your password.", "error")
        return redirect(url_for("admin.users_list"))
    admin_count = db.session.execute(
        select(func.count(User.id)).filter(User.is_admin)
    ).scalar()
    if (admin_count or 0) <= 1:
        flash("Cannot transfer ownership while you are the only admin.", "error")
        return redirect(url_for("admin.users_list"))
    user.is_admin = True
    db.session.flush()

    all_admins = db.session.execute(
        select(User).filter(User.is_admin, User.id != user_id)
    ).scalars().all()
    for admin_user in all_admins:
        admin_user.is_admin = False
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.users_list"))
    session["csrf_tokens"] = [generate_csrf_token()]
    logger.info("Ownership transferred: from user_id=%d to user_id=%d", current_user.id, user_id)
    flash(f"Ownership transferred to '{user.username}'.", "success")
    return redirect(url_for("admin.users_list"))


@admin.route("/users/password/<int:user_id>", methods=["POST"])
@admin_required
def change_password(user_id: int) -> ResponseReturnValue:
    """
    Change a user's password.

    Methods: POST
    POST: Updates user's password. Validates password complexity.
    Requires: Admin authentication.
    Path params: user_id (int) - ID of the user whose password to change.
    Form params: password - New password (8+ chars, 3 of 4 character classes)
    """
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    password = request.form.get("password", "").strip()
    if not _check_password_complexity(password):
        flash(
            "Password must be at least 8 characters and contain at least 3 of 4: lowercase, uppercase, digit, special.",
            "error",
        )
        return redirect(url_for("admin.users_list"))
    user.set_password(password)
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.users_list"))
    logger.info("Password changed: user_id=%d username=%s", user_id, user.username)
    flash(f"Password changed for '{user.username}'.", "success")
    return redirect(url_for("admin.users_list"))
