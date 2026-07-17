"""Top-level CLI lifecycle commands for service management."""

from __future__ import annotations

from typing import Any

import click

from devlog_cli.context import CliContext
from devlog_cli.exit_codes import ExitCode
from devlog_cli.output import render
from devlog_cli.result import Result


def _handle_lifecycle_result(
    cli_ctx: CliContext,
    result: Any,
    *,
    code_prefix: str,
    json_mode: bool | None = None,
) -> None:
    effective_json = json_mode if json_mode is not None else cli_ctx.json_mode

    if result.ok:
        r = Result.success(
            code=result.code,
            summary=result.summary,
            details=result.details,
            warnings=result.warnings,
        )
    else:
        r = Result.failure(
            code=result.code,
            summary=result.summary,
            exit_code=ExitCode.SERVICE_ERROR,
            details=result.details,
            warnings=result.warnings,
            remediation=result.remediation,
        )

    render(r, json_mode=effective_json, verbose=cli_ctx.verbose)
    raise SystemExit(r.exit_code)


def _add_start_command(main: click.Group) -> None:
    @main.command("start")
    @click.pass_context
    def lifecycle_start(ctx: click.Context) -> None:
        """Start the DevLog service."""
        cli_ctx: CliContext = ctx.obj

        try:
            app = cli_ctx.ensure_app_context()
            with app.app_context():
                from app.services.operations.deploy import lifecycle_start

                result = lifecycle_start()
        except ImportError as e:
            r = Result.failure(
                code="lifecycle.start.missing_module",
                summary=f"Deploy service not available: {e}",
                exit_code=ExitCode.MISSING_DEPENDENCY,
                remediation="Ensure app.services.operations.deploy is installed.",
            )
            render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)
        except Exception as e:
            r = Result.failure(
                code="lifecycle.start.unexpected",
                summary=f"Unexpected error: {e}",
                exit_code=ExitCode.GENERAL_FAILURE,
            )
            render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

        _handle_lifecycle_result(cli_ctx, result, code_prefix="lifecycle.start")


def _add_stop_command(main: click.Group) -> None:
    @main.command("stop")
    @click.pass_context
    def lifecycle_stop(ctx: click.Context) -> None:
        """Stop the DevLog service."""
        cli_ctx: CliContext = ctx.obj

        try:
            app = cli_ctx.ensure_app_context()
            with app.app_context():
                from app.services.operations.deploy import lifecycle_stop

                result = lifecycle_stop()
        except ImportError as e:
            r = Result.failure(
                code="lifecycle.stop.missing_module",
                summary=f"Deploy service not available: {e}",
                exit_code=ExitCode.MISSING_DEPENDENCY,
                remediation="Ensure app.services.operations.deploy is installed.",
            )
            render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)
        except Exception as e:
            r = Result.failure(
                code="lifecycle.stop.unexpected",
                summary=f"Unexpected error: {e}",
                exit_code=ExitCode.GENERAL_FAILURE,
            )
            render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

        _handle_lifecycle_result(cli_ctx, result, code_prefix="lifecycle.stop")


def _add_restart_command(main: click.Group) -> None:
    @main.command("restart")
    @click.pass_context
    def lifecycle_restart(ctx: click.Context) -> None:
        """Restart the DevLog service."""
        cli_ctx: CliContext = ctx.obj

        try:
            app = cli_ctx.ensure_app_context()
            with app.app_context():
                from app.services.operations.deploy import lifecycle_restart

                result = lifecycle_restart()
        except ImportError as e:
            r = Result.failure(
                code="lifecycle.restart.missing_module",
                summary=f"Deploy service not available: {e}",
                exit_code=ExitCode.MISSING_DEPENDENCY,
                remediation="Ensure app.services.operations.deploy is installed.",
            )
            render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)
        except Exception as e:
            r = Result.failure(
                code="lifecycle.restart.unexpected",
                summary=f"Unexpected error: {e}",
                exit_code=ExitCode.GENERAL_FAILURE,
            )
            render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

        _handle_lifecycle_result(cli_ctx, result, code_prefix="lifecycle.restart")


def _add_status_command(main: click.Group) -> None:
    @main.command("status")
    @click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
    @click.pass_context
    def lifecycle_status(ctx: click.Context, json_mode: bool) -> None:
        """Show DevLog service status."""
        cli_ctx: CliContext = ctx.obj
        json_mode = json_mode or cli_ctx.json_mode

        try:
            app = cli_ctx.ensure_app_context()
            with app.app_context():
                from app.services.operations.deploy import lifecycle_status

                result = lifecycle_status()
        except ImportError as e:
            r = Result.failure(
                code="lifecycle.status.missing_module",
                summary=f"Deploy service not available: {e}",
                exit_code=ExitCode.MISSING_DEPENDENCY,
                remediation="Ensure app.services.operations.deploy is installed.",
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)
        except Exception as e:
            r = Result.failure(
                code="lifecycle.status.unexpected",
                summary=f"Unexpected error: {e}",
                exit_code=ExitCode.GENERAL_FAILURE,
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

        _handle_lifecycle_result(
            cli_ctx, result, code_prefix="lifecycle.status", json_mode=json_mode
        )


def _add_logs_command(main: click.Group) -> None:
    @main.command("logs")
    @click.option("--follow", "-f", is_flag=True, default=False, help="Follow log output.")
    @click.option("--tail", default=50, type=int, help="Number of lines to show (default: 50).")
    @click.option(
        "--component", "-c", default="web", help="Component to show logs for (default: web)."
    )
    @click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
    @click.pass_context
    def lifecycle_logs(
        ctx: click.Context,
        follow: bool,
        tail: int,
        component: str,
        json_mode: bool,
    ) -> None:
        """Show DevLog service logs."""
        cli_ctx: CliContext = ctx.obj
        json_mode = json_mode or cli_ctx.json_mode

        try:
            app = cli_ctx.ensure_app_context()
            with app.app_context():
                from app.services.operations.deploy import lifecycle_logs

                result = lifecycle_logs(follow=follow, tail=tail, component=component)
        except ImportError as e:
            r = Result.failure(
                code="lifecycle.logs.missing_module",
                summary=f"Deploy service not available: {e}",
                exit_code=ExitCode.MISSING_DEPENDENCY,
                remediation="Ensure app.services.operations.deploy is installed.",
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)
        except Exception as e:
            r = Result.failure(
                code="lifecycle.logs.unexpected",
                summary=f"Unexpected error: {e}",
                exit_code=ExitCode.GENERAL_FAILURE,
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

        _handle_lifecycle_result(cli_ctx, result, code_prefix="lifecycle.logs", json_mode=json_mode)


def register_lifecycle_commands(main: click.Group) -> None:
    """Register top-level lifecycle commands on the main CLI group."""
    _add_start_command(main)
    _add_stop_command(main)
    _add_restart_command(main)
    _add_status_command(main)
    _add_logs_command(main)
