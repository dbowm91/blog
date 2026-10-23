from __future__ import annotations

from dataclasses import dataclass

from app.themes.colors import (
    RGB,
    RGBA,
    alpha_composite,
    contrast_ratio,
    is_dark_background,
    shift_lightness,
    to_css,
    to_hex,
)
from app.themes.diagnostics import (
    TranslationDiagnostics,
    build_provenance,
    check_blog_theme_contrast,
)
from app.themes.halloy import HalloyTheme
from app.themes.model import ALIASES, CSS_VARS, BlogTheme


@dataclass(frozen=True, slots=True)
class ThemeTranslationResult:
    theme: BlogTheme
    is_dark: bool
    diagnostics: TranslationDiagnostics
    source_name: str


def _resolve_bg(color: RGB | RGBA) -> RGB:
    if isinstance(color, RGBA):
        return alpha_composite(color, RGB(255, 255, 255))
    return color


def _derive_accent_dim(accent: RGB, surface: RGB, is_dark: bool) -> RGBA:
    return RGBA(accent.red, accent.green, accent.blue, 0.10)


def _derive_state_bg(fg: RGB, surface: RGB) -> RGBA:
    return RGBA(fg.red, fg.green, fg.blue, 0.15)


def _derive_surface_hover(surface: RGB, is_dark: bool) -> RGB:
    if is_dark:
        return shift_lightness(surface, 0.06)
    return shift_lightness(surface, -0.06)


def _derive_surface_active(surface: RGB, is_dark: bool) -> RGB:
    if is_dark:
        return shift_lightness(surface, 0.12)
    return shift_lightness(surface, -0.12)


def _derive_accent_hover(accent: RGB, is_dark: bool) -> RGB:
    if is_dark:
        return shift_lightness(accent, 0.10)
    return shift_lightness(accent, -0.10)


def _derive_strong_border(border: RGB, is_dark: bool) -> RGB:
    if is_dark:
        return shift_lightness(border, 0.10)
    return shift_lightness(border, -0.10)


def _select_foreground_on_accent(accent: RGB) -> RGB:
    white = RGB(255, 255, 255)
    black = RGB(0, 0, 0)
    ratio_white = contrast_ratio(white, accent)
    ratio_black = contrast_ratio(black, accent)
    if ratio_white >= 4.5:
        return white
    if ratio_black >= 4.5:
        return black
    if ratio_white >= ratio_black:
        return white
    return black


def _select_foreground_on_state(state_fg: RGB, page_bg: RGB) -> RGB:
    state_bg_rgba = _derive_state_bg(state_fg, page_bg)
    composited = alpha_composite(state_bg_rgba, page_bg)
    return _select_foreground_on_accent(composited)


