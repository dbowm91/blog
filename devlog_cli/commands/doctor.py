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
@click.option(
    "--deep",
    is_flag=True,
    default=False,
    help="Include expensive checks (e.g., SQLite integrity, WAL checkpoint).",
)
@click.option(
    "--no-parallel",
    is_flag=True,
    default=False,
    help="Disable parallel check execution.",
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
    deep: bool,
    no_parallel: bool,
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
                checks = registry.list_checks(category=category, deep=deep)
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
                            "deep": c.deep,
                        }
                        for c in checks
                    ]
                    print(json_mod.dumps(check_list, indent=2))
                    raise SystemExit(ExitCode.SUCCESS)

                click.echo(f"Available checks ({len(checks)}):")
                for c in checks:
                    prod = " [required]" if c.production_required else ""
                    fix = f" [fix:{c.safe_fix_id}]" if c.safe_fix_id else ""
                    deep_tag = " [deep]" if c.deep else ""
                    click.echo(
                        f"  {c.check_id:<35s} {c.category:<15s} {c.severity:<12s}{prod}{fix}{deep_tag}"
                    )
                    click.echo(f"    {c.description}")
                raise SystemExit(ExitCode.SUCCESS)

            check_ids = [check_id] if check_id else None

            doctor_result = run_doctor(
                production=production,
                category=category,
                check_ids=check_ids,
                fix_safe=fix_safe,
                deep=deep,
                parallel=not no_parallel,
            )

            if json_mode:
                import json as json_mod

                output = doctor_result.to_dict()
                if fix_safe:
                    plan = get_safe_fix_plan(doctor_result.checks)
                    output["details"]["safe_fixes_applied"] = [
                        {"fix_id": f.fix_id, "description": f.description} for f in plan
                    ]
                print(json_mod.dumps(output, indent=2, default=str))
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


_STATUS_ICONS = {
    "pass": "+",
    "warn": "!",
    "fail": "x",
    "skip": "-",
    "error": "?",
}

_STATUS_COLORS = {
    "pass": "green",
    "warn": "yellow",
    "fail": "red",
    "error": "red",
}


def _render_human_doctor(
    result: "DoctorResult", *, verbose: bool = False, fix_safe: bool = False
) -> None:
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

    severity_order = {"required": 0, "recommended": 1, "optional": 2}
    status_order = {"fail": 0, "error": 1, "warn": 2, "skip": 3, "pass": 4}
    sorted_checks = sorted(
        result.checks,
        key=lambda c: (severity_order.get(c.severity, 9), status_order.get(c.status, 9)),
    )

    categories: dict[str, list] = {}
    for c in sorted_checks:
        categories.setdefault(c.category, []).append(c)

    for cat_name in sorted(categories.keys()):
        cat_checks = categories[cat_name]
        click.echo(f"  [{cat_name.upper()}]")
        for c in cat_checks:
            icon = _STATUS_ICONS.get(c.status, "?")
            color = _STATUS_COLORS.get(c.status)
            styled_icon = click.style(icon, fg=color) if color else icon
            line = f"    {styled_icon} {c.check_id:<35s} {c.summary}"
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
