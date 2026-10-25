"""Font registry: bundled self-hosted families plus operator uploads.

The registry mirrors the theme registry: it discovers a catalog, resolves a
stored key to a family and reports where each family came from.  Bundled
families are declared with ``@font-face`` rules in
``app/static/css/base.css``; custom families are declared at runtime by the
appearance service.
"""

from __future__ import annotations

import logging
from typing import Any

from app.appearance.model import (
    CATEGORY_MONO,
    CATEGORY_SANS,
    SOURCE_BUNDLED,
    SOURCE_CUSTOM,
    FontFamily,
)

logger = logging.getLogger(__name__)

CUSTOM_FONT_PREFIX = "custom-font-"

SANS_STACK: tuple[str, ...] = ("Inter", "-apple-system", "BlinkMacSystemFont", "sans-serif")
MONO_STACK: tuple[str, ...] = ("JetBrains Mono", "Fira Code", "monospace")


def _bundled(
    key: str,
    label: str,
    category: str,
    css_family: str,
    files: tuple[str, ...],
) -> FontFamily:
    return FontFamily(
        key=key,
        label=label,
        category=category,
        source=SOURCE_BUNDLED,
        css_family=css_family,
        files=files,
    )


BUNDLED_FONTS: tuple[FontFamily, ...] = (
    _bundled(
        "inter",
        "Inter",
        CATEGORY_SANS,
        "Inter",
        (
            "inter-300-latin.woff2",
            "inter-400-latin.woff2",
            "inter-500-latin.woff2",
            "inter-600-latin.woff2",
            "inter-700-latin.woff2",
        ),
    ),
    _bundled(
        "ibm-plex-sans",
        "IBM Plex Sans",
        CATEGORY_SANS,
        "IBM Plex Sans",
        ("ibm-plex-sans-latin.woff2",),
    ),
    _bundled(
        "jetbrains-mono",
        "JetBrains Mono",
        CATEGORY_MONO,
        "JetBrains Mono",
        ("jetbrains-mono-400-latin.woff2", "jetbrains-mono-500-latin.woff2"),
    ),
    _bundled(
        "ibm-plex-mono",
        "IBM Plex Mono",
        CATEGORY_MONO,
        "IBM Plex Mono",
        ("ibm-plex-mono-400-latin.woff2", "ibm-plex-mono-600-latin.woff2"),
    ),
    _bundled(
        "fira-code",
        "Fira Code",
        CATEGORY_MONO,
        "Fira Code",
        ("fira-code-latin.woff2",),
    ),
    _bundled(
        "space-grotesk",
        "Space Grotesk",
        CATEGORY_SANS,
        "Space Grotesk",
        ("space-grotesk-latin.woff2",),
    ),
    _bundled(
        "atkinson-hyperlegible",
        "Atkinson Hyperlegible",
        CATEGORY_SANS,
        "Atkinson Hyperlegible",
        (
            "atkinson-hyperlegible-400-latin.woff2",
            "atkinson-hyperlegible-700-latin.woff2",
        ),
    ),
    _bundled(
        "cascadia-code",
        "Cascadia Code",
        CATEGORY_MONO,
        "Cascadia Code",
        ("cascadia-code-latin.woff2",),
    ),
    _bundled(
        "spline-sans-mono",
        "Spline Sans Mono",
        CATEGORY_MONO,
        "Spline Sans Mono",
        ("spline-sans-mono-latin.woff2",),
    ),
    _bundled(
        "meslo-nerd-font",
        "Meslo Nerd Font",
        CATEGORY_MONO,
        "MesloLGS Nerd Font",
        ("meslo-nerd-font-latin.woff2",),
    ),
)


def custom_family_name(key: str) -> str:
    """The CSS family name used for an uploaded font."""
    stem = key[len(CUSTOM_FONT_PREFIX) :] if key.startswith(CUSTOM_FONT_PREFIX) else key
    if stem.endswith(".woff2"):
        stem = stem[: -len(".woff2")]
    elif stem.endswith(".woff"):
        stem = stem[: -len(".woff")]
    return f"DevLog Custom {stem}"


