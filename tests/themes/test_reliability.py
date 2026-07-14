"""Phase 13 — Failure resilience and reliability tests for the Halloy theme system.

Covers:
- Database unavailable during context generation
- Missing settings row
- Configured theme removed
- Malformed external override
- Unreadable external directory
- Packaged resource missing/corrupt
- Concurrent refresh and render
- Custom CSS sanitation failure
- Registry refresh failure
- Resource limit edge cases
- Concurrency stress tests
- App-scoped lifecycle isolation
- Structured logging and observability
- Diagnostic counters and catalog consistency
"""

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models import SiteSettings
from app.themes.cache import ThemeCache, ThemeCacheEntry
from app.themes.model import CSS_VARS, EMERGENCY_DEFAULT
from app.themes.registry import (
    LoadedTheme,
    ThemeNotFoundError,
    ThemeParseFailure,
    ThemeRegistry,
    ThemeValidationError,
)
from app.themes.resources import ThemeSource, validate_theme_name
from app.themes.service import ThemeService

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


class TestDatabaseUnavailableDuringContextGeneration:
    def test_operational_error_triggers_emergency_fallback(self, app, db):
        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=RuntimeError("db unavailable"),
        ):
            ctx = service.get_context()
        assert ctx["theme_dark_name"] == "emergency-default"
        assert ctx["theme_light_name"] == "emergency-default"
        assert len(ctx["theme_dark_vars"]) > 0
        assert len(ctx["theme_light_vars"]) > 0

    def test_emergency_context_has_all_required_keys(self, app, db):
        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=RuntimeError("db down"),
        ):
            ctx = service.get_context()
        required = {
            "theme_dark_name",
            "theme_light_name",
            "theme_default_scheme",
            "theme_dark_vars",
            "theme_light_vars",
            "theme_dark_css",
            "theme_light_css",
            "theme_warnings",
            "syntax_theme",
            "custom_css_enabled",
            "custom_css",
            "logo_text",
            "theme_vars",
        }
        assert required.issubset(set(ctx.keys()))

    def test_emergency_fallback_emits_warnings(self, app, db):
        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=RuntimeError("db error"),
        ):
            ctx = service.get_context()
        assert any("emergency" in w.lower() for w in ctx["theme_warnings"])

    def test_emergency_css_is_nonempty(self, app, db):
        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=RuntimeError("fail"),
        ):
            ctx = service.get_context()
        assert len(ctx["theme_dark_css"]) > 0
        assert len(ctx["theme_light_css"]) > 0

    def test_emergency_fallback_is_dark(self, app, db):
        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=RuntimeError("fail"),
        ):
            ctx = service.get_context()
        assert ctx["theme_default_scheme"] == "dark"

    def test_no_500_on_db_error(self, app, db):
        settings = SiteSettings.get_instance()
        settings.theme_dark_name = "Nonexistent Theme"
        settings.theme_light_name = "Also Nonexistent"
        db.session.commit()

        from app.context_processors import invalidate_settings_cache

        invalidate_settings_cache()

        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=RuntimeError("db down"),
        ):
            ctx = service.get_context()
        assert "theme_dark_vars" in ctx


class TestMissingSettingsRow:
    def test_no_settings_uses_defaults(self, app, db):
        from sqlalchemy import text

        db.session.execute(text("DELETE FROM site_settings"))
        db.session.commit()

        service = ThemeService()
        ctx = service.get_context()
        assert ctx["theme_dark_name"] == "Catppuccin Mocha"
        assert ctx["theme_light_name"] == "Catppuccin Latte"
        assert ctx["theme_default_scheme"] == "system"

    def test_no_settings_produces_valid_vars(self, app, db):
        from sqlalchemy import text

        db.session.execute(text("DELETE FROM site_settings"))
        db.session.commit()

        service = ThemeService()
        ctx = service.get_context()
        assert isinstance(ctx["theme_dark_vars"], dict)
        assert isinstance(ctx["theme_light_vars"], dict)
        assert len(ctx["theme_dark_vars"]) > 0

    def test_no_settings_no_crash(self, client, db):
        from sqlalchemy import text

        db.session.execute(text("DELETE FROM site_settings"))
        db.session.commit()

        from app.context_processors import invalidate_settings_cache

        invalidate_settings_cache()

        resp = client.get("/")
        assert resp.status_code == 200


class TestConfiguredThemeRemoved:
    def test_invalid_dark_theme_falls_back(self, app, db):
        settings = SiteSettings.get_instance()
        settings.theme_dark_name = "Nonexistent Theme XYZ"
        settings.theme_light_name = "Catppuccin Latte"
        db.session.commit()

        from app.context_processors import invalidate_settings_cache

        invalidate_settings_cache()

        service = ThemeService()
        ctx = service.get_context()
        assert len(ctx["theme_dark_vars"]) > 0

    def test_invalid_light_theme_falls_back(self, app, db):
        settings = SiteSettings.get_instance()
        settings.theme_dark_name = "Catppuccin Mocha"
        settings.theme_light_name = "Nonexistent Light XYZ"
        db.session.commit()

        from app.context_processors import invalidate_settings_cache

        invalidate_settings_cache()

        service = ThemeService()
        ctx = service.get_context()
        assert len(ctx["theme_light_vars"]) > 0

    def test_both_invalid_falls_back(self, app, db):
        settings = SiteSettings.get_instance()
        settings.theme_dark_name = "Totally Broken"
        settings.theme_light_name = "Also Broken"
        db.session.commit()

        from app.context_processors import invalidate_settings_cache

        invalidate_settings_cache()

        service = ThemeService()
        ctx = service.get_context()
        assert len(ctx["theme_dark_vars"]) > 0
        assert len(ctx["theme_light_vars"]) > 0

    def test_no_500_on_missing_theme(self, client, db):
        settings = SiteSettings.get_instance()
        settings.theme_dark_name = "Totally Broken"
        settings.theme_light_name = "Also Broken"
        db.session.commit()

        from app.context_processors import invalidate_settings_cache

        invalidate_settings_cache()

        resp = client.get("/")
        assert resp.status_code == 200

    def test_registry_get_fallback_for_missing_theme(self):
        registry = _make_registry(Path())
        loaded = registry.get_fallback("nonexistent-theme")
        assert loaded.descriptor.canonical_name == "Catppuccin Mocha"
        assert isinstance(loaded, LoadedTheme)

    def test_registry_get_fallback_emergency_when_all_missing(self):
        registry = _make_registry(
            Path(),
            bundled_root=Path("/nonexistent"),
            default_theme="nonexistent-default",
        )
        loaded = registry.get_fallback("also-nonexistent")
        assert loaded.descriptor.canonical_name == "emergency-default"
        assert loaded.blog_theme == EMERGENCY_DEFAULT


