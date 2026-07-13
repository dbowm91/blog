from __future__ import annotations

from dataclasses import dataclass

from app.themes.colors import RGB, RGBA, from_hex

CSS_VARS: dict[str, str] = {
    "bg_page": "--blog-bg-page",
    "surface_default": "--blog-surface-default",
    "surface_elevated": "--blog-surface-elevated",
    "surface_hover": "--blog-surface-hover",
    "surface_active": "--blog-surface-active",
    "navbar_bg": "--blog-navbar-bg",
    "overlay_bg": "--blog-overlay-bg",
    "border_primary": "--blog-border-primary",
    "border_subtle": "--blog-border-subtle",
    "border_strong": "--blog-border-strong",
    "border_focus": "--blog-border-focus",
    "navbar_border": "--blog-navbar-border",
    "text_primary": "--blog-text-primary",
    "text_secondary": "--blog-text-secondary",
    "text_muted": "--blog-text-muted",
    "text_dim": "--blog-text-dim",
    "text_on_accent": "--blog-text-on-accent",
    "text_on_success": "--blog-text-on-success",
    "text_on_error": "--blog-text-on-error",
    "text_on_warning": "--blog-text-on-warning",
    "text_on_info": "--blog-text-on-info",
    "text_link": "--blog-text-link",
    "text_link_hover": "--blog-text-link-hover",
    "accent": "--blog-accent",
    "accent_hover": "--blog-accent-hover",
    "accent_dim": "--blog-accent-dim",
    "accent_link": "--blog-accent-link",
    "accent_focus_ring": "--blog-accent-focus-ring",
    "success_fg": "--blog-success-fg",
    "success_bg": "--blog-success-bg",
    "error_fg": "--blog-error-fg",
    "error_bg": "--blog-error-bg",
    "warning_fg": "--blog-warning-fg",
    "warning_bg": "--blog-warning-bg",
    "info_fg": "--blog-info-fg",
    "info_bg": "--blog-info-bg",
    "input_bg": "--blog-input-bg",
    "input_border": "--blog-input-border",
    "input_text": "--blog-input-text",
    "code_bg": "--blog-code-bg",
    "code_border": "--blog-code-border",
    "code_text": "--blog-code-text",
    "selection_bg": "--blog-selection-bg",
    "navbar_text": "--blog-navbar-text",
    "navbar_text_muted": "--blog-navbar-text-muted",
    "shadow_color": "--blog-shadow-color",
    "noscript_bg": "--blog-noscript-bg",
    "noscript_text": "--blog-noscript-text",
    "coral": "--blog-coral",
    "coral_dim": "--blog-coral-dim",
}

ALIASES: dict[str, str] = {
    "bg": "--blog-bg-page",
    "bg-surface": "--blog-surface-default",
    "bg-elevated": "--blog-surface-elevated",
    "border": "--blog-border-primary",
    "text": "--blog-text-primary",
    "text-muted": "--blog-text-muted",
    "text-dim": "--blog-text-dim",
    "text-dim-strong": "--blog-text-dim",
    "text-secondary": "--blog-text-secondary",
    "accent": "--blog-accent",
    "accent-hover": "--blog-accent-hover",
    "accent-dim": "--blog-accent-dim",
    "green": "--blog-success-fg",
    "green-dim": "--blog-success-bg",
    "red": "--blog-error-fg",
    "red-dim": "--blog-error-bg",
    "yellow": "--blog-warning-fg",
    "purple": "--blog-info-fg",
    "purple-dim": "--blog-info-bg",
    "coral": "--blog-coral",
    "coral-dim": "--blog-coral-dim",
    "amber": "--blog-info-fg",
    "amber-dim": "--blog-warning-bg",
    "bg-hover": "--blog-surface-hover",
    "noscript-bg": "--blog-noscript-bg",
    "noscript-text": "--blog-noscript-text",
}


