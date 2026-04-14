from flask import render_template, redirect, url_for, request, flash, abort
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.extensions import db
from app.models import SiteSettings, THEME_PRESETS
from app.routes.admin import admin, admin_required


@admin.route("/settings", methods=["GET"])
@admin_required
def settings():
    settings_obj = db.session.execute(
        select(SiteSettings).order_by(SiteSettings.id).limit(1)
    ).scalar_one_or_none()
    return render_template(
        "admin/settings.html",
        settings=settings_obj,
        theme_presets=THEME_PRESETS,
    )


@admin.route("/settings/theme", methods=["POST"])
@admin_required
def settings_theme():
    settings_obj = db.session.execute(
        select(SiteSettings).order_by(SiteSettings.id).limit(1)
    ).scalar_one_or_none()
    if not settings_obj:
        abort(404)

    preset = request.form.get("preset", "github-dark")
    if preset not in THEME_PRESETS:
        flash("Invalid theme preset selected.", "error")
        return redirect(url_for("admin.settings"))

    settings_obj.theme_preset = preset
    settings_obj.custom_css_enabled = request.form.get("custom_css_enabled") == "on"
    settings_obj.custom_css = request.form.get("custom_css", "").strip()
    settings_obj.logo_text = request.form.get("logo_text", "").strip()[:100]

    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.settings"))

    flash("Theme settings saved.", "success")
    return redirect(url_for("admin.settings"))