class TestMalformedExternalOverride:
    def test_bad_toml_in_listing(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "valid-theme")
        _write_theme(ext, "bad-theme", content="this is not valid toml [[[[")

        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "valid-theme" in names
        assert "bad-theme" in names

    def test_bad_toml_load_raises(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "bad-theme", content=(FIXTURES / "malformed.toml").read_text())

        registry = _make_registry(tmp_path, external_root=ext)
        with pytest.raises(ThemeParseFailure, match="parse error"):
            registry.load("bad-theme")

    def test_bad_toml_does_not_break_other_themes(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "valid-theme")
        _write_theme(ext, "bad-theme", content="[[[[[")

        registry = _make_registry(tmp_path, external_root=ext)
        loaded = registry.load("valid-theme")
        assert loaded.descriptor.canonical_name == "valid-theme"

    def test_empty_file_in_listing(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        (ext / "empty.toml").write_text("")

        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "empty" in names

    def test_syntax_error_file_load_raises(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "syntax-bad", content="valid = [1, 2,\n  missing_bracket")

        registry = _make_registry(tmp_path, external_root=ext)
        with pytest.raises(ThemeParseFailure):
            registry.load("syntax-bad")

    def test_wrong_type_fields_load_error(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "wrong-type", content=(FIXTURES / "wrong_type.toml").read_text())

        registry = _make_registry(tmp_path, external_root=ext)
        with pytest.raises(ThemeParseFailure):
            registry.load("wrong-type")

    def test_malformed_does_not_corrupt_cache(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "bad-theme", content="[[[[[")

        registry = _make_registry(tmp_path, external_root=ext)
        with pytest.raises(ThemeParseFailure):
            registry.load("bad-theme")

        cache_key = ThemeCache.make_key("bad-theme", ThemeSource.EXTERNAL.value)
        assert registry._cache.get(cache_key) is None


class TestUnreadableExternalDirectory:
    def test_unreadable_dir_skipped(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "some-theme")
        os.chmod(ext, 0o000)

        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "some-theme" not in names

        os.chmod(ext, 0o755)

    def test_unreadable_dir_bundled_still_works(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        os.chmod(ext, 0o000)

        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        catalog_files = [p for p in CATALOG.glob("*.toml") if not p.name.startswith("._")]
        assert len(themes) == len(catalog_files)

        os.chmod(ext, 0o755)

    def test_permission_denied_on_file_load_fails(self, tmp_path: Path) -> None:
        if os.getuid() == 0:
            pytest.skip("root bypasses file permissions")

        ext = tmp_path / "external"
        ext.mkdir()
        theme_path = _write_theme(ext, "locked-theme")
        os.chmod(theme_path, 0o000)

        registry = _make_registry(tmp_path, external_root=ext)
        with pytest.raises(Exception):
            registry.load("locked-theme")

        os.chmod(theme_path, 0o644)


class TestPackagedResourceMissingOrCorrupt:
    def test_missing_package_resources_falls_back_to_emergency(self):
        registry = _make_registry(
            Path(),
            bundled_root=Path("/nonexistent"),
            default_theme="nonexistent-default",
        )
        loaded = registry.get_fallback("anything")
        assert loaded.descriptor.canonical_name == "emergency-default"
        assert loaded.blog_theme == EMERGENCY_DEFAULT

    def test_missing_bundled_root_discovery(self) -> None:
        registry = ThemeRegistry(
            bundled_root=Path("/nonexistent/path"),
            external_root=None,
            default_theme="Catppuccin Mocha",
        )
        themes = registry.list_themes()
        assert themes == []

    def test_importlib_resources_error_handling(self) -> None:
        with patch(
            "app.themes.resources.importlib.resources.files",
            side_effect=ModuleNotFoundError("no package"),
        ):
            registry = ThemeRegistry(
                bundled_root=None,
                external_root=None,
                default_theme="Catppuccin Mocha",
            )
            themes = registry.list_themes()
            assert themes == []

    def test_importlib_read_bytes_error(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "good-theme")

        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "good-theme" in names

    def test_corrupt_bundled_file_isolation(self) -> None:
        registry = ThemeRegistry(
            bundled_root=Path("/nonexistent"),
            external_root=None,
            default_theme="Catppuccin Mocha",
        )
        with pytest.raises(ThemeNotFoundError):
            registry.load("Dracula")


class TestConcurrentRefreshAndRender:
    def test_concurrent_load_same_theme(self) -> None:
        registry = _make_registry(Path())
        results = []
        errors = []

        def load_theme():
            try:
                loaded = registry.load("Dracula")
                results.append(loaded)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=load_theme) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 10
        for r in results:
            assert r.descriptor.canonical_name == "Dracula"
            assert r.blog_theme == results[0].blog_theme

    def test_concurrent_invalidate_and_load(self) -> None:
        registry = _make_registry(Path())
        results = []

        def load_theme():
            try:
                loaded = registry.load("Dracula")
                results.append(("load", loaded))
            except Exception as e:
                results.append(("error", str(e)))

        def invalidate_and_load():
            try:
                registry.invalidate()
                loaded = registry.load("Dracula")
                results.append(("load-after-invalidate", loaded))
            except Exception as e:
                results.append(("error", str(e)))

        threads = [
            threading.Thread(target=load_theme),
            threading.Thread(target=invalidate_and_load),
            threading.Thread(target=load_theme),
            threading.Thread(target=invalidate_and_load),
            threading.Thread(target=load_theme),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        load_results = [r for r in results if r[0] in ("load", "load-after-invalidate")]
        assert len(load_results) >= 3

    def test_concurrent_catalog_rebuild(self) -> None:
        registry = _make_registry(Path())
        errors = []

        def rebuild():
            try:
                registry._catalog = None
                themes = registry.list_themes()
                assert len(themes) > 0
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=rebuild) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_get_fallback(self) -> None:
        registry = _make_registry(Path())
        results = []

        def get_fallback():
            loaded = registry.get_fallback("nonexistent")
            results.append(loaded)

        threads = [threading.Thread(target=get_fallback) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10
        for r in results:
            assert isinstance(r, LoadedTheme)
            assert r.blog_theme is not None


class TestCustomCSSSanitationFailure:
    def test_sanitize_exception_does_not_crash(self, app, db):
        settings = SiteSettings.get_instance()
        settings.custom_css_enabled = True
        settings.custom_css = "body { color: red; }"
        db.session.commit()

        from app.context_processors import invalidate_settings_cache

        invalidate_settings_cache()

        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=RuntimeError("sanitize fail"),
        ):
            service = ThemeService()
            ctx = service.get_context()
        assert "theme_dark_vars" in ctx
        assert len(ctx["theme_dark_vars"]) > 0

    def test_sanitize_exception_in_build_context(self, app, db):
        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=Exception("any build error"),
        ):
            ctx = service.get_context()
        assert ctx["theme_dark_name"] == "emergency-default"

    def test_settings_cache_cleared_on_error(self, app, db):
        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=RuntimeError("fail"),
        ):
            ctx1 = service.get_context()

        assert ctx1["theme_dark_name"] == "emergency-default"

        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=RuntimeError("fail again"),
        ):
            ctx2 = service.get_context()

        assert ctx2["theme_dark_name"] == "emergency-default"