@dataclass(frozen=True, slots=True)
class BlogTheme:
    bg_page: RGB
    surface_default: RGB
    surface_elevated: RGB
    surface_hover: RGB
    surface_active: RGB
    navbar_bg: RGBA
    overlay_bg: RGBA
    border_primary: RGB
    border_subtle: RGB
    border_strong: RGB
    border_focus: RGB
    navbar_border: RGB
    text_primary: RGB
    text_secondary: RGB
    text_muted: RGB
    text_dim: RGB
    text_on_accent: RGB
    text_on_success: RGB
    text_on_error: RGB
    text_on_warning: RGB
    text_on_info: RGB
    text_link: RGB
    text_link_hover: RGB
    accent: RGB
    accent_hover: RGB
    accent_dim: RGBA
    accent_link: RGB
    accent_focus_ring: RGB
    success_fg: RGB
    success_bg: RGBA
    error_fg: RGB
    error_bg: RGBA
    warning_fg: RGB
    warning_bg: RGBA
    info_fg: RGB
    info_bg: RGBA
    input_bg: RGB
    input_border: RGB
    input_text: RGB
    code_bg: RGB
    code_border: RGB
    code_text: RGB
    selection_bg: RGB
    navbar_text: RGB
    navbar_text_muted: RGB
    shadow_color: RGBA
    noscript_bg: RGB
    noscript_text: RGB
    coral: RGB
    coral_dim: RGBA


def _rgb(hex_str: str) -> RGB:
    return from_hex(hex_str).rgb


EMERGENCY_DEFAULT = BlogTheme(
    bg_page=_rgb("#0d1117"),
    surface_default=_rgb("#161b22"),
    surface_elevated=_rgb("#1c2128"),
    surface_hover=_rgb("#21262d"),
    surface_active=_rgb("#161b22"),
    navbar_bg=RGBA(13, 17, 23, 0.85),
    overlay_bg=RGBA(0, 0, 0, 0.5),
    border_primary=_rgb("#30363d"),
    border_subtle=_rgb("#30363d"),
    border_strong=_rgb("#484f58"),
    border_focus=_rgb("#58a6ff"),
    navbar_border=_rgb("#30363d"),
    text_primary=_rgb("#e6edf3"),
    text_secondary=_rgb("#c9d1d9"),
    text_muted=_rgb("#8b949e"),
    text_dim=_rgb("#7d8590"),
    text_on_accent=_rgb("#ffffff"),
    text_on_success=_rgb("#ffffff"),
    text_on_error=_rgb("#ffffff"),
    text_on_warning=_rgb("#000000"),
    text_on_info=_rgb("#000000"),
    text_link=_rgb("#58a6ff"),
    text_link_hover=_rgb("#79c0ff"),
    accent=_rgb("#58a6ff"),
    accent_hover=_rgb("#79c0ff"),
    accent_dim=RGBA(88, 166, 255, 0.1),
    accent_link=_rgb("#58a6ff"),
    accent_focus_ring=_rgb("#58a6ff"),
    success_fg=_rgb("#3fb950"),
    success_bg=RGBA(63, 185, 80, 0.15),
    error_fg=_rgb("#f85149"),
    error_bg=RGBA(248, 81, 73, 0.15),
    warning_fg=_rgb("#d29922"),
    warning_bg=RGBA(210, 153, 34, 0.15),
    info_fg=_rgb("#a371f7"),
    info_bg=RGBA(163, 113, 247, 0.15),
    input_bg=_rgb("#0d1117"),
    input_border=_rgb("#30363d"),
    input_text=_rgb("#e6edf3"),
    code_bg=_rgb("#161b22"),
    code_border=_rgb("#30363d"),
    code_text=_rgb("#e6edf3"),
    selection_bg=_rgb("#30363d"),
    navbar_text=_rgb("#e6edf3"),
    navbar_text_muted=_rgb("#8b949e"),
    shadow_color=RGBA(0, 0, 0, 0.15),
    noscript_bg=_rgb("#3b2e00"),
    noscript_text=_rgb("#d4a017"),
    coral=_rgb("#f78166"),
    coral_dim=RGBA(247, 129, 102, 0.15),
)
