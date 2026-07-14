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
    source_fingerprint: str


class ThemeCache:
    def __init__(self) -> None:
        self._cache: dict[str, ThemeCacheEntry] = {}
        self._hits: int = 0
        self._misses: int = 0

    def get(self, key: str) -> ThemeCacheEntry | None:
        entry = self._cache.get(key)
        if entry is not None:
            self._hits += 1
        else:
            self._misses += 1
        return entry

    def set(self, key: str, entry: ThemeCacheEntry) -> None:
        self._cache[key] = entry

    def invalidate(self, key: str | None = None) -> None:
        if key is None:
            self._cache.clear()
        else:
            self._cache.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        keys_to_remove = [k for k in self._cache if k.endswith(":" + prefix)]
        for key in keys_to_remove:
            del self._cache[key]

    def clear(self) -> None:
        self.invalidate(None)

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    def reset_counters(self) -> None:
        self._hits = 0
        self._misses = 0

    @staticmethod
    def make_key(canonical_name: str, source_type: str) -> str:
        return f"{source_type}:{canonical_name}"

    def validate_entry(
        self,
        key: str,
        current_mtime: float,
        current_size: int,
        current_fingerprint: str | None = None,
    ) -> bool:
        entry = self._cache.get(key)
        if entry is None:
            return False
        if current_fingerprint is not None:
            return entry.source_fingerprint == current_fingerprint
        return entry.file_mtime == current_mtime and entry.file_size == current_size
