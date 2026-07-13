from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.themes.model import CSS_VARS, EMERGENCY_DEFAULT
from app.themes.registry import (
    LoadedTheme,
    ThemeParseFailure,
    ThemeRegistry,
    ThemeValidationError,
)
from app.themes.resources import ThemeSource, validate_theme_name

CATALOG = Path(__file__).resolve().parent.parent.parent / "themes"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

VALID_THEME_CONTENT = (FIXTURES / "minimal.toml").read_text()


def _write_theme(directory: Path, name: str, content: str = VALID_THEME_CONTENT) -> Path:
    path = directory / f"{name}.toml"
    path.write_text(content)
    return path


def _make_registry(
    tmp_path: Path,
    *,
    bundled_root: Path | None = None,
    external_root: Path | None = None,
    default_theme: str = "Catppuccin Mocha",
) -> ThemeRegistry:
    return ThemeRegistry(
        bundled_root=bundled_root or CATALOG,
        external_root=external_root,
        default_theme=default_theme,
    )


class TestBundledOnlyListing:
    def test_lists_all_bundled_themes(self) -> None:
        registry = _make_registry(Path())
        themes = registry.list_themes()
        catalog_files = [p for p in CATALOG.glob("*.toml") if not p.name.startswith("._")]
        assert len(themes) == len(catalog_files)

    def test_all_descriptors_are_bundled_source(self) -> None:
        registry = _make_registry(Path())
        themes = registry.list_themes()
        for theme in themes:
            assert theme.source == ThemeSource.BUNDLED

    def test_sorted_by_canonical_name(self) -> None:
        registry = _make_registry(Path())
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert names == sorted(names)

    def test_no_external_root(self) -> None:
        registry = ThemeRegistry(bundled_root=CATALOG, external_root=None)
        themes = registry.list_themes()
        catalog_files = [p for p in CATALOG.glob("*.toml") if not p.name.startswith("._")]
        assert len(themes) == len(catalog_files)

    def test_known_theme_resolves(self) -> None:
        registry = _make_registry(Path())
        descriptor = registry.resolve("Dracula")
        assert descriptor is not None
        assert descriptor.canonical_name == "Dracula"
        assert descriptor.source == ThemeSource.BUNDLED

    def test_unknown_theme_returns_none(self) -> None:
        registry = _make_registry(Path())
        assert registry.resolve("nonexistent-theme") is None


class TestExternalAdditions:
    def test_external_theme_appears_in_listing(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "my-custom-theme")
        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "my-custom-theme" in names

    def test_external_theme_has_external_source(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "my-custom-theme")
        registry = _make_registry(tmp_path, external_root=ext)
        descriptor = registry.resolve("my-custom-theme")
        assert descriptor is not None
        assert descriptor.source == ThemeSource.EXTERNAL

    def test_multiple_external_themes(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "alpha-custom")
        _write_theme(ext, "beta-custom")
        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "alpha-custom" in names
        assert "beta-custom" in names


class TestExternalOverride:
    def test_same_name_overrides_bundled(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "Dracula")
        registry = _make_registry(tmp_path, external_root=ext)
        descriptor = registry.resolve("Dracula")
        assert descriptor is not None
        assert descriptor.source == ThemeSource.EXTERNAL
        assert descriptor.overrides_bundled is True

    def test_count_unchanged_when_overriding(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        count_before = len(_make_registry(tmp_path).list_themes())
        _write_theme(ext, "Dracula")
        count_after = len(_make_registry(tmp_path, external_root=ext).list_themes())
        assert count_after == count_before


class TestOverrideRemovalRevealsBundled:
    def test_removing_external_file_restores_bundled(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "Dracula")
        registry = _make_registry(tmp_path, external_root=ext)
        assert registry.resolve("Dracula").source == ThemeSource.EXTERNAL

        os.remove(ext / "Dracula.toml")
        registry.invalidate()
        descriptor = registry.resolve("Dracula")
        assert descriptor is not None
        assert descriptor.source == ThemeSource.BUNDLED

    def test_full_invalidation_restores_bundled(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "Dracula")
        registry = _make_registry(tmp_path, external_root=ext)
        assert registry.resolve("Dracula").source == ThemeSource.EXTERNAL

        os.remove(ext / "Dracula.toml")
        registry.invalidate()
        descriptor = registry.resolve("Dracula")
        assert descriptor is not None
        assert descriptor.source == ThemeSource.BUNDLED


class TestMissingExternalDirectory:
    def test_works_when_external_dir_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "does-not-exist"
        registry = _make_registry(tmp_path, external_root=missing)
        themes = registry.list_themes()
        catalog_files = [p for p in CATALOG.glob("*.toml") if not p.name.startswith("._")]
        assert len(themes) == len(catalog_files)

    def test_resolve_still_works(self, tmp_path: Path) -> None:
        missing = tmp_path / "does-not-exist"
        registry = _make_registry(tmp_path, external_root=missing)
        assert registry.resolve("Dracula") is not None


class TestMalformedExternalIsolation:
    def test_bad_external_does_not_break_listing(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "valid-theme")
        _write_theme(ext, "bad-theme", content="this is not valid toml [[[")

        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "valid-theme" in names
        assert "bad-theme" in names

    def test_bad_external_load_raises(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "bad-theme", content=(FIXTURES / "malformed.toml").read_text())

        registry = _make_registry(tmp_path, external_root=ext)
        with pytest.raises(ThemeParseFailure, match="parse error"):
            registry.load("bad-theme")


class TestTraversalRejection:
    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_theme_name("")

    def test_slash_rejected(self) -> None:
        with pytest.raises(ValueError, match="path separators"):
            validate_theme_name("foo/bar")

    def test_backslash_rejected(self) -> None:
        with pytest.raises(ValueError, match="path separators"):
            validate_theme_name("foo\\bar")

    def test_dotdot_segment_rejected(self) -> None:
        with pytest.raises(ValueError, match="path segment"):
            validate_theme_name("..")

    def test_absolute_path_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_theme_name("/etc/passwd")

    def test_control_chars_rejected(self) -> None:
        with pytest.raises(ValueError, match="control characters"):
            validate_theme_name("theme\x00name")

    def test_long_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="exceed"):
            validate_theme_name("x" * 201)

    def test_valid_name_accepted(self) -> None:
        result = validate_theme_name("my-theme.toml")
        assert result == "my-theme"

    def test_registry_resolve_rejects_bad_names(self) -> None:
        registry = _make_registry(Path())
        with pytest.raises(ThemeValidationError):
            registry.resolve("../etc/passwd")
        with pytest.raises(ThemeValidationError):
            registry.resolve("/etc/passwd")


