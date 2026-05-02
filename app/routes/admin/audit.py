from __future__ import annotations

from flask import render_template, request, Response

from app.extensions import db
from app.models import AdminAuditLog
from app.routes.admin import admin, admin_required
from sqlalchemy import select
from sqlalchemy.orm import joinedload, QueryableAttribute
from typing import cast, Union


@admin.route("/audit")
@admin_required
def audit_log() -> Union[Response, str, tuple[Union[Response, str], int]]:
    """
    View admin audit log entries.

    Methods: GET
    GET: Renders audit log with pagination and filtering by action.
    Query params:
        page: Page number (default 1)
        action: Filter by action type
    Requires: Admin authentication.
    """
    page = request.args.get("page", 1, type=int)
    action_filter = request.args.get("action", "").strip()

    query = select(AdminAuditLog).options(
        joinedload(cast(QueryableAttribute, AdminAuditLog.actor))
    ).order_by(AdminAuditLog.timestamp.desc())

    if action_filter:
        query = query.filter(AdminAuditLog.action == action_filter)

    pagination = db.paginate(query, page=page, per_page=50, error_out=False)
    entries = pagination.items

    actions = db.session.execute(
        select(AdminAuditLog.action).distinct().order_by(AdminAuditLog.action)
    ).scalars().all()

    return render_template(
        "admin/audit.html",
        entries=entries,
        pagination=pagination,
        actions=actions,
        current_action=action_filter,
    )
