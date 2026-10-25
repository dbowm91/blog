"""Backdrop registry: bundled page graphics plus operator uploads.

A backdrop is a large, single-colour graphic that sits behind the page.  It is
painted through a CSS mask, so the graphic itself only supplies a shape and
the colour comes from the theme at runtime.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.appearance.model import (
    SOURCE_BUNDLED,
    SOURCE_CUSTOM,
    BackdropDescriptor,
)

logger = logging.getLogger(__name__)

CUSTOM_BACKDROP_PREFIX = "custom-backdrop-"

_BACKDROP_ROOT = Path(__file__).resolve().parent.parent / "static" / "img" / "backdrops"

BUNDLED_BACKDROPS: tuple[tuple[str, str, str], ...] = (
    ("default", "Default", "default.svg"),
    ("grid", "Blueprint Grid", "grid.svg"),
    ("waves", "Flow", "waves.svg"),
)


def custom_backdrop_label(key: str) -> str:
    """The human readable label used for an uploaded backdrop."""
    stem = key[len(CUSTOM_BACKDROP_PREFIX) :] if key.startswith(CUSTOM_BACKDROP_PREFIX) else key
    if stem.endswith(".svg"):
        stem = stem[: -len(".svg")]
    words = [part for part in stem.split("-") if part]
    label = " ".join(word.capitalize() for word in words)
    return f"{label or 'Backdrop'} (custom)"


class BackdropRegistry:
    """Catalog of selectable page backdrops."""

    def __init__(self, storage: Any | None = None, bundled_root: Path | None = None) -> None:
        self._storage = storage
        self._bundled_root = bundled_root or _BACKDROP_ROOT
        self._custom: tuple[BackdropDescriptor, ...] | None = None

    def _storage_backend(self) -> Any | None:
        if self._storage is not None:
            return self._storage
        try:
            from app.storage import get_storage

            return get_storage()
        except Exception:
            logger.warning("backdrop registry: storage backend unavailable", exc_info=True)
            return None

    def _in_storage(self, filename: str) -> bool:
        """Whether an uploaded backdrop file is still present in storage."""
        storage = self._storage_backend()
        if storage is None:
            return False
        exists = getattr(storage, "exists", None)
        if exists is None:
            return True
        try:
            return bool(exists(filename))
        except Exception:
            logger.warning("backdrop registry: could not check %r", filename, exc_info=True)
            return False

    def _bundled_url(self, filename: str) -> str:
        from app.vite import vite_asset

        return vite_asset(f"img/backdrops/{filename}")

    def _discover_custom(self) -> tuple[BackdropDescriptor, ...]:
        storage = self._storage_backend()
        if storage is None:
            return ()
        try:
            names = storage.list_files(CUSTOM_BACKDROP_PREFIX)
        except Exception:
            logger.warning("backdrop registry: custom backdrops could not be listed", exc_info=True)
            return ()

        descriptors: list[BackdropDescriptor] = []
        for name in names:
            if not name.startswith(CUSTOM_BACKDROP_PREFIX) or not name.endswith(".svg"):
                continue
            try:
                url = storage.url(name)
            except Exception:
                logger.warning("backdrop registry: no url for %r", name)
                continue
            descriptors.append(
                BackdropDescriptor(
                    key=name,
                    label=custom_backdrop_label(name),
                    source=SOURCE_CUSTOM,
                    url=url,
                )
            )
        descriptors.sort(key=lambda descriptor: descriptor.label.lower())
        return tuple(descriptors)

    def list_backdrops(self) -> list[BackdropDescriptor]:
        """Every known backdrop."""
        if self._custom is None:
            self._custom = self._discover_custom()
        bundled = [
            BackdropDescriptor(
                key=key,
                label=label,
                source=SOURCE_BUNDLED,
                url=self._bundled_url(filename),
            )
            for key, label, filename in BUNDLED_BACKDROPS
            if (self._bundled_root / filename).is_file()
        ]
        return bundled + list(self._custom)

    def resolve(self, key: str) -> BackdropDescriptor | None:
        """Find a backdrop by its stored key.

        An uploaded backdrop whose file has since been removed from storage is
        reported as missing, so the caller stops pointing the page mask at a
        file that no longer exists.
        """
        if not key:
            return None
        for descriptor in self.list_backdrops():
            if descriptor.key != key:
                continue
            if descriptor.source == SOURCE_CUSTOM and not self._in_storage(descriptor.key):
                logger.warning("backdrop registry: %r is no longer in storage", key)
                return None
            return descriptor
        return None

    def invalidate(self) -> None:
        """Drop the cached custom backdrop catalog."""
        self._custom = None


__all__ = [
    "BackdropRegistry",
    "BUNDLED_BACKDROPS",
    "CUSTOM_BACKDROP_PREFIX",
    "custom_backdrop_label",
]
