from __future__ import annotations
from flask import render_template, redirect, url_for, request, flash, abort
from flask.typing import ResponseReturnValue
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from typing import Mapping

from app.extensions import db
from app.models import Page
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import _generate_unique_slug
from app.services.navigation import get_menu_settings, resolve_page_menu
from app.services.site_settings import HOME_KIND_PAGE, reset_homepage_target_if_needed
from app.utils import generate_slug


def _show_in_menu_from_form(form: Mapping[str, str], default: bool) -> bool:
    """Read the ``show_in_menu`` flag from a submitted form.

    The page editor form does not carry the field, so an absent value keeps
    the current flag on edit and falls back to True on create. A form that
    manages the flag sends ``show_in_menu_present`` alongside it, which makes
    an unchecked box record False.
    """
    if "show_in_menu_present" in form:
        return form.get("show_in_menu") == "on"
    if "show_in_menu" in form:
        return form.get("show_in_menu") == "on"
    return default


@admin.route("/pages")
@admin_required
def pages_list() -> ResponseReturnValue:
    """
    List all static pages.

    Methods: GET
    GET: Renders pages management page with all pages.
    Requires: Admin authentication.
    """
    pages = db.session.execute(select(Page).order_by(Page.title)).scalars().all()
    show_pages_in_menu, _ = get_menu_settings()
    menu_page_ids = {page.id for page in resolve_page_menu()}
    return render_template(
        "admin/pages.html",
        pages=pages,
        menu_page_ids=menu_page_ids,
        show_pages_in_menu=show_pages_in_menu,
    )


@admin.route("/pages/new", methods=["GET", "POST"])
@admin_required
def new_page() -> ResponseReturnValue:
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
    show_in_menu = _show_in_menu_from_form(request.form, True)

    errors = {}
    if not title:
        errors["title"] = "Title is required."
    if not body:
        errors["body"] = "Content is required."

    if slug:
        slug = generate_slug(slug)
        existing = db.session.execute(select(Page).filter_by(slug=slug)).scalar_one_or_none()
        if existing:
            errors["slug"] = "A page with this slug already exists."
    else:
        slug = _generate_unique_slug(Page, title)

    if errors:
        return render_template("admin/page_editor.html", page=None, errors=errors), 400

    page = Page(
        title=title,
        slug=slug,
        body=body,
        published=published,
        show_in_menu=show_in_menu,
    )
    db.session.add(page)

    max_attempts = 100
    for attempt in range(max_attempts):
        try:
            db.session.flush()
            db.session.commit()
            break
        except IntegrityError:
            db.session.rollback()
            if attempt == max_attempts - 1:
                raise
            page.slug = _generate_unique_slug(Page, title, exclude_id=page.id if page.id else None)
            db.session.add(page)
        except OperationalError:
            db.session.rollback()
            flash("Database error occurred. Please try again.", "error")
            return redirect(url_for("admin.pages_list"))

    flash(f"Page '{title}' created.", "success")
    return redirect(url_for("admin.pages_list"))


@admin.route("/pages/edit/<int:page_id>", methods=["GET", "POST"])
@admin_required
def edit_page(page_id) -> ResponseReturnValue:
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
    show_in_menu = _show_in_menu_from_form(request.form, page.show_in_menu)

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
        slug = _generate_unique_slug(Page, title, exclude_id=page_id)
    else:
        slug = page.slug

    if errors:
        return render_template("admin/page_editor.html", page=page, errors=errors), 400

    page.title = title
    page.slug = slug
    page.body = body
    page.published = published
    page.show_in_menu = show_in_menu

    if not published:
        reset_homepage_target_if_needed(HOME_KIND_PAGE, page_id)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        page = db.session.get(Page, page_id)
        if not page:
            flash("Page not found.", "error")
            return redirect(url_for("admin.pages_list"))
        page.slug = _generate_unique_slug(Page, title, exclude_id=page_id)
        page.title = title
        page.body = body
        page.published = published
        page.show_in_menu = show_in_menu
        db.session.commit()
    except OperationalError:
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.pages_list"))

    flash(f"Page '{title}' updated.", "success")
    return redirect(url_for("admin.pages_list"))


@admin.route("/pages/delete/<int:page_id>", methods=["POST"])
@admin_required
def delete_page(page_id) -> ResponseReturnValue:
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
    reset_homepage_target_if_needed(HOME_KIND_PAGE, page_id)
    db.session.delete(page)
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.pages_list"))

    flash(f"Page '{title}' deleted.", "success")
    return redirect(url_for("admin.pages_list"))


@admin.route("/pages/<int:page_id>/menu", methods=["POST"])
@admin_required
def set_page_menu(page_id) -> ResponseReturnValue:
    """
    Set whether a page appears in the site navigation menu.

    Methods: POST
    POST: Sets the show_in_menu flag of the specified page.
    Requires: Admin authentication.
    Path params: page_id (int) - ID of the page to update.
    Form params:
        show_in_menu: Whether the page is shown in the menu (checkbox)
    """
    page = db.session.get(Page, page_id)
    if not page:
        abort(404)

    page.show_in_menu = request.form.get("show_in_menu") == "on"
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.pages_list"))

    if page.show_in_menu:
        flash(f"Page '{page.title}' is now shown in the menu.", "success")
    else:
        flash(f"Page '{page.title}' is no longer shown in the menu.", "success")
    return redirect(url_for("admin.pages_list"))
