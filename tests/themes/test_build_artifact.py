from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path


from app.themes.registry import ThemeRegistry
from app.themes.resources import discover_bundled_package

BUNDLED_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "themes" / "bundled"


class TestPackageResourceDiscovery:
    def test_discover_bundled_package_returns_themes(self) -> None:
        themes = discover_bundled_package()
        assert len(themes) == 50

    def test_all_entries_are_bundled_source(self) -> None:
        from app.themes.resources import ThemeSource

        themes = discover_bundled_package()
        for theme in themes:
            assert theme.source == ThemeSource.BUNDLED

    def test_sorted_by_filename(self) -> None:
        themes = discover_bundled_package()
        names = [t.filename for t in themes]
        assert names == sorted(names)

    def test_importlib_resources_access(self) -> None:
        bundled = files("app.themes").joinpath("bundled")
        toml_files = [f for f in bundled.iterdir() if f.name.endswith(".toml")]
        assert len(toml_files) == 50


class TestRegistryWithPackageBundled:
    def test_registry_default_uses_bundled_dir(self) -> None:
        registry = ThemeRegistry()
        assert registry._bundled_root == BUNDLED_DIR

    def test_registry_lists_50_themes(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        themes = registry.list_themes()
        assert len(themes) == 50

    def test_registry_loads_dark_theme(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        loaded = registry.load("Dracula")
        assert loaded.is_dark is True
        assert loaded.css.strip().startswith(":root")
        assert "--blog-bg-page" in loaded.css

    def test_registry_loads_light_theme(self) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        loaded = registry.load("Catppuccin Latte")
        assert loaded.is_dark is False
        assert loaded.css.strip().startswith(":root")


class TestPackagingConfig:
    def test_pyproject_has_package_data(self) -> None:
        pyproject = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
        content = pyproject.read_text()
        assert "app.themes.bundled" in content
        assert "*.toml" in content

    def test_manifest_in_exists(self) -> None:
        manifest_in = Path(__file__).resolve().parent.parent.parent / "MANIFEST.in"
        assert manifest_in.exists()
        content = manifest_in.read_text()
        assert "app/themes/bundled" in content

    def test_attribution_exists(self) -> None:
        attribution = BUNDLED_DIR / "ATTRIBUTION.md"
        assert attribution.exists()

    def test_catalog_manifest_valid_json(self) -> None:
        manifest_path = BUNDLED_DIR / "catalog_manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text())
        assert manifest["version"] == 1
        assert manifest["theme_count"] == 50
        assert len(manifest["themes"]) == 50
