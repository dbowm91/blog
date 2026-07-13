from __future__ import annotations

from dataclasses import dataclass

from app.themes.diagnostics import TranslationDiagnostics
from app.themes.halloy import HalloyTheme
from app.themes.model import BlogTheme

__all__ = ["ThemeCacheEntry", "ThemeCache"]


@dataclass(slots=True)
class ThemeCacheEntry:
    halloy_theme: HalloyTheme
    blog_theme: BlogTheme
    css: str
    is_dark: bool
    source_name: str
    source_type: str
    file_mtime: float
    file_size: int
    translation_schema: str
    diagnostics: TranslationDiagnostics
    css_vars: dict[str, str]
    legacy_vars: dict[str, str]


class ThemeCache:
    def __init__(self) -> None:
        self._cache: dict[str, ThemeCacheEntry] = {}

    def get(self, key: str) -> ThemeCacheEntry | None:
        return self._cache.get(key)

    def set(self, key: str, entry: ThemeCacheEntry) -> None:
        self._cache[key] = entry

    def invalidate(self, key: str | None = None) -> None:
        if key is None:
            self._cache.clear()
        else:
            self._cache.pop(key, None)

    def clear(self) -> None:
        self.invalidate(None)

    @staticmethod
    def make_key(canonical_name: str, source_type: str) -> str:
        return f"{source_type}:{canonical_name}"

    def validate_entry(self, key: str, file_mtime: float, file_size: int) -> bool:
        entry = self._cache.get(key)
        if entry is None:
            return False
        return entry.file_mtime == file_mtime and entry.file_size == file_size
