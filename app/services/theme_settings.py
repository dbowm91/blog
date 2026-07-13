from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.models import SiteSettings

logger = logging.getLogger(__name__)

LEGACY_PRESET_MAP: dict[str, str] = {
    "github-dark": "Catppuccin Mocha",
    "github-light": "Catppuccin Latte",
    "solarized-dark": "Solarized Dark",
    "monokai": "Sonokai",
}

VALID_SCHEMES = ("system", "dark", "light")

_DEFAULT_DARK = "Catppuccin Mocha"
_DEFAULT_LIGHT = "Catppuccin Latte"
_DEFAULT_SCHEME = "system"


@dataclass
class ThemeSettingsValidation:
    dark_name: str
    light_name: str
    scheme: str
    warnings: list[str] = field(default_factory=list)


def validate_theme_settings(
    dark_name: str,
    light_name: str,
    scheme: str,
    registry: object | None = None,
) -> ThemeSettingsValidation:
    warnings: list[str] = []

    if scheme not in VALID_SCHEMES:
        warnings.append(f"invalid scheme {scheme!r}, falling back to {_DEFAULT_SCHEME!r}")
        scheme = _DEFAULT_SCHEME

    effective_dark = dark_name or _DEFAULT_DARK
    effective_light = light_name or _DEFAULT_LIGHT

    if registry is not None and hasattr(registry, "resolve"):
        try:
            if registry.resolve(effective_dark) is None:
                warnings.append(
                    f"dark theme {effective_dark!r} not found in registry, "
                    f"falling back to {_DEFAULT_DARK!r}"
                )
                effective_dark = _DEFAULT_DARK
        except Exception:
            warnings.append(
                f"failed to validate dark theme {effective_dark!r}, "
                f"falling back to {_DEFAULT_DARK!r}"
            )
            effective_dark = _DEFAULT_DARK

        try:
            if registry.resolve(effective_light) is None:
                warnings.append(
                    f"light theme {effective_light!r} not found in registry, "
                    f"falling back to {_DEFAULT_LIGHT!r}"
                )
                effective_light = _DEFAULT_LIGHT
        except Exception:
            warnings.append(
                f"failed to validate light theme {effective_light!r}, "
                f"falling back to {_DEFAULT_LIGHT!r}"
            )
            effective_light = _DEFAULT_LIGHT

    for w in warnings:
        logger.warning("theme_settings: %s", w)

    return ThemeSettingsValidation(
        dark_name=effective_dark,
        light_name=effective_light,
        scheme=scheme,
        warnings=warnings,
    )


def migrate_legacy_preset(preset_key: str) -> str:
    return LEGACY_PRESET_MAP.get(preset_key, preset_key)


def get_effective_theme_names(
    settings: SiteSettings,
    config_defaults: dict[str, str],
) -> tuple[str, str, str]:
    config_dark = config_defaults.get("THEME_DARK_NAME", _DEFAULT_DARK)
    config_light = config_defaults.get("THEME_LIGHT_NAME", _DEFAULT_LIGHT)
    config_scheme = config_defaults.get("THEME_DEFAULT_SCHEME", _DEFAULT_SCHEME)

    dark_name = settings.theme_dark_name or config_dark or _DEFAULT_DARK
    light_name = settings.theme_light_name or config_light or _DEFAULT_LIGHT
    scheme = settings.theme_default_scheme or config_scheme or _DEFAULT_SCHEME

    return dark_name, light_name, scheme
