from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.themes.halloy import parse_halloy_theme_bytes, ThemeParseError
from app.themes.translate import to_css_variables, translate_halloy_theme

BUNDLED_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "themes" / "bundled"
SOURCE_DIR = Path(__file__).resolve().parent.parent.parent / "themes"
MANIFEST_PATH = BUNDLED_DIR / "catalog_manifest.json"

BUNDLED_THEMES = sorted(f for f in BUNDLED_DIR.glob("*.toml") if not f.name.startswith("."))
MANIFEST = json.loads(MANIFEST_PATH.read_text()) if MANIFEST_PATH.exists() else None
MANIFEST_NAMES = {entry["canonical_name"] for entry in MANIFEST["themes"]} if MANIFEST else set()


class TestFilenameSafety:
    @pytest.mark.parametrize("theme_path", BUNDLED_THEMES, ids=lambda p: p.stem)
    def test_filename_is_safe(self, theme_path: Path) -> None:
        name = theme_path.name
        assert not name.startswith(".")
        assert ".." not in name
        assert "/" not in name
        assert "\\" not in name

    def test_all_filenames_are_unique(self) -> None:
        names = [f.name.lower() for f in BUNDLED_THEMES]
        assert len(names) == len(set(names))

    @pytest.mark.parametrize("theme_path", BUNDLED_THEMES, ids=lambda p: p.stem)
    def test_filename_ends_with_toml(self, theme_path: Path) -> None:
        assert theme_path.name.endswith(".toml")


class TestResourceSize:
    @pytest.mark.parametrize("theme_path", BUNDLED_THEMES, ids=lambda p: p.stem)
    def test_theme_is_nonempty(self, theme_path: Path) -> None:
        assert theme_path.stat().st_size > 0

    @pytest.mark.parametrize("theme_path", BUNDLED_THEMES, ids=lambda p: p.stem)
    def test_theme_within_size_limit(self, theme_path: Path) -> None:
        assert theme_path.stat().st_size < 1_048_576


class TestParserSucceeds:
    @pytest.mark.parametrize("theme_path", BUNDLED_THEMES, ids=lambda p: p.stem)
    def test_parse_succeeds(self, theme_path: Path) -> None:
        data = theme_path.read_bytes()
        theme = parse_halloy_theme_bytes(data, source_name=theme_path.stem)
        assert theme is not None
        assert theme.schema_version

    @pytest.mark.parametrize("theme_path", BUNDLED_THEMES, ids=lambda p: p.stem)
    def test_parse_no_exception(self, theme_path: Path) -> None:
        data = theme_path.read_bytes()
        try:
            parse_halloy_theme_bytes(data, source_name=theme_path.stem)
        except ThemeParseError:
            pytest.fail(f"Failed to parse {theme_path.name}")


class TestTranslatorSucceeds:
    @pytest.mark.parametrize("theme_path", BUNDLED_THEMES, ids=lambda p: p.stem)
    def test_translate_succeeds(self, theme_path: Path) -> None:
        data = theme_path.read_bytes()
        halloy_theme = parse_halloy_theme_bytes(data, source_name=theme_path.stem)
        result = translate_halloy_theme(halloy_theme)
        assert result.theme is not None
        assert isinstance(result.is_dark, bool)


class TestCSSComplete:
    @pytest.mark.parametrize("theme_path", BUNDLED_THEMES, ids=lambda p: p.stem)
    def test_css_starts_with_root(self, theme_path: Path) -> None:
        data = theme_path.read_bytes()
        halloy_theme = parse_halloy_theme_bytes(data, source_name=theme_path.stem)
        result = translate_halloy_theme(halloy_theme)
        css = to_css_variables(result.theme)
        assert css.strip().startswith(":root")

    @pytest.mark.parametrize("theme_path", BUNDLED_THEMES, ids=lambda p: p.stem)
    def test_css_contains_blog_vars(self, theme_path: Path) -> None:
        data = theme_path.read_bytes()
        halloy_theme = parse_halloy_theme_bytes(data, source_name=theme_path.stem)
        result = translate_halloy_theme(halloy_theme)
        css = to_css_variables(result.theme)
        assert "--blog-bg-page" in css
        assert "--blog-text-primary" in css


class TestManifestEntryExists:
    def test_manifest_file_exists(self) -> None:
        assert MANIFEST_PATH.exists()

    def test_manifest_version(self) -> None:
        assert MANIFEST is not None
        assert MANIFEST["version"] == 1

    @pytest.mark.parametrize("theme_path", BUNDLED_THEMES, ids=lambda p: p.stem)
    def test_theme_in_manifest(self, theme_path: Path) -> None:
        assert MANIFEST is not None
        assert theme_path.stem in MANIFEST_NAMES

    def test_manifest_count_matches(self) -> None:
        assert MANIFEST is not None
        assert MANIFEST["theme_count"] == len(BUNDLED_THEMES)


class TestSourceBundledMatch:
    def test_count_matches(self) -> None:
        source_count = len([p for p in SOURCE_DIR.glob("*.toml") if not p.name.startswith("._")])
        bundled_count = len(BUNDLED_THEMES)
        assert bundled_count == source_count

    @pytest.mark.parametrize("theme_path", BUNDLED_THEMES, ids=lambda p: p.stem)
    def test_content_matches_source(self, theme_path: Path) -> None:
        source_file = SOURCE_DIR / theme_path.name
        if source_file.exists():
            assert theme_path.read_bytes() == source_file.read_bytes()