def translate_halloy_theme(theme: HalloyTheme) -> ThemeTranslationResult:
    general = theme.general
    text = theme.text
    buffer = theme.buffer

    bg_page = _resolve_bg(general.background)
    surface_default = _resolve_bg(buffer.background)
    surface_elevated = _resolve_bg(buffer.background_title_bar)
    is_dark = is_dark_background(general.background)

    if is_dark:
        shadow_color = RGBA(0, 0, 0, 0.35)
    else:
        shadow_color = RGBA(0, 0, 0, 0.12)

    text_primary = _resolve_bg(text.primary)
    text_secondary = _resolve_bg(buffer.topic)
    text_muted = _resolve_bg(text.secondary)
    text_dim = _resolve_bg(buffer.timestamp)
    text_link = _resolve_bg(buffer.url)
    accent = _resolve_bg(text.tertiary)
    success_fg = _resolve_bg(text.success)
    error_fg = _resolve_bg(text.error)
    input_bg = _resolve_bg(buffer.background_text_input)
    code_bg = _resolve_bg(buffer.background_text_input)
    selection_bg = _resolve_bg(buffer.selection)
    border_primary = _resolve_bg(general.border)
    border_subtle = _resolve_bg(general.horizontal_rule)

    text_on_accent = _select_foreground_on_accent(accent)
    text_on_success = _select_foreground_on_accent(
        alpha_composite(_derive_state_bg(success_fg, bg_page), bg_page)
    )
    text_on_error = _select_foreground_on_accent(
        alpha_composite(_derive_state_bg(error_fg, bg_page), bg_page)
    )

    warning_bg_rgb = alpha_composite(RGBA(210, 153, 34, 0.15), bg_page)
    info_bg_rgb = alpha_composite(RGBA(163, 113, 247, 0.15), bg_page)
    warning_fg = _select_foreground_on_accent(warning_bg_rgb)
    info_fg = _select_foreground_on_accent(info_bg_rgb)
    text_on_warning = _select_foreground_on_accent(warning_bg_rgb)
    text_on_info = _select_foreground_on_accent(info_bg_rgb)

    blog_theme = BlogTheme(
        bg_page=bg_page,
        surface_default=surface_default,
        surface_elevated=surface_elevated,
        surface_hover=_derive_surface_hover(surface_default, is_dark),
        surface_active=_derive_surface_active(surface_default, is_dark),
        navbar_bg=RGBA(bg_page.red, bg_page.green, bg_page.blue, 0.85),
        overlay_bg=RGBA(0, 0, 0, 0.5),
        border_primary=border_primary,
        border_subtle=border_subtle,
        border_strong=_derive_strong_border(border_primary, is_dark),
        border_focus=accent,
        navbar_border=border_primary,
        text_primary=text_primary,
        text_secondary=text_secondary,
        text_muted=text_muted,
        text_dim=text_dim,
        text_on_accent=text_on_accent,
        text_on_success=text_on_success,
        text_on_error=text_on_error,
        text_on_warning=text_on_warning,
        text_on_info=text_on_info,
        text_link=text_link,
        text_link_hover=_derive_accent_hover(accent, is_dark),
        accent=accent,
        accent_hover=_derive_accent_hover(accent, is_dark),
        accent_dim=_derive_accent_dim(accent, surface_default, is_dark),
        accent_link=accent,
        accent_focus_ring=accent,
        success_fg=success_fg,
        success_bg=alpha_composite(_derive_state_bg(success_fg, bg_page), bg_page),
        error_fg=error_fg,
        error_bg=alpha_composite(_derive_state_bg(error_fg, bg_page), bg_page),
        warning_fg=warning_fg,
        warning_bg=warning_bg_rgb,
        info_fg=info_fg,
        info_bg=info_bg_rgb,
        input_bg=input_bg,
        input_border=border_primary,
        input_text=text_primary,
        code_bg=code_bg,
        code_border=border_subtle,
        code_text=text_primary,
        selection_bg=selection_bg,
        navbar_text=text_primary,
        navbar_text_muted=text_muted,
        shadow_color=shadow_color,
        noscript_bg=RGB(0x3B, 0x2E, 0x00),
        noscript_text=RGB(0xD4, 0xA0, 0x17),
        coral=RGB(0xF7, 0x81, 0x66),
        coral_dim=RGBA(247, 129, 102, 0.15),
    )

    contrast_warnings = check_blog_theme_contrast(blog_theme)

    provenance_mapping = {
        "bg_page": "general.background",
        "surface_default": "buffer.background",
        "surface_elevated": "buffer.background_title_bar",
        "border_primary": "general.border",
        "border_subtle": "general.horizontal_rule",
        "text_primary": "text.primary",
        "text_secondary": "buffer.topic",
        "text_muted": "text.secondary",
        "text_dim": "buffer.timestamp",
        "text_link": "buffer.url",
        "accent": "text.tertiary",
        "success_fg": "text.success",
        "error_fg": "text.error",
        "input_bg": "buffer.background_text_input",
        "code_bg": "buffer.background_text_input",
        "selection_bg": "buffer.selection",
    }
    provenance = build_provenance(provenance_mapping)

    diagnostics = TranslationDiagnostics(
        warnings=contrast_warnings,
        provenance=provenance,
        is_dark=is_dark,
        source_name=theme.source_name,
    )

    return ThemeTranslationResult(
        theme=blog_theme,
        is_dark=is_dark,
        diagnostics=diagnostics,
        source_name=theme.source_name,
    )


def _serialize_color(value: RGB | RGBA) -> str:
    if isinstance(value, RGBA) and value.alpha < 1.0:
        return to_css(value.rgb, alpha=value.alpha)
    if isinstance(value, RGBA):
        return to_hex(value.rgb)
    return to_hex(value)


def to_css_variables(theme: BlogTheme, selector: str = ":root") -> str:
    lines = [f"{selector} {{"]
    for field_name, css_var in CSS_VARS.items():
        value = getattr(theme, field_name)
        lines.append(f"  {css_var}: {_serialize_color(value)};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def to_theme_vars(theme: BlogTheme) -> dict[str, str]:
    result: dict[str, str] = {}
    for field_name, css_var in CSS_VARS.items():
        value = getattr(theme, field_name)
        result[css_var] = _serialize_color(value)
    return result


def to_legacy_vars(theme: BlogTheme) -> dict[str, str]:
    theme_vars = to_theme_vars(theme)
    result: dict[str, str] = {}
    for legacy_key, css_var in ALIASES.items():
        if css_var in theme_vars:
            result[legacy_key] = theme_vars[css_var]
    return result


def to_legacy_css(legacy_vars: dict[str, str]) -> str:
    """Serialize legacy alias vars into CSS declaration lines.

    These are the ``--bg`` / ``--text`` / ``--accent`` names the stylesheets
    actually consume, as opposed to the ``--blog-*`` semantic names emitted by
    :func:`to_css_variables`.
    """
    return "\n".join(f"  --{key}: {value};" for key, value in legacy_vars.items() if key != "name")
