"""Phase 13 performance benchmarks for the Halloy theme system.

Covers cold/warm registry operations, external theme scanning, parse/translate
serialization, theme service context generation, template rendering overhead,
and registry refresh cycles.

All thresholds are generous to tolerate CI variance while catching real regressions.
"""

import time
from pathlib import Path

import pytest

from app.themes.registry import ThemeRegistry
from app.themes.service import get_theme_service


MINIMAL_TOML = b"""\
[general]
background = "#11111B"
border = "#6C7086"
horizontal_rule = "#1E1E2E"
unread_indicator = "#CBA6F7"

[text]
primary = "#CDD6F4"
secondary = "#A6ADC8"
tertiary = "#CBA6F7"
success = "#A6E3A1"
error = "#F38BA8"

[buffer]
action = "#FAB387"
background = "#181825"
background_text_input = "#1E1E2E"
background_title_bar = "#1E1E2E"
border = "#11111B"
border_selected = "#4C4163"
code = "#B7BDF8"
highlight = "#594C76"
nickname = "#89DCEB"
selection = "#2C324A"
timestamp = "#585A6E"
topic = "#7F849C"
url = "#89B4FA"

  [buffer.server_messages]
  default = "#F9E2AF"
"""


def _generate_theme_toml(name: str, hue_offset: int = 0) -> bytes:
    """Generate a valid Halloy TOML theme with a slight color shift."""
    shift = hue_offset % 360
    bg = f"#{17 + shift // 30:02x}{17 + shift // 20:02x}{27 + shift // 15:02x}"
    return f"""\
[general]
background = "{bg}"
border = "#6C7086"
horizontal_rule = "#1E1E2E"
unread_indicator = "#CBA6F7"

[text]
primary = "#CDD6F4"
secondary = "#A6ADC8"
tertiary = "#CBA6F7"
success = "#A6E3A1"
error = "#F38BA8"

[buffer]
action = "#FAB387"
background = "#181825"
background_text_input = "#1E1E2E"
background_title_bar = "#1E1E2E"
border = "#11111B"
border_selected = "#4C4163"
code = "#B7BDF8"
highlight = "#594C76"
nickname = "#89DCEB"
selection = "#2C324A"
timestamp = "#585A6E"
topic = "#7F849C"
url = "#89B4FA"

  [buffer.server_messages]
  default = "#F9E2AF"

[buttons.primary]
background = "#00000000"
background_hover = "#1A1A29"
background_selected = "#1E1E2F"
background_selected_hover = "#222236"

[buttons.secondary]
background = "#232336"
background_hover = "#2B2B42"
background_selected = "#4C4163"
background_selected_hover = "#685786"
""".encode()


def _populate_external_dir(directory: Path, count: int) -> None:
    """Write *count* valid TOML theme files into *directory*."""
    for i in range(count):
        name = f"Benchmark Theme {i:03d}"
        (directory / f"{name}.toml").write_bytes(_generate_theme_toml(name, hue_offset=i * 7))


class TestColdRegistryConstruction:
    """Measure time to build a fresh ThemeRegistry from scratch."""

    def test_cold_registry_bundled_only(self):
        """Time constructing a registry with only bundled themes."""
        start = time.perf_counter()
        for _ in range(5):
            ThemeRegistry(default_theme="Catppuccin Mocha")
        elapsed = (time.perf_counter() - start) / 5

        assert elapsed < 0.5, f"Cold registry (bundled) took {elapsed:.4f}s, expected < 0.5s"

    def test_cold_registry_with_external_dir(self, tmp_path):
        """Time constructing a registry with bundled + external themes."""
        external = tmp_path / "themes"
        external.mkdir()
        _populate_external_dir(external, 50)

        start = time.perf_counter()
        for _ in range(3):
            ThemeRegistry(external_root=external, default_theme="Catppuccin Mocha")
        elapsed = (time.perf_counter() - start) / 3

        assert elapsed < 1.0, f"Cold registry (50 external) took {elapsed:.4f}s, expected < 1.0s"


