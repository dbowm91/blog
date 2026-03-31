import csv
import io
import os
import re
import uuid

from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, abort, jsonify, Response, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from datetime import datetime, timedelta

from app.extensions import db
from app.models import Post, Tag, User, PageView, ShareEvent, Subscriber

from app.utils import utc_now, safe_delete_file
from app.cache import invalidate_tag_cache
from app.search import sync_fts, remove_fts

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
TAG_NAME_REGEX = re.compile(r"^[\w\s-]+$")
BACKUP_FILENAME_RE = re.compile(r"^blog_\d{8}_\d{6}\.db(\.gz)?$")


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
        query = Post.query.filter(Post.slug == slug)
        if exclude_id is not None:
            query = query.filter(Post.id != exclude_id)
        if not query.first():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def _save_image(file):
    if file and file.filename and _allowed_file(file.filename):
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
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.is_admin:
            login_user(user)
            return redirect(url_for("admin.dashboard"))
        flash("Invalid credentials.", "error")

    return render_template("admin/login.html")


@admin.route("/newsletter-reset/<int:post_id>", methods=["POST"])
@admin_required
def newsletter_reset(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)
    post.newsletter_sent_at = None
    post.newsletter_attempts = 0
    db.session.commit()
    flash(f"Newsletter flag reset for '{post.title}'. It will be included in the next newsletter.", "success")
    return redirect(url_for("admin.dashboard"))


@admin.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("public.index"))


