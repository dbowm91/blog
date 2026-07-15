"""Standalone CLI admin commands — calls service functions, handles I/O."""

from __future__ import annotations

import sys

import click

from devlog_cli.context import CliContext
from devlog_cli.exit_codes import ExitCode
from devlog_cli.output import render
from devlog_cli.result import Result


def _read_password_from_file(path: str) -> str:
    with open(path) as f:
        return f.read().strip()


def _prompt_password(interactive: bool) -> str:
    if interactive:
        return click.prompt("Password", hide_input=True, confirmation_prompt=True)
    return click.prompt("Password", hide_input=True)


def _handle_admin_create(
    ctx: click.Context,
    username: str | None,
    password_file: str | None,
    update_existing: bool,
) -> None:
    cli_ctx: CliContext = ctx.obj

    if username is None:
        username = click.prompt("Username")

    if password_file:
        password = _read_password_from_file(password_file)
    else:
        interactive = sys.stdin.isatty() if hasattr(sys.stdin, "isatty") else False
        password = _prompt_password(interactive)

    app = cli_ctx.ensure_app_context()
    with app.app_context():
        from app.services.operations.admin import create_admin, ConflictError

        try:
            result = create_admin(username, password, update_existing=update_existing)
        except ValueError as e:
            r = Result.failure(
                code="admin.create.invalid",
                summary=str(e),
                exit_code=ExitCode.INVALID_USAGE,
            )
            render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)
        except ConflictError as e:
            r = Result.failure(
                code="admin.create.conflict",
                summary=str(e),
                exit_code=ExitCode.GENERAL_FAILURE,
            )
            render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

    r = Result.success(
        code=result.code,
        summary=result.summary,
        details={"username": result.username, **result.details},
    )
    render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
    raise SystemExit(r.exit_code)


def _handle_admin_promote(ctx: click.Context, username: str) -> None:
    cli_ctx: CliContext = ctx.obj

    app = cli_ctx.ensure_app_context()
    with app.app_context():
        from app.services.operations.admin import promote_admin, ConflictError

        try:
            result = promote_admin(username)
        except ValueError as e:
            r = Result.failure(
                code="admin.promote.not_found",
                summary=str(e),
                exit_code=ExitCode.GENERAL_FAILURE,
            )
            render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)
        except ConflictError as e:
            r = Result.failure(
                code="admin.promote.conflict",
                summary=str(e),
                exit_code=ExitCode.GENERAL_FAILURE,
            )
            render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

    r = Result.success(
        code=result.code,
        summary=result.summary,
        details={"username": result.username},
    )
    render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
    raise SystemExit(r.exit_code)


def _handle_admin_reset_password(
    ctx: click.Context,
    username: str,
    password_file: str | None,
) -> None:
    cli_ctx: CliContext = ctx.obj

    if password_file:
        password = _read_password_from_file(password_file)
    else:
        interactive = sys.stdin.isatty() if hasattr(sys.stdin, "isatty") else False
        password = _prompt_password(interactive)

    app = cli_ctx.ensure_app_context()
    with app.app_context():
        from app.services.operations.admin import reset_admin_password

        try:
            result = reset_admin_password(username, password)
        except ValueError as e:
            r = Result.failure(
                code="admin.reset_password.invalid",
                summary=str(e),
                exit_code=ExitCode.INVALID_USAGE,
            )
            render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

    r = Result.success(
        code=result.code,
        summary=result.summary,
        details={"username": result.username},
    )
    render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
    raise SystemExit(r.exit_code)


def _handle_admin_list(ctx: click.Context) -> None:
    cli_ctx: CliContext = ctx.obj

    app = cli_ctx.ensure_app_context()
    with app.app_context():
        from app.services.operations.admin import list_admins

        result = list_admins()

    r = Result.success(
        code=result.code,
        summary=result.summary,
        details={"admins": result.admins, "count": result.details.get("count", 0)},
    )
    render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
    raise SystemExit(r.exit_code)


def register_admin_commands(admin_group: click.Group) -> None:
    @admin_group.command("create")
    @click.argument("username", required=False)
    @click.option(
        "--password-file",
        type=click.Path(exists=True),
        help="Read password from file (non-interactive).",
    )
    @click.option(
        "--update-existing",
        is_flag=True,
        default=False,
        help="Promote and reset password if user already exists.",
    )
    @click.pass_context
    def admin_create(
        ctx: click.Context,
        username: str | None,
        password_file: str | None,
        update_existing: bool,
    ) -> None:
        """Create a new admin user, or promote an existing user."""
        _handle_admin_create(ctx, username, password_file, update_existing)

    @admin_group.command("promote")
    @click.argument("username")
    @click.pass_context
    def admin_promote(ctx: click.Context, username: str) -> None:
        """Promote an existing user to admin."""
        _handle_admin_promote(ctx, username)

    @admin_group.command("reset-password")
    @click.argument("username")
    @click.option(
        "--password-file",
        type=click.Path(exists=True),
        help="Read password from file (non-interactive).",
    )
    @click.pass_context
    def admin_reset_password(
        ctx: click.Context,
        username: str,
        password_file: str | None,
    ) -> None:
        """Reset an admin user's password."""
        _handle_admin_reset_password(ctx, username, password_file)

    @admin_group.command("list")
    @click.pass_context
    def admin_list_cmd(ctx: click.Context) -> None:
        """List all admin users."""
        _handle_admin_list(ctx)
