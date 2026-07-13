from __future__ import annotations

from pathlib import Path


from app.themes.registry import ThemeRegistry
from app.themes.resources import ThemeSource

BUNDLED_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "themes" / "bundled"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
VALID_THEME_CONTENT = (FIXTURES / "minimal.toml").read_text()


def _write_theme(directory: Path, name: str, content: str = VALID_THEME_CONTENT) -> Path:
    path = directory / f"{name}.toml"
    path.write_text(content)
    return path


class TestExternalOverrideWithBundled:
    def test_bundled_theme_is_listed(self, tmp_path: Path) -> None:
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "Dracula" in names

    def test_novel_external_theme_extends_list(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "my-novel-theme")
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "my-novel-theme" in names
        assert "Dracula" in names

    def test_same_name_external_overrides_bundled(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "Dracula")
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        descriptor = registry.resolve("Dracula")
        assert descriptor is not None
        assert descriptor.source == ThemeSource.EXTERNAL
        assert descriptor.overrides_bundled is True

    def test_removing_external_restores_bundled(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "Dracula")
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        assert registry.resolve("Dracula").source == ThemeSource.EXTERNAL

        (ext / "Dracula.toml").unlink()
        registry.invalidate()
        descriptor = registry.resolve("Dracula")
        assert descriptor is not None
        assert descriptor.source == ThemeSource.BUNDLED

    def test_invalidating_single_theme_restores_bundled(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "Dracula")
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        assert registry.resolve("Dracula").source == ThemeSource.EXTERNAL

        (ext / "Dracula.toml").unlink()
        registry.invalidate()
        descriptor = registry.resolve("Dracula")
        assert descriptor is not None
        assert descriptor.source == ThemeSource.BUNDLED

    def test_no_code_writes_to_bundled(self, tmp_path: Path) -> None:
        import os

        bundled_contents_before = set(os.listdir(BUNDLED_DIR))
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR)
        registry.list_themes()
        registry.invalidate()
        bundled_contents_after = set(os.listdir(BUNDLED_DIR))
        assert bundled_contents_before == bundled_contents_after

    def test_external_load_works(self, tmp_path: Path) -> None:
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "my-custom")
        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        loaded = registry.load("my-custom")
        assert loaded.descriptor.source == ThemeSource.EXTERNAL
        assert loaded.css.strip().startswith(":root")
