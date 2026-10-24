"""Centralized appearance service for Flask and Jinja integration.

The appearance service owns the two choices the theme system does not make:
the typefaces the site renders with and the large graphic behind the page.  It
mirrors :class:`app.themes.service.ThemeService`: one per-process instance,
a short settings cache, and a template ready context dict.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.appearance.backdrops import BackdropRegistry
from app.appearance.fonts import FontRegistry, font_stack
from app.appearance.model import (
    CATEGORY_MONO,
    CATEGORY_SANS,
    SOURCE_CUSTOM,
    BackdropDescriptor,
    FontFamily,
)

logger = logging.getLogger(__name__)

_SETTINGS_CACHE_TTL = 300  # seconds

DEFAULT_SANS = "inter"
DEFAULT_MONO = "jetbrains-mono"
DEFAULT_BACKDROP = "default"

_FALLBACK_TINT = "rgba(127, 127, 127, 0.14)"


def _font_format(url: str) -> str:
    return "woff2" if url.lower().endswith(".woff2") else "woff"


class AppearanceService:
    """Per-process appearance service owning the registries and the CSS."""

    def __init__(
        self,
        default_sans: str = DEFAULT_SANS,
        default_mono: str = DEFAULT_MONO,
        default_backdrop: str = DEFAULT_BACKDROP,
    ) -> None:
        self._default_sans = default_sans
        self._default_mono = default_mono
        self._default_backdrop = default_backdrop
        self._font_registry = FontRegistry()
        self._backdrop_registry = BackdropRegistry()
        self._settings_cache: dict[str, Any] | None = None
        self._settings_cache_time: float = 0.0

    def get_font_registry(self) -> FontRegistry:
        return self._font_registry

    def get_backdrop_registry(self) -> BackdropRegistry:
        return self._backdrop_registry

    def invalidate_registry(self) -> None:
        """Rescan the custom font and backdrop catalogs."""
        self._font_registry.invalidate()
        self._backdrop_registry.invalidate()

    def invalidate_settings_cache(self) -> None:
        self._settings_cache = None
        self._settings_cache_time = 0.0

    def get_context(self) -> dict[str, Any]:
        now = time.monotonic()
        if (
            self._settings_cache is not None
            and (now - self._settings_cache_time) < _SETTINGS_CACHE_TTL
        ):
            return self._settings_cache

        result = self._build_context()
        self._settings_cache = result
        self._settings_cache_time = now
        return result

    def _build_context(self) -> dict[str, Any]:
        from app.services.site_settings import read_site_settings

        try:
            settings = read_site_settings()
        except Exception:
            logger.exception("appearance service: error loading settings, using defaults")
            settings = None

        sans_key = getattr(settings, "font_sans", "") or self._default_sans
        mono_key = getattr(settings, "font_mono", "") or self._default_mono
        backdrop_value = getattr(settings, "backdrop", None)
        backdrop_key = self._default_backdrop if backdrop_value is None else backdrop_value

        sans = self._resolve_font(sans_key, CATEGORY_SANS, self._default_sans)
        mono = self._resolve_font(mono_key, CATEGORY_MONO, self._default_mono)
        backdrop = self._resolve_backdrop(backdrop_key)

        theme_vars = self._theme_vars()
        tint_dark = self._tint(theme_vars.get("dark", {}), dark=True)
        tint_light = self._tint(theme_vars.get("light", {}), dark=False)

        return {
            "appearance_css": self._build_css(sans, mono, backdrop, tint_dark, tint_light),
            "appearance_font_sans": sans.key,
            "appearance_font_mono": mono.key,
            "appearance_backdrop": backdrop.key if backdrop is not None else "",
            "appearance_backdrop_url": backdrop.url if backdrop is not None else "",
            "appearance_backdrop_tint_dark": tint_dark,
            "appearance_backdrop_tint_light": tint_light,
            "appearance_font_sans_stack": font_stack(sans),
            "appearance_font_mono_stack": font_stack(mono),
            "appearance_preload_fonts": self._preload_fonts(sans, mono),
        }

    @staticmethod
    def _preload_fonts(sans: FontFamily, mono: FontFamily) -> list[dict[str, str]]:
        preloads: list[dict[str, str]] = []
        for family in (sans, mono):
            url = family.preload_url
            if not url:
                continue
            path = url.split("?", 1)[0].split("#", 1)[0].lower()
            media = "font/woff2" if path.endswith(".woff2") else "font/woff"
            preloads.append({"url": url, "type": media})
        return preloads

    def _resolve_font(self, key: str, category: str, fallback: str) -> FontFamily:
        family = self._font_registry.resolve_for_slot(key, category)
        if family is not None:
            return family
        default = self._font_registry.resolve_for_slot(fallback, category)
        if default is not None:
            logger.warning("appearance: font %r unavailable, using %r", key, default.key)
            return default
        logger.warning("appearance: no %s font available", category)
        return FontFamily(
            key=fallback,
            label=fallback,
            category=category,
            source=SOURCE_CUSTOM,
            css_family=fallback,
        )

    def _resolve_backdrop(self, key: str) -> BackdropDescriptor | None:
        if not key:
            return None
        descriptor = self._backdrop_registry.resolve(key)
        if descriptor is not None:
            return descriptor
        logger.warning("appearance: backdrop %r unavailable", key)
        return None

    @staticmethod
    def _theme_vars() -> dict[str, dict[str, str]]:
        try:
            from app.themes.service import get_theme_service

            context = get_theme_service().get_context()
        except Exception:
            logger.exception("appearance service: theme context unavailable")
            return {}
        return {
            "dark": context.get("theme_dark_vars", {}) or {},
            "light": context.get("theme_light_vars", {}) or {},
        }

    @staticmethod
    def _tint(legacy_vars: dict[str, str], *, dark: bool) -> str:
        """A colour a little off the page background, kept deliberately faint."""
        from app.themes.colors import adjust_lightness, from_hex, mix

        bg_value = legacy_vars.get("bg")
        accent_value = legacy_vars.get("accent")
        if not bg_value or not accent_value:
            return _FALLBACK_TINT
        try:
            background = from_hex(bg_value).rgb
            accent = from_hex(accent_value).rgb
        except (TypeError, ValueError):
            return _FALLBACK_TINT
        tinted = mix(background, accent, 0.12)
        shifted = adjust_lightness(tinted, 1.15 if dark else 0.88)
        alpha = 0.16 if dark else 0.13
        return f"rgba({shifted.red}, {shifted.green}, {shifted.blue}, {alpha})"

    @staticmethod
    def _font_face_rule(family: FontFamily) -> str:
        return (
            "@font-face {\n"
            f"  font-family: '{family.css_family}';\n"
            "  font-style: normal;\n"
            "  font-weight: 100 900;\n"
            "  font-display: swap;\n"
            f'  src: url("{family.url}") format("{_font_format(family.url)}");\n'
            "}"
        )

    @staticmethod
    def _build_css(
        sans: FontFamily,
        mono: FontFamily,
        backdrop: BackdropDescriptor | None,
        tint_dark: str,
        tint_light: str,
    ) -> str:
        blocks: list[str] = []

        if sans.source == SOURCE_CUSTOM:
            blocks.append(AppearanceService._font_face_rule(sans))
        if mono.source == SOURCE_CUSTOM:
            blocks.append(AppearanceService._font_face_rule(mono))

        blocks.append(
            f":root {{\n  --font-sans: {font_stack(sans)};\n  --font-mono: {font_stack(mono)};\n}}"
        )

        if backdrop is None:
            blocks.append(":root {\n  --backdrop-tint: transparent;\n  --backdrop-image: none;\n}")
            return "\n\n".join(blocks)

        blocks.append(f':root,\n[data-color-scheme="dark"] {{\n  --backdrop-tint: {tint_dark};\n}}')
        blocks.append(f'[data-color-scheme="light"] {{\n  --backdrop-tint: {tint_light};\n}}')
        blocks.append(f':root {{\n  --backdrop-image: url("{backdrop.url}");\n}}')
        return "\n\n".join(blocks)


def init_appearance_service(
    default_sans: str = DEFAULT_SANS,
    default_mono: str = DEFAULT_MONO,
    default_backdrop: str = DEFAULT_BACKDROP,
    app: Any = None,
) -> AppearanceService:
    service = AppearanceService(
        default_sans=default_sans,
        default_mono=default_mono,
        default_backdrop=default_backdrop,
    )
    if app is not None:
        app.extensions["appearance_service"] = service
    return service


def get_appearance_service() -> AppearanceService:
    from flask import current_app

    try:
        return current_app.extensions["appearance_service"]
    except (RuntimeError, KeyError):
        pass
    return AppearanceService()


__all__ = [
    "AppearanceService",
    "DEFAULT_BACKDROP",
    "DEFAULT_MONO",
    "DEFAULT_SANS",
    "get_appearance_service",
    "init_appearance_service",
]
