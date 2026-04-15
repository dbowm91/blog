import uuid

from flask import render_template, redirect, url_for, request, flash, abort
from flask_login import login_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from typing import Optional

from app.extensions import db
from app.models import Page
from app.routes.admin import admin, admin_required
from app.utils import generate_slug


def _generate_unique_page_slug(title: str, exclude_id: Optional[int] = None) -> str:
    slug = Page.generate_slug(title)
    base_slug = slug
    counter = 2
    while counter <= 100:
        q = select(Page).filter(Page.slug == slug)
        if exclude_id is not None:
            q = q.filter(Page.id != exclude_id)
        if not db.session.execute(q).scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1
    if counter > 100:
        slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"
    return slug


@admin.route("/pages")
@admin_required
def pages_list():
    """
    List all static pages.

    Methods: GET
    GET: Renders pages management page with all pages.
    Requires: Admin authentication.
    """
    pages = db.session.execute(select(Page).order_by(Page.title)).scalars().all()
    return render_template("admin/pages.html", pages=pages)


@admin.route("/pages/new", methods=["GET", "POST"])
@admin_required
def new_page():
    """
    Create a new static page.

    Methods: GET, POST
    GET: Renders page editor form.
    POST: Creates a new page with provided title, slug, body, and published status.
    Requires: Admin authentication.
    Form params:
        title: Page title (required, max 200 chars)
        slug: URL slug (optional, auto-generated if empty)
        body: Page content in Markdown (required)
        published: Whether page is published (checkbox)
    """
    if request.method == "GET":
        return render_template("admin/page_editor.html", page=None, errors=None)

    title = request.form.get("title", "").strip()[:200]
    slug = request.form.get("slug", "").strip()[:200]
    body = request.form.get("body", "").strip()
    published = request.form.get("published") == "on"

    errors = {}
    if not title:
        errors["title"] = "Title is required."
    if not body:
        errors["body"] = "Content is required."

    if slug:
        slug = generate_slug(slug)
        existing = db.session.execute(
            select(Page).filter_by(slug=slug)
        ).scalar_one_or_none()
        if existing:
            errors["slug"] = "A page with this slug already exists."
    else:
        slug = _generate_unique_page_slug(title)

    if errors:
        return render_template("admin/page_editor.html", page=None, errors=errors), 400

    page = Page(
        title=title,
        slug=slug,
        body=body,
        published=published,
    )
    db.session.add(page)
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.pages_list"))

    flash(f"Page '{title}' created.", "success")
    return redirect(url_for("admin.pages_list"))


@admin.route("/pages/edit/<int:page_id>", methods=["GET", "POST"])
@admin_required
def edit_page(page_id):
    """
    Edit an existing static page.

    Methods: GET, POST
    GET: Renders page editor form with existing page data.
    POST: Updates the page with provided title, slug, body, and published status.
    Requires: Admin authentication.
    Path params: page_id (int) - ID of the page to edit.
    Form params:
        title: Page title (required, max 200 chars)
        slug: URL slug (optional, auto-generated if empty)
        body: Page content in Markdown (required)
        published: Whether page is published (checkbox)
    """
    page = db.session.get(Page, page_id)
    if not page:
        abort(404)

    if request.method == "GET":
        return render_template("admin/page_editor.html", page=page, errors=None)

    title = request.form.get("title", "").strip()[:200]
    slug = request.form.get("slug", "").strip()[:200]
    body = request.form.get("body", "").strip()
    published = request.form.get("published") == "on"

    errors = {}
    if not title:
        errors["title"] = "Title is required."
    if not body:
        errors["body"] = "Content is required."

    if slug:
        slug = generate_slug(slug)
        existing = db.session.execute(
            select(Page).filter(Page.slug == slug, Page.id != page_id)
        ).scalar_one_or_none()
        if existing:
            errors["slug"] = "A page with this slug already exists."
    elif title != page.title:
        slug = _generate_unique_page_slug(title, exclude_id=page_id)
    else:
        slug = page.slug

    if errors:
        return render_template("admin/page_editor.html", page=page, errors=errors), 400

    page.title = title
    page.slug = slug
    page.body = body
    page.published = published

    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.pages_list"))

    flash(f"Page '{title}' updated.", "success")
    return redirect(url_for("admin.pages_list"))


@admin.route("/pages/delete/<int:page_id>", methods=["POST"])
@admin_required
def delete_page(page_id):
    """
    Delete a static page.

    Methods: POST
    POST: Deletes the specified page.
    Requires: Admin authentication.
    Path params: page_id (int) - ID of the page to delete.
    """
    page = db.session.get(Page, page_id)
    if not page:
        abort(404)

    title = page.title
    db.session.delete(page)
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.pages_list"))

    flash(f"Page '{title}' deleted.", "success")
    return redirect(url_for("admin.pages_list"))
