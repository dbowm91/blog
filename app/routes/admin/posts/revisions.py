"""Revision routes - view and restore post revisions."""

from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    abort,
    Response,
)
from typing import cast, Union, Any
from flask_login import current_user

from app.extensions import db
from app.models import Post, PostRevision
from app.routes.admin import admin_required
from app.routes.admin.helpers import (
    _cleanup_orphan_tags,
    invalidate_analytics_cache,
    invalidate_dashboard_cache,
    logger,
)
from app.context_processors import invalidate_footer_cache
from app.tag_cache import invalidate_tag_cache
from app.search import sync_fts
from app.routes.rss import invalidate_rss_cache
from app.routes.public import invalidate_archive_cache
from sqlalchemy import select
from sqlalchemy.orm import joinedload, QueryableAttribute
from sqlalchemy.exc import IntegrityError, OperationalError


def _save_revision(post: Post, author_id: int | None) -> None:
    """Save a revision snapshot of the post."""
    revision = PostRevision(
        post_id=post.id,
        title=post.title,
        slug=post.slug,
        body=post.body,
        summary=post.summary,
        author_id=author_id,
    )
    db.session.add(revision)


def register_revisions_routes(admin: Any) -> None:
    """Register revision routes on the admin Blueprint."""

    @admin.route("/posts/<int:post_id>/revisions")
    @admin_required
    def post_revisions(post_id: int) -> Any:
        """View revision history for a post."""
        post = db.session.get(Post, post_id)
        if not post:
            abort(404)

        revisions = (
            db.session.execute(
                select(PostRevision)
                .filter(PostRevision.post_id == post_id)
                .order_by(PostRevision.created_at.desc())
                .options(joinedload(cast(QueryableAttribute, PostRevision.author)))
            )
            .scalars()
            .unique()
            .all()
        )

        return render_template(
            "admin/revisions.html",
            post=post,
            revisions=revisions,
        )

    @admin.route("/posts/<int:post_id>/revisions/<int:revision_id>/restore", methods=["POST"])
    @admin_required
    def restore_revision(post_id: int, revision_id: int) -> Any:
        """Restore a post to a previous revision."""
        post = db.session.get(Post, post_id)
        if not post:
            abort(404)

        revision = db.session.get(PostRevision, revision_id)
        if not revision or revision.post_id != post_id:
            abort(404)

        _save_revision(post, current_user.id)

        post.title = revision.title
        post.slug = revision.slug
        post.body = revision.body
        post.summary = revision.summary

        searchable_changed = True
        fts_ok = True
        if searchable_changed:
            fts_ok = sync_fts(post.id, post.title, post.body, post.summary, post.published)
        invalidate_tag_cache()
        invalidate_analytics_cache()
        invalidate_dashboard_cache()
        invalidate_footer_cache()
        invalidate_rss_cache()
        invalidate_archive_cache()
        _cleanup_orphan_tags()

        if not fts_ok:
            db.session.rollback()
            flash("Search index temporarily unavailable. Please try again.", "error")
            return redirect(url_for("admin.post_revisions", post_id=post_id))

        try:
            db.session.commit()
        except (IntegrityError, OperationalError) as e:
            logger.warning("Failed to restore revision for post %d: %s", post_id, e)
            db.session.rollback()
            flash("Database error occurred. Please try again.", "error")
            return redirect(url_for("admin.post_revisions", post_id=post_id))

        flash("Post restored to previous revision.", "success")
        return redirect(url_for("admin.post_revisions", post_id=post_id))