class TestBundledCatalogEnumeration:
    """Measure time to list all bundled themes."""

    def test_list_all_bundled_themes(self):
        """Benchmark listing all themes from the default bundled catalog."""
        from app.themes.resources import discover_bundled_package

        start = time.perf_counter()
        for _ in range(20):
            themes = discover_bundled_package()
        elapsed = (time.perf_counter() - start) / 20

        assert len(themes) >= 50, f"Expected >= 50 bundled themes, got {len(themes)}"
        assert elapsed < 0.1, f"Bundled catalog enumeration took {elapsed:.4f}s, expected < 0.1s"

    def test_registry_list_themes_cold(self):
        """Benchmark registry.list_themes() on a cold (first-call) registry."""
        registry = ThemeRegistry(default_theme="Catppuccin Mocha")

        start = time.perf_counter()
        themes = registry.list_themes()
        elapsed = time.perf_counter() - start

        assert len(themes) >= 50
        assert elapsed < 0.5, f"Cold list_themes() took {elapsed:.4f}s, expected < 0.5s"

    def test_registry_list_themes_warm(self):
        """Benchmark registry.list_themes() with catalog already built."""
        registry = ThemeRegistry(default_theme="Catppuccin Mocha")
        registry.list_themes()

        start = time.perf_counter()
        for _ in range(100):
            themes = registry.list_themes()
        elapsed = (time.perf_counter() - start) / 100

        assert len(themes) >= 50
        assert elapsed < 0.01, f"Warm list_themes() took {elapsed:.4f}s, expected < 0.01s"


class TestExternalDirectoryScan:
    """Measure external theme discovery with representative file counts."""

    @pytest.mark.parametrize("count", [10, 50, 100])
    def test_discover_external_file_counts(self, tmp_path, count):
        """Benchmark discover_external with varying file counts."""
        from app.themes.resources import discover_external

        external = tmp_path / f"ext_{count}"
        external.mkdir()
        _populate_external_dir(external, count)

        start = time.perf_counter()
        for _ in range(5):
            results = discover_external(external)
        elapsed = (time.perf_counter() - start) / 5

        assert len(results) == count, f"Expected {count} themes, got {len(results)}"
        threshold = 0.05 + count * 0.005
        assert elapsed < threshold, (
            f"External scan ({count} files) took {elapsed:.4f}s, expected < {threshold:.3f}s"
        )

    def test_registry_with_large_external_dir(self, tmp_path):
        """Benchmark full registry construction with 100 external themes."""
        external = tmp_path / "large_ext"
        external.mkdir()
        _populate_external_dir(external, 100)

        start = time.perf_counter()
        registry = ThemeRegistry(external_root=external, default_theme="Catppuccin Mocha")
        themes = registry.list_themes()
        elapsed = time.perf_counter() - start

        assert len(themes) >= 150
        assert elapsed < 2.0, f"Registry with 100 external took {elapsed:.4f}s, expected < 2.0s"


class TestColdParseTranslateSerialize:
    """Measure cold parse+translate+serialize for a single theme."""

    def test_cold_load_catppuccin_mocha(self):
        """Benchmark a full cold load of a bundled theme (invalidate then load)."""
        registry = ThemeRegistry(default_theme="Catppuccin Mocha")

        start = time.perf_counter()
        for _ in range(5):
            registry.invalidate("Catppuccin Mocha")
            loaded = registry.load("Catppuccin Mocha")
        elapsed = (time.perf_counter() - start) / 5

        assert loaded is not None
        assert loaded.css is not None
        assert len(loaded.css_vars) > 0
        assert elapsed < 0.25, (
            f"Cold parse/translate/serialize took {elapsed:.4f}s, expected < 0.25s"
        )

    def test_cold_load_multiple_themes(self):
        """Benchmark cold loads across several different bundled themes."""
        registry = ThemeRegistry(default_theme="Catppuccin Mocha")
        names = ["Catppuccin Mocha", "Rose Pine", "Dracula", "Nord", "One Dark"]

        start = time.perf_counter()
        for name in names:
            registry.invalidate(name)
            loaded = registry.load(name)
            assert loaded is not None
        elapsed = time.perf_counter() - start

        per_theme = elapsed / len(names)
        assert per_theme < 0.3, f"Cold load per-theme took {per_theme:.4f}s, expected < 0.3s"


