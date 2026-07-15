"""Root CLI entry point for DevLog."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from devlog_cli import __version__
from devlog_cli.context import CliContext
from devlog_cli.output import render
from devlog_cli.result import Result


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="devlog")
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    help="Path to config file.",
)
@click.option(
    "--env-file",
    "env_file",
    type=click.Path(exists=True, path_type=Path),
    help="Path to .env file.",
)
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
@click.option("--quiet", "-q", is_flag=True, default=False, help="Suppress non-error output.")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enable verbose output.")
@click.option("--no-color", is_flag=True, default=False, help="Disable colored output.")
@click.pass_context
def main(
    ctx: click.Context,
    config_path: Path | None,
    env_file: Path | None,
    json_mode: bool,
    quiet: bool,
    verbose: bool,
    no_color: bool,
) -> None:
    """DevLog — a self-hosted blog CMS for technical writers."""
    ctx.ensure_object(dict)
    ctx.obj = CliContext(
        config_path=config_path,
        env_file=env_file,
        json_mode=json_mode,
        quiet=quiet,
        verbose=verbose,
        no_color=no_color,
    )

    if ctx.invoked_subcommand is None:
        cli_ctx: CliContext = ctx.obj
        result = Result.success(
            code="cli.version",
            summary=f"DevLog {__version__}",
        )
        render(result, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)


@main.command()
@click.pass_context
def version(ctx: click.Context) -> None:
    """Show DevLog version information."""
    cli_ctx: CliContext = ctx.obj
    result = Result.success(
        code="cli.version",
        summary=f"DevLog {__version__}",
        details={"version": __version__, "python": sys.version.split()[0]},
    )
    render(result, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)


@main.group()
def config() -> None:
    """Manage DevLog configuration."""


from devlog_cli.commands.config import register_config_commands  # noqa: E402

register_config_commands(config)


@main.group()
def admin() -> None:
    """Manage admin users."""


from devlog_cli.commands.admin import register_admin_commands  # noqa: E402

register_admin_commands(admin)


@main.group()
def db() -> None:
    """Database operations."""


from devlog_cli.commands.db import register_db_commands  # noqa: E402

register_db_commands(db)


@main.group()
def themes() -> None:
    """Theme management."""


from devlog_cli.commands.themes import register_theme_commands  # noqa: E402

register_theme_commands(themes)


@main.group()
def backup() -> None:
    """Backup and restore."""


from devlog_cli.commands.backup import register_backup_commands  # noqa: E402

register_backup_commands(backup)


@main.group()
def data() -> None:
    """Import and export site data."""


from devlog_cli.commands.data import register_data_commands  # noqa: E402

register_data_commands(data)


@main.group()
def media() -> None:
    """Media management."""


from devlog_cli.commands.media import register_media_commands  # noqa: E402

register_media_commands(media)


@main.group()
def deploy() -> None:
    """Deployment operations."""
