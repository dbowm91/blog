"""Standalone CLI media commands."""

from __future__ import annotations

import click

from devlog_cli.context import CliContext
from devlog_cli.exit_codes import ExitCode
from devlog_cli.output import render
from devlog_cli.result import Result


@click.group()
def media() -> None:
    """Media management."""


@media.command("scan")
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
@click.pass_context
def media_scan(ctx: click.Context, json_mode: bool) -> None:
    """Scan for orphaned media files (dry run)."""
    cli_ctx: CliContext = ctx.obj
    json_mode = json_mode or cli_ctx.json_mode

    try:
        app = cli_ctx.ensure_app_context()
        with app.app_context():
            from app.services.operations.media import scan_orphaned_media

            op_result = scan_orphaned_media()

            r: Result
            if op_result.ok:
                r = Result.success(
                    code=op_result.code,
                    summary=op_result.summary,
                    details=op_result.details,
                    warnings=op_result.warnings,
                )
            else:
                r = Result.failure(
                    code=op_result.code,
                    summary=op_result.summary,
                    exit_code=ExitCode.SERVICE_ERROR,
                    details=op_result.details,
                    warnings=op_result.warnings,
                )

            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

    except SystemExit:
        raise
    except Exception as e:
        r = Result.failure(
            code="media.scan.unexpected",
            summary=f"Unexpected error: {e}",
            exit_code=ExitCode.SERVICE_ERROR,
        )
        render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
        raise SystemExit(r.exit_code)


@media.command("cleanup")
@click.option(
    "--apply", "apply_cleanup", is_flag=True, default=False, help="Actually delete orphaned files."
)
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
@click.pass_context
def media_cleanup(ctx: click.Context, apply_cleanup: bool, json_mode: bool) -> None:
    """Clean up orphaned media files."""
    cli_ctx: CliContext = ctx.obj
    json_mode = json_mode or cli_ctx.json_mode

    try:
        app = cli_ctx.ensure_app_context()
        with app.app_context():
            from app.services.operations.media import (
                scan_orphaned_media,
                apply_orphaned_media_cleanup,
            )

            if not apply_cleanup:
                op_result = scan_orphaned_media()
                r = Result.success(
                    code=op_result.code,
                    summary=f"Dry run: {op_result.summary}",
                    details=op_result.details,
                    warnings=op_result.warnings,
                )
                render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
                raise SystemExit(0)

            op_result = apply_orphaned_media_cleanup()

            result_r: Result
            if op_result.ok:
                result_r = Result.success(
                    code=op_result.code,
                    summary=op_result.summary,
                    details=op_result.details,
                    warnings=op_result.warnings,
                )
            else:
                result_r = Result.failure(
                    code=op_result.code,
                    summary=op_result.summary,
                    exit_code=ExitCode.SERVICE_ERROR,
                    details=op_result.details,
                    warnings=op_result.warnings,
                )

            render(result_r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(result_r.exit_code)

    except SystemExit:
        raise
    except Exception as e:
        r = Result.failure(
            code="media.cleanup.unexpected",
            summary=f"Unexpected error: {e}",
            exit_code=ExitCode.SERVICE_ERROR,
        )
        render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
        raise SystemExit(r.exit_code)


def register_media_commands(media_group: click.Group) -> None:
    """Register media subcommands on the given Click group."""
    for cmd in [media_scan, media_cleanup]:
        media_group.add_command(cmd)