@admin.route("/")
@admin_required
def dashboard():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "all")

    query = Post.query
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search_term = f"%{escaped}%"
        query = query.filter(Post.title.ilike(search_term, escape="\\"))
    if status == "published":
        query = query.filter(Post.published == True)
    elif status == "draft":
        query = query.filter(Post.published == False)

    pagination = (
        query
        .order_by(Post.updated_at.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )
    posts = pagination.items

    post_ids = [p.id for p in posts]
    if post_ids:
        view_counts_sq = (
            select(PageView.post_id, func.count(PageView.id).label("cnt"))
            .where(PageView.post_id.in_(post_ids))
            .group_by(PageView.post_id).subquery()
        )
        share_counts_sq = (
            select(ShareEvent.post_id, func.count(ShareEvent.id).label("cnt"))
            .where(ShareEvent.post_id.in_(post_ids))
            .group_by(ShareEvent.post_id).subquery()
        )
        rows = db.session.execute(
            select(Post.id,
                   func.coalesce(view_counts_sq.c.cnt, 0).label("views"),
                   func.coalesce(share_counts_sq.c.cnt, 0).label("shares"))
            .outerjoin(view_counts_sq, Post.id == view_counts_sq.c.post_id)
            .outerjoin(share_counts_sq, Post.id == share_counts_sq.c.post_id)
            .where(Post.id.in_(post_ids))
        ).all()
        view_counts = {row.id: row.views for row in rows}
        share_counts = {row.id: row.shares for row in rows}
    else:
        view_counts = {}
        share_counts = {}

    total_views = db.session.query(func.count(PageView.id)).scalar() or 0
    total_posts = db.session.query(func.count(Post.id)).filter(Post.published == True).scalar() or 0
    total_shares = db.session.query(func.count(ShareEvent.id)).scalar() or 0
    total_subscribers = db.session.query(func.count(Subscriber.id)).filter(Subscriber.confirmed == True).scalar() or 0

    thirty_days_ago = utc_now() - timedelta(days=30)
    trending = (
        db.session.query(Post, func.count(PageView.id).label('view_count'))
        .join(PageView)
        .filter(Post.published == True)
        .filter(PageView.created_at >= thirty_days_ago)
        .group_by(Post.id)
        .order_by(func.count(PageView.id).desc())
        .limit(5)
        .all()
    )

    month_start = utc_now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_this_month = db.session.query(func.count(Subscriber.id)).filter(Subscriber.created_at >= month_start).scalar() or 0

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
def new_post():
    if request.method == "POST":
        title = request.form.get("title", "").strip()[:200]
        body = request.form.get("body", "").strip()
        summary = request.form.get("summary", "").strip()[:500]
        tag_names = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
        published = "published" in request.form

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
            title=title, slug=slug, body=body, summary=summary,
            published=published, image=image,
            published_at=now if published else None,
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
                safe_delete_file(os.path.join(current_app.config["UPLOAD_FOLDER"], image))
            slug = _generate_unique_slug(title)
            post = Post(
                title=title, slug=slug, body=body, summary=summary,
                published=published, image=image,
                published_at=now if published else None,
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
def edit_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)

    if request.method == "POST":
        title = request.form.get("title", "").strip()[:200]
        body = request.form.get("body", "").strip()
        summary = request.form.get("summary", "").strip()[:500]
        tag_names = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
        published = "published" in request.form

        if not title or not body:
            flash("Title and body are required.", "error")
            return render_template("admin/editor.html", post=post, tag_names=tag_names)

        searchable_changed = (
            title != post.title or body != post.body or
            summary != post.summary or published != post.published
        )
        if title != post.title:
            post.slug = _generate_unique_slug(title, exclude_id=post.id)
        post.title = title
        post.body = body
        post.summary = summary
        was_published = post.published
        post.published = published
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
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            if image:
                safe_delete_file(os.path.join(current_app.config["UPLOAD_FOLDER"], image))
            post = db.session.get(Post, post_id)
            post.slug = _generate_unique_slug(title, exclude_id=post.id)
            post.title = title
            post.body = body
            post.summary = summary
            post.published = published
            if published and not was_published:
                post.published_at = utc_now()
            post.tags = _get_or_create_tags(tag_names)
            sync_fts(post.id, post.title, post.body, post.summary, post.published)
            db.session.commit()
        # Delete old image file only after successful commit
        if old_image:
            safe_delete_file(os.path.join(current_app.config["UPLOAD_FOLDER"], old_image))
        invalidate_tag_cache()
        _cleanup_orphan_tags()
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
    db.session.delete(post)
    db.session.commit()
    remove_fts(post_id_for_fts)
    if old_image:
        safe_delete_file(os.path.join(current_app.config["UPLOAD_FOLDER"], old_image))
    invalidate_tag_cache()
    _cleanup_orphan_tags()
    flash("Post deleted.", "success")
    return redirect(url_for("admin.dashboard"))


def _cleanup_orphan_tags():
    """Remove tags that have no associated posts."""
    from app.models import post_tags
    orphan_tag_ids = (
        db.session.query(Tag.id)
        .outerjoin(post_tags, Tag.id == post_tags.c.tag_id)
        .filter(post_tags.c.post_id.is_(None))
        .all()
    )
    if orphan_tag_ids:
        ids = [row[0] for row in orphan_tag_ids]
        Tag.query.filter(Tag.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()


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
        tag = Tag.query.filter_by(slug=slug).first()
        if not tag:
            tag = Tag(name=name, slug=slug)
            db.session.add(tag)
        tags.append(tag)
    if invalid_tags:
        flash(f"Invalid tag names (skipped): {', '.join(invalid_tags)}", "warning")
    return tags


@admin.route("/analytics")
@admin_required
def analytics():
    days = request.args.get("days", 30, type=int)
    days = min(max(days, 7), 365)

    start_date = utc_now() - timedelta(days=days)

    daily_views = db.session.query(
        func.date(PageView.created_at).label('date'),
        func.count(PageView.id).label('views')
    ).filter(
        PageView.created_at >= start_date
    ).group_by(
        func.date(PageView.created_at)
    ).order_by(
        func.date(PageView.created_at)
    ).all()

    total_views = db.session.query(func.count(PageView.id)).filter(
        PageView.created_at >= start_date
    ).scalar() or 0

    top_posts = (
        db.session.query(Post, func.count(PageView.id).label('view_count'))
        .join(PageView)
        .filter(Post.published == True)
        .filter(PageView.created_at >= start_date)
        .group_by(Post.id)
        .order_by(func.count(PageView.id).desc())
        .limit(10)
        .all()
    )

    top_post_ids = [p.id for p, _ in top_posts]
    share_counts_analytics = dict(
        db.session.query(ShareEvent.post_id, func.count(ShareEvent.id))
        .filter(ShareEvent.post_id.in_(top_post_ids))
        .group_by(ShareEvent.post_id)
        .all()
    )

    share_platforms = db.session.query(
        ShareEvent.platform,
        func.count(ShareEvent.id).label('count')
    ).group_by(ShareEvent.platform).all()

    referrer_data = db.session.query(
        PageView.referrer,
        func.count(PageView.id).label('count')
    ).filter(
        PageView.referrer != None,
        PageView.created_at >= start_date
    ).group_by(PageView.referrer).order_by(
        func.count(PageView.id).desc()
    ).limit(15).all()

    def categorize_referrer(url):
        if not url:
            return "Direct"
        url_lower = url.lower()
        if "google" in url_lower or "bing" in url_lower or "yahoo" in url_lower or "duckduckgo" in url_lower:
            return "Search"
        if "twitter" in url_lower or "facebook" in url_lower or "linkedin" in url_lower or "reddit" in url_lower:
            return "Social"
        return "Other"

    referrer_summary = {}
    for url, count in referrer_data:
        category = categorize_referrer(url)
        referrer_summary[category] = referrer_summary.get(category, 0) + count

    total_subscribers = db.session.query(func.count(Subscriber.id)).scalar() or 0
    confirmed_subscribers = db.session.query(func.count(Subscriber.id)).filter(Subscriber.confirmed == True).scalar() or 0

    return render_template(
        "admin/analytics.html",
        days=days,
        daily_views=daily_views,
        total_views=total_views,
        top_posts=top_posts,
        share_platforms=share_platforms,
        share_counts=share_counts_analytics,
        referrer_summary=referrer_summary,
        total_subscribers=total_subscribers,
        confirmed_subscribers=confirmed_subscribers,
    )


@admin.route("/preview/<int:post_id>")
@admin_required
def preview_post(post_id):
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
def subscribers():
    page = request.args.get("page", 1, type=int)
    filter_status = request.args.get("status", "all")

    query = Subscriber.query
    if filter_status == "confirmed":
        query = query.filter(Subscriber.confirmed == True)
    elif filter_status == "unconfirmed":
        query = query.filter(Subscriber.confirmed == False)
    elif filter_status == "unsubscribed":
        query = query.filter(Subscriber.unsubscribed_at.isnot(None))

    pagination = (
        query.order_by(Subscriber.created_at.desc())
        .paginate(page=page, per_page=50, error_out=False)
    )
    return render_template(
        "admin/subscribers.html",
        subscribers=pagination.items,
        pagination=pagination,
        filter_status=filter_status,
    )


@admin.route("/subscribers/delete/<int:sub_id>", methods=["POST"])
@admin_required
def delete_subscriber(sub_id):
    sub = db.session.get(Subscriber, sub_id)
    if not sub:
        abort(404)
    email = sub.email
    db.session.delete(sub)
    db.session.commit()
    flash(f"Subscriber {email} deleted.", "success")
    return redirect(url_for("admin.subscribers"))


@admin.route("/subscribers/export")
@admin_required
def export_subscribers():
    subs = Subscriber.query.order_by(Subscriber.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["email", "confirmed", "created_at", "expires_at"])
    for s in subs:
        writer.writerow([
            s.email,
            s.confirmed,
            s.created_at.isoformat() if s.created_at else "",
            s.expires_at.isoformat() if s.expires_at else "",
        ])
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=subscribers.csv"},
    )


@admin.route("/preview-markdown", methods=["POST"])
@admin_required
def preview_markdown():
    data = request.get_json(silent=True)
    if not data or "text" not in data:
        return jsonify({"error": "invalid"}), 400
    import nh3
    import markdown as md
    from app.markdown_config import MARKDOWN_ALLOWED_TAGS, MARKDOWN_ALLOWED_ATTRIBUTES
    html = md.markdown(data["text"], extensions=["fenced_code", "tables"])
    clean = nh3.clean(html, tags=MARKDOWN_ALLOWED_TAGS, attributes=MARKDOWN_ALLOWED_ATTRIBUTES)
    return jsonify({"html": clean})


@admin.route("/media")
@admin_required
def media():
    page = request.args.get("page", 1, type=int)
    per_page = 50
    max_files = 1000
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    all_files = []
    with os.scandir(upload_dir) as entries:
        for entry in entries:
            if not entry.is_file():
                continue
            stat = entry.stat()
            all_files.append({
                "name": entry.name,
                "size": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime),
            })
        all_files.sort(key=lambda f: f["mtime"], reverse=True)
    if len(all_files) > max_files:
        all_files = all_files[:max_files]
    truncated = len(all_files) >= max_files
    total = len(all_files)
    start = (page - 1) * per_page
    end = start + per_page
    files = all_files[start:end]
    total_pages = (total + per_page - 1) // per_page
    return render_template("admin/media.html", files=files, page=page, total_pages=total_pages, truncated=truncated)


