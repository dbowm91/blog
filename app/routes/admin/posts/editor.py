"""Editor routes - new post and edit post."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from flask import (
    render_template,
    redirect,
    url_for,
    request,
    flash,
    jsonify,
    abort,
    current_app,
)
from typing import Any, cast
from flask_login import current_user

from app.extensions import db
from app.markdown_renderer import render_markdown
from app.models import Post, Tag
from app.routes.admin import author_required
from app.routes.admin.helpers import (
    _generate_unique_slug,
    _save_image,
    _apply_post_updates,
    _cleanup_orphan_tags,
    _get_or_create_tags,
    invalidate_analytics_cache,
    invalidate_dashboard_cache,
    logger,
)
from app.services.authors import list_authors, resolve_author_id


from app.routes.admin.posts.revisions import _save_revision  # noqa: E402
from app.context_processors import invalidate_footer_cache  # noqa: E402
from app.utils import utc_now, safe_delete_file  # noqa: E402
from app.tag_cache import invalidate_tag_cache  # noqa: E402
from app.search import sync_fts  # noqa: E402
from app.routes.rss import invalidate_rss_cache  # noqa: E402
from app.routes.public import invalidate_archive_cache  # noqa: E402
from sqlalchemy.exc import IntegrityError, OperationalError  # noqa: E402


def _create_post_object(
    *,
    title: str,
    body: str,
    summary: str,
    published: bool,
    image: str | None,
    now: datetime,
    scheduled_publish_at: datetime | None,
    tag_names: list[str],
    author_id: int | None = None,
) -> Post:
    """Create a Post instance with all fields set."""
    post = Post(
        title=title,
        slug=_generate_unique_slug(Post, title),
        body=body,
        summary=summary,
        published=published,
        image=image,
        published_at=now if published else None,
        scheduled_publish_at=scheduled_publish_at,
        author_id=author_id,
    )
    setattr(post, "tags", _get_or_create_tags(tag_names))
    return post


def _author_options() -> list[Any]:
    """Users that may be selected as the author of a post.

    An admin may pick any author; a non-admin signed-in user only sees
    themselves.
    """
    if current_user.is_authenticated and not current_user.is_admin:
        return [current_user]
    return list_authors()


def _render_editor(post: Post | None, tag_names: list[str]) -> Any:
    """Render the post editor with the available author options."""
    return render_template(
        "admin/editor.html",
        post=post,
        tag_names=tag_names,
        author_options=_author_options(),
    )


def _apply_cache_and_fts_updates(post: Post, searchable_changed: bool) -> bool:
    """Apply cache invalidation and FTS sync for a post."""
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
    return fts_ok


def _commit_post_with_rollback(
    *,
    post: Post,
    image: str | None,
    title: str,
    body: str,
    summary: str,
    published: bool,
    now: datetime,
    scheduled_publish_at: datetime | None,
    tag_names: list[str],
) -> tuple[str, bool]:
    """Attempt to commit a post, handling IntegrityError by regenerating slug and retrying."""
    try:
        db.session.flush()
        if not sync_fts(post.id, post.title, post.body, post.summary, post.published):
            db.session.rollback()
            raise Exception(f"FTS sync failed for post {post.id}")
        db.session.commit()
        return post.slug, True
    except IntegrityError as e:
        db.session.rollback()
        if "slug" not in str(e).lower():
            raise
        if image:
            safe_delete_file(os.path.join(current_app.config["UPLOAD_FOLDER"], image))
        post.slug = _generate_unique_slug(Post, title)
        db.session.add(post)
        db.session.flush()
        if not sync_fts(post.id, post.title, post.body, post.summary, post.published):
            db.session.rollback()
            raise Exception(f"FTS sync failed for post {post.id}")
        db.session.commit()
        return post.slug, False


def register_editor_routes(admin):
    """Register editor routes on the admin Blueprint."""

    @admin.route("/new", methods=["GET", "POST"])
    @author_required
    def new_post() -> Any:
        """Create a new blog post.

        An administrator may publish or schedule the post. An author may
        only create their own draft; publishing is an administrator's
        decision.
        """
        is_admin = current_user.is_admin
        if request.method == "POST":
            title = request.form.get("title", "").strip()[:200]
            body = request.form.get("body", "").strip()
            summary = request.form.get("summary", "").strip()[:500]
            tag_names = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
            published = "published" in request.form and is_admin
            scheduled_str = request.form.get("scheduled_publish_at", "").strip()
            scheduled_publish_at = None
            if scheduled_str and is_admin:
                try:
                    scheduled_publish_at = datetime.fromisoformat(scheduled_str)
                    if scheduled_publish_at.tzinfo is None:
                        scheduled_publish_at = scheduled_publish_at.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    flash("Invalid schedule date format.", "error")
                    return _render_editor(None, tag_names)

            if not title or not body:
                flash("Title and body are required.", "error")
                return _render_editor(None, tag_names)

            try:
                author_id = resolve_author_id(
                    request.form.get("author_id", "").strip(), current_user
                )
            except ValueError as e:
                flash(str(e), "error")
                return _render_editor(None, tag_names)

            image_file = request.files.get("image")
            image, error = _save_image(image_file) if image_file else (None, None)
            if error:
                flash(error, "error")
                return _render_editor(None, tag_names)

            if image:
                from app.routes.admin.media import _invalidate_media_cache

                _invalidate_media_cache()

            now = utc_now()
            post = _create_post_object(
                title=title,
                body=body,
                summary=summary,
                published=published,
                image=image,
                now=now,
                scheduled_publish_at=scheduled_publish_at,
                tag_names=tag_names,
                author_id=author_id,
            )
            db.session.add(post)
            try:
                slug, _ = _commit_post_with_rollback(
                    post=post,
                    image=image,
                    title=title,
                    body=body,
                    summary=summary,
                    published=published,
                    now=now,
                    scheduled_publish_at=scheduled_publish_at,
                    tag_names=tag_names,
                )
            except (IntegrityError, OperationalError) as e:
                logger.warning("FTS sync failed during new post: %s", e)
                if image:
                    safe_delete_file(os.path.join(current_app.config["UPLOAD_FOLDER"], image))
                flash("Search index temporarily unavailable. Please try again.", "error")
                return _render_editor(None, tag_names)
            invalidate_tag_cache()
            invalidate_analytics_cache()
            invalidate_dashboard_cache()
            invalidate_footer_cache()
            flash("Post created.", "success")
            return redirect(url_for("admin.dashboard"))

        return _render_editor(None, [])

    @admin.route("/edit/<int:post_id>", methods=["GET", "POST"])
    @author_required
    def edit_post(post_id: int) -> Any:
        """Edit an existing blog post.

        An author may only open a post they are the author of.
        """
        post = db.session.get(Post, post_id)
        if post is None:
            abort(404)

        is_admin = current_user.is_admin
        if not is_admin and post.author_id != current_user.id:
            abort(403)

        if request.method == "POST":
            title = request.form.get("title", "").strip()[:200]
            body = request.form.get("body", "").strip()
            summary = request.form.get("summary", "").strip()[:500]
            tag_names = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
            published = "published" in request.form and is_admin
            scheduled_str = request.form.get("scheduled_publish_at", "").strip()
            scheduled_publish_at = None
            if scheduled_str and is_admin:
                try:
                    scheduled_publish_at = datetime.fromisoformat(scheduled_str)
                    if scheduled_publish_at.tzinfo is None:
                        scheduled_publish_at = scheduled_publish_at.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    flash("Invalid schedule date format.", "error")
                    return _render_editor(post, tag_names)

            if not title or not body:
                flash("Title and body are required.", "error")
                return _render_editor(post, tag_names)

            author_raw = request.form.get("author_id", "").strip()
            if author_raw:
                try:
                    post.author_id = resolve_author_id(author_raw, current_user)
                except ValueError as e:
                    flash(str(e), "error")
                    return _render_editor(post, tag_names)

            searchable_changed = (
                title != post.title
                or body != post.body
                or summary != post.summary
                or published != post.published
            )
            was_published = post.published
            if was_published:
                _save_revision(post, current_user.id)
            elif published:
                _save_revision(post, current_user.id)
            if title != post.title:
                post.slug = _generate_unique_slug(Post, title, exclude_id=post.id)
            _apply_post_updates(
                post,
                title,
                body,
                summary,
                published,
                was_published,
                scheduled_publish_at,
                tag_names,
            )

            image_file = request.files.get("image")
            image, error = _save_image(image_file) if image_file else (None, None)
            if error:
                flash(error, "error")
                return _render_editor(post, tag_names)
            old_image = None
            if image:
                from app.routes.admin.media import _invalidate_media_cache

                _invalidate_media_cache()
                old_image = post.image
                post.image = image
            elif "remove_image" in request.form:
                old_image = post.image
                post.image = None

            try:
                fts_ok = _apply_cache_and_fts_updates(post, searchable_changed)
                if not fts_ok:
                    db.session.rollback()
                    logger.warning("FTS sync failed for post %d during edit; rolling back", post.id)
                    flash("Search index temporarily unavailable. Please try again.", "error")
                    return _render_editor(post, tag_names)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                if image:
                    safe_delete_file(os.path.join(current_app.config["UPLOAD_FOLDER"], image))
                post = db.session.get(Post, post_id)
                if not post:
                    flash("Post not found.", "error")
                    return redirect(url_for("admin.posts_list"))
                post.slug = _generate_unique_slug(Post, title, exclude_id=post.id)
                _apply_post_updates(
                    post,
                    title,
                    body,
                    summary,
                    published,
                    was_published,
                    scheduled_publish_at,
                    tag_names,
                )
                _apply_cache_and_fts_updates(post, True)
                db.session.commit()
            if old_image:
                safe_delete_file(os.path.join(current_app.config["UPLOAD_FOLDER"], old_image))
            flash("Post updated.", "success")
            return redirect(url_for("admin.dashboard"))

        tag_names = [t.name for t in cast(list[Tag], post.tags)]
        return _render_editor(post, tag_names)

    @admin.route("/preview-markdown", methods=["POST"])
    @author_required
    def preview_markdown() -> Any:
        """Render markdown preview for live editing."""
        if request.content_length and request.content_length > 1024 * 1024:
            return jsonify({"error": "payload too large"}), 413
        data = request.get_json(silent=True)
        if not data or "text" not in data:
            return jsonify({"error": "invalid"}), 400

        clean = render_markdown(data["text"], extensions=("fenced_code", "tables"))
        return jsonify({"html": clean})
