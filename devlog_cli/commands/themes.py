"""Standalone CLI theme commands — thin adapters over the operations facade."""

from __future__ import annotations

import click

from devlog_cli.context import CliContext
from devlog_cli.exit_codes import ExitCode
from devlog_cli.output import render
from devlog_cli.result import Result


def _to_result(op_result, *, verbose: bool = False) -> Result:
    details = dict(op_result.details)
    if hasattr(op_result, "themes"):
        details["themes"] = op_result.themes
        details["total"] = op_result.total
    if op_result.ok:
        return Result.success(
            code=op_result.code,
            summary=op_result.summary,
            details=details,
            warnings=list(op_result.warnings),
        )
    return Result.failure(
        code=op_result.code,
        summary=op_result.summary,
        details=details,
        warnings=list(op_result.warnings),
        remediation=list(op_result.remediation),
    )


def register_theme_commands(group: click.Group) -> None:
    """Register theme subcommands onto a Click group."""

    @group.command("list")
    @click.option(
        "--source",
        type=click.Choice(["all", "bundled", "external"]),
        default="all",
    )
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON for automation.")
    @click.option("--warnings", "show_warnings", is_flag=True, help="Include diagnostic summaries.")
    @click.option("--verbose", is_flag=True, help="Show absolute paths (operator only).")
    @click.pass_context
    def themes_list(
        ctx: click.Context, source: str, as_json: bool, show_warnings: bool, verbose: bool
    ) -> None:
        """List all available themes."""
        cli_ctx: CliContext = ctx.obj
        app = cli_ctx.ensure_app_context()

        from app.services.operations.themes import list_theme_descriptors

        with app.app_context():
            op_result = list_theme_descriptors(source=source)

        as_json = as_json or cli_ctx.json_mode
        verbose = verbose or cli_ctx.verbose

        if as_json:
            render(
                _to_result(op_result, verbose=verbose),
                json_mode=True,
                verbose=verbose,
            )
            return

        if not op_result.themes:
            render(
                Result.success(code="themes.list.empty", summary="No themes found."),
                json_mode=False,
            )
            return

        header = f"{'Name':<30} {'Source':<10} {'Type':<10} {'Status':<10} {'Warns':<7}"
        click.echo(header)
        click.echo("-" * len(header))

        for row in op_result.themes:
            theme_type = (
                "dark"
                if row.get("is_dark")
                else ("light" if row.get("is_dark") is False else "unknown")
            )
            overrides = " (overrides)" if row.get("overrides_bundled") else ""
            warns = str(len(row.get("warnings", []))) if row.get("warnings") else "-"
            line = (
                f"{row['display_name']:<30} {row['source']:<10} {theme_type:<10} "
                f"{row.get('status', 'ok')}{overrides} {warns:<7}"
            )
            click.echo(line)
            if show_warnings and row.get("warnings"):
                for w in row["warnings"]:
                    click.echo(f"  WARNING: {w}")

        click.echo(f"\nTotal: {op_result.total} themes")

    @group.command("validate")
    @click.argument("path")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON for automation.")
    @click.pass_context
    def themes_validate(ctx: click.Context, path: str, as_json: bool) -> None:
        """Validate a Halloy TOML theme file or a registered theme name."""
        cli_ctx: CliContext = ctx.obj
        app = cli_ctx.ensure_app_context()

        from app.services.operations.themes import validate_theme

        with app.app_context():
            op_result = validate_theme(path)

        as_json = as_json or cli_ctx.json_mode
        render(_to_result(op_result), json_mode=as_json, verbose=cli_ctx.verbose)
        if not op_result.ok:
            raise SystemExit(ExitCode.GENERAL_FAILURE)

    @group.command("inspect")
    @click.argument("name")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON for automation.")
    @click.option("--css", "as_css", is_flag=True, help="Output generated CSS variables.")
    @click.pass_context
    def themes_inspect(ctx: click.Context, name: str, as_json: bool, as_css: bool) -> None:
        """Inspect a theme's full details."""
        cli_ctx: CliContext = ctx.obj
        app = cli_ctx.ensure_app_context()

        from app.services.operations.themes import inspect_theme

        with app.app_context():
            op_result = inspect_theme(name)

        if as_css:
            click.echo(op_result.details.get("css", ""))
            return

        as_json = as_json or cli_ctx.json_mode
        render(_to_result(op_result), json_mode=as_json, verbose=cli_ctx.verbose)
        if not op_result.ok:
            raise SystemExit(ExitCode.GENERAL_FAILURE)

    @group.command("refresh")
    @click.pass_context
    def themes_refresh(ctx: click.Context) -> None:
        """Refresh the theme registry."""
        cli_ctx: CliContext = ctx.obj
        app = cli_ctx.ensure_app_context()

        from app.services.operations.themes import refresh_theme_registry

        with app.app_context():
            op_result = refresh_theme_registry()

        render(_to_result(op_result), json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)

    @group.command("paths")
    @click.pass_context
    def themes_paths(ctx: click.Context) -> None:
        """Display theme resource paths and configuration."""
        cli_ctx: CliContext = ctx.obj
        app = cli_ctx.ensure_app_context()

        from app.services.operations.themes import get_theme_paths

        with app.app_context():
            op_result = get_theme_paths()

        render(_to_result(op_result), json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)

    @group.command("accessibility")
    @click.option(
        "--source",
        type=click.Choice(["all", "bundled", "external"]),
        default="all",
    )
    @click.option("--strict", is_flag=True, help="Reject external themes with mandatory failures.")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON for automation.")
    @click.pass_context
    def themes_accessibility(ctx: click.Context, source: str, strict: bool, as_json: bool) -> None:
        """Run WCAG contrast checks over all themes with severity classification."""
        cli_ctx: CliContext = ctx.obj
        app = cli_ctx.ensure_app_context()

        from app.services.operations.themes import run_accessibility_check

        with app.app_context():
            op_result = run_accessibility_check(source=source, strict=strict)

        as_json = as_json or cli_ctx.json_mode
        render(_to_result(op_result), json_mode=as_json, verbose=cli_ctx.verbose)

        if strict and not op_result.ok:
            rejected = op_result.details.get("strict_rejected", [])
            if rejected:
                click.echo(
                    f"\nStrict mode: {len(rejected)} external theme(s) rejected due to "
                    f"unexpected mandatory failures."
                )
                for name in rejected:
                    click.echo(f"  REJECTED: {name}")
                raise SystemExit(ExitCode.GENERAL_FAILURE)
