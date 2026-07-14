from __future__ import annotations
from flask import render_template, redirect, url_for, request, flash
from flask.typing import ResponseReturnValue
from sqlalchemy.exc import IntegrityError, OperationalError

from app.config import (  # noqa: F401
    THEME_DEFAULT_DARK,
    THEME_DEFAULT_LIGHT,
    THEME_DEFAULT_SCHEME,
)
from app.extensions import db
from app.models import SiteSettings, THEME_PRESETS
from app.routes.admin import admin, admin_required
from app.context_processors import invalidate_settings_cache
from app.services.theme_settings import (  # noqa: F401
    validate_theme_settings,
    migrate_legacy_preset,
)
from app.themes.service import get_theme_service
from app.utils import sanitize_css


@admin.route("/settings", methods=["GET"])
@admin_required
def settings() -> ResponseReturnValue:
    """
    Theme and site settings page.

    Methods: GET
    GET: Renders settings page with current SiteSettings and available themes from registry.
    Requires: Admin authentication.
    """
    settings_obj = SiteSettings.get_instance()
    syntax_themes = [
        ("prism", "Prism Default"),
        ("prism-coy", "Prism Coy"),
        ("prism-dark", "Prism Dark"),
        ("prism-funky", "Prism Funky"),
        ("prism-okaidia", "Prism Okaidia"),
        ("prism-tomorrow", "Prism Tomorrow"),
    ]

    service = get_theme_service()
    registry = service.get_registry()
    all_themes = registry.list_themes()

    bundled_themes = [t for t in all_themes if t.source.value == "bundled"]
    external_themes = [t for t in all_themes if t.source.value == "external"]

    return render_template(
        "admin/settings.html",
        settings=settings_obj,
        theme_presets=THEME_PRESETS,
        syntax_themes=syntax_themes,
        theme_dark_name=settings_obj.theme_dark_name,
        theme_light_name=settings_obj.theme_light_name,
        theme_default_scheme=settings_obj.theme_default_scheme,
        valid_schemes=["system", "dark", "light"],
        bundled_themes=bundled_themes,
        external_themes=external_themes,
    )


@admin.route("/settings/theme", methods=["POST"])
@admin_required
def settings_theme() -> ResponseReturnValue:
    """
    Update theme and site settings.

    Methods: POST
    POST: Updates theme names, syntax theme, custom CSS (sanitized), and logo text.
    Requires: Admin authentication.
    Form params:
        theme_dark_name: Dark theme name (must be in registry)
        theme_light_name: Light theme name (must be in registry)
        theme_default_scheme: Default color scheme (system, dark, or light)
        syntax_theme: Syntax highlighting theme
        custom_css_enabled: Checkbox to enable custom CSS
        custom_css: Custom CSS text (sanitized before storage)
        logo_text: Site logo text (max 100 chars)
    """
    settings_obj = SiteSettings.get_instance()

    service = get_theme_service()
    registry = service.get_registry()

    dark_name = request.form.get("theme_dark_name", settings_obj.theme_dark_name)
    light_name = request.form.get("theme_light_name", settings_obj.theme_light_name)
    scheme = request.form.get("theme_default_scheme", settings_obj.theme_default_scheme)

    if registry.resolve(dark_name) is None:
        flash(f"Dark theme '{dark_name}' not found in registry.", "error")
        return redirect(url_for("admin.settings"))

    if registry.resolve(light_name) is None:
        flash(f"Light theme '{light_name}' not found in registry.", "error")
        return redirect(url_for("admin.settings"))

    valid_schemes = ["system", "dark", "light"]
    if scheme not in valid_schemes:
        flash("Invalid theme scheme selected.", "error")
        return redirect(url_for("admin.settings"))

    valid_syntax_themes = [
        "prism",
        "prism-coy",
        "prism-dark",
        "prism-funky",
        "prism-okaidia",
        "prism-tomorrow",
    ]
    syntax_theme = request.form.get("syntax_theme", "prism")
    if syntax_theme not in valid_syntax_themes:
        flash("Invalid syntax theme selected.", "error")
        return redirect(url_for("admin.settings"))

    settings_obj.theme_dark_name = dark_name
    settings_obj.theme_light_name = light_name
    settings_obj.theme_default_scheme = scheme
    settings_obj.syntax_theme = syntax_theme
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


@admin.route("/settings/theme/refresh", methods=["POST"])
@admin_required
def settings_theme_refresh() -> ResponseReturnValue:
    """
    Refresh the theme registry (re-scan bundled and external themes).

    Methods: POST
    POST: Invalidates and rebuilds the theme registry.
    Requires: Admin authentication.
    """
    try:
        service = get_theme_service()
        service.refresh_registry()
        invalidate_settings_cache()
        flash("Theme registry refreshed.", "success")
    except Exception:
        flash("Failed to refresh theme registry.", "error")

    return redirect(url_for("admin.settings"))