def custom_font_label(key: str) -> str:
    """The human readable label used for an uploaded font."""
    stem = key[len(CUSTOM_FONT_PREFIX) :] if key.startswith(CUSTOM_FONT_PREFIX) else key
    for suffix in (".woff2", ".woff"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    words = [part for part in stem.split("-") if part]
    label = " ".join(word.capitalize() for word in words)
    return f"{label or 'Font'} (custom)"


def _font_name(name: str) -> str:
    """Quote a family name that contains a space."""
    if " " in name:
        return f"'{name}'"
    return name


def font_stack(family: FontFamily) -> str:
    """The ``font-family`` value for a family, with the usual fallbacks."""
    base = SANS_STACK if family.category == CATEGORY_SANS else MONO_STACK
    parts = [f"'{family.css_family}'"]
    parts.extend(_font_name(name) for name in base if name != family.css_family)
    return ", ".join(parts)


class FontRegistry:
    """Catalog of selectable font families."""

    def __init__(self, storage: Any | None = None) -> None:
        self._storage = storage
        self._custom: tuple[FontFamily, ...] | None = None

    def _storage_backend(self) -> Any | None:
        if self._storage is not None:
            return self._storage
        try:
            from app.storage import get_storage

            return get_storage()
        except Exception:
            logger.warning("font registry: storage backend unavailable", exc_info=True)
            return None

    def _in_storage(self, filename: str) -> bool:
        """Whether an uploaded font file is still present in storage."""
        storage = self._storage_backend()
        if storage is None:
            return False
        exists = getattr(storage, "exists", None)
        if exists is None:
            return True
        try:
            return bool(exists(filename))
        except Exception:
            logger.warning("font registry: could not check %r", filename, exc_info=True)
            return False

    def _discover_custom(self) -> tuple[FontFamily, ...]:
        storage = self._storage_backend()
        if storage is None:
            return ()
        try:
            names = storage.list_files(CUSTOM_FONT_PREFIX)
        except Exception:
            logger.warning("font registry: custom fonts could not be listed", exc_info=True)
            return ()

        families: list[FontFamily] = []
        for name in names:
            if not name.startswith(CUSTOM_FONT_PREFIX):
                continue
            if not name.endswith((".woff2", ".woff")):
                continue
            try:
                url = storage.url(name)
            except Exception:
                logger.warning("font registry: no url for %r", name)
                continue
            families.append(
                FontFamily(
                    key=name,
                    label=custom_font_label(name),
                    category=CATEGORY_SANS,
                    source=SOURCE_CUSTOM,
                    css_family=custom_family_name(name),
                    files=(name,),
                    url=url,
                )
            )
        families.sort(key=lambda family: family.label.lower())
        return tuple(families)

    def list_families(self, category: str | None = None) -> list[FontFamily]:
        """Every known family, optionally narrowed to one category."""
        if self._custom is None:
            self._custom = self._discover_custom()
        families = list(BUNDLED_FONTS) + list(self._custom)
        if category is not None:
            families = [
                family
                for family in families
                if family.category == category or family.source == SOURCE_CUSTOM
            ]
        return families

    def resolve(self, key: str) -> FontFamily | None:
        """Find a family by its stored key.

        An uploaded family whose file has since been removed from storage is
        reported as missing, so the caller falls back to a bundled family
        instead of emitting a font stack whose first entry never loads.
        """
        if not key:
            return None
        for family in self.list_families():
            if family.key != key:
                continue
            if family.source == SOURCE_CUSTOM and not self._in_storage(family.files[0]):
                logger.warning("font registry: %r is no longer in storage", key)
                return None
            return family
        return None

    def resolve_for_slot(self, key: str, category: str) -> FontFamily | None:
        """Find a family that can be used in the given slot."""
        family = self.resolve(key)
        if family is None:
            return None
        if family.source == SOURCE_CUSTOM:
            return family
        if family.category != category:
            return None
        return family

    def invalidate(self) -> None:
        """Drop the cached custom font catalog."""
        self._custom = None


__all__ = [
    "BUNDLED_FONTS",
    "CUSTOM_FONT_PREFIX",
    "FontRegistry",
    "MONO_STACK",
    "SANS_STACK",
    "custom_family_name",
    "custom_font_label",
    "font_stack",
]
