import os

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
from flask_login import login_required

from app.extensions import db
from app.models import Post, PageView, ShareEvent, Subscriber
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import (
    _get_posts_query,
    _generate_unique_slug,
    _save_image,
    _apply_post_updates,
    _cleanup_orphan_tags,
    _get_or_create_tags,
    invalidate_analytics_cache,
    invalidate_dashboard_cache,
    logger,
)
from app.context_processors import invalidate_footer_cache
from app.routes.admin.helpers.dashboard import _get_dashboard_metrics
from app.config import DASHBOARD_PER_PAGE
from app.utils import utc_now, safe_delete_file
from app.cache import invalidate_tag_cache
from app.search import sync_fts, sync_fts_batch, remove_fts
from app.config import BASE_URL
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError, OperationalError
from datetime import datetime, timedelta, timezone


@admin.route("/")
@admin_required
def dashboard():
    """
    Admin dashboard - lists all posts with pagination and search.

    Methods: GET
    GET: Renders the dashboard with posts, view/share counts, and metrics.
    Query params:
        page: Page number (default 1)
        q: Search query for filtering by title
        status: Filter by publication status (published, draft, all)
    Requires: Admin authentication.
    """
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "all")

    base_q = _get_posts_query(status, q)

    pagination = db.paginate(
        base_q, page=page, per_page=DASHBOARD_PER_PAGE, error_out=False
    )
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
        new_this_month=metrics["new_this_month"],
        views_trend=metrics["views_trend"],
        q=q,
        status=status,
    )


def _create_post_object(
    *, title, body, summary, published, image, now, scheduled_publish_at, tag_names
):
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
    )
    post.tags = _get_or_create_tags(tag_names)
    return post


def _apply_cache_and_fts_updates(post, searchable_changed):
    """Apply cache invalidation and FTS sync for a post.

    Returns True if FTS sync succeeded (or wasn't needed), False if it failed.
    Caller should check return value and handle failure appropriately.
    """
    fts_ok = True
    if searchable_changed:
        fts_ok = sync_fts(post.id, post.title, post.body, post.summary, post.published)
    invalidate_tag_cache()
    invalidate_analytics_cache()
    invalidate_dashboard_cache()
    invalidate_footer_cache()
    _cleanup_orphan_tags()
    return fts_ok


def _commit_post_with_rollback(
    *,
    post,
    image,
    title,
    body,
    summary,
    published,
    now,
    scheduled_publish_at,
    tag_names,
):
    """Attempt to commit a post, handling IntegrityError by regenerating slug and retrying.

    Returns (slug, fts_ok) tuple where fts_ok indicates FTS sync succeeded.
    Raises exception if FTS sync fails to maintain DB/FTS consistency.
    """
    try:
        db.session.flush()
        if not sync_fts(post.id, post.title, post.body, post.summary, post.published):
            db.session.rollback()
            raise Exception("FTS sync failed for post %d" % post.id)
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
            raise Exception("FTS sync failed for post %d" % post.id)
        db.session.commit()
        return post.slug, False


@admin.route("/new", methods=["GET", "POST"])
@admin_required
def new_post():
    """
    Create a new blog post.

    Methods: GET, POST
    GET: Renders the post editor form.
    POST: Creates a new post with title, body, summary, tags, image, and publication status.
          Supports optional scheduled_publish_at for auto-publishing.
    Requires: Admin authentication.
    Form params: title, body, summary, tags, published, scheduled_publish_at, image (file)
    """
    if request.method == "POST":
        title = request.form.get("title", "").strip()[:200]
        body = request.form.get("body", "").strip()
        summary = request.form.get("summary", "").strip()[:500]
        tag_names = [
            t.strip() for t in request.form.get("tags", "").split(",") if t.strip()
        ]
        published = "published" in request.form
        scheduled_str = request.form.get("scheduled_publish_at", "").strip()
        scheduled_publish_at = None
        if scheduled_str:
            try:
                scheduled_publish_at = datetime.fromisoformat(scheduled_str)
                if scheduled_publish_at.tzinfo is None:
                    scheduled_publish_at = scheduled_publish_at.replace(
                        tzinfo=timezone.utc
                    )
            except (ValueError, TypeError):
                flash("Invalid schedule date format.", "error")
                return render_template(
                    "admin/editor.html", post=None, tag_names=tag_names
                )

        if not title or not body:
            flash("Title and body are required.", "error")
            return render_template("admin/editor.html", post=None, tag_names=tag_names)

        image, error = _save_image(request.files.get("image"))
        if error:
            flash(error, "error")
            return render_template("admin/editor.html", post=None, tag_names=tag_names)

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
        except Exception as e:
            logger.warning("FTS sync failed during new post: %s", e)
            if image:
                safe_delete_file(os.path.join(current_app.config["UPLOAD_FOLDER"], image))
            flash("Search index temporarily unavailable. Please try again.", "error")
            return render_template("admin/editor.html", post=None, tag_names=tag_names)
        invalidate_tag_cache()
        invalidate_analytics_cache()
        invalidate_dashboard_cache()
        invalidate_footer_cache()
        flash("Post created.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/editor.html", post=None, tag_names=[])