@admin.route("/media/delete/<filename>", methods=["POST"])
@admin_required
def delete_media(filename):
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
def tags_list():
    from app.models import post_tags
    tags = Tag.query.order_by(Tag.name).all()
    tag_post_counts = dict(
        db.session.query(post_tags.c.tag_id, func.count(post_tags.c.post_id))
        .group_by(post_tags.c.tag_id)
        .all()
    )
    return render_template("admin/tags.html", tags=tags, tag_post_counts=tag_post_counts)


@admin.route("/tags/rename/<int:tag_id>", methods=["POST"])
@admin_required
def rename_tag(tag_id):
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
    existing = Tag.query.filter(Tag.slug == slug, Tag.id != tag.id).first()
    if existing:
        flash(f"Tag '{new_name}' already exists.", "warning")
        return redirect(url_for("admin.tags_list"))
    tag.name = new_name
    tag.slug = slug
    db.session.commit()
    invalidate_tag_cache()
    flash(f"Tag renamed to '{new_name}'.", "success")
    return redirect(url_for("admin.tags_list"))


@admin.route("/tags/delete/<int:tag_id>", methods=["POST"])
@admin_required
def delete_tag(tag_id):
    tag = db.session.get(Tag, tag_id)
    if not tag:
        abort(404)
    name = tag.name
    db.session.delete(tag)
    db.session.commit()
    invalidate_tag_cache()
    flash(f"Tag '{name}' deleted.", "success")
    return redirect(url_for("admin.tags_list"))


