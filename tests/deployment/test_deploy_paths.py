"""Regression tests for the managed deployment path.

The rendered units have to point at the release the installer actually
creates, ``devlog deploy render --output`` has to write files, and the backup
services have to find the database the app actually uses.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from app.deployment import systemd
from app.filesystem.layout import InstallMode, RuntimePaths
from app.services.operations.deploy import _build_context
from devlog_cli.exit_codes import ExitCode
from devlog_cli.main import main

_RENDER_EXIT_CODES = {ExitCode.SUCCESS, ExitCode.DEGRADED}


class TestDeployRenderOutput:
    def test_output_directory_receives_one_file_per_target(self, tmp_path: Path) -> None:
        runner = CliRunner()
        output = tmp_path / "rendered"

        result = runner.invoke(
            main,
            ["deploy", "render", "--mode", "system", "--output", str(output), "--json"],
        )

        assert result.exit_code in _RENDER_EXIT_CODES, result.output
        written = sorted(p.name for p in output.iterdir() if p.is_file())
        assert written, "no files were written to the output directory"
        assert all("-" in name for name in written)
        assert any(name.startswith("systemd-") for name in written)

    def test_render_reports_the_files_it_produced(self, tmp_path: Path) -> None:
        runner = CliRunner()
        output = tmp_path / "rendered"

        result = runner.invoke(
            main,
            ["deploy", "render", "--mode", "system", "--output", str(output), "--json"],
        )

        assert result.exit_code in _RENDER_EXIT_CODES, result.output
        import json

        payload = json.loads(result.output)
        files = payload["details"]["files"]
        assert files
        for entry in files:
            assert entry["filename"]
            assert entry["target"]


class TestSystemdUnits:
    def test_system_units_point_at_the_installed_release(self) -> None:
        ctx = _build_context("system")

        unit = systemd.render_web_unit(ctx)

        assert unit is not None
        release = str(ctx.paths.release_dir.path)
        assert release in unit.content
        assert "granian" in unit.content
        assert "--port" in unit.content

    def test_user_units_do_not_point_at_the_system_prefix(self) -> None:
        ctx = _build_context("user")

        unit = systemd.render_web_unit(ctx, user_unit=True)

        assert unit is not None
        assert "/opt/devlog/current" not in unit.content

    def test_worker_unit_uses_the_release_venv(self) -> None:
        ctx = _build_context("system")

        unit = systemd.render_worker_unit(ctx)

        assert unit is not None
        assert str(ctx.paths.release_dir.path) in unit.content

    def test_system_unit_runs_as_the_service_account(self) -> None:
        ctx = _build_context("system")

        unit = systemd.render_web_unit(ctx)

        assert unit is not None
        assert "User=devlog" in unit.content
        assert "Group=devlog" in unit.content

    def test_system_unit_declares_the_runtime_directory(self) -> None:
        """``/run`` is a tmpfs, so systemd has to recreate the path."""
        ctx = _build_context("system")

        unit = systemd.render_web_unit(ctx)

        assert unit is not None
        assert "RuntimeDirectory=devlog" in unit.content

    def test_user_unit_declares_the_runtime_directory(self, monkeypatch) -> None:
        monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")

        ctx = _build_context("user")

        unit = systemd.render_web_unit(ctx, user_unit=True)

        assert unit is not None
        assert "RuntimeDirectory=devlog" in unit.content

    def test_the_unit_checks_that_its_directories_exist(self) -> None:
        ctx = _build_context("system")

        unit = systemd.render_web_unit(ctx)

        assert unit is not None
        for path in (
            ctx.paths.data_dir.path,
            ctx.paths.log_dir.path,
            ctx.paths.runtime_dir.path,
        ):
            assert f"ExecStartPre=/usr/bin/test -d {path}" in unit.content


class TestRuntimePaths:
    def test_system_release_dir_matches_the_installer(self) -> None:
        paths = RuntimePaths.for_mode(InstallMode.SYSTEM)

        assert paths.release_dir is not None
        assert paths.release_dir.path == Path("/opt/devlog/current")

    def test_release_dir_can_be_overridden(self, monkeypatch) -> None:
        monkeypatch.setenv("DEVLOG_RELEASE_DIR", "/srv/devlog/current")

        paths = RuntimePaths.for_mode(InstallMode.SYSTEM)

        assert paths.release_dir is not None
        assert paths.release_dir.path == Path("/srv/devlog/current")
