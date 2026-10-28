"""Regression tests for the deployment surface the units depend on.

The user-scope systemd units run ``devlog serve``, ``devlog worker`` and
``devlog scheduler``; the system-scope scheduler unit runs
``flask scheduler-start``. The ASGI application has to be importable from the
installed package, and the rendered files have to land in the directories
their consumers read.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from app.deployment.install import DEFAULT_TARGET_DIRS, plan_installation
from app.deployment.model import RenderResult
from devlog_cli.main import main


class TestForegroundCommands:
    def test_serve_is_registered(self) -> None:
        result = CliRunner().invoke(main, ["serve", "--help"])

        assert result.exit_code == 0
        assert "--host" in result.output
        assert "--port" in result.output

    def test_worker_is_registered(self) -> None:
        result = CliRunner().invoke(main, ["worker", "--help"])

        assert result.exit_code == 0
        assert "--concurrency" in result.output

    def test_scheduler_is_registered(self) -> None:
        result = CliRunner().invoke(main, ["scheduler", "--help"])

        assert result.exit_code == 0


class TestAsgiEntryPoint:
    def test_the_asgi_module_is_importable_from_the_package(self) -> None:
        import importlib

        module = importlib.import_module("app.asgi")

        assert hasattr(module, "asgi_app")
        assert hasattr(module, "app")


class TestInstallLayout:
    def _rendered(self, target: str, filename: str) -> RenderResult:
        return RenderResult(
            content="x",
            filename=filename,
            managed=True,
            target=target,
        )

    def test_units_land_in_the_systemd_directory(self) -> None:
        plan = plan_installation([self._rendered("systemd", "devlog-web.service")])

        assert plan.files[0].path == Path("/etc/systemd/system/devlog-web.service")

    def test_the_nginx_include_lands_in_the_nginx_directory(self) -> None:
        plan = plan_installation([self._rendered("nginx", "devlog.conf")])

        assert plan.files[0].path == Path("/etc/nginx/conf.d/devlog.conf")

    def test_the_logrotate_file_lands_in_the_logrotate_directory(self) -> None:
        plan = plan_installation([self._rendered("logrotate", "devlog")])

        assert plan.files[0].path == Path("/etc/logrotate.d/devlog")

    def test_an_explicit_base_dir_overrides_the_defaults(self, tmp_path: Path) -> None:
        plan = plan_installation(
            [self._rendered("systemd", "devlog-web.service")],
            base_dir=tmp_path,
        )

        assert plan.files[0].path == tmp_path / "devlog-web.service"

    def test_every_target_has_a_default_directory(self) -> None:
        for target in ("systemd", "compose", "caddy", "nginx", "logrotate"):
            assert target in DEFAULT_TARGET_DIRS
