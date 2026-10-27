"""Centralized theme service for Flask and Jinja integration.

Provides a single per-process ``ThemeRegistry`` and resolves effective
dark/light theme names from ``SiteSettings``.  Exposes a template-ready
context dict consumed by the ``inject_theme`` context processor.
"""

from __future__ import annotations

import logging
import time
import threading
from pathlib import Path
from typing import Any

from app.themes.registry import (
    LoadedTheme,
    ThemeNotFoundError,
    ThemeParseFailure,
    ThemeLoadError,
    ThemeRegistry,
)

logger = logging.getLogger(__name__)

_SETTINGS_CACHE_TTL = 300  # seconds


class ThemeService:
    """Per-process theme service owning the registry and fallback logic.

    Thread-safe for concurrent WSGI reads.  The registry is lazily
    initialised on first access so that module import never touches the
    database.
    """

    def __init__(
        self,
        default_dark: str = "Catppuccin Mocha",
        default_light: str = "Catppuccin Latte",
        default_scheme: str = "system",
        external_root: Path | None = None,
    ) -> None:
        self._default_dark = default_dark
        self._default_light = default_light
        self._default_scheme = default_scheme
        self._external_root = external_root
        self._registry: ThemeRegistry | None = None
        self._registry_lock = threading.Lock()
        self._settings_cache: dict[str, Any] | None = None
        self._settings_cache_time: float = 0.0

    def _ensure_registry(self) -> ThemeRegistry:
        if self._registry is None:
            with self._registry_lock:
                if self._registry is None:
                    self._registry = ThemeRegistry(
                        external_root=self._external_root,
                        default_theme=self._default_dark,
                    )
        return self._registry

    def get_registry(self) -> ThemeRegistry:
        return self._ensure_registry()

    def invalidate_registry(self, name: str | None = None) -> None:
        registry = self._ensure_registry()
        registry.invalidate(name)

    def refresh_registry(self) -> None:
        with self._registry_lock:
            self._registry = ThemeRegistry(
                external_root=self._external_root,
                default_theme=self._default_dark,
            )

    def _load_with_fallback(self, name: str) -> LoadedTheme:
        registry = self._ensure_registry()
        try:
            return registry.load(name)
        except (ThemeNotFoundError, ThemeParseFailure, ThemeLoadError):
            return registry.get_fallback(name)

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

    def invalidate_settings_cache(self) -> None:
        self._settings_cache = None
        self._settings_cache_time = 0.0

    def _build_context(self) -> dict[str, Any]:
        try:
            return self._build_context_from_db()
        except Exception:
            logger.exception("theme service: error loading settings, using emergency fallback")
            return self._emergency_context()

    def _build_context_from_db(self) -> dict[str, Any]:
        from app.services.site_settings import read_site_settings
        from app.services.theme_settings import (
            get_effective_theme_names,
            validate_theme_settings,
        )
        from app.config import (
            THEME_DEFAULT_DARK,
            THEME_DEFAULT_LIGHT,
            THEME_DEFAULT_SCHEME,
        )
        from sqlalchemy.exc import OperationalError

        try:
            settings = read_site_settings()
        except OperationalError:
            logger.exception("theme service: database error loading settings")
            return self._emergency_context()

        if settings is None:
            return self._build_for_themes(
                self._default_dark,
                self._default_light,
                self._default_scheme,
                custom_css_enabled=False,
                custom_css="",
                logo_text="",
            )

        dark_name, light_name, scheme = get_effective_theme_names(
            settings,
            {
                "THEME_DARK_NAME": THEME_DEFAULT_DARK,
                "THEME_LIGHT_NAME": THEME_DEFAULT_LIGHT,
                "THEME_DEFAULT_SCHEME": THEME_DEFAULT_SCHEME,
            },
        )

        registry = self._ensure_registry()
        validation = validate_theme_settings(dark_name, light_name, scheme, registry)
        dark_name = validation.dark_name
        light_name = validation.light_name
        scheme = validation.scheme

        return self._build_for_themes(
            dark_name,
            light_name,
            scheme,
            custom_css_enabled=settings.custom_css_enabled,
            custom_css=settings.custom_css if settings.custom_css_enabled else "",
            logo_text=settings.logo_text or "",
        )

    def _build_for_themes(
        self,
        dark_name: str,
        light_name: str,
        scheme: str,
        *,
        custom_css_enabled: bool,
        custom_css: str,
        logo_text: str,
    ) -> dict[str, Any]:
        dark = self._load_with_fallback(dark_name)
        light = self._load_with_fallback(light_name)
        warnings: list[str] = list(dark.descriptor.warnings) + list(light.descriptor.warnings)

        dark_legacy = dark.legacy_vars
        light_legacy = light.legacy_vars

        return {
            "theme_dark_name": dark_name,
            "theme_light_name": light_name,
            "theme_default_scheme": scheme,
            "theme_dark_vars": dark_legacy,
            "theme_light_vars": light_legacy,
            "theme_dark_css": self._serialize_vars(dark_legacy),
            "theme_light_css": self._serialize_vars(light_legacy),
            "theme_warnings": warnings,
            "custom_css_enabled": custom_css_enabled,
            "custom_css": custom_css,
            "logo_text": logo_text,
            "theme_vars": dark_legacy,
        }

    def _emergency_context(self) -> dict[str, Any]:
        registry = self._ensure_registry()
        fallback = registry.get_fallback()
        return {
            "theme_dark_name": "emergency-default",
            "theme_light_name": "emergency-default",
            "theme_default_scheme": "dark",
            "theme_dark_vars": fallback.legacy_vars,
            "theme_light_vars": fallback.legacy_vars,
            "theme_dark_css": self._serialize_vars(fallback.legacy_vars),
            "theme_light_css": self._serialize_vars(fallback.legacy_vars),
            "theme_warnings": ["emergency fallback activated"],
            "custom_css_enabled": False,
            "custom_css": "",
            "logo_text": "",
            "theme_vars": fallback.legacy_vars,
        }

    @staticmethod
    def _serialize_vars(vars_dict: dict[str, str]) -> str:
        from app.themes.translate import to_legacy_css

        return to_legacy_css(vars_dict)


def init_theme_service(
    default_dark: str = "Catppuccin Mocha",
    default_light: str = "Catppuccin Latte",
    default_scheme: str = "system",
    external_root: Path | None = None,
    app: Any = None,
) -> ThemeService:
    service = ThemeService(
        default_dark=default_dark,
        default_light=default_light,
        default_scheme=default_scheme,
        external_root=external_root,
    )
    if app is not None:
        app.extensions["theme_service"] = service
    return service


def get_theme_service() -> ThemeService:
    from flask import current_app

    try:
        return current_app.extensions["theme_service"]
    except (RuntimeError, KeyError):
        pass
    return ThemeService()


__all__ = [
    "ThemeService",
    "get_theme_service",
    "init_theme_service",
]
