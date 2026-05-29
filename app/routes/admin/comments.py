from __future__ import annotations

from flask import render_template, request, redirect, url_for, flash, abort
from typing import Any, cast

from app.extensions import db
from app.models import Comment
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import logger
from sqlalchemy import select
from sqlalchemy.orm import joinedload, QueryableAttribute
from sqlalchemy.exc import IntegrityError, OperationalError


@admin.route("/comments")
@admin_required
def comments_list() -> Any:
    """
    List all comments for moderation.

    Methods: GET
    GET: Renders comments list with filtering by approved/spam status.
    Query params:
        approved: Filter by approval status (yes/no/all)
        spam: Filter by spam/quarantine status (yes/no/all)
        page: Page number (default 1)
    Requires: Admin authentication.
    """
    approved_filter = request.args.get("approved", "no")
    spam_filter = request.args.get("spam", "all")
    page = request.args.get("page", 1, type=int)

    query = (
        select(Comment)
        .options(joinedload(cast(QueryableAttribute, Comment.post)))
        .order_by(Comment.created_at.desc())
    )

    if approved_filter == "yes":
        query = query.filter(Comment.approved.is_(True))
    elif approved_filter == "no":
        query = query.filter(Comment.approved.is_(False))

    if spam_filter == "yes":
        query = query.filter(Comment.is_spam.is_(True))
    elif spam_filter == "no":
        query = query.filter(Comment.is_spam.is_(False))

    pagination = db.paginate(query, page=page, per_page=50, error_out=False)
    comments = pagination.items

    return render_template(
        "admin/comments.html",
        comments=comments,
        pagination=pagination,
        approved_filter=approved_filter,
        spam_filter=spam_filter,
    )


@admin.route("/comments/<int:comment_id>/approve", methods=["POST"])
@admin_required
def approve_comment(comment_id: int) -> Any:
    """Approve a comment. Also clears spam flag if present."""
    comment = db.session.get(Comment, comment_id)
    if not comment:
        abort(404)
    comment.approved = True
    if comment.is_spam:
        comment.is_spam = False
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred.", "error")
    else:
        logger.info("Comment approved: comment_id=%d", comment_id)
        flash("Comment approved.", "success")
    return redirect(url_for("admin.comments_list"))


@admin.route("/comments/<int:comment_id>/delete", methods=["POST"])
@admin_required
def delete_comment(comment_id: int) -> Any:
    """Delete a comment."""
    comment = db.session.get(Comment, comment_id)
    if not comment:
        abort(404)
    db.session.delete(comment)
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred.", "error")
    else:
        logger.info("Comment deleted: comment_id=%d", comment_id)
        flash("Comment deleted.", "success")
    return redirect(url_for("admin.comments_list"))
