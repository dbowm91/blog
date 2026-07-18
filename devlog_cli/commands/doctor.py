"""Standalone CLI doctor command."""

from __future__ import annotations

import click

from devlog_cli.context import CliContext
from devlog_cli.exit_codes import ExitCode
from devlog_cli.output import render
from devlog_cli.result import Result

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.operations.doctor import DoctorResult


@click.command("doctor")
@click.option(
    "--production",
    is_flag=True,
    default=False,
    help="Enforce production-required checks as failures.",
)
@click.option("--check", "check_id", type=str, default=None, help="Run a specific check by ID.")
@click.option("--category", type=str, default=None, help="Filter checks by category.")
@click.option("--fix-safe", is_flag=True, default=False, help="Apply safe fixes after checks.")
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
@click.option(
    "--list-checks", is_flag=True, default=False, help="List all available checks and exit."
)
@click.pass_context
def doctor(
    ctx: click.Context,
    production: bool,
    check_id: str | None,
    category: str | None,
    fix_safe: bool,
    json_mode: bool,
    list_checks: bool,
) -> None:
    """Run diagnostic checks to assess installation health."""
    cli_ctx: CliContext = ctx.obj
    json_mode = json_mode or cli_ctx.json_mode

    try:
        app = cli_ctx.ensure_app_context()
        with app.app_context():
            from app.services.operations.doctor import (
                get_registry,
                run_doctor,
                get_safe_fix_plan,
            )

            registry = get_registry()

            if list_checks:
                checks = registry.list_checks(category=category)
                if not checks:
                    r = Result.success(code="doctor.list.empty", summary="No checks registered.")
                    render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
                    raise SystemExit(ExitCode.SUCCESS)

                if json_mode:
                    import json as json_mod

                    check_list = [
                        {
                            "check_id": c.check_id,
                            "category": c.category,
                            "description": c.description,
                            "severity": c.severity,
                            "production_required": c.production_required,
                            "timeout_seconds": c.timeout_seconds,
                            "safe_fix_id": c.safe_fix_id,
                        }
                        for c in checks
                    ]
                    print(json_mod.dumps(check_list, indent=2))
                    raise SystemExit(ExitCode.SUCCESS)

                click.echo(f"Available checks ({len(checks)}):")
                for c in checks:
                    prod = " [required]" if c.production_required else ""
                    fix = f" [fix:{c.safe_fix_id}]" if c.safe_fix_id else ""
                    click.echo(
                        f"  {c.check_id:<30s} {c.category:<15s} {c.severity:<12s}{prod}{fix}"
                    )
                    click.echo(f"    {c.description}")
                raise SystemExit(ExitCode.SUCCESS)

            check_ids = [check_id] if check_id else None

            doctor_result = run_doctor(
                production=production,
                category=category,
                check_ids=check_ids,
                fix_safe=fix_safe,
            )

            if json_mode:
                import json as json_mod

                output = doctor_result.to_dict()
                if fix_safe:
                    plan = get_safe_fix_plan(doctor_result.checks)
                    output["details"]["safe_fixes_applied"] = [
                        {"fix_id": f.fix_id, "description": f.description} for f in plan
                    ]
                print(json_mod.dumps(output, indent=2))
            else:
                _render_human_doctor(doctor_result, verbose=cli_ctx.verbose, fix_safe=fix_safe)

            if doctor_result.status == "failure":
                raise SystemExit(ExitCode.GENERAL_FAILURE)
            elif doctor_result.status == "degraded":
                raise SystemExit(ExitCode.DEGRADED)
            else:
                raise SystemExit(ExitCode.SUCCESS)

    except SystemExit:
        raise
    except Exception as e:
        r = Result.failure(
            code="doctor.unexpected",
            summary=f"Unexpected error: {e}",
            exit_code=ExitCode.GENERAL_FAILURE,
        )
        render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
        raise SystemExit(r.exit_code)


def _render_human_doctor(
    result: "DoctorResult", *, verbose: bool = False, fix_safe: bool = False
) -> None:
    """Render doctor results in human-readable format."""
    status_icons = {
        "pass": "+",
        "warn": "!",
        "fail": "x",
        "skip": "-",
        "error": "?",
    }

    if result.ok and result.status == "healthy":
        click.echo(click.style(f"  {result.summary}", fg="green"))
    elif result.status == "degraded":
        click.echo(click.style(f"  {result.summary}", fg="yellow"))
    else:
        click.echo(click.style(f"  {result.summary}", fg="red"))

    click.echo(
        f"  Mode: {result.mode} | Version: {result.version} | Duration: {result.duration_ms:.0f}ms"
    )
    click.echo()

    categories: dict[str, list] = {}
    for c in result.checks:
        categories.setdefault(c.category, []).append(c)

    for cat_name in sorted(categories.keys()):
        cat_checks = categories[cat_name]
        click.echo(f"  [{cat_name.upper()}]")
        for c in cat_checks:
            icon = status_icons.get(c.status, "?")
            if c.status == "pass":
                color = "green"
            elif c.status == "warn":
                color = "yellow"
            elif c.status in ("fail", "error"):
                color = "red"
            else:
                color = None
            styled_icon = click.style(icon, fg=color) if color else icon
            line = f"    {styled_icon} {c.check_id:<30s} {c.summary}"
            if c.duration_ms > 0:
                line += f" ({c.duration_ms:.0f}ms)"
            click.echo(line)
            if verbose and c.details:
                for k, v in c.details.items():
                    click.echo(f"      {k}: {v}")
            if verbose and c.remediation:
                for r in c.remediation:
                    click.echo(f"      -> {r}")
        click.echo()

    if result.warnings:
        click.echo(click.style("  Warnings:", fg="yellow"))
        for w in result.warnings:
            click.echo(f"    ! {w}")
        click.echo()

    if result.remediation:
        click.echo(click.style("  Remediation:", fg="cyan"))
        for r in result.remediation:
            click.echo(f"    -> {r}")
        click.echo()

    if fix_safe:
        click.echo(click.style("  Safe fixes applied.", fg="cyan"))


def register_doctor_commands(main_group: click.Group) -> None:
    """Register the doctor command with the main CLI group."""
    main_group.add_command(doctor)