class TestWarmThemeLoad:
    """Measure cached theme load performance."""

    def test_warm_load_performance(self):
        """Benchmark loading an already-cached theme."""
        registry = ThemeRegistry(default_theme="Catppuccin Mocha")
        registry.load("Catppuccin Mocha")

        start = time.perf_counter()
        for _ in range(200):
            loaded = registry.load("Catppuccin Mocha")
        elapsed = (time.perf_counter() - start) / 200

        assert loaded is not None
        assert elapsed < 0.01, f"Warm theme load took {elapsed:.4f}s, expected < 0.01s"

    def test_warm_load_css_populated(self):
        """Verify cached theme returns full CSS output."""
        registry = ThemeRegistry(default_theme="Catppuccin Mocha")
        loaded = registry.load("Catppuccin Mocha")

        assert ":root" in loaded.css
        assert "--" in loaded.css
        assert loaded.is_dark is not None
        assert len(loaded.css_vars) >= 40


class TestThemeServiceContextGeneration:
    """Measure ThemeService.get_context() performance."""

    def test_get_context_cold(self, app, db):
        """Benchmark cold context generation (cache invalidated)."""
        with app.app_context():
            service = get_theme_service()
            service.invalidate_settings_cache()

            start = time.perf_counter()
            ctx = service.get_context()
            elapsed = time.perf_counter() - start

            assert "theme_dark_vars" in ctx
            assert "theme_light_vars" in ctx
            assert elapsed < 1.0, f"Cold get_context() took {elapsed:.4f}s, expected < 1.0s"

    def test_get_context_warm(self, app, db):
        """Benchmark cached context generation."""
        with app.app_context():
            service = get_theme_service()
            service.invalidate_settings_cache()
            service.get_context()

            start = time.perf_counter()
            for _ in range(50):
                ctx = service.get_context()
            elapsed = (time.perf_counter() - start) / 50

            assert "theme_dark_vars" in ctx
            assert elapsed < 0.01, f"Warm get_context() took {elapsed:.4f}s, expected < 0.01s"

    def test_get_context_after_invalidation(self, app, db):
        """Benchmark context rebuild after settings cache invalidation."""
        with app.app_context():
            service = get_theme_service()
            service.get_context()

            start = time.perf_counter()
            for _ in range(10):
                service.invalidate_settings_cache()
                ctx = service.get_context()
            elapsed = (time.perf_counter() - start) / 10

            assert "theme_dark_vars" in ctx
            assert elapsed < 0.5, f"Context after invalidation took {elapsed:.4f}s, expected < 0.5s"

    def test_get_context_serialized_css(self, app, db):
        """Verify serialized CSS is produced in context."""
        with app.app_context():
            service = get_theme_service()
            ctx = service.get_context()

            assert "theme_dark_css" in ctx
            assert "theme_light_css" in ctx
            assert "--" in ctx["theme_dark_css"]
            assert "--" in ctx["theme_light_css"]


class TestBaseTemplateRenderOverhead:
    """Measure template rendering time with theme vars injected."""

    def test_minimal_template_render(self, app):
        """Benchmark rendering a minimal Jinja template with theme vars."""
        with app.app_context():
            service = get_theme_service()
            ctx = service.get_context()

            with app.test_request_context():
                from jinja2 import Template

                tpl = Template(
                    "<style>{{ theme_dark_css }}</style>"
                    "<body style='background:{{ theme_vars.bg }}'>{{ theme_vars.text }}</body>"
                )

                render_ctx = {
                    "theme_dark_css": ctx["theme_dark_css"],
                    "theme_light_css": ctx["theme_light_css"],
                    "theme_vars": ctx["theme_vars"],
                }

                start = time.perf_counter()
                for _ in range(200):
                    result = tpl.render(**render_ctx)
                elapsed = (time.perf_counter() - start) / 200

                assert "--" in result
                assert elapsed < 0.005, f"Template render took {elapsed:.6f}s, expected < 0.005s"

    def test_full_theme_context_render(self, app):
        """Benchmark rendering with all theme context keys."""
        with app.app_context():
            service = get_theme_service()
            ctx = service.get_context()

            with app.test_request_context():
                from jinja2 import Template

                tpl = Template(
                    "<style>{{ theme_dark_css }}</style>"
                    "<style>{{ theme_light_css }}</style>"
                    "<div data-color-scheme='{{ theme_dark_name }}'>{{ theme_dark_name }}</div>"
                    "<div>{{ theme_default_scheme }}</div>"
                )

                start = time.perf_counter()
                for _ in range(200):
                    result = tpl.render(**ctx)
                elapsed = (time.perf_counter() - start) / 200

                assert "--" in result
                assert elapsed < 0.005, (
                    f"Full theme context render took {elapsed:.6f}s, expected < 0.005s"
                )


