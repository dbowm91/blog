"""Admin service functions — reusable logic for user/admin management."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import User
from app.services.operations.results import (
    AdminCreatedResult,
    AdminListResult,
    AdminPasswordResetResult,
    AdminPromotedResult,
)
from app.transaction import commit_with_rollback


def _check_password_complexity(password: str) -> bool:
    if len(password) < 8:
        return False
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    return sum((has_lower, has_upper, has_digit, has_special)) >= 3


def create_admin(
    username: str, password: str, *, update_existing: bool = False
) -> AdminCreatedResult:
    if not _check_password_complexity(password):
        raise ValueError(
            "Password must be at least 8 characters and contain "
            "at least 3 of 4: lowercase, uppercase, digit, special character."
        )

    existing = db.session.execute(select(User).filter_by(username=username)).scalar_one_or_none()

    if existing:
        if not update_existing:
            raise ConflictError(f"User '{username}' already exists.")

        existing.is_admin = True
        existing.set_password(password)
        commit_with_rollback()
        return AdminCreatedResult(
            ok=True,
            code="admin.created",
            summary=f"User '{username}' promoted to admin.",
            username=username,
            details={"action": "promoted", "existing_user": True},
        )

    user = User(username=username, is_admin=True)
    user.set_password(password)
    db.session.add(user)
    try:
        commit_with_rollback()
    except IntegrityError:
        db.session.rollback()
        raise ConflictError(f"User '{username}' already exists.")

    return AdminCreatedResult(
        ok=True,
        code="admin.created",
        summary=f"Admin user '{username}' created.",
        username=username,
        details={"action": "created", "existing_user": False},
    )


def promote_admin(username: str) -> AdminPromotedResult:
    user = db.session.execute(select(User).filter_by(username=username)).scalar_one_or_none()

    if not user:
        raise ValueError(f"User '{username}' not found.")

    if user.is_admin:
        raise ConflictError(f"User '{username}' is already an admin.")

    user.is_admin = True
    commit_with_rollback()

    return AdminPromotedResult(
        ok=True,
        code="admin.promoted",
        summary=f"User '{username}' promoted to admin.",
        username=username,
    )


def reset_admin_password(username: str, password: str) -> AdminPasswordResetResult:
    if not _check_password_complexity(password):
        raise ValueError(
            "Password must be at least 8 characters and contain "
            "at least 3 of 4: lowercase, uppercase, digit, special character."
        )

    user = db.session.execute(select(User).filter_by(username=username)).scalar_one_or_none()

    if not user:
        raise ValueError(f"User '{username}' not found.")

    user.set_password(password)
    commit_with_rollback()

    return AdminPasswordResetResult(
        ok=True,
        code="admin.password_reset",
        summary=f"Password reset for user '{username}'.",
        username=username,
    )


def list_admins() -> AdminListResult:
    admins = (
        db.session.execute(select(User).filter_by(is_admin=True).order_by(User.username))
        .scalars()
        .all()
    )

    admin_dicts = [{"id": u.id, "username": u.username, "email": u.email} for u in admins]

    return AdminListResult(
        ok=True,
        code="admin.list",
        summary=f"Found {len(admins)} admin user(s).",
        admins=admin_dicts,
        details={"count": len(admins)},
    )


class ConflictError(Exception):
    pass
