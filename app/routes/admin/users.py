from flask import render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import User
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import _check_password_complexity, logger
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, OperationalError


@admin.route("/users")
@admin_required
def users_list():
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
def create_user():
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
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.id == current_user.id:
        flash("Cannot delete your own account.", "error")
        return redirect(url_for("admin.users_list"))
    admin_count = db.session.execute(
        select(func.count(User.id)).filter_by(is_admin=True)
    ).scalar_one()
    if user.is_admin and admin_count <= 1:
        flash("Cannot delete the last admin user.", "error")
        return redirect(url_for("admin.users_list"))
    username = user.username
    is_admin = user.is_admin
    db.session.delete(user)
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.users_list"))
    logger.info(
        "User deleted: id=%d username=%s is_admin=%s", user_id, username, is_admin
    )
    flash(f"User '{username}' deleted.", "success")
    return redirect(url_for("admin.users_list"))


@admin.route("/users/password/<int:user_id>", methods=["POST"])
@admin_required
def change_password(user_id):
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
