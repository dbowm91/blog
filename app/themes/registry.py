from __future__ import annotations

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
    discover_external,
    validate_theme_name,
)
from app.themes.translate import (
    to_css_variables,
    to_legacy_vars,
    to_theme_vars,
    translate_halloy_theme,
)
from app.themes.diagnostics import TranslationDiagnostics

logger = logging.getLogger(__name__)


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


class ThemeRegistry:
    def __init__(
        self,
        bundled_root: Path | None = None,
        external_root: Path | None = None,
        default_theme: str = "catppuccin-mocha",
    ) -> None:
        self._bundled_root = (
            bundled_root
            if bundled_root is not None
            else Path(__file__).resolve().parent / "bundled"
        )
        self._external_root = external_root
        self._default_theme = default_theme
        self._cache = ThemeCache()
        self._catalog: dict[str, ThemeDescriptor] | None = None

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
        merged: dict[str, ThemeDescriptor] = {}
        lowercase_seen: dict[str, str] = {}

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
            merged[name] = self._make_descriptor(info)

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
            merged[name] = self._make_descriptor(info, overrides_bundled=overrides_bundled)

        self._catalog = merged

    def list_themes(self) -> list[ThemeDescriptor]:
        if self._catalog is None:
            self._rebuild_catalog()
        assert self._catalog is not None
        return sorted(self._catalog.values(), key=lambda d: d.canonical_name)

    def resolve(self, name: str) -> ThemeDescriptor | None:
        try:
            validate_theme_name(name)
        except ValueError:
            logger.warning("invalid theme name: %r", name)
            return None
        if self._catalog is None:
            self._rebuild_catalog()
        assert self._catalog is not None
        if name in self._catalog:
            return self._catalog[name]
        lower = name.lower()
        for canonical, descriptor in self._catalog.items():
            if canonical.lower() == lower:
                return descriptor
        return None

    def load(self, name: str) -> LoadedTheme:
        descriptor = self.resolve(name)
        if descriptor is None:
            raise ValueError(f"theme not found: {name!r}")

        canonical_name = descriptor.canonical_name
        source_type = descriptor.source.value
        cache_key = ThemeCache.make_key(canonical_name, source_type)

        entry = self._cache.get(cache_key)
        if entry is not None:
            if self._cache.validate_entry(cache_key, entry.file_mtime, entry.file_size):
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

        info = self._find_file_info(canonical_name)
        if info is None:
            raise ValueError(f"theme file not found: {name!r}")

        try:
            data = info.path.read_bytes()
        except OSError as exc:
            raise ValueError(f"cannot read theme file: {name!r}") from exc

        try:
            halloy_theme = parse_halloy_theme_bytes(data, source_name=canonical_name)
        except ThemeParseError as exc:
            logger.warning("parse error for %r: %s", canonical_name, exc)
            raise ValueError(f"parse error in theme {name!r}: {exc}") from exc

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
        )
        self._cache.set(cache_key, cache_entry)

        return loaded

    def _find_file_info(self, canonical_name: str) -> ThemeFileInfo | None:
        for info in discover_bundled(self._bundled_root):
            if info.canonical_name == canonical_name:
                return info
        if self._external_root:
            for info in discover_external(self._external_root):
                if info.canonical_name == canonical_name:
                    return info
        return None

    def invalidate(self, name: str | None = None) -> None:
        if name is not None:
            if self._catalog is not None:
                descriptor = self._catalog.get(name)
                if descriptor is not None:
                    cache_key = ThemeCache.make_key(name, descriptor.source.value)
                    self._cache.invalidate(cache_key)
                self._catalog.pop(name, None)
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
            except ValueError:
                continue

        emergency = _emergency_halloy_theme()
        result = translate_halloy_theme(emergency)
        return LoadedTheme(
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
            css="",
            is_dark=True,
            diagnostics=result.diagnostics,
            css_vars={},
            legacy_vars={},
        )


__all__ = [
    "LoadedTheme",
    "ThemeDescriptor",
    "ThemeRegistry",
]