class TestCaseCollision:
    def test_case_collision_rejects_both(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        (ext / "MyTheme.toml").write_text(VALID_THEME_CONTENT)
        (ext / "mytheme.toml").write_text(VALID_THEME_CONTENT)

        registry = ThemeRegistry(
            bundled_root=tmp_path / "empty",
            external_root=ext,
            default_theme="Catppuccin Mocha",
        )
        themes = registry.list_themes()
        names = {t.canonical_name.lower() for t in themes}
        assert "mytheme" not in names

    def test_external_case_collision_with_bundled(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "dracula")

        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "dracula" not in names
        assert "Dracula" not in names


class TestFileSizeLimit:
    def test_oversized_external_theme_skipped(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        big_content = "[general]\n" + ('background = "#000000"\n' * 80000)
        (ext / "huge-theme.toml").write_text(big_content)

        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "huge-theme" not in names


class TestWarmCacheBehavior:
    def test_second_load_returns_cached_result(self) -> None:
        registry = _make_registry(Path())
        first = registry.load("Dracula")
        second = registry.load("Dracula")
        assert first.blog_theme == second.blog_theme
        assert first.css == second.css
        assert first.is_dark == second.is_dark

    def test_cached_result_preserves_descriptor(self) -> None:
        registry = _make_registry(Path())
        loaded = registry.load("Dracula")
        assert loaded.descriptor.canonical_name == "Dracula"
        assert loaded.descriptor.source == ThemeSource.BUNDLED


class TestInvalidation:
    def test_invalidate_single_theme_removes_from_catalog(self) -> None:
        registry = _make_registry(Path())
        registry.load("Dracula")
        registry.invalidate("Dracula")
        assert registry._catalog is None
        descriptor = registry.resolve("Dracula")
        assert descriptor is not None
        assert descriptor.canonical_name == "Dracula"

    def test_invalidate_all_forces_reread(self) -> None:
        registry = _make_registry(Path())
        first = registry.load("Dracula")
        registry.invalidate()
        second = registry.load("Dracula")
        assert first is not second

    def test_invalidate_unknown_theme_no_error(self) -> None:
        registry = _make_registry(Path())
        registry.invalidate("nonexistent")

    def test_invalidate_clears_cache_and_catalog(self) -> None:
        registry = _make_registry(Path())
        registry.list_themes()
        assert registry._catalog is not None
        registry.invalidate()
        assert registry._catalog is None


class TestGetFallback:
    def test_returns_configured_theme(self) -> None:
        registry = _make_registry(Path())
        loaded = registry.get_fallback("Dracula")
        assert loaded.descriptor.canonical_name == "Dracula"
        assert isinstance(loaded, LoadedTheme)

    def test_returns_default_when_configured_fails(self) -> None:
        registry = _make_registry(Path(), default_theme="Dracula")
        loaded = registry.get_fallback("nonexistent-theme")
        assert loaded.descriptor.canonical_name == "Dracula"

    def test_returns_emergency_when_all_fail(self) -> None:
        registry = _make_registry(
            Path(),
            bundled_root=Path("/nonexistent"),
            default_theme="nonexistent-default",
        )
        loaded = registry.get_fallback("also-nonexistent")
        assert loaded.descriptor.canonical_name == "emergency-default"
        assert loaded.descriptor.status == "fallback"
        assert loaded.blog_theme == EMERGENCY_DEFAULT

    def test_returns_default_when_configured_is_none(self) -> None:
        registry = _make_registry(Path(), default_theme="Dracula")
        loaded = registry.get_fallback(None)
        assert loaded.descriptor.canonical_name == "Dracula"

    def test_emergency_fallback_is_dark(self) -> None:
        registry = _make_registry(
            Path(),
            bundled_root=Path("/nonexistent"),
            default_theme="nonexistent-default",
        )
        loaded = registry.get_fallback("nope")
        assert loaded.is_dark is True


class TestNoAbsolutePathLeakage:
    def test_descriptor_has_no_path_attribute(self) -> None:
        registry = _make_registry(Path())
        themes = registry.list_themes()
        for theme in themes:
            assert not hasattr(theme, "path")
            assert not hasattr(theme, "file_path")

    def test_descriptor_fields_are_name_source_status(self) -> None:
        registry = _make_registry(Path())
        themes = registry.list_themes()
        for theme in themes:
            assert isinstance(theme.canonical_name, str)
            assert isinstance(theme.source, ThemeSource)
            assert isinstance(theme.status, str)
            assert isinstance(theme.warnings, tuple)

    def test_loaded_theme_descriptor_no_path(self) -> None:
        registry = _make_registry(Path())
        loaded = registry.load("Dracula")
        assert not hasattr(loaded.descriptor, "path")
        assert not hasattr(loaded.descriptor, "file_path")


class TestLoadedThemeStructure:
    def test_loaded_theme_has_required_fields(self) -> None:
        registry = _make_registry(Path())
        loaded = registry.load("Dracula")
        assert loaded.descriptor is not None
        assert loaded.blog_theme is not None
        assert loaded.halloy_theme is not None
        assert isinstance(loaded.css, str)
        assert isinstance(loaded.is_dark, bool)
        assert loaded.diagnostics is not None

    def test_loaded_theme_has_css_vars(self) -> None:
        registry = _make_registry(Path())
        loaded = registry.load("Dracula")
        assert isinstance(loaded.css_vars, dict)
        assert len(loaded.css_vars) > 0
        for key in CSS_VARS.values():
            assert key in loaded.css_vars

    def test_loaded_theme_has_legacy_vars(self) -> None:
        registry = _make_registry(Path())
        loaded = registry.load("Dracula")
        assert isinstance(loaded.legacy_vars, dict)

    def test_css_output_starts_with_root_selector(self) -> None:
        registry = _make_registry(Path())
        loaded = registry.load("Dracula")
        assert loaded.css.strip().startswith(":root")


class TestRegistryInitDefaults:
    def test_default_bundled_root(self) -> None:
        registry = ThemeRegistry(bundled_root=None, external_root=None)
        expected = Path(__file__).resolve().parent.parent.parent / "app" / "themes" / "bundled"
        assert registry._bundled_root == expected

    def test_default_theme_name(self) -> None:
        registry = ThemeRegistry()
        assert registry._default_theme == "Catppuccin Mocha"

    def test_custom_default_theme(self) -> None:
        registry = ThemeRegistry(default_theme="Dracula")
        assert registry._default_theme == "Dracula"


class TestBundledPackageResources:
    def test_bundled_package_dir_exists(self) -> None:
        bundled_dir = Path(__file__).resolve().parent.parent.parent / "app" / "themes" / "bundled"
        assert bundled_dir.is_dir()

    def test_bundled_count_matches_source(self) -> None:
        source_count = len([p for p in CATALOG.glob("*.toml") if not p.name.startswith("._")])
        bundled_dir = Path(__file__).resolve().parent.parent.parent / "app" / "themes" / "bundled"
        bundled_count = len(list(bundled_dir.glob("*.toml")))
        assert bundled_count == source_count

    def test_all_bundled_files_exist_in_source(self) -> None:
        bundled_dir = Path(__file__).resolve().parent.parent.parent / "app" / "themes" / "bundled"
        for f in bundled_dir.glob("*.toml"):
            source = CATALOG / f.name
            assert source.exists(), f"bundled theme {f.name} not found in source catalog"

    def test_manifest_exists(self) -> None:
        bundled_dir = Path(__file__).resolve().parent.parent.parent / "app" / "themes" / "bundled"
        manifest = bundled_dir / "catalog_manifest.json"
        assert manifest.exists()

    def test_manifest_theme_count(self) -> None:
        import json

        bundled_dir = Path(__file__).resolve().parent.parent.parent / "app" / "themes" / "bundled"
        manifest = json.loads((bundled_dir / "catalog_manifest.json").read_text())
        assert manifest["theme_count"] == 50

    def test_bundled_package_importlib_resources(self) -> None:
        from importlib.resources import files

        bundled = files("app.themes").joinpath("bundled")
        toml_files = [f for f in bundled.iterdir() if f.name.endswith(".toml")]
        assert len(toml_files) == 50
