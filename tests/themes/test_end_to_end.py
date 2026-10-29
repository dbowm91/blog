from __future__ import annotations

from pathlib import Path

import pytest

from app.themes.cache import ThemeCache
from app.themes.model import CSS_VARS, EMERGENCY_DEFAULT
from app.themes.registry import (
    LoadedTheme,
    ThemeNotFoundError,
    ThemeParseFailure,
    ThemeRegistry,
    ThemeValidationError,
)
from app.themes.resources import ThemeSource

BUNDLED_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "themes" / "bundled"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
VALID_THEME_CONTENT = (FIXTURES / "minimal.toml").read_text()

DARK_THEME_CONTENT = (FIXTURES / "dark.toml").read_text()
LIGHT_THEME_CONTENT = (FIXTURES / "light.toml").read_text()
MALFORMED_CONTENT = (FIXTURES / "malformed.toml").read_text()


def _write_theme(directory: Path, name: str, content: str = VALID_THEME_CONTENT) -> Path:
    path = directory / f"{name}.toml"
    path.write_text(content)
    return path


class TestBundledThemeFullChain:
    def test_full_chain_with_content_assertion(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        loaded = registry.load("Dracula")
        assert isinstance(loaded, LoadedTheme)
        assert loaded.descriptor.canonical_name == "Dracula"
        assert loaded.descriptor.source == ThemeSource.BUNDLED
        assert loaded.is_dark is True
        assert loaded.css.strip().startswith(":root")
        assert "--blog-bg-page" in loaded.css
        assert "--blog-text-primary" in loaded.css
        assert loaded.blog_theme is not None
        assert loaded.halloy_theme is not None
        assert loaded.diagnostics is not None
        assert isinstance(loaded.css_vars, dict)
        assert len(loaded.css_vars) > 0
        assert isinstance(loaded.legacy_vars, dict)
        for key in CSS_VARS.values():
            assert key in loaded.css_vars

    def test_dark_and_light_load_correctly(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        dark = registry.load("Dracula")
        light = registry.load("Catppuccin Latte")
        assert dark.is_dark is True
        assert light.is_dark is False
        assert dark.css_vars != light.css_vars


class TestNovelExternalTheme:
    def test_novel_theme_loads_full_chain(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "my-novel", content=DARK_THEME_CONTENT)
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        loaded = registry.load("my-novel")
        assert loaded.descriptor.source == ThemeSource.EXTERNAL
        assert loaded.is_dark is True
        assert loaded.css.strip().startswith(":root")
        assert "--blog-bg-page" in loaded.css

    def test_novel_theme_in_catalog(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "novel-one")
        _write_theme(ext, "novel-two", content=LIGHT_THEME_CONTENT)
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "novel-one" in names
        assert "novel-two" in names


class TestSameNameOverride:
    def test_override_changes_css_values(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        override_content = (
            "[general]\n"
            'background = "#abcdef"\n'
            'border = "#123456"\n'
            'horizontal_rule = "#654321"\n'
            'unread_indicator = "#ffffff"\n\n'
            "[text]\n"
            'primary = "#000000"\n'
            'secondary = "#111111"\n'
            'tertiary = "#222222"\n'
            'success = "#00ff00"\n'
            'error = "#ff0000"\n\n'
            "[buffer]\n"
            'action = "#ff0000"\n'
            'background = "#999999"\n'
            'background_text_input = "#888888"\n'
            'background_title_bar = "#777777"\n'
            'border = "#666666"\n'
            'border_selected = "#555555"\n'
            'code = "#444444"\n'
            'highlight = "#333333"\n'
            'nickname = "#222222"\n'
            'selection = "#111111"\n'
            'timestamp = "#aaaaaa"\n'
            'topic = "#bbbbbb"\n'
            'url = "#cccccc"\n\n'
            "  [buffer.server_messages]\n"
            '  default = "#dddddd"\n\n'
            "[buttons.primary]\n"
            'background = "#ff0000"\n'
            'background_hover = "#ee0000"\n'
            'background_selected = "#dd0000"\n'
            'background_selected_hover = "#cc0000"\n\n'
            "[buttons.secondary]\n"
            'background = "#666666"\n'
            'background_hover = "#777777"\n'
            'background_selected = "#888888"\n'
            'background_selected_hover = "#999999"\n'
        )
        _write_theme(ext, "Dracula", content=override_content)

        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        loaded = registry.load("Dracula")
        assert loaded.descriptor.source == ThemeSource.EXTERNAL
        assert loaded.descriptor.overrides_bundled is True
        assert "#abcdef" in loaded.css.lower()

        bundled_registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        bundled_loaded = bundled_registry.load("Dracula")
        assert loaded.css != bundled_loaded.css

    def test_override_descriptor_flags_bundled(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "Dracula")
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        descriptor = registry.resolve("Dracula")
        assert descriptor is not None
        assert descriptor.overrides_bundled is True
        assert descriptor.source == ThemeSource.EXTERNAL


class TestExternalEditCacheInvalidation:
    def test_same_byte_length_edit_invalidates_cache(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        original = DARK_THEME_CONTENT
        _write_theme(ext, "editable", content=original)

        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        first = registry.load("editable")
        assert first.css.strip().startswith(":root")

        edited = LIGHT_THEME_CONTENT
        _write_theme(ext, "editable", content=edited)
        registry.invalidate("editable")
        second = registry.load("editable")
        assert first.css != second.css


class TestExternalDeletionRestoresBundled:
    def test_deletion_restores_bundled_after_invalidation(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "Dracula")

        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        loaded = registry.load("Dracula")
        assert loaded.descriptor.source == ThemeSource.EXTERNAL

        (ext / "Dracula.toml").unlink()
        registry.invalidate("Dracula")
        restored = registry.load("Dracula")
        assert restored.descriptor.source == ThemeSource.BUNDLED
        assert restored.descriptor.overrides_bundled is False


class TestMalformedExternalOverride:
    def test_malformed_override_raises_parse_failure(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "Dracula", content=MALFORMED_CONTENT)
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        with pytest.raises(ThemeParseFailure, match="parse error"):
            registry.load("Dracula")

    def test_malformed_override_does_not_break_listing(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "Dracula", content=MALFORMED_CONTENT)
        _write_theme(ext, "other-theme")
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "Dracula" in names
        assert "other-theme" in names

    def test_malformed_bundled_raises_parse_failure(self) -> None:
        with pytest.raises(ThemeParseFailure, match="parse error"):
            registry = ThemeRegistry(
                bundled_root=FIXTURES,
                default_theme="malformed",
            )
            registry.load("malformed")


class TestInvalidDefaultFallback:
    def test_invalid_configured_falls_back_to_default(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, default_theme="Dracula")
        loaded = registry.get_fallback("nonexistent-theme")
        assert loaded.descriptor.canonical_name == "Dracula"
        assert loaded.is_dark is True

    def test_both_invalid_falls_to_emergency(self) -> None:
        registry = ThemeRegistry(
            bundled_root=Path("/nonexistent"),
            default_theme="nonexistent-default",
        )
        loaded = registry.get_fallback("also-nonexistent")
        assert loaded.descriptor.canonical_name == "emergency-default"
        assert loaded.descriptor.status == "fallback"
        assert loaded.blog_theme == EMERGENCY_DEFAULT


class TestNamedInvalidation:
    def test_invalidate_single_theme_removes_from_catalog(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        registry.load("Dracula")
        registry.invalidate("Dracula")
        assert registry._catalog is None
        descriptor = registry.resolve("Dracula")
        assert descriptor is not None
        assert descriptor.canonical_name == "Dracula"

    def test_invalidate_single_does_not_affect_others(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        registry.load("Dracula")
        registry.load("Catppuccin Latte")
        registry.invalidate("Dracula")
        assert registry._catalog is None
        assert registry.resolve("Dracula") is not None
        assert registry.resolve("Catppuccin Latte") is not None

    def test_invalidate_evicts_cache_and_rebuilds(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        registry.load("Dracula")
        cache_key = ThemeCache.make_key("Dracula", "bundled")
        assert registry._cache.get(cache_key) is not None
        registry.invalidate("Dracula")
        assert registry._cache.get(cache_key) is None
        assert registry._catalog is None
        loaded = registry.load("Dracula")
        assert registry._cache.get(cache_key) is not None
        assert loaded.descriptor.canonical_name == "Dracula"

    def test_invalidate_unrelated_themes_unaffected(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        first_latte = registry.load("Catppuccin Latte")
        registry.invalidate("Dracula")
        second_latte = registry.load("Catppuccin Latte")
        assert first_latte.css == second_latte.css

    def test_external_override_removal_reveals_bundled(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "Dracula")
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        assert registry.resolve("Dracula").source == ThemeSource.EXTERNAL
        (ext / "Dracula.toml").unlink()
        registry.invalidate("Dracula")
        restored = registry.load("Dracula")
        assert restored.descriptor.source == ThemeSource.BUNDLED
        assert restored.descriptor.overrides_bundled is False


class TestFullInvalidation:
    def test_full_invalidation_clears_catalog_and_cache(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        registry.list_themes()
        assert registry._catalog is not None
        registry.invalidate()
        assert registry._catalog is None

    def test_full_invalidation_forces_reread(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        first = registry.load("Dracula")
        registry.invalidate()
        second = registry.load("Dracula")
        assert first is not second
        assert first.blog_theme == second.blog_theme

    def test_full_invalidation_with_external_restores_bundled(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "Dracula")
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        assert registry.resolve("Dracula").source == ThemeSource.EXTERNAL

        (ext / "Dracula.toml").unlink()
        registry.invalidate()
        assert registry.resolve("Dracula").source == ThemeSource.BUNDLED


class TestCaseCollisionHandling:
    def test_case_collision_rejects_both_in_external(self, tmp_path: Path, case_collision) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        (ext / "MyTheme.toml").write_text(VALID_THEME_CONTENT)
        (ext / "mytheme.toml").write_text(VALID_THEME_CONTENT)
        case_collision(ext, ("MyTheme", "mytheme"))
        registry = ThemeRegistry(
            bundled_root=tmp_path / "empty",
            external_root=ext,
            default_theme="Catppuccin Mocha",
        )
        themes = registry.list_themes()
        names = {t.canonical_name.lower() for t in themes}
        assert "mytheme" not in names

    def test_external_case_collision_with_bundled_rejects_both(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "dracula")
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "dracula" not in names
        assert "Dracula" not in names


class TestSpecialCharNames:
    def test_name_with_spaces_resolves(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "My Custom Theme")
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        descriptor = registry.resolve("My Custom Theme")
        assert descriptor is not None
        assert descriptor.canonical_name == "My Custom Theme"

    def test_name_with_parentheses_resolves(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        descriptor = registry.resolve("Discord (80_ Saturation)")
        assert descriptor is not None

    def test_name_with_underscore_resolves(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        descriptor = registry.resolve("base16-atelier-forest-light")
        assert descriptor is not None


class TestEmergencyFallbackOutput:
    def test_emergency_css_is_valid(self) -> None:
        registry = ThemeRegistry(
            bundled_root=Path("/nonexistent"),
            default_theme="nonexistent",
        )
        loaded = registry.get_fallback("nope")
        assert loaded.css.strip().startswith(":root")
        assert "--blog-bg-page" in loaded.css

    def test_emergency_css_vars_populated(self) -> None:
        registry = ThemeRegistry(
            bundled_root=Path("/nonexistent"),
            default_theme="nonexistent",
        )
        loaded = registry.get_fallback("nope")
        assert isinstance(loaded.css_vars, dict)
        assert len(loaded.css_vars) > 0

    def test_emergency_legacy_vars_populated(self) -> None:
        registry = ThemeRegistry(
            bundled_root=Path("/nonexistent"),
            default_theme="nonexistent",
        )
        loaded = registry.get_fallback("nope")
        assert isinstance(loaded.legacy_vars, dict)
        assert len(loaded.legacy_vars) > 0

    def test_emergency_blog_theme_matches_default(self) -> None:
        registry = ThemeRegistry(
            bundled_root=Path("/nonexistent"),
            default_theme="nonexistent",
        )
        loaded = registry.get_fallback("nope")
        assert loaded.blog_theme == EMERGENCY_DEFAULT

    def test_emergency_descriptor_fields(self) -> None:
        registry = ThemeRegistry(
            bundled_root=Path("/nonexistent"),
            default_theme="nonexistent",
        )
        loaded = registry.get_fallback("nope")
        assert loaded.descriptor.canonical_name == "emergency-default"
        assert loaded.descriptor.status == "fallback"
        assert loaded.descriptor.source == ThemeSource.BUNDLED
        assert loaded.is_dark is True


class TestErrorTypes:
    def test_theme_not_found_error(self, tmp_path: Path) -> None:
        registry = ThemeRegistry(
            bundled_root=tmp_path / "empty",
            default_theme="nonexistent",
        )
        with pytest.raises(ThemeNotFoundError, match="theme not found"):
            registry.load("nope")

    def test_theme_validation_error_for_bad_names(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        with pytest.raises(ThemeValidationError):
            registry.resolve("/etc/passwd")

    def test_theme_parse_failure_for_malformed(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "bad", content=MALFORMED_CONTENT)
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        with pytest.raises(ThemeParseFailure, match="parse error"):
            registry.load("bad")

    def test_theme_load_error_for_missing_file(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "temp")
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        registry.load("temp")
        (ext / "temp.toml").unlink()
        registry.invalidate("temp")
        registry._rebuild_catalog()
        registry._catalog.pop("temp", None)
        with pytest.raises(ThemeNotFoundError):
            registry.load("temp")


class TestLoggingBehavior:
    def test_fallback_logs_warning(self, tmp_path: Path, caplog) -> None:
        import logging

        with caplog.at_level(logging.WARNING, logger="app.themes.registry"):
            registry = ThemeRegistry(
                bundled_root=Path("/nonexistent"),
                default_theme="nonexistent-default",
            )
            registry.get_fallback("also-bad")
        assert "fallback activation" in caplog.text
        assert "emergency-default" in caplog.text


class TestNoAbsolutePathsInPublicAPI:
    def test_descriptor_no_path_attribute(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        themes = registry.list_themes()
        for theme in themes:
            assert not hasattr(theme, "path")
            assert not hasattr(theme, "file_path")

    def test_loaded_theme_descriptor_no_path(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        loaded = registry.load("Dracula")
        assert not hasattr(loaded.descriptor, "path")
        assert not hasattr(loaded.descriptor, "file_path")

    def test_descriptor_fields_are_safe(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        themes = registry.list_themes()
        for theme in themes:
            assert isinstance(theme.canonical_name, str)
            assert isinstance(theme.source, ThemeSource)
            assert isinstance(theme.status, str)
            assert isinstance(theme.warnings, tuple)


class TestCanonicalNameNormalization:
    def test_exact_lookup(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        descriptor = registry.resolve("Dracula")
        assert descriptor is not None
        assert descriptor.canonical_name == "Dracula"

    def test_case_insensitive_lookup(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        descriptor = registry.resolve("dracula")
        assert descriptor is not None
        assert descriptor.canonical_name == "Dracula"

    def test_case_insensitive_all_caps(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        descriptor = registry.resolve("DRACULA")
        assert descriptor is not None
        assert descriptor.canonical_name == "Dracula"

    def test_toml_suffix_stripped(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        descriptor = registry.resolve("Dracula.toml")
        assert descriptor is not None
        assert descriptor.canonical_name == "Dracula"

    def test_default_fallback(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, default_theme="Catppuccin Mocha")
        loaded = registry.get_fallback("nonexistent-theme")
        assert loaded.descriptor.canonical_name == "Catppuccin Mocha"

    def test_alias_catppuccin_mocha(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        descriptor = registry.resolve("catppuccin-mocha")
        assert descriptor is not None
        assert descriptor.canonical_name == "Catppuccin Mocha"

    def test_alias_rose_pine(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        descriptor = registry.resolve("rose-pine")
        assert descriptor is not None
        assert descriptor.canonical_name == "Rose Pine"

    def test_alias_tokyo_night_storm(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        descriptor = registry.resolve("tokyo-night-storm")
        assert descriptor is not None
        assert descriptor.canonical_name == "Tokyo Night Storm"

    def test_name_with_spaces_resolves(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        descriptor = registry.resolve("Catppuccin Mocha")
        assert descriptor is not None
        assert descriptor.canonical_name == "Catppuccin Mocha"

    def test_name_with_parentheses_resolves(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        descriptor = registry.resolve("Discord (80_ Saturation)")
        assert descriptor is not None

    def test_invalid_name_raises_validation_error(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        with pytest.raises(ThemeValidationError):
            registry.resolve("/etc/passwd")

    def test_empty_name_raises_validation_error(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        with pytest.raises(ThemeValidationError):
            registry.resolve("")

    def test_normalize_theme_name_strips_toml(self) -> None:
        from app.themes.resources import normalize_theme_name

        assert normalize_theme_name("theme.toml") == "theme"
        assert normalize_theme_name("theme.test.toml") == "theme.test"

    def test_normalize_theme_name_preserves_valid(self) -> None:
        from app.themes.resources import normalize_theme_name

        assert normalize_theme_name("my-theme") == "my-theme"
        assert normalize_theme_name("Catppuccin Mocha") == "Catppuccin Mocha"


class TestPackageResourceAbstraction:
    def test_default_registry_uses_package_resources(self) -> None:
        registry = ThemeRegistry()
        assert registry._use_package_resources is True

    def test_explicit_bundled_root_uses_filesystem(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        assert registry._use_package_resources is False

    def test_default_registry_lists_bundled_themes(self) -> None:
        registry = ThemeRegistry()
        themes = registry.list_themes()
        assert len(themes) == 50

    def test_default_registry_loads_dark_theme(self) -> None:
        registry = ThemeRegistry()
        loaded = registry.load("Dracula")
        assert loaded.is_dark is True
        assert loaded.css.strip().startswith(":root")

    def test_default_registry_loads_light_theme(self) -> None:
        registry = ThemeRegistry()
        loaded = registry.load("Catppuccin Latte")
        assert loaded.is_dark is False

    def test_theme_resource_has_read_bytes(self) -> None:
        from app.themes.resources import discover_bundled_package

        themes = discover_bundled_package()
        for theme in themes:
            assert theme.resource is not None
            data = theme.resource.read_bytes()
            assert len(data) > 0

    def test_theme_file_info_read_bytes_via_resource(self) -> None:
        from app.themes.resources import discover_bundled_package

        themes = discover_bundled_package()
        for theme in themes:
            data = theme.read_bytes()
            assert len(data) > 0


class TestCacheFingerprint:
    def test_bundled_uses_content_hash(self) -> None:
        from app.themes.registry import _compute_fingerprint
        from app.themes.resources import ThemeSource

        fp = _compute_fingerprint(b"test data", ThemeSource.BUNDLED, 0.0, 9)
        assert len(fp) == 64
        assert fp == _compute_fingerprint(b"test data", ThemeSource.BUNDLED, 0.0, 9)

    def test_external_uses_mtime_size(self) -> None:
        from app.themes.registry import _compute_fingerprint
        from app.themes.resources import ThemeSource

        fp = _compute_fingerprint(b"test", ThemeSource.EXTERNAL, 1234567890.0, 4)
        assert fp == "1234567890.0:4"

    def test_cache_entry_has_fingerprint(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        registry.load("Dracula")
        cache_key = ThemeCache.make_key("Dracula", "bundled")
        entry = registry._cache.get(cache_key)
        assert entry is not None
        assert entry.source_fingerprint != ""
        assert len(entry.source_fingerprint) == 64


class TestExternalEditFollowedByNamedInvalidation:
    def test_edit_then_invalidate_name_reloads_fresh(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "mutable", content=DARK_THEME_CONTENT)

        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        first = registry.load("mutable")
        first_css = first.css

        _write_theme(ext, "mutable", content=LIGHT_THEME_CONTENT)
        registry.invalidate("mutable")
        second = registry.load("mutable")

        assert first_css != second.css
        assert second.is_dark is False


class TestExternalAdditionFollowedByFullInvalidation:
    def test_new_theme_appears_after_full_invalidate(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "original-theme")

        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        names_before = [t.canonical_name for t in registry.list_themes()]
        assert "new-theme" not in names_before

        _write_theme(ext, "new-theme", content=LIGHT_THEME_CONTENT)
        registry.invalidate()

        names_after = [t.canonical_name for t in registry.list_themes()]
        assert "new-theme" in names_after
        loaded = registry.load("new-theme")
        assert loaded.descriptor.source == ThemeSource.EXTERNAL


class TestOverrideReplacementAfterInvalidation:
    def test_replace_override_invalidation_picks_up_new_content(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        override_v1 = (
            "[general]\n"
            'background = "#aaaaaa"\n'
            'border = "#bbbbbb"\n'
            'horizontal_rule = "#cccccc"\n'
            'unread_indicator = "#dddddd"\n\n'
            "[text]\n"
            'primary = "#111111"\n'
            'secondary = "#222222"\n'
            'tertiary = "#333333"\n'
            'success = "#444444"\n'
            'error = "#555555"\n\n'
            "[buffer]\n"
            'action = "#666666"\n'
            'background = "#777777"\n'
            'background_text_input = "#888888"\n'
            'background_title_bar = "#999999"\n'
            'border = "#aaaaaa"\n'
            'border_selected = "#bbbbbb"\n'
            'code = "#cccccc"\n'
            'highlight = "#dddddd"\n'
            'nickname = "#eeeeee"\n'
            'selection = "#ffffff"\n'
            'timestamp = "#000000"\n'
            'topic = "#111111"\n'
            'url = "#222222"\n\n'
            "  [buffer.server_messages]\n"
            '  default = "#333333"\n\n'
            "[buttons.primary]\n"
            'background = "#444444"\n'
            'background_hover = "#555555"\n'
            'background_selected = "#666666"\n'
            'background_selected_hover = "#777777"\n\n'
            "[buttons.secondary]\n"
            'background = "#888888"\n'
            'background_hover = "#999999"\n'
            'background_selected = "#aaaaaa"\n'
            'background_selected_hover = "#bbbbbb"\n'
        )
        override_v2 = (
            "[general]\n"
            'background = "#ff00ff"\n'
            'border = "#00ff00"\n'
            'horizontal_rule = "#0000ff"\n'
            'unread_indicator = "#ffff00"\n\n'
            "[text]\n"
            'primary = "#ff0000"\n'
            'secondary = "#00ff00"\n'
            'tertiary = "#0000ff"\n'
            'success = "#ffff00"\n'
            'error = "#ff00ff"\n\n'
            "[buffer]\n"
            'action = "#00ffff"\n'
            'background = "#111111"\n'
            'background_text_input = "#222222"\n'
            'background_title_bar = "#333333"\n'
            'border = "#444444"\n'
            'border_selected = "#555555"\n'
            'code = "#666666"\n'
            'highlight = "#777777"\n'
            'nickname = "#888888"\n'
            'selection = "#999999"\n'
            'timestamp = "#aaaaaa"\n'
            'topic = "#bbbbbb"\n'
            'url = "#cccccc"\n\n'
            "  [buffer.server_messages]\n"
            '  default = "#dddddd"\n\n'
            "[buttons.primary]\n"
            'background = "#eeeeee"\n'
            'background_hover = "#ffffff"\n'
            'background_selected = "#000000"\n'
            'background_selected_hover = "#111111"\n\n'
            "[buttons.secondary]\n"
            'background = "#222222"\n'
            'background_hover = "#333333"\n'
            'background_selected = "#444444"\n'
            'background_selected_hover = "#555555"\n'
        )

        _write_theme(ext, "Dracula", content=override_v1)
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        loaded_v1 = registry.load("Dracula")
        assert loaded_v1.descriptor.source == ThemeSource.EXTERNAL
        assert "#aaaaaa" in loaded_v1.css.lower() or "#aaaaaa" in loaded_v1.css

        _write_theme(ext, "Dracula", content=override_v2)
        registry.invalidate("Dracula")
        loaded_v2 = registry.load("Dracula")
        assert loaded_v2.descriptor.source == ThemeSource.EXTERNAL
        assert "#ff00ff" in loaded_v2.css.lower() or "#ff00ff" in loaded_v2.css
        assert loaded_v1.css != loaded_v2.css


class TestNamedInvalidationClearsBothCacheVariants:
    def test_bundled_then_external_invalidate_clears_both(self, tmp_path: Path) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        loaded_bundled = registry.load("Dracula")
        assert loaded_bundled.descriptor.source == ThemeSource.BUNDLED
        bundled_key = ThemeCache.make_key("Dracula", "bundled")
        assert registry._cache.get(bundled_key) is not None

        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "Dracula")

        registry2 = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        loaded_external = registry2.load("Dracula")
        assert loaded_external.descriptor.source == ThemeSource.EXTERNAL
        external_key = ThemeCache.make_key("Dracula", "external")
        assert registry2._cache.get(external_key) is not None

        registry2.invalidate("Dracula")
        assert registry2._cache.get(external_key) is None
        assert registry2._cache.get(bundled_key) is None
        assert registry2._catalog is None

        restored = registry2.load("Dracula")
        assert restored.descriptor.source == ThemeSource.EXTERNAL


class TestDefaultAliasAndTomlSuffixResolution:
    def test_alias_resolves(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        descriptor = registry.resolve("catppuccin-mocha")
        assert descriptor is not None
        assert descriptor.canonical_name == "Catppuccin Mocha"

    def test_toml_suffix_stripped(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        descriptor = registry.resolve("Dracula.toml")
        assert descriptor is not None
        assert descriptor.canonical_name == "Dracula"


class TestEmergencyFallbackCompleteVariableOutput:
    def test_all_css_vars_present(self) -> None:
        registry = ThemeRegistry(
            bundled_root=Path("/nonexistent"),
            default_theme="nonexistent",
        )
        loaded = registry.get_fallback("nope")
        for key in CSS_VARS.values():
            assert key in loaded.css_vars, f"missing css_var: {key}"
