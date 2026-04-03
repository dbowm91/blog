from flask import render_template, redirect, url_for, request, flash, abort
from flask_login import login_required

from app.extensions import db
from app.models import Tag
from app.routes.admin import (
    admin,
    admin_required,
    validate_tag_name,
    invalidate_tag_cache,
)
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, OperationalError


@admin.route("/tags")
@admin_required
def tags_list():
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
def rename_tag(tag_id):
    from app.routes.admin import logger

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
def delete_tag(tag_id):
    from app.routes.admin import logger

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
def create_tag():
    from app.routes.admin import logger

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
