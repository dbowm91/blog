from __future__ import annotations

import logging
from typing import Any

from flask import jsonify, render_template, redirect, url_for, request, flash
from flask.typing import ResponseReturnValue
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.config import (  # noqa: F401
    THEME_DEFAULT_DARK,
    THEME_DEFAULT_LIGHT,
    THEME_DEFAULT_SCHEME,
)
from app.extensions import db
from app.models import Page, Project, SiteSettings
from app.routes.admin import admin, admin_required
from app.context_processors import invalidate_footer_cache, invalidate_settings_cache
from app.appearance.model import CATEGORY_MONO, CATEGORY_SANS, SOURCE_CUSTOM
from app.appearance.service import get_appearance_service
from app.appearance.uploads import save_custom_backdrop, save_custom_font
from app.services.appearance_settings import (
    CUSTOM_OPTION,
    resolve_backdrop_key,
    resolve_font_key,
    validate_appearance_settings,
)
from app.services.site_settings import (
    SiteSettingsValidationError,
    parse_menu_pages,
    validate_site_settings,
)
from app.storage import get_storage
from app.themes.registry import (
    ThemeValidationError,
    ThemeNotFoundError,
    ThemeParseFailure,
    ThemeLoadError,
)
from app.themes.service import get_theme_service
from app.themes.translate import to_legacy_css
from app.utils import sanitize_css

logger = logging.getLogger(__name__)


def _store_upload(
    files: Any,
    field: str,
    saver: Any,
    storage: Any,
) -> tuple[str | None, str | None]:
    """Store an optional upload, returning the stored name or an error."""
    upload = files.get(field)
    if upload is None or not getattr(upload, "filename", ""):
        return None, None
    return saver(storage, upload)


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

    service = get_theme_service()
    registry = service.get_registry()
    all_themes = registry.list_themes()

    bundled_themes = [t for t in all_themes if t.source.value == "bundled"]
    external_themes = [t for t in all_themes if t.source.value == "external"]

    menu_choices = db.session.execute(select(Page).order_by(Page.title)).scalars().all()

    homepage_pages = (
        db.session.execute(select(Page).filter(Page.published.is_(True)).order_by(Page.title))
        .scalars()
        .all()
    )
    homepage_projects = (
        db.session.execute(
            select(Project)
            .filter(Project.published.is_(True))
            .order_by(Project.sort_order.asc(), Project.title.asc())
        )
        .scalars()
        .all()
    )

    appearance_service = get_appearance_service()
    font_registry = appearance_service.get_font_registry()
    backdrop_registry = appearance_service.get_backdrop_registry()

    sans_families = font_registry.list_families(CATEGORY_SANS)
    mono_families = font_registry.list_families(CATEGORY_MONO)
    backdrops = backdrop_registry.list_backdrops()

    return render_template(
        "admin/settings.html",
        settings=settings_obj,
        theme_dark_name=settings_obj.theme_dark_name,
        theme_light_name=settings_obj.theme_light_name,
        theme_default_scheme=settings_obj.theme_default_scheme,
        valid_schemes=["system", "dark", "light"],
        bundled_themes=bundled_themes,
        external_themes=external_themes,
        menu_choices=menu_choices,
        menu_pages_selected=parse_menu_pages(settings_obj.menu_pages),
        homepage_pages=homepage_pages,
        homepage_projects=homepage_projects,
        homepage_kind=settings_obj.homepage_kind or "blog",
        homepage_target_id=settings_obj.homepage_target_id,
        bundled_sans_fonts=[f for f in sans_families if f.source != SOURCE_CUSTOM],
        custom_sans_fonts=[f for f in sans_families if f.source == SOURCE_CUSTOM],
        bundled_mono_fonts=[f for f in mono_families if f.source != SOURCE_CUSTOM],
        custom_mono_fonts=[f for f in mono_families if f.source == SOURCE_CUSTOM],
        bundled_backdrops=[b for b in backdrops if b.source != SOURCE_CUSTOM],
        custom_backdrops=[b for b in backdrops if b.source == SOURCE_CUSTOM],
        font_family_map={f.key: f.css_family for f in [*sans_families, *mono_families]},
        custom_option=CUSTOM_OPTION,
    )


