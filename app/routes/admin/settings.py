from flask import render_template, redirect, url_for, request, flash, abort
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.extensions import db
from app.models import SiteSettings, THEME_PRESETS
from app.routes.admin import admin, admin_required
from app.context_processors import invalidate_settings_cache
from app.utils import sanitize_css


@admin.route("/settings", methods=["GET"])
@admin_required
def settings():
    """
    Theme and site settings page.

    Methods: GET
    GET: Renders settings page with current SiteSettings and available theme presets.
    Requires: Admin authentication.
    """
    settings_obj = SiteSettings.get_instance()
    return render_template(
        "admin/settings.html",
        settings=settings_obj,
        theme_presets=THEME_PRESETS,
    )


@admin.route("/settings/theme", methods=["POST"])
@admin_required
def settings_theme():
    """
    Update theme and site settings.

    Methods: POST
    POST: Updates theme preset, custom CSS (sanitized), and logo text.
    Requires: Admin authentication.
    Form params:
        preset: Theme preset key (must be in THEME_PRESETS)
        custom_css_enabled: Checkbox to enable custom CSS
        custom_css: Custom CSS text (sanitized before storage)
        logo_text: Site logo text (max 100 chars)
    """
    settings_obj = SiteSettings.get_instance()

    preset = request.form.get("preset", "github-dark")
    if preset not in THEME_PRESETS:
        flash("Invalid theme preset selected.", "error")
        return redirect(url_for("admin.settings"))

    settings_obj.theme_preset = preset
    settings_obj.custom_css_enabled = request.form.get("custom_css_enabled") == "on"
    settings_obj.custom_css = sanitize_css(request.form.get("custom_css", "").strip())
    settings_obj.logo_text = request.form.get("logo_text", "").strip()[:100]

    try:
        db.session.commit()
        invalidate_settings_cache()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.settings"))

    flash("Theme settings saved.", "success")
    return redirect(url_for("admin.settings"))
