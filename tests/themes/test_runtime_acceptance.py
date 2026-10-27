"""Runtime and operator acceptance tests.

Validates end-to-end behavior that operators and deployers rely on:
default theme pairing, CSS variable completeness, external theme
discovery, emergency fallback resilience, and CLI command correctness.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from app import create_app
from app.config import THEME_DEFAULT_DARK, THEME_DEFAULT_LIGHT, THEME_DEFAULT_SCHEME
from app.themes.model import CSS_VARS, EMERGENCY_DEFAULT
from app.themes.registry import ThemeRegistry
from app.themes.service import ThemeService, get_theme_service
from app.themes.translate import to_theme_vars


BUNDLED_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "themes" / "bundled"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
VALID_THEME_CONTENT = (FIXTURES / "minimal.toml").read_text()


def _write_theme(directory: Path, name: str, content: str = VALID_THEME_CONTENT) -> Path:
    path = directory / f"{name}.toml"
    path.write_text(content)
    return path


def _sample_theme_toml() -> str:
    return (
        "[general]\n"
        'background = "#1e1e2e"\n'
        'border = "#45475a"\n'
        'horizontal_rule = "#45475a"\n'
        'unread_indicator = "#89b4fa"\n'
        "\n"
        "[text]\n"
        'primary = "#cdd6f4"\n'
        'secondary = "#a6adc8"\n'
        'tertiary = "#89b4fa"\n'
        'success = "#a6e3a1"\n'
        'error = "#f38ba8"\n'
        "\n"
        "[buffer]\n"
        'action = "#89b4fa"\n'
        'background = "#181825"\n'
        'background_text_input = "#11111b"\n'
        'background_title_bar = "#1e1e2e"\n'
        'border = "#45475a"\n'
        'border_selected = "#89b4fa"\n'
        'code = "#181825"\n'
        'highlight = "#89b4fa"\n'
        'nickname = "#89b4fa"\n'
        'selection = "#45475a"\n'
        'timestamp = "#6c7086"\n'
        'topic = "#a6adc8"\n'
        'url = "#89b4fa"\n'
        "\n"
        "[buffer.server_messages]\n"
        'default = "#6c7086"\n'
        "\n"
        "[buttons.primary]\n"
        'background = "#00000000"\n'
        'background_hover = "#1a1a29"\n'
        'background_selected = "#1e1e2f"\n'
        'background_selected_hover = "#222236"\n'
        "\n"
        "[buttons.secondary]\n"
        'background = "#232336"\n'
        'background_hover = "#2b2b42"\n'
        'background_selected = "#4c4163"\n'
        'background_selected_hover = "#685786"\n'
    )


# ---------------------------------------------------------------------------
# 1. Default behavior tests
# ---------------------------------------------------------------------------


class TestDefaultBehavior:
    """Fresh deployment must produce the expected Catppuccin dark/light pair."""

    def test_fresh_deployment_defaults_to_catppuccin_pair(self):
        assert THEME_DEFAULT_DARK == "Catppuccin Mocha"
        assert THEME_DEFAULT_LIGHT == "Catppuccin Latte"

    def test_default_scheme_is_system(self):
        assert THEME_DEFAULT_SCHEME == "system"

    def test_theme_service_produces_complete_css_vars(self, app, db):
        service = get_theme_service()
        registry = service.get_registry()
        loaded = registry.load("Catppuccin Mocha")
        theme_vars = to_theme_vars(loaded.blog_theme)
        for semantic_key, css_var in CSS_VARS.items():
            assert css_var in theme_vars, f"missing CSS var: {css_var} (semantic: {semantic_key})"

    def test_theme_service_context_has_all_required_keys(self, app, db):
        service = get_theme_service()
        ctx = service.get_context()
        required = [
            "theme_dark_name",
            "theme_light_name",
            "theme_default_scheme",
            "theme_dark_vars",
            "theme_light_vars",
            "theme_dark_css",
            "theme_light_css",
            "theme_warnings",
            "custom_css_enabled",
            "custom_css",
            "logo_text",
            "theme_vars",
        ]
        for key in required:
            assert key in ctx, f"missing required key: {key}"

    def test_dark_and_light_css_nonempty(self, app, db):
        service = get_theme_service()
        ctx = service.get_context()
        assert len(ctx["theme_dark_css"]) > 0
        assert len(ctx["theme_light_css"]) > 0
        assert ctx["theme_dark_css"].startswith("  --")
        assert ctx["theme_light_css"].startswith("  --")


# ---------------------------------------------------------------------------
# 2. External theme tests
# ---------------------------------------------------------------------------


class TestExternalThemeDiscovery:
    """External themes in THEME_EXTERNAL_DIR are discoverable by the registry."""

    def test_external_theme_discovery(self, tmp_path):
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "my-custom-operator-theme")

        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]
        assert "my-custom-operator-theme" in names

    def test_external_theme_loads_css(self, tmp_path):
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "loadable-theme")

        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        loaded = registry.load("loadable-theme")
        assert loaded.css.strip().startswith(":root")
        assert len(loaded.css_vars) > 0

    def test_malformed_theme_isolation(self, tmp_path):
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "good-theme")
        _write_theme(ext, "bad-theme", content="[invalid\ncorrupt")

        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        themes = registry.list_themes()
        names = [t.canonical_name for t in themes]

        assert "good-theme" in names

        loaded = registry.load("good-theme")
        assert loaded.css.strip().startswith(":root")

    def test_external_overrides_bundled(self, tmp_path):
        ext = tmp_path / "external"
        ext.mkdir()
        _write_theme(ext, "Dracula")

        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        from app.themes.resources import ThemeSource

        descriptor = registry.resolve("Dracula")
        assert descriptor is not None
        assert descriptor.source == ThemeSource.EXTERNAL
        assert descriptor.overrides_bundled is True

    def test_empty_external_dir_no_crash(self, tmp_path):
        ext = tmp_path / "external"
        ext.mkdir()

        registry = ThemeRegistry(bundled_root=BUNDLED_DIR, external_root=ext)
        themes = registry.list_themes()
        assert len(themes) > 0


# ---------------------------------------------------------------------------
# 3. Emergency fallback tests
# ---------------------------------------------------------------------------


class TestEmergencyFallbackAcceptance:
    """Emergency fallback must render a complete, usable palette."""

    def test_emergency_fallback_renders_complete_palette(self):
        theme_vars = to_theme_vars(EMERGENCY_DEFAULT)
        for var_key in CSS_VARS.values():
            assert var_key in theme_vars, f"EMERGENCY_DEFAULT missing CSS var: {var_key}"

    def test_emergency_fallback_has_all_model_fields(self):
        for field_name in CSS_VARS:
            value = getattr(EMERGENCY_DEFAULT, field_name, None)
            assert value is not None, f"EMERGENCY_DEFAULT missing field: {field_name}"

    def test_emergency_fallback_logs_cause(self, caplog):
        service = ThemeService()
        with caplog.at_level(logging.WARNING, logger="app.themes.service"):
            with patch(
                "app.themes.service.ThemeService._build_context_from_db",
                side_effect=RuntimeError("database locked"),
            ):
                ctx = service.get_context()

        assert ctx["theme_dark_name"] == "emergency-default"
        assert any("emergency" in record.message.lower() for record in caplog.records)

    def test_emergency_context_has_nonempty_css(self):
        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=RuntimeError("db down"),
        ):
            ctx = service.get_context()

        assert len(ctx["theme_dark_css"]) > 0
        assert len(ctx["theme_light_css"]) > 0
        assert "--bg:" in ctx["theme_dark_css"]
        assert "--accent:" in ctx["theme_dark_css"]

    def test_emergency_context_scheme_is_dark(self):
        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=RuntimeError("fail"),
        ):
            ctx = service.get_context()
        assert ctx["theme_default_scheme"] == "dark"

    def test_emergency_context_has_no_syntax_theme(self):
        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=RuntimeError("fail"),
        ):
            ctx = service.get_context()
        assert "syntax_theme" not in ctx

    def test_emergency_context_custom_css_disabled(self):
        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=RuntimeError("fail"),
        ):
            ctx = service.get_context()
        assert ctx["custom_css_enabled"] is False
        assert ctx["custom_css"] == ""

    def test_emergency_survives_operational_error(self):
        from sqlalchemy.exc import OperationalError

        service = ThemeService()
        with patch(
            "app.themes.service.ThemeService._build_context_from_db",
            side_effect=OperationalError("db error", {}, None),
        ):
            ctx = service.get_context()
        assert ctx["theme_dark_name"] == "emergency-default"
        assert len(ctx["theme_dark_vars"]) > 0

    def test_public_page_never_500s_on_theme_failure(self, client, db):
        settings_patch = {
            "theme_dark_name": "Totally Invalid Theme XYZ",
            "theme_light_name": "Also Invalid Theme ABC",
        }
        from app.models import SiteSettings

        settings = SiteSettings.get_instance()
        for k, v in settings_patch.items():
            setattr(settings, k, v)
        db.session.commit()

        from app.context_processors import invalidate_settings_cache

        invalidate_settings_cache()

        resp = client.get("/")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 4. CLI acceptance tests
# ---------------------------------------------------------------------------


@pytest.fixture
def cli_app(db):
    app = create_app()
    return app


@pytest.fixture
def runner(cli_app):
    return CliRunner()


class TestCLIListOutputsJSON:
    def test_cli_list_outputs_json(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "canonical_name" in data[0]
        assert "source" in data[0]
        assert "is_dark" in data[0]

    def test_cli_list_json_all_themes_have_required_fields(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        required_fields = {"canonical_name", "display_name", "source", "is_dark", "status"}
        for theme in data:
            missing = required_fields - set(theme.keys())
            assert not missing, f"theme {theme.get('canonical_name')} missing: {missing}"

    def test_cli_list_human_readable(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "list"])
        assert result.exit_code == 0
        assert "Total:" in result.output


class TestCLIValidateValidTheme:
    def test_cli_validate_valid_theme(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "validate", "Catppuccin Mocha"])
        assert result.exit_code == 0
        assert "is valid" in result.output

    def test_cli_validate_file_path_exits_zero(self, runner, cli_app, tmp_path):
        theme_file = tmp_path / "acceptance-theme.toml"
        theme_file.write_text(_sample_theme_toml())
        result = runner.invoke(cli_app.cli, ["themes", "validate", str(theme_file)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_cli_validate_nonexistent_exits_nonzero(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "validate", "Nonexistent Theme"])
        assert result.exit_code != 0

    def test_cli_validate_json_output(self, runner, cli_app, tmp_path):
        theme_file = tmp_path / "json-theme.toml"
        theme_file.write_text(_sample_theme_toml())
        result = runner.invoke(cli_app.cli, ["themes", "validate", str(theme_file), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["valid"] is True

    def test_cli_validate_empty_file_exits_nonzero(self, runner, cli_app, tmp_path):
        theme_file = tmp_path / "empty.toml"
        theme_file.write_text("")
        result = runner.invoke(cli_app.cli, ["themes", "validate", str(theme_file)])
        assert result.exit_code != 0


class TestCLIAccessibilityStrict:
    def test_cli_accessibility_strict_bundled_passes(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "accessibility", "--source", "bundled"])
        assert result.exit_code == 0
        assert "Checked" in result.output

    def test_cli_accessibility_strict_flag_passes_with_no_external(self, runner, cli_app):
        result = runner.invoke(
            cli_app.cli,
            ["themes", "accessibility", "--source", "bundled", "--strict"],
        )
        assert result.exit_code == 0

    def test_cli_accessibility_strict_rejects_bad_external(self, runner, cli_app, tmp_path):
        from app.themes.diagnostics import (
            ThemeAccessibilityReport,
            AccessibilityFinding,
            Severity,
            ClassificationAudit,
        )
        from app.themes.resources import ThemeSource

        mandatory_finding = AccessibilityFinding(
            theme_name="broken-external",
            token="text_primary",
            description="test failure",
            foreground="#000000",
            background="#000000",
            ratio=1.0,
            required=4.5,
            wcag="AA",
            severity=Severity.MANDATORY,
            remediation="fix contrast",
            exception_reason=None,
        )
        failed_report = ThemeAccessibilityReport(
            theme_name="broken-external",
            source="external",
            is_dark=True,
            findings=[mandatory_finding],
            classification=ClassificationAudit(
                theme_name="broken-external",
                filename_dark=True,
                computed_dark=True,
                page_luminance=0.01,
                mismatch=False,
            ),
        )

        mock_descriptor = MagicMock()
        mock_descriptor.canonical_name = "broken-external"
        mock_descriptor.source = ThemeSource.EXTERNAL
        mock_descriptor.is_dark = True

        mock_loaded = MagicMock()
        mock_loaded.descriptor = mock_descriptor

        mock_service = MagicMock()
        mock_registry = MagicMock()
        mock_registry.list_themes.return_value = [mock_descriptor]
        mock_service.get_registry.return_value = mock_registry

        with patch(
            "app.themes.diagnostics.validate_theme_accessibility",
            return_value=failed_report,
        ):
            with patch(
                "app.themes.service.get_theme_service",
                return_value=mock_service,
            ):
                result = runner.invoke(
                    cli_app.cli,
                    ["themes", "accessibility", "--source", "external", "--strict"],
                )

        assert result.exit_code != 0 or "REJECTED" in result.output

    def test_cli_accessibility_json_output(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "accessibility", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "total_themes" in data
        assert "total_mandatory_failures" in data
