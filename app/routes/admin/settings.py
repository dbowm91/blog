from __future__ import annotations

import logging

from flask import jsonify, render_template, redirect, url_for, request, flash
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
from app.themes.registry import (
    ThemeValidationError,
    ThemeNotFoundError,
    ThemeParseFailure,
    ThemeLoadError,
)
from app.themes.service import get_theme_service
from app.utils import sanitize_css

logger = logging.getLogger(__name__)


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

    try:
        if registry.resolve(dark_name) is None:
            flash(f"Dark theme '{dark_name}' not found in registry.", "error")
            return redirect(url_for("admin.settings"))
    except ThemeValidationError as e:
        flash(f"Invalid dark theme name: {e}", "error")
        return redirect(url_for("admin.settings"))

    try:
        if registry.resolve(light_name) is None:
            flash(f"Light theme '{light_name}' not found in registry.", "error")
            return redirect(url_for("admin.settings"))
    except ThemeValidationError as e:
        flash(f"Invalid light theme name: {e}", "error")
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


_MAX_CSS_BYTES = 50 * 1024


@admin.route("/settings/theme/preview", methods=["POST"])
@admin_required
def settings_theme_preview() -> ResponseReturnValue:
    """
    Preview theme CSS variables without persisting changes.

    Methods: POST
    POST: Returns JSON with CSS variables for dark and light themes.
    Requires: Admin authentication.
    Form params:
        theme_dark_name: Dark theme name (must be in registry)
        theme_light_name: Light theme name (must be in registry)
    """
    dark_name = request.form.get("theme_dark_name", "").strip()
    light_name = request.form.get("theme_light_name", "").strip()

    if not dark_name or not light_name:
        return jsonify(
            {
                "error": "Both theme_dark_name and theme_light_name are required.",
            }
        ), 400

    service = get_theme_service()
    registry = service.get_registry()

    errors: list[str] = []
    dark_css = ""
    light_css = ""
    resolved_dark_name = ""
    resolved_light_name = ""
    dark_is_dark = False
    light_is_dark = False
    dark_warnings: list[str] = []
    light_warnings: list[str] = []
    warnings: list[str] = []

    try:
        if registry.resolve(dark_name) is None:
            errors.append(f"Dark theme '{dark_name}' not found in registry.")
    except ThemeValidationError as e:
        errors.append(f"Invalid dark theme name: {e}")

    try:
        if registry.resolve(light_name) is None:
            errors.append(f"Light theme '{light_name}' not found in registry.")
    except ThemeValidationError as e:
        errors.append(f"Invalid light theme name: {e}")

    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    try:
        loaded_dark = registry.load(dark_name)
        resolved_dark_name = loaded_dark.descriptor.canonical_name
        dark_css = loaded_dark.css
        dark_is_dark = loaded_dark.is_dark
        dark_warnings = [
            f"{w.token}: {w.description} ({w.ratio:.2f}:1, WCAG {w.wcag})"
            for w in loaded_dark.diagnostics.warnings
        ]
    except ThemeNotFoundError:
        errors.append(f"Dark theme '{dark_name}' not found.")
    except (ThemeParseFailure, ThemeLoadError) as e:
        errors.append(f"Failed to load dark theme: {e}")
    except ThemeValidationError as e:
        errors.append(f"Invalid dark theme name: {e}")

    try:
        loaded_light = registry.load(light_name)
        resolved_light_name = loaded_light.descriptor.canonical_name
        light_css = loaded_light.css
        light_is_dark = loaded_light.is_dark
        light_warnings = [
            f"{w.token}: {w.description} ({w.ratio:.2f}:1, WCAG {w.wcag})"
            for w in loaded_light.diagnostics.warnings
        ]
    except ThemeNotFoundError:
        errors.append(f"Light theme '{light_name}' not found.")
    except (ThemeParseFailure, ThemeLoadError) as e:
        errors.append(f"Failed to load light theme: {e}")
    except ThemeValidationError as e:
        errors.append(f"Invalid light theme name: {e}")

    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    if dark_is_dark and light_is_dark:
        warnings.append("Both themes are classified as dark.")
    elif not dark_is_dark and not light_is_dark:
        warnings.append("Both themes are classified as light.")

    if len(dark_css.encode("utf-8")) > _MAX_CSS_BYTES:
        dark_css = dark_css[:_MAX_CSS_BYTES]
        warnings.append("Dark theme CSS truncated (exceeded 50KB limit).")

    if len(light_css.encode("utf-8")) > _MAX_CSS_BYTES:
        light_css = light_css[:_MAX_CSS_BYTES]
        warnings.append("Light theme CSS truncated (exceeded 50KB limit).")

    return jsonify(
        {
            "dark_css": dark_css,
            "light_css": light_css,
            "dark_name": resolved_dark_name,
            "light_name": resolved_light_name,
            "dark_is_dark": dark_is_dark,
            "light_is_dark": light_is_dark,
            "warnings": warnings,
            "dark_warnings": dark_warnings,
            "light_warnings": light_warnings,
        }
    )


@admin.route("/settings/theme/refresh", methods=["POST"])
@admin_required
def settings_theme_refresh() -> ResponseReturnValue:
    """
    Refresh the theme registry (re-scan bundled and external themes).

    Methods: POST
    POST: Invalidates and rebuilds the theme registry, then reports
          added, removed, and override counts. Warns if a currently
          selected theme disappeared and shows the effective fallback.
    Requires: Admin authentication.
    """
    try:
        service = get_theme_service()

        old_registry = service.get_registry()
        old_themes = {t.canonical_name for t in old_registry.list_themes()}

        service.refresh_registry()

        new_registry = service.get_registry()
        new_themes = {t.canonical_name for t in new_registry.list_themes()}
        new_external_overrides = sum(
            1
            for t in new_registry.list_themes()
            if t.source.value == "external" and t.overrides_bundled
        )

        added = sorted(new_themes - old_themes)
        removed = sorted(old_themes - new_themes)

        invalidate_settings_cache()

        if added:
            flash(f"Added themes: {', '.join(added)}.", "success")
        if removed:
            flash(f"Removed themes: {', '.join(removed)}.", "warning")
        if new_external_overrides:
            flash(
                f"{new_external_overrides} external override(s) active.",
                "info",
            )

        settings_obj = SiteSettings.get_instance()
        dark_name = settings_obj.theme_dark_name
        light_name = settings_obj.theme_light_name
        fallback = new_registry.get_fallback()

        if dark_name and dark_name not in new_themes:
            flash(
                f"Dark theme '{dark_name}' no longer available. "
                f"Effective fallback: '{fallback.descriptor.canonical_name}'.",
                "warning",
            )
        if light_name and light_name not in new_themes:
            flash(
                f"Light theme '{light_name}' no longer available. "
                f"Effective fallback: '{fallback.descriptor.canonical_name}'.",
                "warning",
            )

        if not added and not removed:
            flash("Theme registry refreshed. No changes detected.", "success")

    except (ThemeNotFoundError, ThemeParseFailure, ThemeLoadError, ThemeValidationError) as e:
        logger.warning("theme refresh failed: %s", e)
        flash("Failed to refresh theme registry.", "error")
    except Exception:
        logger.exception("unexpected error during theme refresh")
        flash("Failed to refresh theme registry.", "error")

    return redirect(url_for("admin.settings"))