@admin.route("/settings/theme", methods=["POST"])
@admin_required
def settings_theme() -> ResponseReturnValue:
    """
    Update theme and site settings.

    Methods: POST
    POST: Updates theme names, custom CSS (sanitized), and logo text.
    Requires: Admin authentication.
    Form params:
        theme_dark_name: Dark theme name (must be in registry)
        theme_light_name: Light theme name (must be in registry)
        theme_default_scheme: Default color scheme (system, dark, or light)
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
    except (ThemeValidationError, ThemeParseFailure, ThemeLoadError) as e:
        flash(f"Invalid dark theme name: {e}", "error")
        return redirect(url_for("admin.settings"))

    try:
        if registry.resolve(light_name) is None:
            flash(f"Light theme '{light_name}' not found in registry.", "error")
            return redirect(url_for("admin.settings"))
    except (ThemeValidationError, ThemeParseFailure, ThemeLoadError) as e:
        flash(f"Invalid light theme name: {e}", "error")
        return redirect(url_for("admin.settings"))

    valid_schemes = ["system", "dark", "light"]
    if scheme not in valid_schemes:
        flash("Invalid theme scheme selected.", "error")
        return redirect(url_for("admin.settings"))

    settings_obj.theme_dark_name = dark_name
    settings_obj.theme_light_name = light_name
    settings_obj.theme_default_scheme = scheme
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


@admin.route("/settings/appearance", methods=["POST"])
@admin_required
def settings_appearance() -> ResponseReturnValue:
    """
    Update the font and backdrop choices.

    Methods: POST
    POST: Stores the selected font families and page backdrop, and any
          uploaded font or backdrop file. Validation is owned by
          `app.services.appearance_settings`.
    Requires: Admin authentication.
    Form params:
        font_sans: Sans font key, or the custom sentinel to upload a file
        font_mono: Monospace font key, or the custom sentinel to upload a file
        backdrop: Backdrop key, the custom sentinel, or an empty value for none
        font_sans_file: Optional woff2 upload for the sans slot
        font_mono_file: Optional woff2 upload for the monospace slot
        backdrop_file: Optional SVG upload for the backdrop
    """
    payload = validate_appearance_settings(request.form)
    settings_obj = SiteSettings.get_instance()

    service = get_appearance_service()
    font_registry = service.get_font_registry()
    backdrop_registry = service.get_backdrop_registry()
    storage = get_storage()

    sans_file, error = _store_upload(request.files, "font_sans_file", save_custom_font, storage)
    if error:
        flash(error, "error")
        return redirect(url_for("admin.settings"))

    mono_file, error = _store_upload(request.files, "font_mono_file", save_custom_font, storage)
    if error:
        flash(error, "error")
        return redirect(url_for("admin.settings"))

    backdrop_file, error = _store_upload(
        request.files, "backdrop_file", save_custom_backdrop, storage
    )
    if error:
        flash(error, "error")
        return redirect(url_for("admin.settings"))

    if sans_file or mono_file or backdrop_file:
        service.invalidate_registry()

    sans_key, error = resolve_font_key(
        payload.font_sans,
        sans_file,
        settings_obj.font_sans,
        font_registry,
        CATEGORY_SANS,
        "sans",
    )
    if error:
        flash(error, "error")
        return redirect(url_for("admin.settings"))

    mono_key, error = resolve_font_key(
        payload.font_mono,
        mono_file,
        settings_obj.font_mono,
        font_registry,
        CATEGORY_MONO,
        "monospace",
    )
    if error:
        flash(error, "error")
        return redirect(url_for("admin.settings"))

    backdrop_key, error = resolve_backdrop_key(
        payload.backdrop,
        backdrop_file,
        settings_obj.backdrop,
        backdrop_registry,
    )
    if error:
        flash(error, "error")
        return redirect(url_for("admin.settings"))

    settings_obj.font_sans = sans_key
    settings_obj.font_mono = mono_key
    settings_obj.backdrop = backdrop_key

    try:
        db.session.commit()
        invalidate_settings_cache()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.settings"))

    flash("Appearance settings saved.", "success")
    return redirect(url_for("admin.settings"))


@admin.route("/settings/site", methods=["POST"])
@admin_required
def settings_site() -> ResponseReturnValue:
    """
    Update the site-level settings.

    Methods: POST
    POST: Updates the comments switch, the footer text, the two footer column
    switches, the page menu, the projects menu and the homepage selection.
    Validation is owned by
    `app.services.site_settings.validate_site_settings`.
    Requires: Admin authentication.
    Form params:
        comments_enabled: Checkbox — comments are accepted on the public site
        footer_text: Footer line (max 300 chars, plain text)
        footer_show_posts: Checkbox — show the "Latest from the blog" column
        footer_show_tags: Checkbox — show the "Browse by tag" column
        show_pages_in_menu: Checkbox — show the pages menu
        menu_pages: JSON array of page ids, in menu order
        show_projects_in_menu: Checkbox — show the projects menu
        projects_menu_label: Label of the projects menu entry
        homepage_kind: blog, page or project
        homepage_target_id: Id of the selected page or project
    """
    try:
        payload = validate_site_settings(request.form)
    except SiteSettingsValidationError as exc:
        for message in exc.messages:
            flash(message, "error")
        return redirect(url_for("admin.settings"))

    settings_obj = SiteSettings.get_instance()

    settings_obj.comments_enabled = payload.comments_enabled
    settings_obj.footer_text = payload.footer_text
    settings_obj.footer_show_posts = payload.footer_show_posts
    settings_obj.footer_show_tags = payload.footer_show_tags
    settings_obj.show_pages_in_menu = payload.show_pages_in_menu
    settings_obj.menu_pages = payload.menu_pages
    settings_obj.show_projects_in_menu = payload.show_projects_in_menu
    settings_obj.projects_menu_label = payload.projects_menu_label
    settings_obj.homepage_kind = payload.homepage_kind
    settings_obj.homepage_target_id = payload.homepage_target_id

    try:
        db.session.commit()
        invalidate_settings_cache()
        invalidate_footer_cache()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        flash("Database error occurred. Please try again.", "error")
        return redirect(url_for("admin.settings"))

    flash("Site settings saved.", "success")
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
    except (ThemeValidationError, ThemeParseFailure, ThemeLoadError) as e:
        errors.append(f"Invalid dark theme name: {e}")

    try:
        if registry.resolve(light_name) is None:
            errors.append(f"Light theme '{light_name}' not found in registry.")
    except (ThemeValidationError, ThemeParseFailure, ThemeLoadError) as e:
        errors.append(f"Invalid light theme name: {e}")

    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    try:
        loaded_dark = registry.load(dark_name)
        resolved_dark_name = loaded_dark.descriptor.canonical_name
        dark_css = to_legacy_css(loaded_dark.legacy_vars)
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
        light_css = to_legacy_css(loaded_light.legacy_vars)
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
