"""Tests for the theme operations facade."""

from __future__ import annotations

import os
from pathlib import Path
import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")


@pytest.fixture(autouse=True)
def _app_context(app, db):
    with app.app_context():
        yield


class TestListThemeDescriptors:
    def test_list_all_themes(self, app):
        from app.services.operations.themes import list_theme_descriptors

        result = list_theme_descriptors(source="all")
        assert result.ok
        assert result.total > 0
        assert result.code == "themes.list"
        assert isinstance(result.themes, list)
        for theme in result.themes:
            assert "canonical_name" in theme
            assert "source" in theme

    def test_list_bundled_only(self, app):
        from app.services.operations.themes import list_theme_descriptors

        result = list_theme_descriptors(source="bundled")
        assert result.ok
        for theme in result.themes:
            assert theme["source"] == "bundled"

    def test_list_external_only(self, app):
        from app.services.operations.themes import list_theme_descriptors

        result = list_theme_descriptors(source="external")
        assert result.ok
        for theme in result.themes:
            assert theme["source"] == "external"

    def test_list_returns_descriptor_details(self, app):
        from app.services.operations.themes import list_theme_descriptors

        result = list_theme_descriptors(source="bundled")
        assert result.ok
        first = result.themes[0]
        assert "display_name" in first
        assert "is_dark" in first
        assert "status" in first
        assert "overrides_bundled" in first
        assert "path" in first


class TestValidateTheme:
    def test_validate_registered_name(self, app):
        from app.services.operations.themes import validate_theme

        result = validate_theme("Catppuccin Mocha")
        assert result.ok
        assert result.valid is True
        assert result.theme_name == "Catppuccin Mocha"

    def test_validate_invalid_theme(self, app):
        from app.services.operations.themes import validate_theme

        result = validate_theme("Nonexistent Theme XYZ")
        assert not result.ok
        assert result.valid is False
        assert "not found" in result.summary.lower()

    def test_validate_file_on_disk(self, app, tmp_path):
        from app.services.operations.themes import validate_theme

        bundled_toml = Path(__file__).resolve().parent.parent.parent / "app" / "themes" / "bundled"
        sample_files = list(bundled_toml.glob("*.toml"))
        assert len(sample_files) > 0, "No bundled theme files found"

        sample = sample_files[0]
        result = validate_theme(str(sample))
        assert result.ok
        assert result.valid is True

    def test_validate_missing_file(self, app, tmp_path):
        from app.services.operations.themes import validate_theme

        result = validate_theme(str(tmp_path / "nope.toml"))
        assert not result.ok
        assert result.valid is False


class TestInspectTheme:
    def test_inspect_existing_theme(self, app):
        from app.services.operations.themes import inspect_theme

        result = inspect_theme("Catppuccin Mocha")
        assert result.ok
        assert result.theme_name == "Catppuccin Mocha"
        assert result.css_vars
        assert "canonical_name" in result.details
        assert "accessibility" in result.details
        assert "is_dark" in result.details

    def test_inspect_missing_theme(self, app):
        from app.services.operations.themes import inspect_theme

        result = inspect_theme("Nonexistent Theme")
        assert not result.ok
        assert "not found" in result.summary.lower()

    def test_inspect_includes_css(self, app):
        from app.services.operations.themes import inspect_theme

        result = inspect_theme("Catppuccin Mocha")
        assert result.ok
        assert "css" in result.details
        assert "--blog-" in result.details["css"]


class TestRefreshThemeRegistry:
    def test_refresh_returns_counts(self, app):
        from app.services.operations.themes import refresh_theme_registry

        result = refresh_theme_registry()
        assert result.ok
        assert result.code == "themes.refresh.ok"
        assert result.old_count >= 0
        assert result.new_count > 0

    def test_refresh_detects_changes(self, app):
        from app.services.operations.themes import refresh_theme_registry

        result = refresh_theme_registry()
        assert result.ok
        assert isinstance(result.added, list)
        assert isinstance(result.removed, list)


class TestGetThemePaths:
    def test_returns_bundled_info(self, app):
        from app.services.operations.themes import get_theme_paths

        result = get_theme_paths()
        assert result.ok
        assert "bundled" in result.paths
        assert "toml_count" in result.paths["bundled"] or "error" in result.paths["bundled"]

    def test_returns_config(self, app):
        from app.services.operations.themes import get_theme_paths

        result = get_theme_paths()
        assert result.ok
        assert "config" in result.paths
        assert "THEME_ALLOW_EXTERNAL" in result.paths["config"]


class TestRunAccessibilityCheck:
    def test_accessibility_check(self, app):
        from app.services.operations.themes import run_accessibility_check

        result = run_accessibility_check(source="bundled")
        assert result.ok
        assert result.total_themes > 0
        assert isinstance(result.passed_exact, int)
        assert isinstance(result.failed, int)

    def test_strict_accessibility_rejects_failures(self, app):
        from app.services.operations.themes import run_accessibility_check

        result = run_accessibility_check(source="external", strict=True)
        assert result.ok
        strict_rejected = result.details.get("strict_rejected", [])
        assert isinstance(strict_rejected, list)

    def test_accessibility_includes_findings(self, app):
        from app.services.operations.themes import run_accessibility_check

        result = run_accessibility_check(source="bundled")
        assert result.ok
        for report in result.reports:
            assert "theme_name" in report
            assert "findings" in report
            assert "passed" in report
