import csv
import io
import os
import re
import secrets
import uuid
import time
import threading
import logging

from functools import wraps

from flask import (
    Blueprint,
    abort,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    current_app,
    jsonify,
    Response,
    send_file,
    session,
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import delete, func, select
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError, OperationalError

from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import Post, Tag, User, PageView, ShareEvent, Subscriber, AdminSession

from app.utils import utc_now, safe_delete_file
from app.config import (
    DASHBOARD_PER_PAGE,
    SUBSCRIBERS_PER_PAGE,
    MEDIA_PER_PAGE,
    MEDIA_MAX_FILES,
)
from app.cache import invalidate_tag_cache
from app.search import sync_fts, remove_fts

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
TAG_NAME_REGEX = re.compile(r"^[\w\s-]+$")
BACKUP_FILENAME_RE = re.compile(r"^blog_\d{8}_\d{6}\.db(\.gz)?$")

logger = logging.getLogger(__name__)

_analytics_cache = {}
_analytics_cache_lock = threading.Lock()
_ANALYTICS_CACHE_TTL = 300


def _categorize_referrer(url):
    if not url:
        return "Direct"
    url_lower = url.lower()
    if (
        "google" in url_lower
        or "bing" in url_lower
        or "yahoo" in url_lower
        or "duckduckgo" in url_lower
    ):
        return "Search"
    if (
        "twitter" in url_lower
        or "facebook" in url_lower
        or "linkedin" in url_lower
        or "reddit" in url_lower
    ):
        return "Social"
    return "Other"


def _check_password_complexity(password: str) -> bool:
    """Check password has at least 3 of 4: lowercase, uppercase, digit, special."""
    if len(password) < 8:
        return False
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    return sum([has_lower, has_upper, has_digit, has_special]) >= 3


def _get_posts_query(status: str, search: str, order_by=None):
    """Common post query builder with joinedload and optional filtering."""
    base_q = select(Post).options(joinedload(Post.tags))
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search_term = f"%{escaped}%"
        base_q = base_q.filter(Post.title.ilike(search_term, escape="\\"))
    if status == "published":
        base_q = base_q.filter(Post.published == True)
    elif status == "draft":
        base_q = base_q.filter(Post.published == False)
    if order_by is None:
        order_by = Post.updated_at.desc()
    return base_q.order_by(order_by)


def _get_analytics_data(days: int):
    """Get analytics data with simple in-memory caching."""
    cache_key = days
    now = time.time()

    with _analytics_cache_lock:
        cached = _analytics_cache.get(cache_key)
        if cached and (now - cached["timestamp"]) < _ANALYTICS_CACHE_TTL:
            return cached["data"]

    start_date = utc_now() - timedelta(days=days)

    daily_views = db.session.execute(
        select(
            func.date(PageView.created_at).label("date"),
            func.count(PageView.id).label("views"),
        )
        .filter(PageView.created_at >= start_date)
        .group_by(func.date(PageView.created_at))
        .order_by(func.date(PageView.created_at))
    ).all()

    total_views = (
        db.session.execute(
            select(func.count(PageView.id)).filter(PageView.created_at >= start_date)
        ).scalar_one()
        or 0
    )

    top_posts = db.session.execute(
        select(Post, func.count(PageView.id).label("view_count"))
        .join(PageView)
        .filter(Post.published == True)
        .filter(PageView.created_at >= start_date)
        .group_by(Post.id)
        .order_by(func.count(PageView.id).desc())
        .limit(10)
    ).all()

    top_post_ids = [p.id for p, _ in top_posts]
    share_counts_analytics = dict(
        db.session.execute(
            select(ShareEvent.post_id, func.count(ShareEvent.id))
            .filter(ShareEvent.post_id.in_(top_post_ids))
            .group_by(ShareEvent.post_id)
        ).all()
    )

    share_platforms = db.session.execute(
        select(ShareEvent.platform, func.count(ShareEvent.id).label("count")).group_by(
            ShareEvent.platform
        )
    ).all()

    referrer_data = db.session.execute(
        select(PageView.referrer, func.count(PageView.id).label("count"))
        .filter(PageView.referrer != None, PageView.created_at >= start_date)
        .group_by(PageView.referrer)
        .order_by(func.count(PageView.id).desc())
        .limit(15)
    ).all()

    referrer_summary = {}
    for url, count in referrer_data:
        category = _categorize_referrer(url)
        referrer_summary[category] = referrer_summary.get(category, 0) + count

    total_subscribers = (
        db.session.execute(select(func.count(Subscriber.id))).scalar_one() or 0
    )
    confirmed_subscribers = (
        db.session.execute(
            select(func.count(Subscriber.id)).filter(Subscriber.confirmed == True)
        ).scalar_one()
        or 0
    )

    data = {
        "daily_views": daily_views,
        "total_views": total_views,
        "top_posts": top_posts,
        "share_platforms": share_platforms,
        "share_counts_analytics": share_counts_analytics,
        "referrer_summary": referrer_summary,
        "total_subscribers": total_subscribers,
        "confirmed_subscribers": confirmed_subscribers,
    }

    with _analytics_cache_lock:
        _analytics_cache[cache_key] = {"timestamp": now, "data": data}

    return data


def validate_tag_name(name: str) -> tuple[bool, str]:
    """Validate tag name against allowed pattern. Returns (is_valid, error_message)."""
    if not name or not TAG_NAME_REGEX.match(name):
        return False, "Invalid tag name."
    return True, ""


def _detect_image_type(header):
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if header[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if header[:3] == b"GIF" and header[3:6] in (b"87a", b"89a"):
        return "gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


admin = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _generate_unique_slug(title, exclude_id=None):
    """Generate a unique slug for a post, appending a counter if needed."""
    slug = Post.generate_slug(title)
    base_slug = slug
    counter = 2
    while True:
        q = select(Post).filter(Post.slug == slug)
        if exclude_id is not None:
            q = q.filter(Post.id != exclude_id)
        if not db.session.execute(q).scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def _save_image(file):
    if file and file.filename and _allowed_file(file.filename):
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        if size > 10 * 1024 * 1024:
            return None, "File too large. Maximum size is 10MB."
        header = file.read(32)
        file.seek(0)
        detected = _detect_image_type(header)
        if detected not in ("png", "jpeg", "gif", "webp"):
            return None, "Uploaded file is not a valid image."
        ext = detected
        filename = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
        return filename, None
    return None, None


@admin.route("/login", methods=["GET", "POST"])
def login() -> Response:
    """Admin login page. POST authenticates admin users only."""
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = db.session.execute(
            select(User).filter_by(username=username)
        ).scalar_one_or_none()
        if user and user.check_password(password) and user.is_admin:
            login_user(user)
            # Track admin session
            sid = secrets.token_hex(32)
            admin_session = AdminSession(
                user_id=user.id,
                session_id=sid,
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent", "")[:256],
            )
            db.session.add(admin_session)
            db.session.commit()
            session["admin_session_id"] = sid
            return redirect(url_for("admin.dashboard"))
        flash("Invalid credentials.", "error")

    return render_template("admin/login.html")


@admin.route("/newsletter-reset/<int:post_id>", methods=["POST"])
@admin_required
def newsletter_reset(post_id) -> Response:
    """Reset newsletter sent flag for a post.

    Path params:
        post_id: Post ID

    Response:
        Redirects to dashboard with flash message.
        Sets newsletter_sent_at to None and newsletter_attempts to 0.
    """
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)
    post.newsletter_sent_at = None
    post.newsletter_attempts = 0
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.dashboard"))
    flash(
        f"Newsletter flag reset for '{post.title}'. It will be included in the next newsletter.",
        "success",
    )
    return redirect(url_for("admin.dashboard"))


@admin.route("/logout", methods=["POST"])
@login_required
def logout() -> Response:
    """Log out the current user and redirect to homepage."""
    # Remove admin session tracking
    sid = session.pop("admin_session_id", None)
    if sid:
        admin_session = db.session.execute(
            select(AdminSession).filter_by(session_id=sid)
        ).scalar_one_or_none()
        if admin_session:
            db.session.delete(admin_session)
            try:
                db.session.commit()
            except (IntegrityError, OperationalError):
                db.session.rollback()
    logout_user()
    return redirect(url_for("public.index"))


@admin.route("/")
@admin_required
def dashboard() -> Response:
    """Admin dashboard with post list, search, filter, and site stats."""
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

    thirty_days_ago = utc_now() - timedelta(days=30)
    trending = db.session.execute(
        select(Post, func.count(PageView.id).label("view_count"))
        .join(PageView)
        .filter(Post.published == True)
        .filter(PageView.created_at >= thirty_days_ago)
        .group_by(Post.id)
        .order_by(func.count(PageView.id).desc())
        .limit(5)
    ).all()

    month_start = utc_now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_this_month = (
        db.session.execute(
            select(func.count(Subscriber.id)).filter(
                Subscriber.created_at >= month_start
            )
        ).scalar_one()
        or 0
    )

    return render_template(
        "admin/dashboard.html",
        posts=posts,
        pagination=pagination,
        view_counts=view_counts,
        share_counts=share_counts,
        total_views=total_views,
        total_posts=total_posts,
        total_shares=total_shares,
        total_subscribers=total_subscribers,
        trending=trending,
        new_this_month=new_this_month,
        q=q,
        status=status,
    )


@admin.route("/new", methods=["GET", "POST"])
@admin_required
def new_post() -> Response:
    """Create a new post. GET shows editor, POST saves the post."""
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

        slug = _generate_unique_slug(title)
        image, error = _save_image(request.files.get("image"))
        if error:
            flash(error, "error")
            return render_template("admin/editor.html", post=None, tag_names=tag_names)

        now = utc_now()
        post = Post(
            title=title,
            slug=slug,
            body=body,
            summary=summary,
            published=published,
            image=image,
            published_at=now if published else None,
            scheduled_publish_at=scheduled_publish_at,
        )
        post.tags = _get_or_create_tags(tag_names)
        db.session.add(post)
        try:
            db.session.flush()
            sync_fts(post.id, post.title, post.body, post.summary, post.published)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            if image:
                safe_delete_file(
                    os.path.join(current_app.config["UPLOAD_FOLDER"], image)
                )
            slug = _generate_unique_slug(title)
            post = Post(
                title=title,
                slug=slug,
                body=body,
                summary=summary,
                published=published,
                image=image,
                published_at=now if published else None,
                scheduled_publish_at=scheduled_publish_at,
            )
            post.tags = _get_or_create_tags(tag_names)
            db.session.add(post)
            db.session.flush()
            sync_fts(post.id, post.title, post.body, post.summary, post.published)
            db.session.commit()
        flash("Post created.", "success")
        invalidate_tag_cache()
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/editor.html", post=None, tag_names=[])


@admin.route("/edit/<int:post_id>", methods=["GET", "POST"])
@admin_required
def edit_post(post_id) -> Response:
    """Edit an existing post. GET shows editor with current data, POST saves changes."""
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
        if title != post.title:
            post.slug = _generate_unique_slug(title, exclude_id=post.id)
        post.title = title
        post.body = body
        post.summary = summary
        was_published = post.published
        post.published = published
        post.scheduled_publish_at = scheduled_publish_at
        if published and not was_published:
            post.published_at = utc_now()
        post.tags = _get_or_create_tags(tag_names)

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
            post.title = title
            post.body = body
            post.summary = summary
            post.published = published
            post.scheduled_publish_at = scheduled_publish_at
            if published and not was_published:
                post.published_at = utc_now()
            post.tags = _get_or_create_tags(tag_names)
            sync_fts(post.id, post.title, post.body, post.summary, post.published)
            invalidate_tag_cache()
            _cleanup_orphan_tags()
            db.session.commit()
        # Delete old image file only after successful commit
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
def delete_post(post_id) -> Response:
    """Delete a post and its image file. Cleans up FTS index and orphan tags."""
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)
    old_image = post.image
    post_id_for_fts = post.id
    post_title = post.title
    db.session.delete(post)
    invalidate_tag_cache()
    _cleanup_orphan_tags()
    db.session.commit()
    remove_fts(post_id_for_fts)
    if old_image:
        safe_delete_file(os.path.join(current_app.config["UPLOAD_FOLDER"], old_image))
    logger.info("Post deleted: id=%d title=%s", post_id, post_title)
    flash("Post deleted.", "success")
    return redirect(url_for("admin.dashboard"))