@admin.route("/tags/create", methods=["POST"])
@admin_required
def create_tag():
    name = request.form.get("name", "").strip()[:50]
    if not name:
        flash("Tag name cannot be empty.", "error")
        return redirect(url_for("admin.tags_list"))
    is_valid, error_msg = validate_tag_name(name)
    if not is_valid:
        flash(error_msg, "error")
        return redirect(url_for("admin.tags_list"))
    slug = Tag.generate_slug(name)
    existing = Tag.query.filter_by(slug=slug).first()
    if existing:
        flash(f"Tag '{name}' already exists.", "warning")
        return redirect(url_for("admin.tags_list"))
    tag = Tag(name=name, slug=slug)
    db.session.add(tag)
    db.session.commit()
    invalidate_tag_cache()
    flash(f"Tag '{name}' created.", "success")
    return redirect(url_for("admin.tags_list"))


@admin.route("/newsletter-test", methods=["POST"])
@admin_required
def newsletter_test():
    from app.email import send_newsletter
    from app.config import APP_TITLE, FROM_ADDRESS
    posts = (
        Post.query.filter_by(published=True)
        .order_by(Post.created_at.desc())
        .limit(3)
        .all()
    )
    if not posts:
        flash("No published posts to send.", "error")
        return redirect(url_for("admin.dashboard"))
    from app.models import User
    admin_user = User.query.first()
    if not admin_user:
        flash("No admin user found.", "error")
        return redirect(url_for("admin.dashboard"))
    test_email = request.form.get("test_email", "").strip()
    if not test_email:
        test_email = FROM_ADDRESS.split("<")[-1].rstrip(">") if "<" in FROM_ADDRESS else FROM_ADDRESS
    fake_sub = type("FakeSub", (), {
        "email": test_email,
        "token": "test",
    })()
    try:
        send_newsletter(posts, [fake_sub])
        flash(f"Test newsletter sent to {test_email}.", "success")
    except Exception as e:
        flash(f"Failed to send test newsletter: {e}", "error")
    return redirect(url_for("admin.dashboard"))


