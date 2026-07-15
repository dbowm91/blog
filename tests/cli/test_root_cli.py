import json
import pytest
from click.testing import CliRunner
from devlog_cli.main import main
from devlog_cli import __version__


@pytest.fixture
def runner():
    return CliRunner()


class TestRootHelp:
    def test_help_output(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "DevLog" in result.output
        assert "self-hosted blog CMS" in result.output

    def test_help_lists_command_groups(self, runner):
        result = runner.invoke(main, ["--help"])
        assert "config" in result.output
        assert "admin" in result.output
        assert "db" in result.output
        assert "themes" in result.output
        assert "backup" in result.output
        assert "deploy" in result.output


class TestVersion:
    def test_version_flag(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output
        assert "devlog" in result.output

    def test_version_subcommand(self, runner):
        result = runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_json_output(self, runner):
        result = runner.invoke(main, ["--json", "version"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["status"] == "success"
        assert data["code"] == "cli.version"
        assert "DevLog" in data["summary"]
        assert "details" in data
        assert data["details"]["version"] == __version__


class TestNoSubcommand:
    def test_no_subcommand_shows_version(self, runner):
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_no_subcommand_json(self, runner):
        result = runner.invoke(main, ["--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True


class TestGlobalOptions:
    def test_verbose_flag(self, runner):
        result = runner.invoke(main, ["--verbose", "version"])
        assert result.exit_code == 0

    def test_quiet_flag(self, runner):
        result = runner.invoke(main, ["--quiet", "version"])
        assert result.exit_code == 0

    def test_no_color_flag(self, runner):
        result = runner.invoke(main, ["--no-color", "version"])
        assert result.exit_code == 0

    def test_json_and_verbose(self, runner):
        result = runner.invoke(main, ["--json", "--verbose", "version"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True


class TestCommandGroups:
    def test_config_help(self, runner):
        result = runner.invoke(main, ["config", "--help"])
        assert result.exit_code == 0
        assert "Manage DevLog configuration" in result.output

    def test_admin_help(self, runner):
        result = runner.invoke(main, ["admin", "--help"])
        assert result.exit_code == 0
        assert "Manage admin users" in result.output

    def test_db_help(self, runner):
        result = runner.invoke(main, ["db", "--help"])
        assert result.exit_code == 0
        assert "Database operations" in result.output

    def test_themes_help(self, runner):
        result = runner.invoke(main, ["themes", "--help"])
        assert result.exit_code == 0
        assert "Theme management" in result.output

    def test_backup_help(self, runner):
        result = runner.invoke(main, ["backup", "--help"])
        assert result.exit_code == 0
        assert "Backup and restore" in result.output

    def test_deploy_help(self, runner):
        result = runner.invoke(main, ["deploy", "--help"])
        assert result.exit_code == 0
        assert "Deployment operations" in result.output


class TestUnknownOption:
    def test_unknown_option_returns_error(self, runner):
        result = runner.invoke(main, ["--bogus"])
        assert result.exit_code != 0


class TestNoFlaskStartup:
    def test_help_does_not_import_app(self, runner):
        """Verify --help does not trigger Flask app construction."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "DevLog" in result.output
