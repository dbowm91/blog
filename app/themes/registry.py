from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

from app.themes.cache import ThemeCache, ThemeCacheEntry
from app.themes.halloy import (
    HalloyBuffer,
    HalloyBufferServerMessages,
    HalloyButtons,
    HalloyGeneral,
    HalloyText,
    HalloyTheme,
    ThemeParseError,
    parse_halloy_theme_bytes,
)
from app.themes.model import EMERGENCY_DEFAULT, BlogTheme
from app.themes.resources import (
    ThemeFileInfo,
    ThemeSource,
    discover_bundled,
    discover_bundled_package,
    discover_external,
    normalize_theme_name,
)
from app.themes.translate import (
    to_css_variables,
    to_legacy_vars,
    to_theme_vars,
    translate_halloy_theme,
)
from app.themes.diagnostics import TranslationDiagnostics

logger = logging.getLogger(__name__)

_THEME_ALIASES: dict[str, str] = {
    "catppuccin-mocha": "Catppuccin Mocha",
    "catppuccin-latte": "Catppuccin Latte",
    "catppuccin-macchiato": "Catppuccin Macchiato",
    "rose-pine": "Rose Pine",
    "rose-pine-dawn": "Rose Pine Dawn",
    "rose-pine-moon": "Rose Pine Moon",
    "tokyo-night-storm": "Tokyo Night Storm",
    "one-dark": "One Dark",
    "solarized-dark": "Solarized Dark",
    "halcyon-dark": "Halcyon Dark",
    "macaw-dark": "Macaw Dark",
    "macaw-light": "Macaw Light",
    "ferra-light": "Ferra Light",
    "flexor-dark": "Flexor Dark",
    "noctis-lilac": "Noctis Lilac",
    "intellij-light": "IntelliJ Light",
    "cyber-red": "Cyber Red",
    "nostromo-terminal": "Nostromo Terminal",
    "base16-atelier-forest-light": "base16-atelier-forest-light",
    "black-but-with-important-highlights": "black but with important highlights",
    "discord-80_-saturation": "Discord (80_ Saturation)",
}


class ThemeNotFoundError(ValueError):
    """Theme name not found in registry."""


class ThemeParseFailure(ValueError):
    """Theme file exists but cannot be parsed."""


class ThemeLoadError(ValueError):
    """Theme file exists but cannot be read."""


class ThemeValidationError(ValueError):
    """Theme name failed validation."""


@dataclass(frozen=True, slots=True)
class ThemeDescriptor:
    canonical_name: str
    display_name: str
    source: ThemeSource
    overrides_bundled: bool
    is_dark: bool | None
    status: str
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LoadedTheme:
    descriptor: ThemeDescriptor
    blog_theme: BlogTheme
    halloy_theme: HalloyTheme
    css: str
    is_dark: bool
    diagnostics: TranslationDiagnostics
    css_vars: dict[str, str]
    legacy_vars: dict[str, str]


def _emergency_halloy_theme() -> HalloyTheme:
    from app.themes.colors import RGBA

    bg = EMERGENCY_DEFAULT.bg_page
    return HalloyTheme(
        source_name="emergency-default",
        schema_version="emergency",
        general=HalloyGeneral(
            background=RGBA(bg.red, bg.green, bg.blue, 1.0),
            border=RGBA(48, 54, 61, 1.0),
            horizontal_rule=RGBA(48, 54, 61, 1.0),
            unread_indicator=RGBA(88, 166, 255, 1.0),
        ),
        text=HalloyText(
            primary=RGBA(230, 237, 243, 1.0),
            secondary=RGBA(201, 209, 217, 1.0),
            tertiary=RGBA(88, 166, 255, 1.0),
            success=RGBA(63, 185, 80, 1.0),
            error=RGBA(248, 81, 73, 1.0),
        ),
        buffer=HalloyBuffer(
            action=RGBA(121, 192, 255, 1.0),
            background=RGBA(22, 27, 34, 1.0),
            background_text_input=RGBA(13, 17, 23, 1.0),
            background_title_bar=RGBA(28, 33, 40, 1.0),
            border=RGBA(48, 54, 61, 1.0),
            border_selected=RGBA(88, 166, 255, 1.0),
            code=RGBA(22, 27, 34, 1.0),
            highlight=RGBA(88, 166, 255, 0.4),
            nickname=RGBA(121, 192, 255, 1.0),
            selection=RGBA(48, 54, 61, 1.0),
            timestamp=RGBA(125, 133, 144, 1.0),
            topic=RGBA(201, 209, 217, 1.0),
            url=RGBA(88, 166, 255, 1.0),
            server_messages=HalloyBufferServerMessages(
                default=RGBA(139, 148, 158, 1.0),
            ),
        ),
        buttons=HalloyButtons(),
    )


def _compute_fingerprint(data: bytes, source: ThemeSource, mtime: float, size: int) -> str:
    if source == ThemeSource.BUNDLED:
        return hashlib.sha256(data).hexdigest()
    return f"{mtime}:{size}"


