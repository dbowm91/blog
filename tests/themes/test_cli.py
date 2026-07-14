import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from app import create_app


@pytest.fixture
def cli_app(db):
    app = create_app()
    return app


@pytest.fixture
def runner(cli_app):
    return CliRunner()


CATALOG = Path(__file__).resolve().parent.parent.parent / "themes"


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


class TestThemesList:
    def test_list_default(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "list"])
        assert result.exit_code == 0
        assert "Total:" in result.output

    def test_list_bundled_only(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "list", "--source", "bundled"])
        assert result.exit_code == 0
        assert "Total:" in result.output

    def test_list_json_output(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "canonical_name" in data[0]
        assert "source" in data[0]

    def test_list_json_bundled(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "list", "--json", "--source", "bundled"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert all(t["source"] == "bundled" for t in data)

    def test_list_warnings_flag(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "list", "--warnings"])
        assert result.exit_code == 0
        assert "Total:" in result.output

    def test_list_empty_source(self, runner, cli_app, tmp_path):
        result = runner.invoke(cli_app.cli, ["themes", "list", "--source", "external"])
        assert result.exit_code == 0
        assert "No themes found." in result.output or "Total: 0" in result.output


class TestThemesValidate:
    def test_validate_bundled_name(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "validate", "Catppuccin Mocha"])
        assert result.exit_code == 0
        assert "is valid" in result.output

    def test_validate_nonexistent_name(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "validate", "Nonexistent Theme"])
        assert result.exit_code != 0

    def test_validate_file_path(self, runner, cli_app, tmp_path):
        theme_file = tmp_path / "test-theme.toml"
        theme_file.write_text(_sample_theme_toml())
        result = runner.invoke(cli_app.cli, ["themes", "validate", str(theme_file)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_validate_file_not_found(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "validate", "/nonexistent/theme.toml"])
        assert result.exit_code != 0

    def test_validate_empty_file(self, runner, cli_app, tmp_path):
        theme_file = tmp_path / "empty.toml"
        theme_file.write_text("")
        result = runner.invoke(cli_app.cli, ["themes", "validate", str(theme_file)])
        assert result.exit_code != 0

    def test_validate_invalid_toml(self, runner, cli_app, tmp_path):
        theme_file = tmp_path / "bad.toml"
        theme_file.write_text("[invalid\ncorrupt")
        result = runner.invoke(cli_app.cli, ["themes", "validate", str(theme_file)])
        assert result.exit_code != 0

    def test_validate_json_output(self, runner, cli_app, tmp_path):
        theme_file = tmp_path / "test-theme.toml"
        theme_file.write_text(_sample_theme_toml())
        result = runner.invoke(cli_app.cli, ["themes", "validate", str(theme_file), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["valid"] is True
        assert "normalized_name" in data

    def test_validate_json_failure(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "validate", "Nonexistent", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["valid"] is False


class TestThemesInspect:
    def test_inspect_bundled_theme(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "inspect", "Catppuccin Mocha"])
        assert result.exit_code == 0
        assert "Theme:" in result.output
        assert "Canonical name:" in result.output

    def test_inspect_not_found(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "inspect", "Nonexistent Theme"])
        assert result.exit_code != 0

    def test_inspect_json_output(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "inspect", "Catppuccin Mocha", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "canonical_name" in data
        assert "css_vars" in data
        assert "is_dark" in data

    def test_inspect_css_output(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "inspect", "Catppuccin Mocha", "--css"])
        assert result.exit_code == 0
        assert ":root" in result.output
        assert "--blog-" in result.output

    def test_inspect_by_alias(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "inspect", "catppuccin-mocha"])
        assert result.exit_code == 0
        assert "Theme:" in result.output


class TestThemesRefresh:
    def test_refresh_basic(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "refresh"])
        assert result.exit_code == 0
        assert "refreshed" in result.output.lower()
        assert "Catalog:" in result.output


class TestThemesPaths:
    def test_paths_output(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "paths"])
        assert result.exit_code == 0
        assert "Theme paths:" in result.output
        assert "Bundled package:" in result.output
        assert "Configuration:" in result.output
        assert "Precedence:" in result.output

    def test_paths_shows_bundled_count(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "paths"])
        assert result.exit_code == 0
        assert "Bundled themes:" in result.output


class TestThemesAccessibility:
    def test_accessibility_default(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "accessibility"])
        assert result.exit_code == 0
        assert "Checked" in result.output

    def test_accessibility_bundled_only(self, runner, cli_app):
        result = runner.invoke(cli_app.cli, ["themes", "accessibility", "--source", "bundled"])
        assert result.exit_code == 0
        assert "Checked" in result.output
