from __future__ import annotations

import os

from flask import (
    render_template,
    redirect,
    url_for,
    request,
    flash,
    current_app,
)
from flask.typing import ResponseReturnValue
from flask_login import current_user
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, QueryableAttribute
from typing import cast
from sqlalchemy.exc import IntegrityError, OperationalError

from app.extensions import db
from app.models import Post, PageView, ShareEvent
from app.utils import utc_now, safe_delete_file
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import (
    _get_posts_query,
    _cleanup_orphan_tags,
    invalidate_analytics_cache,
)
from app.context_processors import invalidate_footer_cache
from app.routes.admin.helpers.dashboard import _get_dashboard_metrics
from app.config import DASHBOARD_PER_PAGE
from app.tag_cache import invalidate_tag_cache
from app.routes.rss import invalidate_rss_cache
from app.routes.public import invalidate_archive_cache
from app.search import sync_fts_batch
from app.search import remove_fts
from app.routes.admin.posts.revisions import _save_revision

# Import registration functions from sub-modules
from app.routes.admin.posts.editor import register_editor_routes
from app.routes.admin.posts.manage import register_manage_routes
from app.routes.admin.posts.revisions import register_revisions_routes

# Register all routes
register_editor_routes(admin)
register_manage_routes(admin)
register_revisions_routes(admin)


@admin.route("/")
@admin_required
def dashboard() -> ResponseReturnValue:
    """Admin dashboard - lists all posts with pagination and search."""
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "all")

    base_q = _get_posts_query(status, q)

    pagination = db.paginate(base_q, page=page, per_page=DASHBOARD_PER_PAGE, error_out=False)
    posts = pagination.items

    post_ids = [p.id for p in posts]
    if post_ids:
        view_counts_sq = (
            select(PageView.post_id, func.count(PageView.id).label("cnt"))
            .where(PageView.post_id.in_(post_ids))
            .group_by(PageView.post_id)
            .subquery()
        )
        share_counts_sq = (
            select(ShareEvent.post_id, func.count(ShareEvent.id).label("cnt"))
            .where(ShareEvent.post_id.in_(post_ids))
            .group_by(ShareEvent.post_id)
            .subquery()
        )
        rows = db.session.execute(
            select(
                Post.id,
                func.coalesce(view_counts_sq.c.cnt, 0).label("views"),
                func.coalesce(share_counts_sq.c.cnt, 0).label("shares"),
            )
            .outerjoin(view_counts_sq, Post.id == view_counts_sq.c.post_id)
            .outerjoin(share_counts_sq, Post.id == share_counts_sq.c.post_id)
            .where(Post.id.in_(post_ids))
        ).all()
        view_counts = {row.id: row.views for row in rows}
        share_counts = {row.id: row.shares for row in rows}
    else:
        view_counts = {}
        share_counts = {}

    metrics = _get_dashboard_metrics()

    return render_template(
        "admin/dashboard.html",
        posts=posts,
        pagination=pagination,
        view_counts=view_counts,
        share_counts=share_counts,
        total_views=metrics["total_views"],
        total_posts=metrics["total_posts"],
        total_shares=metrics["total_shares"],
        total_subscribers=metrics["total_subscribers"],
        trending=metrics["trending"],
        top_shares=metrics["top_shares"],
        daily_views=metrics["daily_views"],
        new_this_month=metrics["new_this_month"],
        views_trend=metrics["views_trend"],
        q=q,
        status=status,
    )


@admin.route("/bulk", methods=["POST"])
@admin_required
def bulk_operations() -> ResponseReturnValue:
    """Bulk operations on selected posts."""
    action = request.form.get("action")
    post_ids = request.form.getlist("post_ids")
    if not post_ids:
        flash("No posts selected.", "error")
        return redirect(url_for("admin.dashboard"))

    valid_ids = []
    for pid in post_ids:
        try:
            valid_ids.append(int(pid))
        except (ValueError, TypeError):
            flash("Invalid post ID.", "error")
            return redirect(url_for("admin.dashboard"))

    posts = (
        db.session.execute(
            select(Post)
            .filter(Post.id.in_(valid_ids))
            .options(joinedload(cast(QueryableAttribute, Post.tags)))
        )
        .scalars()
        .unique()
        .all()
    )
    if not posts:
        flash("No posts found.", "error")
        return redirect(url_for("admin.dashboard"))

    if action == "publish":
        now = utc_now()
        fts_items = []
        for post in posts:
            if post.published:
                _save_revision(post, current_user.id)
            else:
                post.published = True
                post.published_at = now
            fts_items.append((post.id, post.title, post.body, post.summary, post.published))
        invalidate_tag_cache()
        invalidate_analytics_cache()
        invalidate_footer_cache()
        invalidate_rss_cache()
        invalidate_archive_cache()
        if not sync_fts_batch(fts_items):
            db.session.rollback()
            flash("Search index temporarily unavailable. Please try again.", "error")
            return redirect(url_for("admin.dashboard"))
        try:
            db.session.commit()
        except (IntegrityError, OperationalError):
            db.session.rollback()
            flash("Database error occurred. Please try again.", "error")
            return redirect(url_for("admin.dashboard"))
        flash(f"Published {len(posts)} post(s).", "success")
    elif action == "unpublish":
        fts_items = []
        for post in posts:
            post.published = False
            fts_items.append((post.id, post.title, post.body, post.summary, post.published))
        invalidate_tag_cache()
        invalidate_analytics_cache()
        invalidate_footer_cache()
        invalidate_rss_cache()
        invalidate_archive_cache()
        if not sync_fts_batch(fts_items):
            db.session.rollback()
            flash("Search index temporarily unavailable. Please try again.", "error")
            return redirect(url_for("admin.dashboard"))
        try:
            db.session.commit()
        except (IntegrityError, OperationalError):
            db.session.rollback()
            flash("Database error occurred. Please try again.", "error")
            return redirect(url_for("admin.dashboard"))
        flash(f"Unpublished {len(posts)} post(s).", "success")
    elif action == "unschedule":
        for post in posts:
            post.scheduled_publish_at = None
        invalidate_tag_cache()
        invalidate_analytics_cache()
        invalidate_footer_cache()
        try:
            db.session.commit()
        except (IntegrityError, OperationalError):
            db.session.rollback()
            flash("Database error occurred. Please try again.", "error")
            return redirect(url_for("admin.dashboard"))
        flash(f"Unscheduled {len(posts)} post(s).", "success")
    elif action == "delete":
        images_to_delete = []
        deleted_post_ids = []
        for post in posts:
            if post.image:
                images_to_delete.append(post.image)
            deleted_post_ids.append(post.id)
            db.session.delete(post)
        invalidate_tag_cache()
        invalidate_analytics_cache()
        invalidate_footer_cache()
        _cleanup_orphan_tags()
        try:
            db.session.commit()
        except (IntegrityError, OperationalError):
            db.session.rollback()
            flash("Database error occurred. Please try again.", "error")
            return redirect(url_for("admin.dashboard"))
        for pid in deleted_post_ids:
            remove_fts(pid)
        for img in images_to_delete:
            safe_delete_file(os.path.join(current_app.config["UPLOAD_FOLDER"], img))
        flash(f"Deleted {len(posts)} post(s).", "success")
    else:
        flash("Invalid action.", "error")

    return redirect(url_for("admin.dashboard"))