class TestAdminCatalogPageRender:
    """Measure admin theme settings page rendering performance."""

    def test_admin_theme_settings_page(self, app, db, admin_user, authenticated_client):
        """Benchmark the admin theme settings page with themes loaded."""
        with app.app_context():
            service = get_theme_service()
            service.get_context()

        start = time.perf_counter()
        for _ in range(5):
            response = authenticated_client.get("/admin/settings")
        elapsed = (time.perf_counter() - start) / 5

        assert response.status_code == 200
        assert elapsed < 2.0, f"Admin theme settings page took {elapsed:.4f}s, expected < 2.0s"

    def test_admin_theme_catalog_list(self, app):
        """Benchmark listing themes for admin catalog display."""
        with app.app_context():
            service = get_theme_service()
            registry = service.get_registry()

            start = time.perf_counter()
            for _ in range(20):
                themes = registry.list_themes()
                catalog = [
                    {
                        "name": t.canonical_name,
                        "display_name": t.display_name,
                        "source": t.source.value,
                        "status": t.status,
                    }
                    for t in themes
                ]
            elapsed = (time.perf_counter() - start) / 20

            assert len(catalog) >= 50
            assert elapsed < 0.05, f"Admin catalog list took {elapsed:.4f}s, expected < 0.05s"


class TestRegistryRefresh:
    """Measure invalidation and catalog rebuild cycles."""

    def test_full_registry_invalidation(self):
        """Benchmark full invalidate() + catalog rebuild."""
        registry = ThemeRegistry(default_theme="Catppuccin Mocha")
        registry.list_themes()

        start = time.perf_counter()
        for _ in range(10):
            registry.invalidate()
            themes = registry.list_themes()
        elapsed = (time.perf_counter() - start) / 10

        assert len(themes) >= 50
        assert elapsed < 0.5, f"Full registry invalidation took {elapsed:.4f}s, expected < 0.5s"

    def test_single_theme_invalidation(self):
        """Benchmark invalidating a single theme and reloading."""
        registry = ThemeRegistry(default_theme="Catppuccin Mocha")
        registry.load("Catppuccin Mocha")

        start = time.perf_counter()
        for _ in range(20):
            registry.invalidate("Catppuccin Mocha")
            loaded = registry.load("Catppuccin Mocha")
        elapsed = (time.perf_counter() - start) / 20

        assert loaded is not None
        assert elapsed < 0.15, f"Single theme invalidation took {elapsed:.4f}s, expected < 0.15s"

    def test_registry_rebuild_with_external(self, tmp_path):
        """Benchmark full refresh when external directory has many files."""
        external = tmp_path / "ext_refresh"
        external.mkdir()
        _populate_external_dir(external, 50)

        registry = ThemeRegistry(external_root=external, default_theme="Catppuccin Mocha")
        registry.list_themes()

        start = time.perf_counter()
        for _ in range(5):
            registry.invalidate()
            themes = registry.list_themes()
        elapsed = (time.perf_counter() - start) / 5

        assert len(themes) >= 100
        assert elapsed < 1.0, f"Registry refresh (50 external) took {elapsed:.4f}s, expected < 1.0s"

    def test_service_refresh_registry(self, app, db):
        """Benchmark ThemeService.refresh_registry() full re-initialization."""
        with app.app_context():
            service = get_theme_service()
            service.get_registry().list_themes()

            start = time.perf_counter()
            for _ in range(5):
                service.refresh_registry()
                service.get_registry().list_themes()
            elapsed = (time.perf_counter() - start) / 5

            assert elapsed < 1.0, f"Service refresh_registry took {elapsed:.4f}s, expected < 1.0s"