def _cleanup_orphan_tags():
    """Remove tags that have no associated posts. Callers are responsible for committing."""
    from app.models import post_tags

    orphan_tag_ids = (
        db.session.execute(
            select(Tag.id)
            .outerjoin(post_tags, Tag.id == post_tags.c.tag_id)
            .filter(post_tags.c.post_id.is_(None))
        )
        .scalars()
        .all()
    )
    if orphan_tag_ids:
        db.session.execute(delete(Tag).where(Tag.id.in_(orphan_tag_ids)))


def _get_or_create_tags(names):
    tags = []
    invalid_tags = []
    for name in names:
        name = name.strip()[:50]
        if not name:
            continue
        is_valid, _ = validate_tag_name(name)
        if not is_valid:
            invalid_tags.append(name)
            continue
        slug = Tag.generate_slug(name)
        tag = db.session.execute(select(Tag).filter_by(slug=slug)).scalar_one_or_none()
        if not tag:
            tag = Tag(name=name, slug=slug)
            db.session.add(tag)
        tags.append(tag)
    if invalid_tags:
        flash(f"Invalid tag names (skipped): {', '.join(invalid_tags)}", "warning")
    return tags


@admin.route("/analytics")
@admin_required
def analytics() -> Response:
    """Analytics dashboard with views, top posts, referrers, and subscriber stats."""
    days = request.args.get("days", 30, type=int)
    days = min(max(days, 7), 365)

    data = _get_analytics_data(days)

    return render_template(
        "admin/analytics.html",
        days=days,
        daily_views=data["daily_views"],
        total_views=data["total_views"],
        top_posts=data["top_posts"],
        share_platforms=data["share_platforms"],
        share_counts=data["share_counts_analytics"],
        referrer_summary=data["referrer_summary"],
        total_subscribers=data["total_subscribers"],
        confirmed_subscribers=data["confirmed_subscribers"],
    )


