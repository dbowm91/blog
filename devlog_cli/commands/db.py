"""Standalone CLI database commands."""

from __future__ import annotations

import click

from devlog_cli.context import CliContext
from devlog_cli.exit_codes import ExitCode
from devlog_cli.output import render
from devlog_cli.result import Result


@click.group()
def db() -> None:
    """Database operations."""


@db.command("check")
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
@click.pass_context
def db_check(ctx: click.Context, json_mode: bool) -> None:
    """Run SQLite database integrity check."""
    cli_ctx: CliContext = ctx.obj
    json_mode = json_mode or cli_ctx.json_mode

    try:
        app = cli_ctx.ensure_app_context()
        with app.app_context():
            from app.services.operations.database import check_database_integrity

            op_result = check_database_integrity()

            r: Result
            if op_result.ok:
                r = Result.success(
                    code=op_result.code,
                    summary=op_result.summary,
                    details=op_result.details,
                )
            else:
                r = Result.failure(
                    code=op_result.code,
                    summary=op_result.summary,
                    exit_code=ExitCode.DATABASE_ERROR,
                    details=op_result.details,
                    remediation=op_result.remediation,
                )

            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

    except SystemExit:
        raise
    except Exception as e:
        r = Result.failure(
            code="db.check.unexpected",
            summary=f"Unexpected error: {e}",
            exit_code=ExitCode.DATABASE_ERROR,
        )
        render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
        raise SystemExit(r.exit_code)


@db.command("rebuild-search")
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
@click.pass_context
def db_rebuild_search(ctx: click.Context, json_mode: bool) -> None:
    """Rebuild the FTS5 search index."""
    cli_ctx: CliContext = ctx.obj
    json_mode = json_mode or cli_ctx.json_mode

    try:
        app = cli_ctx.ensure_app_context()
        with app.app_context():
            from app.services.operations.database import rebuild_search_index

            op_result = rebuild_search_index()

            r: Result
            if op_result.ok:
                r = Result.success(
                    code=op_result.code,
                    summary=op_result.summary,
                    details=op_result.details,
                )
            else:
                r = Result.failure(
                    code=op_result.code,
                    summary=op_result.summary,
                    exit_code=ExitCode.SERVICE_ERROR,
                    details=op_result.details,
                    remediation=op_result.remediation,
                )

            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

    except SystemExit:
        raise
    except Exception as e:
        r = Result.failure(
            code="db.rebuild_search.unexpected",
            summary=f"Unexpected error: {e}",
            exit_code=ExitCode.SERVICE_ERROR,
        )
        render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
        raise SystemExit(r.exit_code)


@db.command("status")
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
@click.pass_context
def db_status(ctx: click.Context, json_mode: bool) -> None:
    """Show current Alembic migration status."""
    cli_ctx: CliContext = ctx.obj
    json_mode = json_mode or cli_ctx.json_mode

    try:
        app = cli_ctx.ensure_app_context()
        with app.app_context():
            from app.services.operations.database import get_migration_status

            op_result = get_migration_status()

            r: Result
            if op_result.ok:
                r = Result.success(
                    code=op_result.code,
                    summary=op_result.summary,
                    details=op_result.details,
                )
            else:
                r = Result.failure(
                    code=op_result.code,
                    summary=op_result.summary,
                    exit_code=ExitCode.DATABASE_ERROR,
                    details=op_result.details,
                    remediation=op_result.remediation,
                )

            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

    except SystemExit:
        raise
    except Exception as e:
        r = Result.failure(
            code="db.status.unexpected",
            summary=f"Unexpected error: {e}",
            exit_code=ExitCode.DATABASE_ERROR,
        )
        render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
        raise SystemExit(r.exit_code)


@db.command("migrate")
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
@click.pass_context
def db_migrate(ctx: click.Context, json_mode: bool) -> None:
    """Apply pending database migrations."""
    cli_ctx: CliContext = ctx.obj
    json_mode = json_mode or cli_ctx.json_mode

    try:
        app = cli_ctx.ensure_app_context()
        with app.app_context():
            from app.services.operations.database import run_migrations

            op_result = run_migrations()

            r: Result
            if op_result.ok:
                r = Result.success(
                    code=op_result.code,
                    summary=op_result.summary,
                    details=op_result.details,
                )
            else:
                r = Result.failure(
                    code=op_result.code,
                    summary=op_result.summary,
                    exit_code=ExitCode.DATABASE_ERROR,
                    details=op_result.details,
                    remediation=op_result.remediation,
                )

            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

    except SystemExit:
        raise
    except Exception as e:
        r = Result.failure(
            code="db.migrate.unexpected",
            summary=f"Unexpected error: {e}",
            exit_code=ExitCode.DATABASE_ERROR,
        )
        render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
        raise SystemExit(r.exit_code)


def register_db_commands(db_group: click.Group) -> None:
    """Register database commands with the db click group."""
    for cmd in [db_check, db_rebuild_search, db_status, db_migrate]:
        db_group.add_command(cmd)
