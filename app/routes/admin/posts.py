import os
import time
import threading

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
    DASHBOARD_PER_PAGE,
    utc_now,
    safe_delete_file,
    invalidate_tag_cache,
    invalidate_analytics_cache,
    sync_fts,
    remove_fts,
    logger,
)
from app.config import BASE_URL
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError, OperationalError
from datetime import datetime, timedelta, timezone

_dashboard_metrics_cache = {}
_dashboard_metrics_cache_lock = threading.Lock()
_DASHBOARD_METRICS_CACHE_TTL = 120


def _get_dashboard_metrics():
    """Get dashboard metrics with 2-minute cache."""
    now = time.time()

    with _dashboard_metrics_cache_lock:
        cached = _dashboard_metrics_cache.get("metrics")
        if cached and (now - cached["timestamp"]) < _DASHBOARD_METRICS_CACHE_TTL:
            return cached["data"]

    thirty_days_ago = utc_now() - timedelta(days=30)
    month_start = utc_now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_views = db.session.execute(select(func.count(PageView.id))).scalar_one() or 0
    total_posts = (
        db.session.execute(
            select(func.count(Post.id)).filter(Post.published == True)
        ).scalar_one()
        or 0
    )
    total_shares = (
        db.session.execute(select(func.count(ShareEvent.id))).scalar_one() or 0
    )
    total_subscribers = (
        db.session.execute(
            select(func.count(Subscriber.id)).filter(Subscriber.confirmed == True)
        ).scalar_one()
        or 0
    )

    trending = db.session.execute(
        select(Post, func.count(PageView.id).label("view_count"))
        .join(PageView)
        .filter(Post.published == True)
        .filter(PageView.created_at >= thirty_days_ago)
        .group_by(Post.id)
        .order_by(func.count(PageView.id).desc())
        .limit(5)
    ).all()

    new_this_month = (
        db.session.execute(
            select(func.count(Subscriber.id)).filter(
                Subscriber.created_at >= month_start
            )
        ).scalar_one()
        or 0
    )

    views_trend = None
    views_this_period = total_views
    sixty_days_ago = utc_now() - timedelta(days=60)
    views_last_period = (
        db.session.execute(
            select(func.count(PageView.id)).filter(
                PageView.created_at >= sixty_days_ago,
                PageView.created_at < thirty_days_ago,
            )
        ).scalar_one()
        or 0
    )
    if views_last_period > 0:
        change = ((views_this_period - views_last_period) / views_last_period) * 100
        views_trend = round(change, 1)
    elif views_this_period > 0:
        views_trend = 100.0

    data = {
        "total_views": total_views,
        "total_posts": total_posts,
        "total_shares": total_shares,
        "total_subscribers": total_subscribers,
        "trending": trending,
        "new_this_month": new_this_month,
        "views_trend": views_trend,
    }

    with _dashboard_metrics_cache_lock:
        _dashboard_metrics_cache["metrics"] = {"timestamp": now, "data": data}

    return data


def _invalidate_dashboard_cache():
    """Clear the dashboard metrics cache."""
    with _dashboard_metrics_cache_lock:
        _dashboard_metrics_cache.clear()


def invalidate_dashboard_cache():
    """Public function to invalidate dashboard metrics cache."""
    _invalidate_dashboard_cache()


@admin.route("/")
@admin_required
def dashboard():
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
        slug=_generate_unique_slug(title),
        body=body,
        summary=summary,
        published=published,
        image=image,
        published_at=now if published else None,
        scheduled_publish_at=scheduled_publish_at,
    )
    post.tags = _get_or_create_tags(tag_names)
    return post


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
    """Attempt to commit a post, handling IntegrityError by regenerating slug and retrying."""
    try:
        db.session.flush()
        sync_fts(post.id, post.title, post.body, post.summary, post.published)
        db.session.commit()
        return True
    except IntegrityError as e:
        db.session.rollback()
        if "slug" not in str(e).lower():
            raise
        if image:
            safe_delete_file(os.path.join(current_app.config["UPLOAD_FOLDER"], image))
        new_post = _create_post_object(
            title=title,
            body=body,
            summary=summary,
            published=published,
            image=image,
            now=now,
            scheduled_publish_at=scheduled_publish_at,
            tag_names=tag_names,
        )
        db.session.add(new_post)
        db.session.flush()
        sync_fts(
            new_post.id,
            new_post.title,
            new_post.body,
            new_post.summary,
            new_post.published,
        )
        db.session.commit()
        return False


@admin.route("/new", methods=["GET", "POST"])
@admin_required
def new_post():
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
        _commit_post_with_rollback(
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
        flash("Post created.", "success")
        invalidate_tag_cache()
        invalidate_analytics_cache()
        invalidate_dashboard_cache()
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/editor.html", post=None, tag_names=[])


@admin.route("/edit/<int:post_id>", methods=["GET", "POST"])
@admin_required
def edit_post(post_id):
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
            post.slug = _generate_unique_slug(title, exclude_id=post.id)
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
            if searchable_changed:
                sync_fts(post.id, post.title, post.body, post.summary, post.published)
            invalidate_tag_cache()
            invalidate_analytics_cache()
            invalidate_dashboard_cache()
            _cleanup_orphan_tags()
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            if image:
                safe_delete_file(
                    os.path.join(current_app.config["UPLOAD_FOLDER"], image)
                )
            post = db.session.get(Post, post_id)
            post.slug = _generate_unique_slug(title, exclude_id=post.id)
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
            sync_fts(post.id, post.title, post.body, post.summary, post.published)
            invalidate_tag_cache()
            invalidate_analytics_cache()
            invalidate_dashboard_cache()
            _cleanup_orphan_tags()
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
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)
    old_image = post.image
    post_id_for_fts = post.id
    post_title = post.title
    db.session.delete(post)
    invalidate_tag_cache()
    invalidate_analytics_cache()
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
        for post in posts:
            if not post.published:
                post.published = True
                post.published_at = now
        for post in posts:
            sync_fts(post.id, post.title, post.body, post.summary, post.published)
        invalidate_tag_cache()
        invalidate_analytics_cache()
        try:
            db.session.commit()
        except (IntegrityError, OperationalError):
            db.session.rollback()
            flash("Database error occurred. Please try again.", "error")
            return redirect(url_for("admin.dashboard"))
        flash(f"Published {len(posts)} post(s).", "success")
    elif action == "unpublish":
        for post in posts:
            post.published = False
        for post in posts:
            sync_fts(post.id, post.title, post.body, post.summary, post.published)
        invalidate_tag_cache()
        invalidate_analytics_cache()
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
