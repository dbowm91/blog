from __future__ import annotations

import json
import subprocess
import sys
import venv
from importlib.resources import files
from pathlib import Path

import pytest

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


def _build_wheel(tmpdir: Path) -> Path | None:
    project_root = Path(__file__).resolve().parent.parent.parent
    dist_dir = tmpdir / "dist"
    dist_dir.mkdir()
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "-o", str(dist_dir)],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(project_root),
    )
    if result.returncode != 0:
        return None
    wheels = list(dist_dir.glob("*.whl"))
    return wheels[0] if wheels else None


def _install_wheel_in_venv(wheel_path: Path, venv_dir: Path) -> Path:
    venv.create(venv_dir, with_pip=True)
    pip = venv_dir / "bin" / "pip"
    subprocess.run(
        [str(pip), "install", str(wheel_path)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return venv_dir / "bin" / "python"


@pytest.mark.slow
class TestWheelBuildAndInstall:
    def test_wheel_builds_and_theme_resources_accessible(self, tmp_path: Path) -> None:
        wheel_path = _build_wheel(tmp_path)
        if wheel_path is None:
            pytest.skip("build package not available")

        venv_dir = tmp_path / "install_venv"
        python = _install_wheel_in_venv(wheel_path, venv_dir)

        result = subprocess.run(
            [
                str(python),
                "-c",
                "from app.themes.resources import discover_bundled_package;"
                "themes = discover_bundled_package();"
                "assert len(themes) == 50, f'Expected 50, got {len(themes)}';"
                "print(f'OK: {len(themes)} bundled themes')",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"Import failed: {result.stderr}"
        assert "OK: 50 bundled themes" in result.stdout

    def test_wheel_theme_registry_works(self, tmp_path: Path) -> None:
        wheel_path = _build_wheel(tmp_path)
        if wheel_path is None:
            pytest.skip("build package not available")

        venv_dir = tmp_path / "install_venv2"
        python = _install_wheel_in_venv(wheel_path, venv_dir)

        script = (
            "from app.themes.registry import ThemeRegistry;"
            "reg = ThemeRegistry();"
            "themes = reg.list_themes();"
            "assert len(themes) == 50, f'Expected 50, got {len(themes)}';"
            "loaded = reg.load('Dracula');"
            "assert loaded.is_dark is True;"
            "assert '--blog-bg-page' in loaded.css;"
            "loaded_light = reg.load('Catppuccin Latte');"
            "assert loaded_light.is_dark is False;"
            "print('OK: registry works from wheel')"
        )
        result = subprocess.run(
            [str(python), "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"Registry test failed: {result.stderr}"
        assert "OK: registry works from wheel" in result.stdout

    def test_wheel_manifest_and_attribution_accessible(self, tmp_path: Path) -> None:
        wheel_path = _build_wheel(tmp_path)
        if wheel_path is None:
            pytest.skip("build package not available")

        venv_dir = tmp_path / "install_venv3"
        python = _install_wheel_in_venv(wheel_path, venv_dir)

        script = (
            "from importlib.resources import files;"
            "import json;"
            "m = files('app.themes').joinpath('bundled/catalog_manifest.json').read_text();"
            "d = json.loads(m);"
            "assert d['theme_count'] == 50;"
            "a = files('app.themes').joinpath('bundled/ATTRIBUTION.md').read_text();"
            "assert len(a) > 0;"
            "print('OK: manifest and attribution accessible')"
        )
        result = subprocess.run(
            [str(python), "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"Asset test failed: {result.stderr}"
        assert "OK: manifest and attribution accessible" in result.stdout

    def test_wheel_external_theme_override(self, tmp_path: Path) -> None:
        wheel_path = _build_wheel(tmp_path)
        if wheel_path is None:
            pytest.skip("build package not available")

        venv_dir = tmp_path / "install_venv4"
        python = _install_wheel_in_venv(wheel_path, venv_dir)

        external_dir = tmp_path / "external_themes"
        external_dir.mkdir()
        external_theme = external_dir / "MyOverride.toml"
        external_theme.write_text(
            "[general]\n"
            'background = "#ff0000"\n'
            'border = "#00ff00"\n'
            'horizontal_rule = "#0000ff"\n'
            'unread_indicator = "#ffffff"\n\n'
            "[text]\n"
            'primary = "#ffffff"\n'
            'secondary = "#cccccc"\n'
            'tertiary = "#aaaaaa"\n'
            'success = "#00ff00"\n'
            'error = "#ff0000"\n\n'
            "[buffer]\n"
            'action = "#ff0000"\n'
            'background = "#222222"\n'
            'background_text_input = "#111111"\n'
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
            'background = "#ff0000"\n'
            'background_hover = "#ee0000"\n'
            'background_selected = "#dd0000"\n'
            'background_selected_hover = "#cc0000"\n\n'
            "[buttons.secondary]\n"
            'background = "#444444"\n'
            'background_hover = "#555555"\n'
            'background_selected = "#666666"\n'
            'background_selected_hover = "#777777"\n'
        )

        script = (
            f"from pathlib import Path;"
            f"from app.themes.registry import ThemeRegistry;"
            f"reg = ThemeRegistry(external_root=Path('{external_dir}'));"
            f"loaded = reg.load('MyOverride');"
            f"assert loaded.descriptor.source.value == 'external';"
            f"assert loaded.css.strip().startswith(':root');"
            f"assert '#ff0000' in loaded.css.lower() or '#ff0000' in loaded.css;"
            f"print('OK: external theme override works from wheel')"
        )
        result = subprocess.run(
            [str(python), "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"Override test failed: {result.stderr}"
        assert "OK: external theme override works from wheel" in result.stdout
