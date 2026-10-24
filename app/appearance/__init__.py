"""Appearance layer: font families and page backdrops.

The appearance layer sits beside the theme layer.  The theme owns colour; the
appearance layer owns typefaces and the large graphic behind the page.  Both
follow the same shape: a registry of what can be chosen, a per-process
service that resolves the choice, settings that persist it and an admin page
that changes it.
"""

from app.appearance.backdrops import BackdropRegistry
from app.appearance.fonts import FontRegistry, font_stack
from app.appearance.model import (
    CATEGORY_MONO,
    CATEGORY_SANS,
    SOURCE_BUNDLED,
    SOURCE_CUSTOM,
    BackdropDescriptor,
    FontFamily,
)
from app.appearance.service import (
    AppearanceService,
    get_appearance_service,
    init_appearance_service,
)

__all__ = [
    "AppearanceService",
    "BackdropDescriptor",
    "BackdropRegistry",
    "CATEGORY_MONO",
    "CATEGORY_SANS",
    "FontFamily",
    "FontRegistry",
    "SOURCE_BUNDLED",
    "SOURCE_CUSTOM",
    "font_stack",
    "get_appearance_service",
    "init_appearance_service",
]
