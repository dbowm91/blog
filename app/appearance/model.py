"""Typed records for the appearance layer: fonts and page backdrops.

The appearance layer owns everything the theme does not: which typefaces the
site renders with and which large graphic sits behind the page.  Colour stays
with the theme system, so these records carry names, sources and file
locations rather than palettes.
"""

from __future__ import annotations

from dataclasses import dataclass

SOURCE_BUNDLED = "bundled"
SOURCE_CUSTOM = "custom"

CATEGORY_SANS = "sans"
CATEGORY_MONO = "mono"

CUSTOM_KEY = "custom"


@dataclass(frozen=True, slots=True)
class FontFamily:
    """A selectable typeface.

    ``css_family`` is the family name used in ``font-family`` declarations.
    Bundled families are declared with ``@font-face`` rules in
    ``app/static/css/base.css``; custom families get a runtime rule emitted by
    the appearance service.
    """

    key: str
    label: str
    category: str
    source: str
    css_family: str
    files: tuple[str, ...] = ()
    url: str = ""

    @property
    def is_custom(self) -> bool:
        return self.source == SOURCE_CUSTOM

    @property
    def primary_file(self) -> str:
        """The file that carries the regular weight of the family."""
        for filename in self.files:
            if "400" in filename:
                return filename
        return self.files[0] if self.files else ""

    @property
    def preload_url(self) -> str:
        """The URL the browser should preload for this family."""
        if self.source == SOURCE_CUSTOM:
            return self.url
        from app.vite import vite_asset

        return vite_asset(f"fonts/{self.primary_file}")


@dataclass(frozen=True, slots=True)
class BackdropDescriptor:
    """A selectable page backdrop graphic."""

    key: str
    label: str
    source: str
    url: str

    @property
    def is_custom(self) -> bool:
        return self.source == SOURCE_CUSTOM


__all__ = [
    "BackdropDescriptor",
    "CATEGORY_MONO",
    "CATEGORY_SANS",
    "CUSTOM_KEY",
    "FontFamily",
    "SOURCE_BUNDLED",
    "SOURCE_CUSTOM",
]