@admin.route("/preview/<int:post_id>")
@admin_required
def preview_post(post_id) -> Response:
    """Preview a post (draft or published) with a yellow preview banner."""
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)
    from app.config import BASE_URL

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


@admin.route("/subscribers")
@admin_required
def subscribers() -> Response:
    """Subscriber list with status filter and pagination."""
    page = request.args.get("page", 1, type=int)
    filter_status = request.args.get("status", "all")

    base_q = select(Subscriber)
    if filter_status == "confirmed":
        base_q = base_q.filter(Subscriber.confirmed == True)
    elif filter_status == "unconfirmed":
        base_q = base_q.filter(Subscriber.confirmed == False)
    elif filter_status == "unsubscribed":
        base_q = base_q.filter(Subscriber.unsubscribed_at.isnot(None))

    pagination = db.paginate(
        base_q.order_by(Subscriber.created_at.desc()),
        page=page,
        per_page=SUBSCRIBERS_PER_PAGE,
        error_out=False,
    )
    return render_template(
        "admin/subscribers.html",
        subscribers=pagination.items,
        pagination=pagination,
        filter_status=filter_status,
    )


@admin.route("/subscribers/delete/<int:sub_id>", methods=["POST"])
@admin_required
def delete_subscriber(sub_id) -> Response:
    """Delete a single subscriber by ID."""
    sub = db.session.get(Subscriber, sub_id)
    if not sub:
        abort(404)
    email = sub.email
    db.session.delete(sub)
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.subscribers"))
    logger.info("Subscriber deleted: sub_id=%d email=%s", sub_id, email)
    flash(f"Subscriber {email} deleted.", "success")
    return redirect(url_for("admin.subscribers"))