@dataclass(frozen=True, slots=True)
class _CatalogEntry:
    descriptor: ThemeDescriptor
    file_info: ThemeFileInfo


class ThemeRegistry:
    """Central theme catalog and loader with in-process caching.

    Cache freshness contract:
        The registry builds an in-memory catalog on first access and caches
        loaded theme results.  External file changes (edits, additions,
        deletions) are **not** auto-detected after the initial catalog build.
        To observe external changes you must call ``invalidate()`` (full
        refresh) or ``invalidate(name)`` (single-theme refresh) before the
        next ``load()`` call.

    This explicit-invalidation design avoids filesystem polling and keeps the
    hot path O(1) for repeated loads of the same theme.
    """

    def __init__(
        self,
        bundled_root: Path | None = None,
        external_root: Path | None = None,
        default_theme: str = "Catppuccin Mocha",
    ) -> None:
        if bundled_root is not None:
            self._bundled_root = bundled_root
            self._use_package_resources = False
        else:
            self._bundled_root = Path(__file__).resolve().parent / "bundled"
            self._use_package_resources = True
        self._external_root = external_root
        self._default_theme = default_theme
        self._cache = ThemeCache()
        self._catalog: dict[str, _CatalogEntry] | None = None

    def _make_descriptor(
        self,
        info: ThemeFileInfo,
        *,
        overrides_bundled: bool = False,
    ) -> ThemeDescriptor:
        canonical_name = info.canonical_name
        display_name = canonical_name.replace("-", " ").replace("_", " ").title()
        return ThemeDescriptor(
            canonical_name=canonical_name,
            display_name=display_name,
            source=info.source,
            overrides_bundled=overrides_bundled,
            is_dark=None,
            status="ok",
            warnings=(),
        )

    def _rebuild_catalog(self) -> None:
        merged: dict[str, _CatalogEntry] = {}
        lowercase_seen: dict[str, str] = {}

        if self._use_package_resources:
            bundled = list(discover_bundled_package())
        else:
            bundled = list(discover_bundled(self._bundled_root))
        external = list(discover_external(self._external_root)) if self._external_root else []

        for info in bundled:
            name = info.canonical_name
            lower = name.lower()
            if lower in lowercase_seen and lowercase_seen[lower] != name:
                logger.warning(
                    "case collision between %r and %r, rejecting both",
                    lowercase_seen[lower],
                    name,
                )
                merged.pop(lowercase_seen[lower], None)
                merged.pop(name, None)
                continue
            lowercase_seen[lower] = name
            merged[name] = _CatalogEntry(
                descriptor=self._make_descriptor(info),
                file_info=info,
            )

        for info in external:
            name = info.canonical_name
            lower = name.lower()
            if lower in lowercase_seen and lowercase_seen[lower] != name:
                logger.warning(
                    "case collision between %r and %r, rejecting both",
                    lowercase_seen[lower],
                    name,
                )
                merged.pop(lowercase_seen[lower], None)
                merged.pop(name, None)
                continue
            existing = merged.get(name)
            overrides_bundled = existing is not None
            lowercase_seen[lower] = name
            merged[name] = _CatalogEntry(
                descriptor=self._make_descriptor(info, overrides_bundled=overrides_bundled),
                file_info=info,
            )

        self._catalog = merged

    def _resolve_alias(self, name: str) -> str:
        lower = name.lower()
        if lower in _THEME_ALIASES:
            return _THEME_ALIASES[lower]
        return name

    def list_themes(self) -> list[ThemeDescriptor]:
        if self._catalog is None:
            self._rebuild_catalog()
        assert self._catalog is not None
        return sorted(
            (entry.descriptor for entry in self._catalog.values()),
            key=lambda d: d.canonical_name,
        )

    def resolve(self, name: str) -> ThemeDescriptor | None:
        try:
            normalized = normalize_theme_name(name)
        except ValueError as exc:
            raise ThemeValidationError(str(exc)) from exc
        resolved_name = self._resolve_alias(normalized)
        if self._catalog is None:
            self._rebuild_catalog()
        assert self._catalog is not None
        if resolved_name in self._catalog:
            return self._catalog[resolved_name].descriptor
        lower = resolved_name.lower()
        for canonical, entry in self._catalog.items():
            if canonical.lower() == lower:
                return entry.descriptor
        return None

    def load(self, name: str) -> LoadedTheme:
        """Load and translate a theme by name, returning a cached result when valid.

        The load checks the existing cache entry against the **current
        catalog's** file metadata (mtime, size, fingerprint).  The catalog
        itself is only rebuilt on ``invalidate()`` or when it has not been
        built yet.  Therefore external file edits are only observed after an
        explicit invalidation – this is the intended freshness boundary.
        """
        descriptor = self.resolve(name)
        if descriptor is None:
            raise ThemeNotFoundError(f"theme not found: {name!r}")

        canonical_name = descriptor.canonical_name
        source_type = descriptor.source.value
        cache_key = ThemeCache.make_key(canonical_name, source_type)

        entry = self._cache.get(cache_key)
        if entry is not None:
            if self._catalog is not None and canonical_name in self._catalog:
                current_info = self._catalog[canonical_name].file_info
                current_fp = _compute_fingerprint(
                    current_info.read_bytes(),
                    current_info.source,
                    current_info.mtime,
                    current_info.size_bytes,
                )
                if self._cache.validate_entry(
                    cache_key,
                    current_info.mtime,
                    current_info.size_bytes,
                    current_fp,
                ):
                    return LoadedTheme(
                        descriptor=descriptor,
                        blog_theme=entry.blog_theme,
                        halloy_theme=entry.halloy_theme,
                        css=entry.css,
                        is_dark=entry.is_dark,
                        diagnostics=entry.diagnostics,
                        css_vars=entry.css_vars,
                        legacy_vars=entry.legacy_vars,
                    )

        if self._catalog is None or canonical_name not in self._catalog:
            raise ThemeNotFoundError(f"theme file not found: {name!r}")
        info = self._catalog[canonical_name].file_info

        try:
            data = info.read_bytes()
        except OSError as exc:
            raise ThemeLoadError(f"cannot read theme file: {name!r}") from exc

        try:
            halloy_theme = parse_halloy_theme_bytes(data, source_name=canonical_name)
        except ThemeParseError as exc:
            if info.source == ThemeSource.BUNDLED:
                logger.error("malformed bundled theme %r: %s", canonical_name, exc)
            else:
                logger.warning("malformed external theme %r: %s", canonical_name, exc)
            raise ThemeParseFailure(f"parse error in theme {name!r}: {exc}") from exc

        result = translate_halloy_theme(halloy_theme)
        css = to_css_variables(result.theme)
        css_vars = to_theme_vars(result.theme)
        legacy_vars = to_legacy_vars(result.theme)

        loaded = LoadedTheme(
            descriptor=descriptor,
            blog_theme=result.theme,
            halloy_theme=halloy_theme,
            css=css,
            is_dark=result.is_dark,
            diagnostics=result.diagnostics,
            css_vars=css_vars,
            legacy_vars=legacy_vars,
        )

        fingerprint = _compute_fingerprint(data, info.source, info.mtime, info.size_bytes)
        cache_entry = ThemeCacheEntry(
            halloy_theme=halloy_theme,
            blog_theme=result.theme,
            css=css,
            is_dark=result.is_dark,
            source_name=canonical_name,
            source_type=source_type,
            file_mtime=info.mtime,
            file_size=info.size_bytes,
            translation_schema=halloy_theme.schema_version,
            diagnostics=result.diagnostics,
            css_vars=css_vars,
            legacy_vars=legacy_vars,
            source_fingerprint=fingerprint,
        )
        self._cache.set(cache_key, cache_entry)

        return loaded

    def invalidate(self, name: str | None = None) -> None:
        """Refresh the registry's view of available themes.

        This is the only supported boundary for observing external filesystem
        changes.  After calling this method the catalog is rebuilt and the
        affected cache entries are evicted, so the next ``load()`` will read
        fresh data from disk or package resources.

        Args:
            name: If provided, evict cache entries for this single theme and
                  rebuild the catalog.  If ``None``, evict everything and
                  rebuild from scratch.
        """
        if name is not None:
            try:
                normalized = normalize_theme_name(name)
            except ValueError:
                return
            resolved_name = self._resolve_alias(normalized)
            self._cache.invalidate_prefix(resolved_name)
            self._catalog = None
        else:
            self._cache.clear()
            self._catalog = None

    def get_fallback(self, configured: str | None = None) -> LoadedTheme:
        tried: set[str] = set()
        candidates = [configured, self._default_theme]
        for candidate in candidates:
            if candidate is None or candidate in tried:
                continue
            tried.add(candidate)
            try:
                return self.load(candidate)
            except (ThemeNotFoundError, ThemeParseFailure, ThemeLoadError):
                continue

        logger.warning(
            "fallback activation: requested=%r default=%r using emergency-default",
            configured,
            self._default_theme,
        )
        emergency = _emergency_halloy_theme()
        result = translate_halloy_theme(emergency)
        css = to_css_variables(result.theme)
        css_vars = to_theme_vars(result.theme)
        legacy_vars = to_legacy_vars(result.theme)
        loaded = LoadedTheme(
            descriptor=ThemeDescriptor(
                canonical_name="emergency-default",
                display_name="Emergency Default",
                source=ThemeSource.BUNDLED,
                overrides_bundled=False,
                is_dark=True,
                status="fallback",
                warnings=(),
            ),
            blog_theme=EMERGENCY_DEFAULT,
            halloy_theme=emergency,
            css=css,
            is_dark=True,
            diagnostics=result.diagnostics,
            css_vars=css_vars,
            legacy_vars=legacy_vars,
        )
        return loaded


__all__ = [
    "LoadedTheme",
    "ThemeDescriptor",
    "ThemeLoadError",
    "ThemeNotFoundError",
    "ThemeParseFailure",
    "ThemeRegistry",
    "ThemeValidationError",
    "_THEME_ALIASES",
]