@admin.route("/bulk", methods=["POST"])
@admin_required
def bulk_operations():
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

    posts = Post.query.filter(Post.id.in_(valid_ids)).all()
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
        db.session.commit()
        invalidate_tag_cache()
        flash(f"Published {len(posts)} post(s).", "success")
    elif action == "unpublish":
        for post in posts:
            post.published = False
        for post in posts:
            sync_fts(post.id, post.title, post.body, post.summary, post.published)
        db.session.commit()
        invalidate_tag_cache()
        flash(f"Unpublished {len(posts)} post(s).", "success")
    elif action == "delete":
        images_to_delete = []
        deleted_post_ids = []
        for post in posts:
            if post.image:
                images_to_delete.append(post.image)
            deleted_post_ids.append(post.id)
            db.session.delete(post)
        db.session.commit()
        for pid in deleted_post_ids:
            remove_fts(pid)
        for img in images_to_delete:
            safe_delete_file(os.path.join(current_app.config["UPLOAD_FOLDER"], img))
        invalidate_tag_cache()
        _cleanup_orphan_tags()
        flash(f"Deleted {len(posts)} post(s).", "success")
    else:
        flash("Invalid action.", "error")

    return redirect(url_for("admin.dashboard"))


@admin.route("/users")
@admin_required
def users_list():
    users = User.query.order_by(User.username).all()
    return render_template("admin/users.html", users=users)


@admin.route("/users/create", methods=["POST"])
@admin_required
def create_user():
    username = request.form.get("username", "").strip()[:80]
    password = request.form.get("password", "").strip()
    is_admin = "is_admin" in request.form

    if not username or not password:
        flash("Username and password are required.", "error")
        return redirect(url_for("admin.users_list"))

    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return redirect(url_for("admin.users_list"))

    existing = User.query.filter_by(username=username).first()
    if existing:
        flash(f"User '{username}' already exists.", "error")
        return redirect(url_for("admin.users_list"))

    user = User(username=username, is_admin=is_admin)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash(f"User '{username}' created.", "success")
    return redirect(url_for("admin.users_list"))


@admin.route("/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.id == current_user.id:
        flash("Cannot delete your own account.", "error")
        return redirect(url_for("admin.users_list"))
    admin_count = User.query.filter_by(is_admin=True).count()
    if user.is_admin and admin_count <= 1:
        flash("Cannot delete the last admin user.", "error")
        return redirect(url_for("admin.users_list"))
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f"User '{username}' deleted.", "success")
    return redirect(url_for("admin.users_list"))


@admin.route("/users/password/<int:user_id>", methods=["POST"])
@admin_required
def change_password(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    password = request.form.get("password", "").strip()
    if not password or len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return redirect(url_for("admin.users_list"))
    user.set_password(password)
    db.session.commit()
    flash(f"Password changed for '{user.username}'.", "success")
    return redirect(url_for("admin.users_list"))


def _get_backup_dir():
    return os.path.join(current_app.instance_path, "backups")


@admin.route("/backup")
@admin_required
def backup():
    backup_dir = _get_backup_dir()
    backups = []
    if os.path.isdir(backup_dir):
        for fname in sorted(os.listdir(backup_dir), reverse=True):
            if fname.startswith("blog_") and (fname.endswith(".db") or fname.endswith(".db.gz")):
                fpath = os.path.join(backup_dir, fname)
                stat = os.stat(fpath)
                backups.append({
                    "name": fname,
                    "size": stat.st_size,
                    "mtime": datetime.fromtimestamp(stat.st_mtime),
                })
    return render_template("admin/backup.html", backups=backups)


@admin.route("/backup/create", methods=["POST"])
@admin_required
def create_backup():
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
def download_backup(filename):
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
def restore_backup(filename):
    import shutil as _shutil
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
    _shutil.copy2(real_path, db_path)
    flash(f"Database restored from {filename}.", "success")
    return redirect(url_for("admin.backup"))


@admin.route("/backup/delete/<filename>", methods=["POST"])
@admin_required
def delete_backup(filename):
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