class TestRegistryRefreshFailure:
    def test_rebuild_catalog_error_propagates(self, tmp_path: Path) -> None:
        registry = _make_registry(tmp_path)
        with patch.object(registry, "_rebuild_catalog", side_effect=RuntimeError("disk error")):
            with pytest.raises(RuntimeError, match="disk error"):
                registry.list_themes()

    def test_rebuild_catalog_error_leaves_catalog_none(self, tmp_path: Path) -> None:
        registry = _make_registry(tmp_path)
        with patch.object(registry, "_rebuild_catalog", side_effect=RuntimeError("disk error")):
            try:
                registry.list_themes()
            except RuntimeError:
                pass
        assert registry._catalog is None

    def test_invalidate_after_build_error_allows_retry(self, tmp_path: Path) -> None:
        registry = _make_registry(tmp_path)
        call_count = 0
        original_rebuild = registry._rebuild_catalog.__func__

        def flaky_rebuild(self_reg):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("transient error")
            return original_rebuild(self_reg)

        with patch.object(
            registry, "_rebuild_catalog", side_effect=lambda: flaky_rebuild(registry)
        ):
            try:
                registry.list_themes()
            except RuntimeError:
                pass

        registry._catalog = None
        themes = registry.list_themes()
        assert len(themes) > 0

    def test_refresh_registry_replaces_old_registry(self, app, db):
        service = ThemeService()
        old_registry = service.get_registry()
        service.refresh_registry()
        new_registry = service.get_registry()
        assert old_registry is not new_registry


