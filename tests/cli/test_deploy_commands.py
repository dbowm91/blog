from __future__ import annotations

import pytest
from click.testing import CliRunner

from devlog_cli.main import main


@pytest.fixture
def runner():
    return CliRunner()


class TestDeployRenderHelp:
    def test_help(self, runner):
        result = runner.invoke(main, ["deploy", "render", "--help"])
        assert result.exit_code == 0
        assert "--mode" in result.output
        assert "--target" in result.output

    def test_mode_required(self, runner):
        result = runner.invoke(main, ["deploy", "render"])
        assert result.exit_code != 0
        assert (
            "Missing" in result.output
            or "required" in result.output.lower()
            or "Error" in result.output
        )


class TestDeployInstallHelp:
    def test_help(self, runner):
        result = runner.invoke(main, ["deploy", "install", "--help"])
        assert result.exit_code == 0
        assert "--mode" in result.output
        assert "--force" in result.output
        assert "--dry-run" in result.output


class TestDeployCheckHelp:
    def test_help(self, runner):
        result = runner.invoke(main, ["deploy", "check", "--help"])
        assert result.exit_code == 0
        assert "--mode" in result.output


class TestStartHelp:
    def test_help(self, runner):
        result = runner.invoke(main, ["start", "--help"])
        assert result.exit_code == 0


class TestStopHelp:
    def test_help(self, runner):
        result = runner.invoke(main, ["stop", "--help"])
        assert result.exit_code == 0


class TestRestartHelp:
    def test_help(self, runner):
        result = runner.invoke(main, ["restart", "--help"])
        assert result.exit_code == 0


class TestStatusHelp:
    def test_help(self, runner):
        result = runner.invoke(main, ["status", "--help"])
        assert result.exit_code == 0


class TestLogsHelp:
    def test_help(self, runner):
        result = runner.invoke(main, ["logs", "--help"])
        assert result.exit_code == 0