@admin.route("/edit/<int:post_id>", methods=["GET", "POST"])
@admin_required
def edit_post(post_id):
    """
    Edit an existing blog post.

    Methods: GET, POST
    GET: Renders the post editor form pre-filled with post data.
    POST: Updates the post with new title, body, summary, tags, image, and publication status.
          Regenerates slug if title changed. Handles image replacement/removal.
    Requires: Admin authentication.
    Path params: post_id (int) - ID of the post to edit.
    Form params: title, body, summary, tags, published, scheduled_publish_at, image (file), remove_image
    """
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)

    if request.method == "POST":
        title = request.form.get("title", "").strip()[:200]
        body = request.form.get("body", "").strip()
        summary = request.form.get("summary", "").strip()[:500]
        tag_names = [
            t.strip() for t in request.form.get("tags", "").split(",") if t.strip()
        ]
        published = "published" in request.form
        scheduled_str = request.form.get("scheduled_publish_at", "").strip()
        scheduled_publish_at = None
        if scheduled_str:
            try:
                scheduled_publish_at = datetime.fromisoformat(scheduled_str)
                if scheduled_publish_at.tzinfo is None:
                    scheduled_publish_at = scheduled_publish_at.replace(
                        tzinfo=timezone.utc
                    )
            except (ValueError, TypeError):
                flash("Invalid schedule date format.", "error")
                return render_template(
                    "admin/editor.html", post=post, tag_names=tag_names
                )

        if not title or not body:
            flash("Title and body are required.", "error")
            return render_template("admin/editor.html", post=post, tag_names=tag_names)

        searchable_changed = (
            title != post.title
            or body != post.body
            or summary != post.summary
            or published != post.published
        )
        was_published = post.published
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

        image, error = _save_image(request.files.get("image"))
        if error:
            flash(error, "error")
            return render_template("admin/editor.html", post=post, tag_names=tag_names)
        old_image = None
        if image:
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
                return render_template("admin/editor.html", post=post, tag_names=tag_names)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            if image:
                safe_delete_file(
                    os.path.join(current_app.config["UPLOAD_FOLDER"], image)
                )
            post = db.session.get(Post, post_id)
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
            safe_delete_file(
                os.path.join(current_app.config["UPLOAD_FOLDER"], old_image)
            )
        flash("Post updated.", "success")
        return redirect(url_for("admin.dashboard"))

    tag_names = [t.name for t in post.tags]
    return render_template("admin/editor.html", post=post, tag_names=tag_names)


@admin.route("/delete/<int:post_id>", methods=["POST"])
@admin_required
def delete_post(post_id):
    """
    Delete a blog post.

    Methods: POST
    POST: Deletes the post, associated image file, FTS index entry, and orphan tags.
    Requires: Admin authentication.
    Path params: post_id (int) - ID of the post to delete.
    """
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)
    old_image = post.image
    post_id_for_fts = post.id
    post_title = post.title
    db.session.delete(post)
    invalidate_tag_cache()
    invalidate_analytics_cache()
    invalidate_footer_cache()
    _cleanup_orphan_tags()
    db.session.commit()
    remove_fts(post_id_for_fts)
    if old_image:
        safe_delete_file(os.path.join(current_app.config["UPLOAD_FOLDER"], old_image))
    logger.info("Post deleted: id=%d title=%s", post_id, post_title)
    flash("Post deleted.", "success")
    return redirect(url_for("admin.dashboard"))


@admin.route("/preview/<int:post_id>")
@admin_required
def preview_post(post_id):
    """
    Preview a post before publishing.

    Methods: GET
    GET: Renders the post in preview mode with banner, even if unpublished.
    Requires: Admin authentication.
    Path params: post_id (int) - ID of the post to preview.
    """
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)

    short_code = post.short_code()
    share_url = f"{BASE_URL}/s/{short_code}"
    return render_template(
        "admin/preview.html",
        post=post,
        related=[],
        share_url=share_url,
        short_code=short_code,
        preview_mode=True,
    )


@admin.route("/bulk", methods=["POST"])
@admin_required
def bulk_operations():
    """
    Bulk operations on selected posts.

    Methods: POST
    POST: Performs action (publish, unpublish, delete) on selected posts.
    Requires: Admin authentication.
    Form params:
        action: One of 'publish', 'unpublish', 'delete'
        post_ids: List of post IDs to operate on
    """
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
        db.session.execute(select(Post).filter(Post.id.in_(valid_ids))).scalars().all()
    )
    if not posts:
        flash("No posts found.", "error")
        return redirect(url_for("admin.dashboard"))

    if action == "publish":
        now = utc_now()
        fts_items = []
        for post in posts:
            if not post.published:
                post.published = True
                post.published_at = now
            fts_items.append((post.id, post.title, post.body, post.summary, post.published))
        invalidate_tag_cache()
        invalidate_analytics_cache()
        invalidate_footer_cache()
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


@admin.route("/preview-markdown", methods=["POST"])
@admin_required
def preview_markdown():
    """
    Render markdown preview for live editing.

    Methods: POST
    POST: Takes JSON body with 'text' (markdown), returns sanitized HTML.
    Requires: Admin authentication.
    Request body (JSON): {"text": str} - Markdown text to render
    Response (JSON): {"html": str} - Rendered HTML
    """
    if request.content_length and request.content_length > 1024 * 1024:
        return jsonify({"error": "payload too large"}), 413
    data = request.get_json(silent=True)
    if not data or "text" not in data:
        return jsonify({"error": "invalid"}), 400
    import nh3
    import markdown as md
    from app.markdown_config import MARKDOWN_ALLOWED_TAGS, MARKDOWN_ALLOWED_ATTRIBUTES

    html = md.markdown(data["text"], extensions=["fenced_code", "tables"])
    clean = nh3.clean(
        html, tags=MARKDOWN_ALLOWED_TAGS, attributes=MARKDOWN_ALLOWED_ATTRIBUTES
    )
    return jsonify({"html": clean})