@admin.route("/subscribers/export")
@admin_required
def export_subscribers() -> Response:
    """Stream CSV export of all subscribers."""

    def generate():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["email", "confirmed", "created_at", "expires_at"])
        yield buffer.getvalue()
        buffer.truncate(0)
        buffer.seek(0)

        offset = 0
        batch_size = 500
        while True:
            rows = (
                db.session.execute(
                    select(Subscriber)
                    .order_by(Subscriber.created_at.desc())
                    .offset(offset)
                    .limit(batch_size)
                )
                .scalars()
                .all()
            )
            if not rows:
                break
            for s in rows:
                writer.writerow(
                    [
                        (
                            s.email
                            if not s.email.startswith(("=", "+", "-", "@"))
                            else "'" + s.email
                        ),
                        s.confirmed,
                        s.created_at.isoformat() if s.created_at else "",
                        s.expires_at.isoformat() if s.expires_at else "",
                    ]
                )
                yield buffer.getvalue()
                buffer.truncate(0)
                buffer.seek(0)
            offset += batch_size

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=subscribers.csv"},
    )


@admin.route("/subscribers/bulk", methods=["POST"])
@admin_required
def subscribers_bulk() -> Response:
    """Bulk operations on selected subscribers.

    Form params:
        action: 'delete' or 'export'
        sub_ids: List of subscriber IDs

    Response:
        delete: Redirects with flash count.
        export: Streams CSV of selected subscribers.
    """
    action = request.form.get("action")
    sub_ids = request.form.getlist("sub_ids")
    filter_status = request.args.get("status", "all")

    if action in ("delete", "export"):
        if not sub_ids:
            flash("No subscribers selected.", "error")
            return redirect(url_for("admin.subscribers", status=filter_status))

        valid_ids = []
        for sid in sub_ids:
            try:
                valid_ids.append(int(sid))
            except (ValueError, TypeError):
                flash("Invalid subscriber ID.", "error")
                return redirect(url_for("admin.subscribers", status=filter_status))

        if action == "delete":
            subs = (
                db.session.execute(
                    select(Subscriber).filter(Subscriber.id.in_(valid_ids))
                )
                .scalars()
                .all()
            )
            count = len(subs)
            for sub in subs:
                db.session.delete(sub)
            db.session.commit()
            flash(f"Deleted {count} subscriber(s).", "success")
        elif action == "export":

            def generate():
                buffer = io.StringIO()
                writer = csv.writer(buffer)
                writer.writerow(["email", "confirmed", "created_at", "expires_at"])
                yield buffer.getvalue()
                buffer.truncate(0)
                buffer.seek(0)

                subs = (
                    db.session.execute(
                        select(Subscriber)
                        .filter(Subscriber.id.in_(valid_ids))
                        .order_by(Subscriber.created_at.desc())
                    )
                    .scalars()
                    .all()
                )
                for s in subs:
                    writer.writerow(
                        [
                            (
                                s.email
                                if not s.email.startswith(("=", "+", "-", "@"))
                                else "'" + s.email
                            ),
                            s.confirmed,
                            s.created_at.isoformat() if s.created_at else "",
                            s.expires_at.isoformat() if s.expires_at else "",
                        ]
                    )
                    yield buffer.getvalue()
                    buffer.truncate(0)
                    buffer.seek(0)

            return Response(
                generate(),
                mimetype="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=subscribers_selected.csv"
                },
            )

    return redirect(url_for("admin.subscribers", status=filter_status))


