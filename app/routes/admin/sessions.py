from __future__ import annotations
from flask import render_template, redirect, url_for, flash, session, abort
from flask.typing import ResponseReturnValue

from app.extensions import db
from app.models import AdminSession
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import logger
from sqlalchemy import select
from sqlalchemy.orm import joinedload, QueryableAttribute
from typing import cast
from sqlalchemy.exc import IntegrityError, OperationalError


@admin.route("/sessions")
@admin_required
def sessions_list() -> ResponseReturnValue:
    """
    List all active admin sessions.

    Methods: GET
    GET: Renders session management page showing all AdminSession records.
    Requires: Admin authentication.
    """
    sessions = (
        db.session.execute(
            select(AdminSession)
            .options(joinedload(cast(QueryableAttribute, AdminSession.user)))
            .order_by(AdminSession.last_activity.desc())
        )
        .unique()
        .scalars()
        .all()
    )
    current_session_id = session.get("admin_session_id", "")
    return render_template(
        "admin/sessions.html",
        sessions=sessions,
        current_session_id=current_session_id,
    )


@admin.route("/sessions/revoke/<int:sess_id>", methods=["POST"])
@admin_required
def revoke_session(sess_id) -> ResponseReturnValue:
    """
    Revoke an admin session.

    Methods: POST
    POST: Deletes the AdminSession record, forcing logout.
    Requires: Admin authentication.
    Guards: Cannot revoke own current session.
    Path params: sess_id (int) - ID of the session to revoke.
    """
    admin_session = db.session.get(AdminSession, sess_id)
    if not admin_session:
        abort(404)
    if admin_session.session_id == session.get("admin_session_id"):
        flash("Cannot revoke your own current session. Use logout instead.", "error")
        return redirect(url_for("admin.sessions_list"))
    db.session.delete(admin_session)
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.sessions_list"))
    logger.info("Session revoked: sess_id=%d", sess_id)
    flash("Session revoked.", "success")
    return redirect(url_for("admin.sessions_list"))
