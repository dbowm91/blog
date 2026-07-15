"""Standalone CLI data commands for DevLog."""

from __future__ import annotations

import click

from devlog_cli.context import CliContext
from devlog_cli.exit_codes import ExitCode
from devlog_cli.output import render
from devlog_cli.result import Result


@click.group()
def data() -> None:
    """Import and export site data."""


@data.command("export")
@click.argument("destination", type=click.Path())
@click.option("--force", is_flag=True, default=False, help="Overwrite existing file.")
@click.pass_context
def data_export(ctx: click.Context, destination: str, force: bool) -> None:
    """Export all site data to a JSON file."""
    cli_ctx: CliContext = ctx.obj

    try:
        app = cli_ctx.ensure_app_context()
        with app.app_context():
            from app.services.operations.transfer import export_site_data

            result = export_site_data(destination, force=force)
    except FileExistsError as exc:
        r = Result.failure(
            code="data.export.exists",
            summary=str(exc),
            exit_code=ExitCode.GENERAL_FAILURE,
            remediation="Use --force to overwrite the existing file.",
        )
        render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
        raise SystemExit(r.exit_code)
    except Exception as exc:
        r = Result.failure(
            code="data.export.error",
            summary=f"Export failed: {exc}",
            exit_code=ExitCode.SERVICE_ERROR,
        )
        render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
        raise SystemExit(r.exit_code)

    r = Result.success(
        code=result.code,
        summary=result.summary,
        details={
            "posts": result.posts,
            "subscribers": result.subscribers,
            "tags": result.tags,
            "pages": result.pages,
            "path": result.path,
        },
    )
    render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
    raise SystemExit(r.exit_code)


@data.command("import")
@click.argument("source", type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True, default=False, help="Validate without applying changes.")
@click.option("--apply", "do_apply", is_flag=True, default=False, help="Apply the import.")
@click.option(
    "--skip-confirmed/--include-confirmed",
    default=True,
    help="Skip already-confirmed subscribers (default: skip).",
)
@click.pass_context
def data_import(
    ctx: click.Context,
    source: str,
    dry_run: bool,
    do_apply: bool,
    skip_confirmed: bool,
) -> None:
    """Import site data from a JSON file."""
    cli_ctx: CliContext = ctx.obj

    if not dry_run and not do_apply:
        r = Result.failure(
            code="data.import.no_action",
            summary="Specify either --dry-run or --apply to proceed.",
            exit_code=ExitCode.INVALID_USAGE,
            remediation="Use --dry-run to preview changes, or --apply to execute the import.",
        )
        render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
        raise SystemExit(r.exit_code)

    try:
        app = cli_ctx.ensure_app_context()
        with app.app_context():
            from app.services.operations.transfer import import_site_data, validate_import

            validation = validate_import(source)
            if not validation.ok:
                r = Result.failure(
                    code=validation.code,
                    summary=validation.summary,
                    exit_code=ExitCode.INVALID_CONFIG,
                    details=validation.details,
                    warnings=validation.warnings,
                    remediation=validation.remediation,
                )
                render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
                raise SystemExit(r.exit_code)

            if dry_run:
                result = import_site_data(source, skip_confirmed=skip_confirmed, dry_run=True)
            else:
                result = import_site_data(source, skip_confirmed=skip_confirmed, dry_run=False)
    except SystemExit:
        raise
    except Exception as exc:
        r = Result.failure(
            code="data.import.error",
            summary=f"Import failed: {exc}",
            exit_code=ExitCode.SERVICE_ERROR,
        )
        render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
        raise SystemExit(r.exit_code)

    r = Result.success(
        code=result.code,
        summary=result.summary,
        details={
            "posts": result.posts,
            "subscribers": result.subscribers,
            "tags": result.tags,
            "pages": result.pages,
        },
    )
    render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
    raise SystemExit(r.exit_code)


def register_data_commands(data_group: click.Group) -> None:
    for cmd in [data_export, data_import]:
        data_group.add_command(cmd)