@admin.route("/preview-markdown", methods=["POST"])
@admin_required
def preview_markdown() -> Response:
    """Render markdown for live preview.

    Request body (JSON):
        {"text": str}

    Response:
        200: {"html": str} - sanitized HTML
        400: {"error": "invalid"}
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


@admin.route("/media")
@admin_required
def media() -> Response:
    """Uploaded media file browser with pagination."""
    page = request.args.get("page", 1, type=int)
    per_page = MEDIA_PER_PAGE
    max_files = MEDIA_MAX_FILES
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    all_files = []
    with os.scandir(upload_dir) as entries:
        for entry in entries:
            if not entry.is_file():
                continue
            stat = entry.stat()
            all_files.append(
                {
                    "name": entry.name,
                    "size": stat.st_size,
                    "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                }
            )
        all_files.sort(key=lambda f: f["mtime"], reverse=True)
    if len(all_files) > max_files:
        all_files = all_files[:max_files]
    truncated = len(all_files) >= max_files
    total = len(all_files)
    start = (page - 1) * per_page
    end = start + per_page
    files = all_files[start:end]
    total_pages = (total + per_page - 1) // per_page
    return render_template(
        "admin/media.html",
        files=files,
        page=page,
        total_pages=total_pages,
        truncated=truncated,
    )


@admin.route("/media/upload", methods=["POST"])
@admin_required
def upload_media() -> Response:
    """Handle media file uploads via drag-and-drop or form."""
    if "file" not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for("admin.media"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("admin.media"))

    filename, error = _save_image(file)
    if error:
        flash(error, "error")
    else:
        flash(f"Uploaded {filename}.", "success")

    return redirect(url_for("admin.media"))


@admin.route("/media/delete/<filename>", methods=["POST"])
@admin_required
def delete_media(filename) -> Response:
    """Delete an uploaded media file after path traversal validation."""
    filename = secure_filename(filename)
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    real_path = os.path.realpath(filepath)
    upload_dir = os.path.realpath(current_app.config["UPLOAD_FOLDER"])
    if not real_path.startswith(upload_dir + os.sep):
        abort(400)
    if not os.path.exists(real_path):
        abort(404)
    if not safe_delete_file(real_path):
        flash("Failed to delete file.", "error")
        return redirect(url_for("admin.media"))
    flash(f"Deleted {filename}.", "success")
    return redirect(url_for("admin.media"))


@admin.route("/tags")
@admin_required
def tags_list() -> Response:
    """Tag management page with post counts."""
    from app.models import post_tags

    tags = db.session.execute(select(Tag).order_by(Tag.name)).scalars().all()
    tag_post_counts = dict(
        db.session.execute(
            select(
                post_tags.c.tag_id, func.count(post_tags.c.post_id).label("cnt")
            ).group_by(post_tags.c.tag_id)
        ).all()
    )
    return render_template(
        "admin/tags.html", tags=tags, tag_post_counts=tag_post_counts
    )


@admin.route("/tags/rename/<int:tag_id>", methods=["POST"])
@admin_required
def rename_tag(tag_id) -> Response:
    """Rename a tag, validating uniqueness and name format."""
    tag = db.session.get(Tag, tag_id)
    if not tag:
        abort(404)
    new_name = request.form.get("name", "").strip()[:50]
    if not new_name:
        flash("Tag name cannot be empty.", "error")
        return redirect(url_for("admin.tags_list"))
    is_valid, error_msg = validate_tag_name(new_name)
    if not is_valid:
        flash(error_msg, "error")
        return redirect(url_for("admin.tags_list"))
    slug = Tag.generate_slug(new_name)
    existing = db.session.execute(
        select(Tag).filter(Tag.slug == slug, Tag.id != tag.id)
    ).scalar_one_or_none()
    if existing:
        flash(f"Tag '{new_name}' already exists.", "warning")
        return redirect(url_for("admin.tags_list"))
    old_name = tag.name
    tag.name = new_name
    tag.slug = slug
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.tags_list"))
    invalidate_tag_cache()
    logger.info(
        "Tag renamed: id=%d old_name=%s new_name=%s", tag_id, old_name, new_name
    )
    flash(f"Tag renamed to '{new_name}'.", "success")
    return redirect(url_for("admin.tags_list"))


@admin.route("/tags/delete/<int:tag_id>", methods=["POST"])
@admin_required
def delete_tag(tag_id) -> Response:
    """Delete a tag and invalidate the tag cache."""
    tag = db.session.get(Tag, tag_id)
    if not tag:
        abort(404)
    name = tag.name
    db.session.delete(tag)
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.tags_list"))
    invalidate_tag_cache()
    logger.info("Tag deleted: id=%d name=%s", tag_id, name)
    flash(f"Tag '{name}' deleted.", "success")
    return redirect(url_for("admin.tags_list"))


@admin.route("/tags/create", methods=["POST"])
@admin_required
def create_tag() -> Response:
    """Create a new tag with validated name."""
    name = request.form.get("name", "").strip()[:50]
    if not name:
        flash("Tag name cannot be empty.", "error")
        return redirect(url_for("admin.tags_list"))
    is_valid, error_msg = validate_tag_name(name)
    if not is_valid:
        flash(error_msg, "error")
        return redirect(url_for("admin.tags_list"))
    slug = Tag.generate_slug(name)
    existing = db.session.execute(select(Tag).filter_by(slug=slug)).scalar_one_or_none()
    if existing:
        flash(f"Tag '{name}' already exists.", "warning")
        return redirect(url_for("admin.tags_list"))
    tag = Tag(name=name, slug=slug)
    db.session.add(tag)
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.tags_list"))
    invalidate_tag_cache()
    logger.info("Tag created: id=%d name=%s", tag.id, name)
    flash(f"Tag '{name}' created.", "success")
    return redirect(url_for("admin.tags_list"))


@admin.route("/newsletter-test", methods=["POST"])
@admin_required
def newsletter_test() -> Response:
    """Send a test newsletter to a specified email address."""
    from app.email import send_newsletter
    from app.config import APP_TITLE, FROM_ADDRESS

    posts = (
        db.session.execute(
            select(Post)
            .filter_by(published=True)
            .order_by(Post.created_at.desc())
            .limit(3)
        )
        .scalars()
        .all()
    )
    if not posts:
        flash("No published posts to send.", "error")
        return redirect(url_for("admin.dashboard"))
    from app.models import User

    admin_user = db.session.execute(select(User)).scalars().first()
    if not admin_user:
        flash("No admin user found.", "error")
        return redirect(url_for("admin.dashboard"))
    test_email = request.form.get("test_email", "").strip()
    if not test_email:
        test_email = (
            FROM_ADDRESS.split("<")[-1].rstrip(">")
            if "<" in FROM_ADDRESS
            else FROM_ADDRESS
        )
    fake_sub = type(
        "FakeSub",
        (),
        {
            "email": test_email,
            "token": "test",
        },
    )()
    try:
        send_newsletter(posts, [fake_sub])
        flash(f"Test newsletter sent to {test_email}.", "success")
    except Exception as e:
        flash(f"Failed to send test newsletter: {e}", "error")
    return redirect(url_for("admin.dashboard"))


@admin.route("/bulk", methods=["POST"])
@admin_required
def bulk_operations() -> Response:
    """Bulk publish, unpublish, or delete posts.

    Form params:
        action: 'publish', 'unpublish', or 'delete'
        post_ids: List of post IDs

    Response:
        Redirects to dashboard with flash message.
        Removes image files on delete. Cleans up orphan tags.
    """
    action = request.form.get("action")
    post_ids = request.form.getlist("post_ids")
    if not post_ids:
        flash("No posts selected.", "error")
        return redirect(url_for("admin.dashboard"))

    # Validate all post_ids are integers
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


@admin.route("/users")
@admin_required
def users_list() -> Response:
    """User management page with pagination."""
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
def create_user() -> Response:
    """Create a new user with optional admin privileges."""
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
def delete_user(user_id) -> Response:
    """Delete a user. Prevents self-deletion and last admin removal."""
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
def change_password(user_id) -> Response:
    """Change a user's password (minimum 8 characters)."""
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