class TestEndToEndThemePipeline:
    """Benchmark the full pipeline: scan -> parse -> translate -> serialize -> cache."""

    def test_full_pipeline_with_10_external_themes(self, tmp_path):
        """End-to-end: scan external dir, load every theme, verify output."""

        external = tmp_path / "e2e_ext"
        external.mkdir()
        _populate_external_dir(external, 10)

        registry = ThemeRegistry(external_root=external, default_theme="Catppuccin Mocha")

        start = time.perf_counter()
        themes = registry.list_themes()
        for theme in themes:
            loaded = registry.load(theme.canonical_name)
            assert loaded.css is not None
            assert len(loaded.css_vars) > 0
            assert len(loaded.legacy_vars) > 0
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0, f"E2E pipeline (10 themes) took {elapsed:.4f}s, expected < 2.0s"

    def test_full_pipeline_cold_then_warm(self, tmp_path):
        """Benchmark cold load followed by warm cache hits."""
        external = tmp_path / "e2e_cw"
        external.mkdir()
        _populate_external_dir(external, 5)

        registry = ThemeRegistry(external_root=external, default_theme="Catppuccin Mocha")
        themes = registry.list_themes()

        names = [t.canonical_name for t in themes[:5]]

        start = time.perf_counter()
        for name in names:
            registry.invalidate(name)
            registry.load(name)
        cold_elapsed = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(50):
            for name in names:
                registry.load(name)
        warm_elapsed = (time.perf_counter() - start) / 50

        assert cold_elapsed < 2.0, f"Cold pipeline took {cold_elapsed:.4f}s, expected < 2.0s"
        assert warm_elapsed < 0.01, f"Warm pipeline took {warm_elapsed:.4f}s, expected < 0.01s"

    def test_css_output_size(self):
        """Verify CSS output is a reasonable size for a bundled theme."""
        registry = ThemeRegistry(default_theme="Catppuccin Mocha")
        loaded = registry.load("Catppuccin Mocha")

        css_size = len(loaded.css.encode())
        assert css_size > 500, f"CSS output too small: {css_size} bytes"
        assert css_size < 50_000, f"CSS output too large: {css_size} bytes"

        line_count = loaded.css.count("\n")
        assert line_count >= 40, f"Expected >= 40 CSS lines, got {line_count}"


class TestThemeCacheBehavior:
    """Verify cache correctness under timing constraints."""

    def test_cache_hit_returns_same_object(self):
        """Cached loads return equivalent data without re-parsing."""
        registry = ThemeRegistry(default_theme="Catppuccin Mocha")
        first = registry.load("Catppuccin Mocha")
        second = registry.load("Catppuccin Mocha")

        assert first.css == second.css
        assert first.blog_theme == second.blog_theme
        assert first.is_dark == second.is_dark

    def test_invalidate_then_reload_fresh(self):
        """After invalidation, load returns fresh (not stale) data."""
        registry = ThemeRegistry(default_theme="Catppuccin Mocha")
        first = registry.load("Catppuccin Mocha")
        registry.invalidate("Catppuccin Mocha")
        second = registry.load("Catppuccin Mocha")

        assert second.css == first.css

    def test_cache_eviction_timing(self):
        """Invalidate + reload is still fast."""
        registry = ThemeRegistry(default_theme="Catppuccin Mocha")
        registry.load("Catppuccin Mocha")

        start = time.perf_counter()
        for _ in range(20):
            registry.invalidate()
            registry.load("Catppuccin Mocha")
        elapsed = (time.perf_counter() - start) / 20

        assert elapsed < 0.15, f"Cache evict+reload took {elapsed:.4f}s, expected < 0.15s"
