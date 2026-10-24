"""Validation for the appearance settings form.

The appearance form owns three choices: the sans font, the monospace font and
the page backdrop.  Each choice is either a catalog key or the
:data:`CUSTOM_OPTION` sentinel, which asks the route to store an upload.  The
parsing and the resolution live here so the route never interprets raw form
values on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from app.appearance.backdrops import BackdropRegistry
    from app.appearance.fonts import FontRegistry

CUSTOM_OPTION = "__custom__"

NONE_OPTION = ""

MAX_KEY_LENGTH = 128


@dataclass(frozen=True)
class AppearanceSettingsPayload:
    font_sans: str
    font_mono: str
    backdrop: str

    @property
    def wants_custom_sans(self) -> bool:
        return self.font_sans == CUSTOM_OPTION

    @property
    def wants_custom_mono(self) -> bool:
        return self.font_mono == CUSTOM_OPTION

    @property
    def wants_custom_backdrop(self) -> bool:
        return self.backdrop == CUSTOM_OPTION


def validate_appearance_settings(form: Mapping[str, str]) -> AppearanceSettingsPayload:
    """Turn the raw appearance form into a validated payload."""
    font_sans = (form.get("font_sans") or "").strip()[:MAX_KEY_LENGTH]
    font_mono = (form.get("font_mono") or "").strip()[:MAX_KEY_LENGTH]
    backdrop = (form.get("backdrop") or "").strip()[:MAX_KEY_LENGTH]
    return AppearanceSettingsPayload(
        font_sans=font_sans,
        font_mono=font_mono,
        backdrop=backdrop,
    )


def resolve_font_key(
    selected: str,
    uploaded_filename: str | None,
    current_value: str,
    registry: "FontRegistry",
    category: str,
    label: str,
) -> tuple[str | None, str | None]:
    """Resolve the key stored for one font slot.

    Returns ``(key, None)`` on success and ``(None, message)`` when the
    selection cannot be honoured.
    """
    if selected == CUSTOM_OPTION:
        if uploaded_filename:
            if registry.resolve(uploaded_filename) is None:
                return None, f"The uploaded {label} font could not be found in storage."
            return uploaded_filename, None
        current = registry.resolve(current_value) if current_value else None
        if current is not None and current.is_custom:
            return current.key, None
        return None, f"Upload a woff2 file to use a custom {label} font."

    family = registry.resolve_for_slot(selected, category)
    if family is None:
        return None, f"'{selected}' is not an available {label} font."
    return family.key, None


def resolve_backdrop_key(
    selected: str,
    uploaded_filename: str | None,
    current_value: str,
    registry: "BackdropRegistry",
) -> tuple[str | None, str | None]:
    """Resolve the key stored for the page backdrop."""
    if selected == CUSTOM_OPTION:
        if uploaded_filename:
            if registry.resolve(uploaded_filename) is None:
                return None, "The uploaded backdrop could not be found in storage."
            return uploaded_filename, None
        current = registry.resolve(current_value) if current_value else None
        if current is not None and current.is_custom:
            return current.key, None
        return None, "Upload an SVG file to use a custom backdrop."

    if selected == NONE_OPTION:
        return NONE_OPTION, None

    descriptor = registry.resolve(selected)
    if descriptor is None:
        return None, f"'{selected}' is not an available backdrop."
    return descriptor.key, None


__all__ = [
    "AppearanceSettingsPayload",
    "CUSTOM_OPTION",
    "NONE_OPTION",
    "resolve_backdrop_key",
    "resolve_font_key",
    "validate_appearance_settings",
]
