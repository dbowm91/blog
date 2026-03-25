import os
import uuid
from datetime import datetime, timezone

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, abort
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Post, Tag, User, PageView, ShareEvent
from app.rate_limit import check_rate_limit, record_failed_attempt, clear_attempts

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def _detect_image_type(header):
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if header[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if header[:4] == b"GIF8" and header[5:6] == b"a":
        return "gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None

admin = Blueprint("admin", __name__, url_prefix="/admin")


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
            return None
        ext = file.filename.rsplit(".", 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
        return filename
    return None


@admin.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        limited = check_rate_limit()
        if limited:
            return limited

        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            clear_attempts()
            login_user(user)
            return redirect(url_for("admin.dashboard"))
        record_failed_attempt()
        flash("Invalid credentials.", "error")

    return render_template("admin/login.html")


@admin.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("public.index"))


@admin.route("/")
@login_required
def dashboard():
    posts = Post.query.order_by(Post.updated_at.desc()).all()

    view_counts = dict(
        db.session.query(PageView.post_id, func.count(PageView.id))
        .group_by(PageView.post_id)
        .all()
    )
    share_counts = dict(
        db.session.query(ShareEvent.post_id, func.count(ShareEvent.id))
        .group_by(ShareEvent.post_id)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        posts=posts,
        view_counts=view_counts,
        share_counts=share_counts,
    )


@admin.route("/new", methods=["GET", "POST"])
@login_required
def new_post():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        summary = request.form.get("summary", "").strip()
        tag_names = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
        published = "published" in request.form

        if not title or not body:
            flash("Title and body are required.", "error")
            return render_template("admin/editor.html", post=None, tag_names=tag_names)

        slug = _generate_unique_slug(title)
        image = _save_image(request.files.get("image"))

        now = datetime.now(timezone.utc)
        post = Post(
            title=title, slug=slug, body=body, summary=summary,
            published=published, image=image,
            published_at=now if published else None,
        )
        post.tags = _get_or_create_tags(tag_names)
        db.session.add(post)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            slug = _generate_unique_slug(title + "-post")
            post = Post(
                title=title, slug=slug, body=body, summary=summary,
                published=published, image=image,
                published_at=now if published else None,
            )
            post.tags = _get_or_create_tags(tag_names)
            db.session.add(post)
            db.session.commit()
        flash("Post created.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/editor.html", post=None, tag_names=[])


@admin.route("/edit/<int:post_id>", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        summary = request.form.get("summary", "").strip()
        tag_names = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
        published = "published" in request.form

        if not title or not body:
            flash("Title and body are required.", "error")
            return render_template("admin/editor.html", post=post, tag_names=tag_names)

        post.title = title
        new_slug = _generate_unique_slug(title, exclude_id=post.id)
        post.slug = new_slug
        post.body = body
        post.summary = summary
        post.published = published
        if published and not post.published_at:
            post.published_at = datetime.now(timezone.utc)
        post.tags = _get_or_create_tags(tag_names)

        image = _save_image(request.files.get("image"))
        if image:
            post.image = image
        elif "remove_image" in request.form:
            post.image = None

        db.session.commit()
        flash("Post updated.", "success")
        return redirect(url_for("admin.dashboard"))

    tag_names = [t.name for t in post.tags]
    return render_template("admin/editor.html", post=post, tag_names=tag_names)


@admin.route("/delete/<int:post_id>", methods=["POST"])
@login_required
def delete_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        abort(404)
    db.session.delete(post)
    db.session.commit()
    flash("Post deleted.", "success")
    return redirect(url_for("admin.dashboard"))


def _get_or_create_tags(names):
    tags = []
    for name in names:
        slug = Tag.generate_slug(name)
        tag = Tag.query.filter_by(slug=slug).first()
        if not tag:
            tag = Tag(name=name, slug=slug)
            db.session.add(tag)
        tags.append(tag)
    return tags