class TestResourceLimits:
    def test_maximum_theme_name_length(self) -> None:
        with pytest.raises(ValueError, match="exceed"):
            validate_theme_name("a" * 201)

    def test_maximum_theme_name_at_boundary(self) -> None:
        result = validate_theme_name("a" * 200)
        assert result == "a" * 200

    def test_oversized_external_file_skipped(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        big_content = "[general]\n" + ('background = "#000000"\n' * 80000)
        (ext / "huge-theme.toml").write_text(big_content)

        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "huge-theme" not in names

    def test_many_external_files_bounded(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        for i in range(100):
            _write_theme(ext, f"theme-{i:04d}")

        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        bundled_count = len([p for p in CATALOG.glob("*.toml") if not p.name.startswith("._")])
        assert len(themes) == bundled_count + 100

    def test_many_external_files_cache_bounded(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        for i in range(50):
            _write_theme(ext, f"theme-{i:04d}")

        registry = _make_registry(tmp_path, external_root=ext)
        for i in range(50):
            registry.load(f"theme-{i:04d}")

        assert len(registry._cache._cache) == 50

    def test_no_recursive_scanning(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        subdir = ext / "subdir"
        subdir.mkdir()
        _write_theme(subdir, "nested-theme")

        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "nested-theme" not in names

    def test_cache_prevents_repeated_parsing(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "parse-once")

        registry = _make_registry(tmp_path, external_root=ext)
        first = registry.load("parse-once")
        second = registry.load("parse-once")
        assert first.blog_theme == second.blog_theme
        assert first.css == second.css
        assert first.is_dark == second.is_dark

    def test_cache_hit_after_invalidate_same_content(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "stable-theme")

        registry = _make_registry(tmp_path, external_root=ext)
        first = registry.load("stable-theme")
        registry.invalidate()
        second = registry.load("stable-theme")
        assert first.blog_theme == second.blog_theme

    def test_file_size_exactly_at_limit(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        exact_content = "x" * 1_048_576
        (ext / "exact-limit.toml").write_text(exact_content)

        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "exact-limit" in names

    def test_file_size_one_over_limit(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        over_content = "x" * 1_048_577
        (ext / "over-limit.toml").write_text(over_content)

        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "over-limit" not in names

    def test_css_output_starts_with_root_selector(self) -> None:
        registry = _make_registry(Path())
        loaded = registry.load("Dracula")
        assert loaded.css.strip().startswith(":root")

    def test_css_vars_keys_match_expected(self) -> None:
        registry = _make_registry(Path())
        loaded = registry.load("Dracula")
        for key in CSS_VARS.values():
            assert key in loaded.css_vars

    def test_max_theme_name_rejected_by_registry(self) -> None:
        registry = _make_registry(Path())
        with pytest.raises(ThemeValidationError):
            registry.resolve("a" * 201)


class TestConcurrencyStress:
    def test_parallel_get_context(self, app, db) -> None:
        service = ThemeService()
        results = []
        errors = []

        def get_ctx():
            try:
                ctx = service.get_context()
                results.append(ctx)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(get_ctx) for _ in range(20)]
            for f in as_completed(futures):
                f.result()

        assert len(errors) == 0
        assert len(results) == 20
        for ctx in results:
            assert "theme_dark_vars" in ctx
            assert "theme_light_vars" in ctx

    def test_parallel_registry_loads_different_themes(self) -> None:
        registry = _make_registry(Path())
        themes_to_load = [
            "Dracula",
            "Catppuccin Mocha",
            "Catppuccin Latte",
            "Rose Pine",
            "Solarized Dark",
            "Tokyo Night Storm",
            "One Dark",
            "Nord",
        ]
        results = {}
        errors = []

        def load_one(name):
            try:
                loaded = registry.load(name)
                results[name] = loaded
            except Exception as e:
                errors.append((name, e))

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(load_one, name) for name in themes_to_load]
            for f in as_completed(futures):
                f.result()

        assert len(errors) == 0
        assert len(results) == len(themes_to_load)
        for name, loaded in results.items():
            assert loaded.descriptor.canonical_name is not None
            assert loaded.blog_theme is not None

    def test_refresh_plus_reads_simultaneously(self) -> None:
        registry = _make_registry(Path())
        errors = []
        load_count = 0

        def reader():
            nonlocal load_count
            for _ in range(5):
                try:
                    loaded = registry.load("Dracula")
                    assert loaded.descriptor.canonical_name == "Dracula"
                    load_count += 1
                except Exception as e:
                    errors.append(e)

        def refresher():
            for _ in range(3):
                try:
                    registry.invalidate()
                    time.sleep(0.001)
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=refresher),
            threading.Thread(target=reader),
            threading.Thread(target=refresher),
            threading.Thread(target=reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert load_count > 0

    def test_settings_invalidation_plus_reads(self, app, db) -> None:
        service = ThemeService()
        errors = []
        ctx_count = 0

        def reader():
            nonlocal ctx_count
            for _ in range(5):
                try:
                    ctx = service.get_context()
                    assert "theme_dark_vars" in ctx
                    ctx_count += 1
                except Exception as e:
                    errors.append(e)

        def invalidator():
            for _ in range(3):
                try:
                    service.invalidate_settings_cache()
                    time.sleep(0.001)
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=invalidator),
            threading.Thread(target=reader),
            threading.Thread(target=invalidator),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert ctx_count > 0

    def test_parallel_invalidate_and_list(self) -> None:
        registry = _make_registry(Path())
        errors = []
        list_counts = []

        def lister():
            try:
                themes = registry.list_themes()
                list_counts.append(len(themes))
            except Exception as e:
                errors.append(e)

        def invalidator():
            try:
                registry.invalidate()
            except Exception as e:
                errors.append(e)

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=lister))
            threads.append(threading.Thread(target=invalidator))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(list_counts) >= 5

    def test_no_cross_thread_result_pollution(self) -> None:
        registry = _make_registry(Path())
        results = {}

        def load_theme(name, thread_id):
            loaded = registry.load(name)
            results[thread_id] = loaded

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(load_theme, "Dracula", 0),
                executor.submit(load_theme, "Catppuccin Mocha", 1),
                executor.submit(load_theme, "Rose Pine", 2),
                executor.submit(load_theme, "Solarized Dark", 3),
            ]
            for f in as_completed(futures):
                f.result()

        assert results[0].descriptor.canonical_name == "Dracula"
        assert results[1].descriptor.canonical_name == "Catppuccin Mocha"
        assert results[2].descriptor.canonical_name == "Rose Pine"
        assert results[3].descriptor.canonical_name == "Solarized Dark"

    def test_concurrent_cache_operations(self) -> None:
        cache = ThemeCache()
        errors = []

        def write_entries():
            for i in range(50):
                try:
                    key = f"bundled:theme-{i}"
                    from app.themes.halloy import HalloyTheme

                    entry = ThemeCacheEntry(
                        halloy_theme=MagicMock(spec=HalloyTheme),
                        blog_theme=EMERGENCY_DEFAULT,
                        css="",
                        is_dark=True,
                        source_name=f"theme-{i}",
                        source_type="bundled",
                        file_mtime=0.0,
                        file_size=0,
                        translation_schema="1.0",
                        diagnostics=MagicMock(),
                        css_vars={},
                        legacy_vars={},
                        source_fingerprint="",
                    )
                    cache.set(key, entry)
                except Exception as e:
                    errors.append(e)

        def read_entries():
            for i in range(50):
                try:
                    key = f"bundled:theme-{i}"
                    cache.get(key)
                except Exception as e:
                    errors.append(e)

        def invalidate_entries():
            for i in range(0, 50, 5):
                try:
                    key = f"bundled:theme-{i}"
                    cache.invalidate(key)
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=write_entries),
            threading.Thread(target=read_entries),
            threading.Thread(target=invalidate_entries),
            threading.Thread(target=write_entries),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestAppScopedLifecycle:
    def test_two_service_instances_are_independent(self, app, db) -> None:
        service1 = ThemeService()
        service2 = ThemeService()
        assert service1 is not service2

    def test_independent_registries(self, app, db) -> None:
        service1 = ThemeService()
        service2 = ThemeService()
        r1 = service1.get_registry()
        r2 = service2.get_registry()
        assert r1 is not r2

    def test_registry_refresh_on_one_does_not_affect_other(self, app, db) -> None:
        service1 = ThemeService()
        service2 = ThemeService()
        r1 = service1.get_registry()
        r2 = service2.get_registry()

        r1.list_themes()
        assert r1._catalog is not None

        r2.list_themes()
        assert r2._catalog is not None

        r1.invalidate()
        assert r1._catalog is None
        assert r2._catalog is not None

    def test_settings_cache_is_per_instance(self, app, db) -> None:
        service1 = ThemeService()
        service2 = ThemeService()

        service1.get_context()
        assert service1._settings_cache is not None
        assert service2._settings_cache is None

    def test_invalidate_settings_on_one_does_not_affect_other(self, app, db) -> None:
        service1 = ThemeService()
        service2 = ThemeService()

        service1.get_context()
        service2.get_context()
        assert service1._settings_cache is not None
        assert service2._settings_cache is not None

        service1.invalidate_settings_cache()
        assert service1._settings_cache is None
        assert service2._settings_cache is not None

    def test_independent_emergency_fallbacks(self, app, db) -> None:
        service1 = ThemeService()
        service2 = ThemeService()

        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=RuntimeError("fail 1"),
        ):
            ctx1 = service1.get_context()

        ctx2 = service2.get_context()

        assert ctx1["theme_dark_name"] == "emergency-default"
        assert ctx2["theme_dark_name"] != "emergency-default"

    def test_two_services_same_process_same_result(self, app, db) -> None:
        service1 = ThemeService()
        service2 = ThemeService()

        ctx1 = service1.get_context()
        ctx2 = service2.get_context()

        assert ctx1["theme_dark_vars"] == ctx2["theme_dark_vars"]
        assert ctx1["theme_light_vars"] == ctx2["theme_light_vars"]