@admin.route("/sessions")
@admin_required
def sessions_list() -> Response:
    """View active admin sessions. Only admins can see all sessions."""
    sessions = (
        db.session.execute(
            select(AdminSession)
            .options(joinedload(AdminSession.user))
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
def revoke_session(sess_id) -> Response:
    """Revoke a specific admin session."""
    admin_session = db.session.get(AdminSession, sess_id)
    if not admin_session:
        abort(404)
    # Prevent revoking own current session
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


def _get_backup_dir():
    return os.path.join(current_app.instance_path, "backups")


@admin.route("/backup")
@admin_required
def backup() -> Response:
    """List all database backups with size and modification time."""
    backup_dir = _get_backup_dir()
    backups = []
    if os.path.isdir(backup_dir):
        for fname in sorted(os.listdir(backup_dir), reverse=True):
            if fname.startswith("blog_") and (
                fname.endswith(".db") or fname.endswith(".db.gz")
            ):
                fpath = os.path.join(backup_dir, fname)
                stat = os.stat(fpath)
                backups.append(
                    {
                        "name": fname,
                        "size": stat.st_size,
                        "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                    }
                )
    return render_template("admin/backup.html", backups=backups)


@admin.route("/backup/create", methods=["POST"])
@admin_required
def create_backup() -> Response:
    """Create a database backup, optionally gzip-compressed."""
    from backup import create_backup as _create_backup

    compress = "compress" in request.form
    db_path = os.path.join(current_app.instance_path, "blog.db")
    backup_dir = _get_backup_dir()
    result = _create_backup(db_path, backup_dir, compress=compress, keep=10)
    if result:
        flash("Backup created successfully.", "success")
    else:
        flash("Backup failed.", "error")
    return redirect(url_for("admin.backup"))


@admin.route("/backup/download/<filename>")
@admin_required
def download_backup(filename) -> Response:
    """Download a backup file after filename and path validation."""
    if not BACKUP_FILENAME_RE.match(filename):
        abort(400)
    backup_dir = _get_backup_dir()
    filepath = os.path.join(backup_dir, filename)
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(os.path.realpath(backup_dir) + os.sep):
        abort(400)
    if not os.path.exists(real_path):
        abort(404)
    return send_file(real_path, as_attachment=True, download_name=filename)


@admin.route("/backup/restore/<filename>", methods=["POST"])
@admin_required
def restore_backup(filename) -> Response:
    """Restore database from a backup file. Requires app restart."""
    import shutil as _shutil
    import gzip
    import tempfile

    if not BACKUP_FILENAME_RE.match(filename):
        abort(400)
    backup_dir = _get_backup_dir()
    filepath = os.path.join(backup_dir, filename)
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(os.path.realpath(backup_dir) + os.sep):
        abort(400)
    if not os.path.exists(real_path):
        abort(404)
    db_path = os.path.join(current_app.instance_path, "blog.db")
    db.engine.dispose()
    if filename.endswith(".gz"):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name
        with gzip.open(real_path, "rb") as f_in:
            with open(tmp_path, "wb") as f_out:
                _shutil.copyfileobj(f_in, f_out)
        _shutil.copy2(tmp_path, db_path)
        os.unlink(tmp_path)
    else:
        _shutil.copy2(real_path, db_path)
    flash(
        f"Database restored from {filename}. You may need to restart the app for all changes to take effect.",
        "success",
    )
    return redirect(url_for("admin.backup"))


@admin.route("/backup/delete/<filename>", methods=["POST"])
@admin_required
def delete_backup(filename) -> Response:
    """Delete a backup file after filename and path validation."""
    if not BACKUP_FILENAME_RE.match(filename):
        abort(400)
    backup_dir = _get_backup_dir()
    filepath = os.path.join(backup_dir, filename)
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(os.path.realpath(backup_dir) + os.sep):
        abort(400)
    if os.path.exists(real_path):
        if safe_delete_file(real_path):
            flash(f"Backup {filename} deleted.", "success")
        else:
            flash("Failed to delete backup file.", "error")
    else:
        abort(404)
    return redirect(url_for("admin.backup"))
