from flask import render_template, redirect, url_for, request, flash, abort
from flask_login import login_required

from app.extensions import db
from app.models import Tag
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import validate_tag_name, logger
from app.tag_cache import invalidate_tag_cache
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, OperationalError


@admin.route("/tags")
@admin_required
def tags_list():
    """
    List all tags with post counts.

    Methods: GET
    GET: Renders tags management page with all tags and their post counts.
    Requires: Admin authentication.
    """
    from app.models import post_tags

    rows = db.session.execute(
        select(Tag, func.count(post_tags.c.post_id).label("cnt"))
        .outerjoin(post_tags, Tag.id == post_tags.c.tag_id)
        .group_by(Tag.id)
        .order_by(Tag.name)
    ).all()
    tags = [row[0] for row in rows]
    tag_post_counts = {row[0].id: row[1] for row in rows}
    return render_template(
        "admin/tags.html", tags=tags, tag_post_counts=tag_post_counts
    )


@admin.route("/tags/rename/<int:tag_id>", methods=["POST"])
@admin_required
def rename_tag(tag_id):
    """
    Rename a tag.

    Methods: POST
    POST: Updates tag name and slug. Validates name format (ASCII alphanumeric).
    Requires: Admin authentication.
    Path params: tag_id (int) - ID of the tag to rename.
    Form params: name - New tag name (max 50 chars)
    """
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
    """
    Delete a tag.

    Methods: POST
    POST: Deletes the tag (posts retain their associations via post_tags).
    Requires: Admin authentication.
    Path params: tag_id (int) - ID of the tag to delete.
    """
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
    """
    Create a new tag.

    Methods: POST
    POST: Creates a new tag with auto-generated slug. Validates name format.
    Requires: Admin authentication.
    Form params: name - Tag name (max 50 chars, ASCII alphanumeric)
    """
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