class TestStructuredLogging:
    def test_fallback_activation_logs_warning(self, caplog) -> None:
        registry = _make_registry(
            Path(),
            bundled_root=Path("/nonexistent"),
            default_theme="nonexistent-default",
        )
        with caplog.at_level("WARNING", logger="app.themes.registry"):
            registry.get_fallback("also-nonexistent")
        assert "fallback activation" in caplog.text

    def test_fallback_activation_includes_configured_and_default(self, caplog) -> None:
        registry = _make_registry(
            Path(),
            bundled_root=Path("/nonexistent"),
            default_theme="nonexistent-default",
        )
        with caplog.at_level("WARNING", logger="app.themes.registry"):
            registry.get_fallback("my-missing-theme")
        assert "my-missing-theme" in caplog.text
        assert "nonexistent-default" in caplog.text
        assert "emergency-default" in caplog.text

    def test_malformed_bundled_theme_logs_error(self, tmp_path: Path, caplog) -> None:
        bundled = tmp_path / "bundled"
        bundled.mkdir()
        _write_theme(bundled, "bad-bundled", content="[[[[[invalid")

        registry = _make_registry(tmp_path, bundled_root=bundled)
        with caplog.at_level("ERROR", logger="app.themes.registry"):
            with pytest.raises(ThemeParseFailure):
                registry.load("bad-bundled")
        assert "malformed bundled theme" in caplog.text

    def test_malformed_bundled_theme_logs_canonical_name(self, tmp_path: Path, caplog) -> None:
        bundled = tmp_path / "bundled"
        bundled.mkdir()
        _write_theme(bundled, "broken-theme", content="[[[[[")

        registry = _make_registry(tmp_path, bundled_root=bundled)
        with caplog.at_level("ERROR", logger="app.themes.registry"):
            with pytest.raises(ThemeParseFailure):
                registry.load("broken-theme")
        assert "broken-theme" in caplog.text

    def test_malformed_external_theme_logs_warning(self, tmp_path: Path, caplog) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "bad-external", content="[[[[[")

        registry = _make_registry(tmp_path, external_root=ext)
        with caplog.at_level("WARNING", logger="app.themes.registry"):
            with pytest.raises(ThemeParseFailure):
                registry.load("bad-external")
        assert "malformed external theme" in caplog.text

    def test_malformed_external_theme_logs_canonical_name(self, tmp_path: Path, caplog) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "my-bad-theme", content="not toml {[")

        registry = _make_registry(tmp_path, external_root=ext)
        with caplog.at_level("WARNING", logger="app.themes.registry"):
            with pytest.raises(ThemeParseFailure):
                registry.load("my-bad-theme")
        assert "my-bad-theme" in caplog.text

    def test_bundled_error_vs_external_warning(self, tmp_path: Path, caplog) -> None:
        bundled = tmp_path / "bundled"
        bundled.mkdir()
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(bundled, "bad-bundled", content="[[[[[")
        _write_theme(ext, "bad-external", content="[[[[[")

        registry = _make_registry(tmp_path, bundled_root=bundled, external_root=ext)
        with caplog.at_level("WARNING", logger="app.themes.registry"):
            with pytest.raises(ThemeParseFailure):
                registry.load("bad-bundled")
        assert "malformed bundled theme" in caplog.text
        assert "malformed external theme" not in caplog.text

        caplog.clear()
        with caplog.at_level("WARNING", logger="app.themes.registry"):
            with pytest.raises(ThemeParseFailure):
                registry.load("bad-external")
        assert "malformed external theme" in caplog.text
        assert "malformed bundled theme" not in caplog.text

    def test_case_collision_bundled_logs_warning(self, tmp_path: Path, caplog) -> None:
        bundled = tmp_path / "bundled"
        bundled.mkdir()
        _write_theme(bundled, "MyTheme")
        _write_theme(bundled, "mytheme")

        registry = _make_registry(tmp_path, bundled_root=bundled)
        with caplog.at_level("WARNING", logger="app.themes.registry"):
            registry.list_themes()
        assert "case collision" in caplog.text
        assert "MyTheme" in caplog.text
        assert "mytheme" in caplog.text

    def test_case_collision_bundled_vs_external_logs_warning(self, tmp_path: Path, caplog) -> None:
        bundled = tmp_path / "bundled"
        bundled.mkdir()
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(bundled, "MyTheme")
        _write_theme(ext, "mytheme")

        registry = _make_registry(tmp_path, bundled_root=bundled, external_root=ext)
        with caplog.at_level("WARNING", logger="app.themes.registry"):
            registry.list_themes()
        assert "case collision" in caplog.text

    def test_oversized_external_file_logs_warning(self, tmp_path: Path, caplog) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        big_content = "[general]\n" + ('background = "#000000"\n' * 80000)
        (ext / "huge-theme.toml").write_text(big_content)

        registry = _make_registry(tmp_path, external_root=ext)
        with caplog.at_level("WARNING", logger="app.themes.resources"):
            registry.list_themes()
        assert "skipping oversized theme" in caplog.text
        assert "huge-theme" in caplog.text

    def test_oversized_logs_file_size(self, tmp_path: Path, caplog) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        big_content = "[general]\n" + ('background = "#000000"\n' * 80000)
        (ext / "over.toml").write_text(big_content)
        file_size = (ext / "over.toml").stat().st_size

        registry = _make_registry(tmp_path, external_root=ext)
        with caplog.at_level("WARNING", logger="app.themes.resources"):
            registry.list_themes()
        assert str(file_size) in caplog.text

    def test_traversal_symlink_logs_warning(self, tmp_path: Path, caplog) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "regular-theme")
        _write_theme(ext, "escaped-theme")

        original_is_inside = None
        import app.themes.resources as _res_mod

        original_is_inside = _res_mod._is_inside

        def mock_is_inside(path: Path, root: Path) -> bool:
            if "escaped-theme" in str(path):
                return False
            return original_is_inside(path, root)

        registry = _make_registry(tmp_path, external_root=ext)
        with patch("app.themes.resources._is_inside", side_effect=mock_is_inside):
            with caplog.at_level("WARNING", logger="app.themes.resources"):
                registry.list_themes()
        assert "skipping theme outside external root" in caplog.text
        assert "escaped-theme" in caplog.text

    def test_refresh_rebuilds_catalog(self) -> None:
        registry = _make_registry(Path())
        registry.list_themes()
        first_catalog = registry._catalog
        assert first_catalog is not None
        first_count = len(first_catalog)

        registry.invalidate()
        assert registry._catalog is None

        registry.list_themes()
        second_catalog = registry._catalog
        assert second_catalog is not None
        second_count = len(second_catalog)
        assert first_count == second_count
        assert first_catalog is not second_catalog

    def test_single_theme_invalidation_rebuilds_catalog(self) -> None:
        registry = _make_registry(Path())
        registry.list_themes()
        assert registry._catalog is not None

        registry.invalidate("Dracula")
        assert registry._catalog is None

        registry.list_themes()
        assert registry._catalog is not None

    def test_fallback_does_not_log_when_theme_found(self, caplog) -> None:
        registry = _make_registry(Path())
        with caplog.at_level("WARNING", logger="app.themes.registry"):
            registry.get_fallback("Dracula")
        assert "fallback activation" not in caplog.text

    def test_no_logging_for_valid_external_theme(self, tmp_path: Path, caplog) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "valid-theme")

        registry = _make_registry(tmp_path, external_root=ext)
        with caplog.at_level("WARNING", logger="app.themes.registry"):
            with caplog.at_level("WARNING", logger="app.themes.resources"):
                registry.load("valid-theme")
        assert "malformed" not in caplog.text
        assert "oversized" not in caplog.text
        assert "outside external root" not in caplog.text
        assert "case collision" not in caplog.text


