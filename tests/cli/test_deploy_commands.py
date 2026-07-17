from __future__ import annotations

from unittest.mock import patch

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

    def test_user_flag_accepted(self, runner):
        result = runner.invoke(main, ["deploy", "render", "--help"])
        assert "--user" in result.output


class TestDeployInstallHelp:
    def test_help(self, runner):
        result = runner.invoke(main, ["deploy", "install", "--help"])
        assert result.exit_code == 0
        assert "--mode" in result.output
        assert "--force" in result.output
        assert "--dry-run" in result.output

    def test_user_flag_accepted(self, runner):
        result = runner.invoke(main, ["deploy", "install", "--help"])
        assert "--user" in result.output


class TestDeployCheckHelp:
    def test_help(self, runner):
        result = runner.invoke(main, ["deploy", "check", "--help"])
        assert result.exit_code == 0
        assert "--mode" in result.output

    def test_user_flag_accepted(self, runner):
        result = runner.invoke(main, ["deploy", "check", "--help"])
        assert "--user" in result.output


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


class TestDeployRenderExitCodes:
    @patch("app.services.operations.deploy.deploy_render")
    def test_success_returns_zero(self, mock_render, runner):
        from app.services.operations.deploy import DeployRenderResult

        mock_render.return_value = DeployRenderResult(
            ok=True,
            code="deploy.render.ok",
            summary="Rendered 1 file(s)",
            files=[],
        )
        result = runner.invoke(main, ["deploy", "render", "--mode", "system"])
        assert result.exit_code == 0

    @patch("app.services.operations.deploy.deploy_render")
    def test_failure_returns_nonzero(self, mock_render, runner):
        from app.services.operations.deploy import DeployRenderResult

        mock_render.return_value = DeployRenderResult(
            ok=False,
            code="deploy.render.error",
            summary="Failed to render",
        )
        result = runner.invoke(main, ["deploy", "render", "--mode", "system"])
        assert result.exit_code != 0


class TestDeployInstallExitCodes:
    @patch("app.services.operations.deploy.deploy_install")
    def test_dry_run_returns_zero(self, mock_install, runner):
        from app.services.operations.deploy import DeployInstallResult

        mock_install.return_value = DeployInstallResult(
            ok=True,
            code="deploy.install.ok",
            summary="Dry run: Installed 1 file(s).",
        )
        result = runner.invoke(main, ["deploy", "install", "--mode", "system", "--dry-run"])
        assert result.exit_code == 0

    @patch("app.services.operations.deploy.deploy_install")
    def test_failure_returns_nonzero(self, mock_install, runner):
        from app.services.operations.deploy import DeployInstallResult

        mock_install.return_value = DeployInstallResult(
            ok=False,
            code="deploy.install.failed",
            summary="Failed to install",
        )
        result = runner.invoke(main, ["deploy", "install", "--mode", "system"])
        assert result.exit_code != 0


class TestLifecycleExitCodes:
    @patch("app.services.operations.deploy.lifecycle_start")
    def test_start_success_returns_zero(self, mock_start, runner):
        from app.services.operations.deploy import LifecycleResult

        mock_start.return_value = LifecycleResult(
            ok=True,
            code="lifecycle.start.ok",
            summary="Service started.",
            backend="systemd",
        )
        result = runner.invoke(main, ["start"])
        assert result.exit_code == 0

    @patch("app.services.operations.deploy.lifecycle_start")
    def test_start_failure_returns_nonzero(self, mock_start, runner):
        from app.services.operations.deploy import LifecycleResult

        mock_start.return_value = LifecycleResult(
            ok=False,
            code="lifecycle.start.failed",
            summary="Failed to start service.",
            backend="systemd",
        )
        result = runner.invoke(main, ["start"])
        assert result.exit_code != 0

    @patch("app.services.operations.deploy.lifecycle_stop")
    def test_stop_failure_returns_nonzero(self, mock_stop, runner):
        from app.services.operations.deploy import LifecycleResult

        mock_stop.return_value = LifecycleResult(
            ok=False,
            code="lifecycle.stop.failed",
            summary="Failed to stop service.",
            backend="systemd",
        )
        result = runner.invoke(main, ["stop"])
        assert result.exit_code != 0

    @patch("app.services.operations.deploy.lifecycle_restart")
    def test_restart_failure_returns_nonzero(self, mock_restart, runner):
        from app.services.operations.deploy import LifecycleResult

        mock_restart.return_value = LifecycleResult(
            ok=False,
            code="lifecycle.restart.failed",
            summary="Failed to restart service.",
            backend="systemd",
        )
        result = runner.invoke(main, ["restart"])
        assert result.exit_code != 0
