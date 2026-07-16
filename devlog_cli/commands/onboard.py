"""Standalone CLI onboarding commands — calls service functions, handles I/O."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click

from devlog_cli.context import CliContext
from devlog_cli.exit_codes import ExitCode
from devlog_cli.output import render
from devlog_cli.result import Result


def _read_password_from_file(path: str) -> str:
    with open(path) as f:
        return f.read().strip()


def _handle_onboard_detect(ctx: click.Context) -> None:
    cli_ctx: CliContext = ctx.obj

    app = cli_ctx.ensure_app_context()
    with app.app_context():
        from app.services.operations.onboard import detect_installation

        result = detect_installation()

    details: dict[str, Any] = {
        "state": result.state,
        "config_exists": result.config_exists,
        "database_exists": result.database_exists,
        "admin_exists": result.admin_exists,
        **result.details,
    }
    r = Result.success(
        code=result.code,
        summary=result.summary,
        details=details,
    )
    render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
    raise SystemExit(r.exit_code)


def _handle_onboard_plan(
    ctx: click.Context,
    mode: str,
    profile: str,
    json_mode: bool,
) -> None:
    cli_ctx: CliContext = ctx.obj

    app = cli_ctx.ensure_app_context()
    with app.app_context():
        from app.onboarding.model import OnboardingInput
        from app.services.operations.onboard import generate_plan

        inp = OnboardingInput(mode=mode, profile=profile)
        result = generate_plan(inp)

    if json_mode:
        details: dict[str, Any] = {
            "actions": result.actions,
            "action_count": result.action_count,
        }
    else:
        from app.onboarding.planner import PlannedAction, format_plan_text

        plan = [PlannedAction(**a) for a in result.actions]
        plan_text = format_plan_text(plan)
        details = {
            "plan_text": plan_text,
            "action_count": result.action_count,
        }

    r = Result.success(
        code=result.code,
        summary=result.summary,
        details=details,
    )
    render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
    raise SystemExit(r.exit_code)


def _handle_onboard_run(
    ctx: click.Context,
    mode: str,
    profile: str,
    non_interactive: bool,
    dry_run: bool,
    accept_defaults: bool,
    site_url: str | None,
    admin_username: str | None,
    admin_password_file: str | None,
    json_mode: bool,
) -> None:
    cli_ctx: CliContext = ctx.obj

    admin_password = ""
    if admin_password_file:
        admin_password = _read_password_from_file(admin_password_file)
    elif non_interactive:
        r = Result.failure(
            code="onboard.run.missing_password",
            summary="Admin password is required in non-interactive mode. Use --admin-password-file.",
            exit_code=ExitCode.INVALID_USAGE,
        )
        render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
        raise SystemExit(r.exit_code)

    input_dict: dict[str, Any] = {
        "mode": mode,
        "profile": profile,
        "non_interactive": non_interactive,
        "dry_run": dry_run,
        "accept_defaults": accept_defaults,
        "admin_password": admin_password,
    }

    if site_url:
        input_dict["base_url"] = site_url
    if admin_username:
        input_dict["admin_username"] = admin_username

    if not non_interactive and not admin_password:
        interactive = sys.stdin.isatty() if hasattr(sys.stdin, "isatty") else False
        if interactive:
            admin_password = click.prompt(
                "Admin password", hide_input=True, confirmation_prompt=True
            )
            input_dict["admin_password"] = admin_password
        else:
            r = Result.failure(
                code="onboard.run.missing_password",
                summary="Admin password is required. Use --admin-password-file.",
                exit_code=ExitCode.INVALID_USAGE,
            )
            render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

    app = cli_ctx.ensure_app_context()
    with app.app_context():
        from app.services.operations.onboard import apply_onboarding

        try:
            result = apply_onboarding(input_dict)
        except ValueError as e:
            r = Result.failure(
                code="onboard.run.failed",
                summary=str(e),
                exit_code=ExitCode.GENERAL_FAILURE,
            )
            render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

    details: dict[str, Any] = {
        "config_path": result.config_path,
        "data_path": result.data_path,
        "admin_username": result.admin_username,
        "migration_head": result.migration_head,
        "steps_completed": result.steps_completed,
        "steps_total": result.steps_total,
        "next_command": result.next_command,
    }
    r = Result.success(
        code=result.code,
        summary=result.summary,
        details=details,
    )
    render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
    raise SystemExit(r.exit_code)


def _handle_onboard_resume(
    ctx: click.Context,
    data_path: str | None,
    json_mode: bool,
) -> None:
    cli_ctx: CliContext = ctx.obj

    resolved_data = Path(data_path) if data_path else None

    app = cli_ctx.ensure_app_context()
    with app.app_context():
        from app.services.operations.onboard import resume_onboarding

        result = resume_onboarding(data_path=resolved_data)

    details: dict[str, Any] = {
        "last_step": result.last_step,
        "last_step_index": result.last_step_index,
        "stopped_at": result.stopped_at,
        "stopped_reason": result.stopped_reason,
        "completed": result.completed,
    }

    if result.ok:
        r = Result.success(
            code=result.code,
            summary=result.summary,
            details=details,
        )
    else:
        r = Result.failure(
            code=result.code,
            summary=result.summary,
            exit_code=ExitCode.GENERAL_FAILURE,
        )

    render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
    raise SystemExit(r.exit_code)


def register_onboard_commands(onboard_group: click.Group) -> None:
    @onboard_group.command("detect")
    @click.pass_context
    def onboard_detect(ctx: click.Context) -> None:
        """Detect current installation state."""
        _handle_onboard_detect(ctx)

    @onboard_group.command("plan")
    @click.option(
        "--mode",
        type=click.Choice(["native", "docker"]),
        default="native",
        show_default=True,
        help="Installation mode.",
    )
    @click.option(
        "--profile",
        type=click.Choice(
            ["development", "native-production", "docker-production", "minimal", "full"]
        ),
        default="development",
        show_default=True,
        help="Deployment profile.",
    )
    @click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
    @click.pass_context
    def onboard_plan(
        ctx: click.Context,
        mode: str,
        profile: str,
        json_mode: bool,
    ) -> None:
        """Show onboarding plan without applying changes."""
        _handle_onboard_plan(ctx, mode, profile, json_mode)

    @onboard_group.command("run")
    @click.option(
        "--mode",
        type=click.Choice(["native", "docker"]),
        default="native",
        show_default=True,
        help="Installation mode.",
    )
    @click.option(
        "--profile",
        type=click.Choice(
            ["development", "native-production", "docker-production", "minimal", "full"]
        ),
        default="development",
        show_default=True,
        help="Deployment profile.",
    )
    @click.option(
        "--non-interactive",
        is_flag=True,
        default=False,
        help="Disable interactive prompts. Requires all values via options.",
    )
    @click.option(
        "--dry-run",
        is_flag=True,
        default=False,
        help="Show what would be done without making changes.",
    )
    @click.option(
        "--accept-defaults",
        is_flag=True,
        default=False,
        help="Accept default values for all prompts.",
    )
    @click.option("--site-url", default=None, help="Site base URL.")
    @click.option("--admin-username", default=None, help="Admin username.")
    @click.option(
        "--admin-password-file",
        type=click.Path(exists=True),
        default=None,
        help="Read admin password from file (non-interactive).",
    )
    @click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
    @click.pass_context
    def onboard_run(
        ctx: click.Context,
        mode: str,
        profile: str,
        non_interactive: bool,
        dry_run: bool,
        accept_defaults: bool,
        site_url: str | None,
        admin_username: str | None,
        admin_password_file: str | None,
        json_mode: bool,
    ) -> None:
        """Run interactive or non-interactive onboarding."""
        _handle_onboard_run(
            ctx,
            mode=mode,
            profile=profile,
            non_interactive=non_interactive,
            dry_run=dry_run,
            accept_defaults=accept_defaults,
            site_url=site_url,
            admin_username=admin_username,
            admin_password_file=admin_password_file,
            json_mode=json_mode,
        )

    @onboard_group.command("resume")
    @click.option(
        "--data-path",
        type=click.Path(),
        default=None,
        help="Path to data directory with onboarding metadata.",
    )
    @click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
    @click.pass_context
    def onboard_resume(
        ctx: click.Context,
        data_path: str | None,
        json_mode: bool,
    ) -> None:
        """Resume interrupted onboarding from last completed step."""
        _handle_onboard_resume(ctx, data_path, json_mode)