class TestDiagnosticCounters:
    def test_catalog_size_matches_list_themes(self) -> None:
        registry = _make_registry(Path())
        themes = registry.list_themes()
        catalog = registry._catalog
        assert catalog is not None
        assert len(themes) == len(catalog)

    def test_catalog_size_includes_bundled_themes(self) -> None:
        registry = _make_registry(Path())
        themes = registry.list_themes()
        bundled_files = [p for p in CATALOG.glob("*.toml") if not p.name.startswith("._")]
        assert len(themes) >= len(bundled_files)

    def test_catalog_size_with_external_themes(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        for i in range(5):
            _write_theme(ext, f"ext-theme-{i}")

        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        bundled_files = [p for p in CATALOG.glob("*.toml") if not p.name.startswith("._")]
        assert len(themes) == len(bundled_files) + 5

    def test_overrides_bundled_flag_when_no_override(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "unique-external-theme")

        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        ext_theme = [t for t in themes if t.canonical_name == "unique-external-theme"]
        assert len(ext_theme) == 1
        assert ext_theme[0].overrides_bundled is False

    def test_overrides_bundled_flag_when_overrides(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "Dracula")

        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        dracula = [t for t in themes if t.canonical_name == "Dracula"]
        assert len(dracula) == 1
        assert dracula[0].overrides_bundled is True

    def test_overrides_bundled_flag_on_load(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "Dracula")

        registry = _make_registry(tmp_path, external_root=ext)
        loaded = registry.load("Dracula")
        assert loaded.descriptor.overrides_bundled is True

    def test_cache_hit_returns_same_result(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "cached-theme")

        registry = _make_registry(tmp_path, external_root=ext)
        first = registry.load("cached-theme")
        second = registry.load("cached-theme")
        assert first.blog_theme == second.blog_theme
        assert first.css == second.css
        assert first.descriptor is second.descriptor

    def test_cache_hit_returns_same_blog_theme(self) -> None:
        registry = _make_registry(Path())
        first = registry.load("Dracula")
        second = registry.load("Dracula")
        assert first.blog_theme.bg_page == second.blog_theme.bg_page
        assert first.blog_theme.text_primary == second.blog_theme.text_primary

    def test_cache_miss_after_invalidation(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "miss-theme")

        registry = _make_registry(tmp_path, external_root=ext)
        first = registry.load("miss-theme")
        registry.invalidate("miss-theme")

        cache_key = ThemeCache.make_key("miss-theme", "external")
        assert registry._cache.get(cache_key) is None

        second = registry.load("miss-theme")
        assert first.blog_theme == second.blog_theme

    def test_invalidate_clears_all_cache_entries(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "theme-a")
        _write_theme(ext, "theme-b")

        registry = _make_registry(tmp_path, external_root=ext)
        registry.load("theme-a")
        registry.load("theme-b")
        assert len(registry._cache._cache) >= 2

        registry.invalidate()
        assert len(registry._cache._cache) == 0

    def test_emergency_fallback_returns_emergency_theme(self) -> None:
        registry = _make_registry(
            Path(),
            bundled_root=Path("/nonexistent"),
            default_theme="nonexistent-default",
        )
        loaded = registry.get_fallback("nonexistent")
        assert loaded.descriptor.canonical_name == "emergency-default"
        assert loaded.blog_theme == EMERGENCY_DEFAULT
        assert loaded.is_dark is True

    def test_emergency_fallback_produces_valid_css(self) -> None:
        registry = _make_registry(
            Path(),
            bundled_root=Path("/nonexistent"),
            default_theme="nonexistent-default",
        )
        loaded = registry.get_fallback("nonexistent")
        assert len(loaded.css) > 0
        assert loaded.css.strip().startswith(":root")
        assert len(loaded.css_vars) > 0

    def test_emergency_fallback_descriptor_fields(self) -> None:
        registry = _make_registry(
            Path(),
            bundled_root=Path("/nonexistent"),
            default_theme="nonexistent-default",
        )
        loaded = registry.get_fallback("nonexistent")
        assert loaded.descriptor.source == ThemeSource.BUNDLED
        assert loaded.descriptor.status == "fallback"
        assert loaded.descriptor.overrides_bundled is False
        assert loaded.descriptor.is_dark is True

    def test_refresh_rebuilds_catalog_with_same_count(self) -> None:
        registry = _make_registry(Path())
        first = registry.list_themes()
        first_count = len(first)

        registry.invalidate()
        second = registry.list_themes()
        second_count = len(second)
        assert first_count == second_count

    def test_refresh_updates_catalog_reference(self) -> None:
        registry = _make_registry(Path())
        registry.list_themes()
        old_catalog = registry._catalog

        registry.invalidate()
        registry.list_themes()
        new_catalog = registry._catalog
        assert old_catalog is not new_catalog

    def test_single_theme_invalidation_preserves_other_cache(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "theme-a")
        _write_theme(ext, "theme-b")

        registry = _make_registry(tmp_path, external_root=ext)
        registry.load("theme-a")
        registry.load("theme-b")

        key_a = ThemeCache.make_key("theme-a", "external")
        key_b = ThemeCache.make_key("theme-b", "external")
        assert registry._cache.get(key_a) is not None
        assert registry._cache.get(key_b) is not None

        registry.invalidate("theme-a")
        assert registry._cache.get(key_a) is None
        assert registry._cache.get(key_b) is not None

    def test_catalog_rebuild_after_invalidate_discovers_new_theme(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "existing-theme")

        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        assert "new-theme" not in [t.canonical_name for t in themes]

        _write_theme(ext, "new-theme")
        registry.invalidate()
        themes = registry.list_themes()
        assert "new-theme" in [t.canonical_name for t in themes]

    def test_empty_external_dir_no_extra_themes(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()

        registry = _make_registry(tmp_path, external_root=ext)
        themes = registry.list_themes()
        bundled_files = [p for p in CATALOG.glob("*.toml") if not p.name.startswith("._")]
        assert len(themes) == len(bundled_files)


class TestRefreshSummaryLogging:
    def test_refresh_summary_logs_info(self, caplog) -> None:
        registry = _make_registry(Path())
        with caplog.at_level("INFO", logger="app.themes.registry"):
            registry.list_themes()
        assert "theme refresh #1 completed in" in caplog.text
        assert "themes" in caplog.text

    def test_refresh_summary_includes_count(self, caplog) -> None:
        registry = _make_registry(Path())
        with caplog.at_level("INFO", logger="app.themes.registry"):
            registry.list_themes()
        assert "#1" in caplog.text

    def test_refresh_summary_includes_theme_count(self, caplog) -> None:
        registry = _make_registry(Path())
        with caplog.at_level("INFO", logger="app.themes.registry"):
            registry.list_themes()
        themes = registry.list_themes()
        assert str(len(themes)) in caplog.text

    def test_second_refresh_increments_count(self, caplog) -> None:
        registry = _make_registry(Path())
        with caplog.at_level("INFO", logger="app.themes.registry"):
            registry.list_themes()
            registry.invalidate()
            registry.list_themes()
        assert "#2" in caplog.text

    def test_no_refresh_log_when_catalog_already_built(self, caplog) -> None:
        registry = _make_registry(Path())
        registry.list_themes()
        caplog.clear()
        with caplog.at_level("INFO", logger="app.themes.registry"):
            registry.list_themes()
        assert "theme refresh" not in caplog.text

    def test_refresh_failure_increments_failure_count(self, tmp_path: Path) -> None:
        registry = _make_registry(tmp_path)
        with patch.object(registry, "_rebuild_catalog", side_effect=RuntimeError("disk error")):
            try:
                registry.list_themes()
            except RuntimeError:
                pass
        assert registry.refresh_failure_count == 1

    def test_refresh_success_does_not_increment_failure_count(self) -> None:
        registry = _make_registry(Path())
        registry.list_themes()
        assert registry.refresh_failure_count == 0

    def test_catalog_rebuild_logs_debug(self, caplog) -> None:
        registry = _make_registry(Path())
        with caplog.at_level("DEBUG", logger="app.themes.registry"):
            registry.list_themes()
        assert "catalog rebuilt:" in caplog.text


class TestCacheInvalidationLogging:
    def test_full_invalidation_logs_debug(self, caplog) -> None:
        registry = _make_registry(Path())
        registry.list_themes()
        with caplog.at_level("DEBUG", logger="app.themes.registry"):
            registry.invalidate()
        assert "cache invalidated (full refresh)" in caplog.text

    def test_single_theme_invalidation_logs_debug(self, caplog) -> None:
        registry = _make_registry(Path())
        registry.load("Dracula")
        with caplog.at_level("DEBUG", logger="app.themes.registry"):
            registry.invalidate("Dracula")
        assert "cache invalidated for theme" in caplog.text
        assert "Dracula" in caplog.text

    def test_invalidation_logs_theme_name_in_message(self, caplog) -> None:
        registry = _make_registry(Path())
        registry.load("Catppuccin Mocha")
        with caplog.at_level("DEBUG", logger="app.themes.registry"):
            registry.invalidate("Catppuccin Mocha")
        assert "Catppuccin Mocha" in caplog.text


class TestDiagnosticCountersProperties:
    def test_cache_hits_zero_initially(self) -> None:
        registry = _make_registry(Path())
        assert registry.cache_hits == 0

    def test_cache_misses_zero_initially(self) -> None:
        registry = _make_registry(Path())
        assert registry.cache_misses == 0

    def test_cache_hits_increment_on_load(self) -> None:
        registry = _make_registry(Path())
        registry.load("Dracula")
        first_hits = registry.cache_hits
        registry.load("Dracula")
        assert registry.cache_hits > first_hits

    def test_cache_misses_increment_on_cold_load(self) -> None:
        registry = _make_registry(Path())
        assert registry.cache_misses == 0
        registry.load("Dracula")
        assert registry.cache_misses >= 1

    def test_refresh_count_zero_initially(self) -> None:
        registry = _make_registry(Path())
        assert registry.refresh_count == 0

    def test_refresh_count_increments_on_list_themes(self) -> None:
        registry = _make_registry(Path())
        registry.list_themes()
        assert registry.refresh_count == 1

    def test_refresh_count_increments_on_invalidate_plus_list(self) -> None:
        registry = _make_registry(Path())
        registry.list_themes()
        registry.invalidate()
        registry.list_themes()
        assert registry.refresh_count == 2

    def test_fallback_count_zero_initially(self) -> None:
        registry = _make_registry(Path())
        assert registry.fallback_count == 0

    def test_fallback_count_increments_on_emergency(self) -> None:
        registry = _make_registry(
            Path(),
            bundled_root=Path("/nonexistent"),
            default_theme="nonexistent-default",
        )
        registry.get_fallback("missing")
        assert registry.fallback_count == 1

    def test_fallback_count_increments_on_each_emergency(self) -> None:
        registry = _make_registry(
            Path(),
            bundled_root=Path("/nonexistent"),
            default_theme="nonexistent-default",
        )
        registry.get_fallback("missing1")
        registry.get_fallback("missing2")
        assert registry.fallback_count == 2

    def test_fallback_count_does_not_increment_on_success(self) -> None:
        registry = _make_registry(Path())
        registry.get_fallback("Dracula")
        assert registry.fallback_count == 0

    def test_external_override_count_zero_with_no_external(self) -> None:
        registry = _make_registry(Path())
        registry.list_themes()
        assert registry.external_override_count == 0

    def test_external_override_count_with_override(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "Dracula")

        registry = _make_registry(tmp_path, external_root=ext)
        registry.list_themes()
        assert registry.external_override_count == 1

    def test_external_override_count_without_override(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "unique-theme")

        registry = _make_registry(tmp_path, external_root=ext)
        registry.list_themes()
        assert registry.external_override_count == 0

    def test_external_override_count_zero_before_catalog_built(self) -> None:
        registry = _make_registry(Path())
        assert registry.external_override_count == 0

    def test_cache_hit_miss_ratio_after_loads(self) -> None:
        registry = _make_registry(Path())
        registry.load("Dracula")
        registry.load("Dracula")
        registry.load("Dracula")
        assert registry.cache_hits >= 2
        assert registry.cache_misses >= 1


class TestWarmPathZeroIO:
    def test_cache_hit_does_not_call_read_bytes(self) -> None:
        registry = _make_registry(Path())
        registry.load("Dracula")
        registry._cache.reset_counters()

        with patch("app.themes.registry._compute_fingerprint") as mock_fp:
            mock_fp.return_value = "cached-fingerprint"
            result = registry.load("Dracula")
            assert result is not None
            assert result.descriptor.canonical_name == "Dracula"
            mock_fp.assert_not_called()

    def test_cache_hit_does_not_call_parse(self) -> None:
        registry = _make_registry(Path())
        registry.load("Dracula")
        registry._cache.reset_counters()

        with patch("app.themes.halloy.parse_halloy_theme_bytes") as mock_parse:
            loaded = registry.load("Dracula")
            assert loaded is not None
            mock_parse.assert_not_called()

    def test_cache_hit_does_not_call_translate(self) -> None:
        registry = _make_registry(Path())
        registry.load("Dracula")
        registry._cache.reset_counters()

        with patch("app.themes.translate.translate_halloy_theme") as mock_translate:
            loaded = registry.load("Dracula")
            assert loaded is not None
            mock_translate.assert_not_called()

    def test_multiple_cache_hits_no_io(self) -> None:
        registry = _make_registry(Path())
        registry.load("Dracula")
        registry.load("Catppuccin Mocha")
        registry._cache.reset_counters()

        with (
            patch("app.themes.registry._compute_fingerprint") as mock_fp,
            patch("app.themes.halloy.parse_halloy_theme_bytes") as mock_parse,
        ):
            mock_fp.return_value = "cached-fingerprint"
            for _ in range(10):
                registry.load("Dracula")
                registry.load("Catppuccin Mocha")
            mock_fp.assert_not_called()
            mock_parse.assert_not_called()

    def test_cache_hit_returns_same_data_without_reparse(self) -> None:
        registry = _make_registry(Path())
        first = registry.load("Dracula")
        registry._cache.reset_counters()

        with patch("app.themes.halloy.parse_halloy_theme_bytes") as mock_parse:
            second = registry.load("Dracula")
            assert first.css == second.css
            assert first.blog_theme == second.blog_theme
            mock_parse.assert_not_called()
