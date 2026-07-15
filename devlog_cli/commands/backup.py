"""CLI commands for backup operations."""

from __future__ import annotations

import click

from devlog_cli.context import CliContext
from devlog_cli.exit_codes import ExitCode
from devlog_cli.output import render
from devlog_cli.result import Result


@click.group()
def backup() -> None:
    """Backup and restore."""


@backup.command("create")
@click.option("--compress", is_flag=True, default=False, help="Compress the backup with gzip.")
@click.option("--encrypt", is_flag=True, default=False, help="Encrypt the backup with AES-256-GCM.")
@click.option("--keep", default=7, type=int, help="Number of backups to retain.")
@click.pass_context
def backup_create(ctx: click.Context, compress: bool, encrypt: bool, keep: int) -> None:
    """Create a database backup."""
    cli_ctx: CliContext = ctx.obj

    try:
        app = cli_ctx.ensure_app_context()
    except Exception as exc:
        r = Result.failure(
            code="backup.create.app_context_failed",
            summary=f"Failed to initialize application: {exc}",
            exit_code=ExitCode.GENERAL_FAILURE,
        )
        render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
        raise SystemExit(r.exit_code)

    with app.app_context():
        try:
            from app.services.operations.backup import create_backup_operation
        except ImportError as exc:
            r = Result.failure(
                code="backup.create.import_failed",
                summary=f"Backup service unavailable: {exc}",
                exit_code=ExitCode.MISSING_DEPENDENCY,
            )
            render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

        try:
            op_result = create_backup_operation(
                compress=compress,
                encrypt=encrypt,
                keep=keep,
            )
        except Exception as exc:
            r = Result.failure(
                code="backup.create.error",
                summary=f"Backup failed: {exc}",
                exit_code=ExitCode.BACKUP_ERROR,
            )
            render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

    details = dict(op_result.details)
    if op_result.path:
        details["path"] = op_result.path
    details["verified"] = op_result.verified

    if op_result.ok:
        r = Result.success(
            code=op_result.code,
            summary=op_result.summary,
            details=details,
            warnings=op_result.warnings,
        )
    else:
        exit_code = ExitCode.BACKUP_ERROR
        if op_result.code == "backup.create.db_not_found":
            exit_code = ExitCode.DATABASE_ERROR
        elif op_result.code == "backup.create.encryption_unavailable":
            exit_code = ExitCode.MISSING_DEPENDENCY
        r = Result.failure(
            code=op_result.code,
            summary=op_result.summary,
            exit_code=exit_code,
            details=details,
            warnings=op_result.warnings,
            remediation=op_result.remediation,
        )

    render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
    raise SystemExit(r.exit_code)


@backup.command("verify")
@click.argument("path", type=click.Path(exists=True))
@click.pass_context
def backup_verify(ctx: click.Context, path: str) -> None:
    """Verify a backup file exists and is readable."""
    cli_ctx: CliContext = ctx.obj

    try:
        app = cli_ctx.ensure_app_context()
    except Exception as exc:
        r = Result.failure(
            code="backup.verify.app_context_failed",
            summary=f"Failed to initialize application: {exc}",
            exit_code=ExitCode.GENERAL_FAILURE,
        )
        render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
        raise SystemExit(r.exit_code)

    with app.app_context():
        try:
            from app.services.operations.backup import verify_backup
        except ImportError as exc:
            r = Result.failure(
                code="backup.verify.import_failed",
                summary=f"Backup service unavailable: {exc}",
                exit_code=ExitCode.MISSING_DEPENDENCY,
            )
            render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

        try:
            op_result = verify_backup(path)
        except Exception as exc:
            r = Result.failure(
                code="backup.verify.error",
                summary=f"Verification failed: {exc}",
                exit_code=ExitCode.BACKUP_ERROR,
            )
            render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

    details = dict(op_result.details)
    details["path"] = op_result.path

    if op_result.ok:
        r = Result.success(
            code=op_result.code,
            summary=op_result.summary,
            details=details,
            warnings=op_result.warnings,
        )
    else:
        r = Result.failure(
            code=op_result.code,
            summary=op_result.summary,
            exit_code=ExitCode.BACKUP_ERROR,
            details=details,
            warnings=op_result.warnings,
            remediation=op_result.remediation,
        )

    render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
    raise SystemExit(r.exit_code)


@backup.command("inspect")
@click.argument("path", type=click.Path(exists=True))
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
@click.pass_context
def backup_inspect(ctx: click.Context, path: str, json_mode: bool) -> None:
    """Inspect a backup file's type and properties."""
    cli_ctx: CliContext = ctx.obj
    json_mode = json_mode or cli_ctx.json_mode

    try:
        app = cli_ctx.ensure_app_context()
    except Exception as exc:
        r = Result.failure(
            code="backup.inspect.app_context_failed",
            summary=f"Failed to initialize application: {exc}",
            exit_code=ExitCode.GENERAL_FAILURE,
        )
        render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
        raise SystemExit(r.exit_code)

    with app.app_context():
        try:
            from app.services.operations.backup import inspect_backup
        except ImportError as exc:
            r = Result.failure(
                code="backup.inspect.import_failed",
                summary=f"Backup service unavailable: {exc}",
                exit_code=ExitCode.MISSING_DEPENDENCY,
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

        try:
            op_result = inspect_backup(path)
        except Exception as exc:
            r = Result.failure(
                code="backup.inspect.error",
                summary=f"Inspection failed: {exc}",
                exit_code=ExitCode.BACKUP_ERROR,
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

    details = dict(op_result.details)
    details["path"] = op_result.path

    if op_result.ok:
        r = Result.success(
            code=op_result.code,
            summary=op_result.summary,
            details=details,
        )
    else:
        r = Result.failure(
            code=op_result.code,
            summary=op_result.summary,
            exit_code=ExitCode.BACKUP_ERROR,
            details=details,
            remediation=op_result.remediation,
        )

    render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
    raise SystemExit(r.exit_code)


def register_backup_commands(backup_group: click.Group) -> None:
    """Register backup subcommands on the given Click group."""
    for cmd in [backup_create, backup_verify, backup_inspect]:
        backup_group.add_command(cmd)
