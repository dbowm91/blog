"""CLI commands for deployment file rendering and installation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from devlog_cli.context import CliContext
from devlog_cli.exit_codes import ExitCode
from devlog_cli.output import render
from devlog_cli.result import Result

TARGET_CHOICES = ["systemd", "compose", "caddy", "nginx", "logrotate", "all"]
MODE_CHOICES = ["system", "user", "docker", "development"]


def _add_render_command(group: click.Group) -> None:
    @group.command("render")
    @click.option(
        "--mode",
        type=click.Choice(MODE_CHOICES, case_sensitive=False),
        required=True,
        help="Installation mode to render files for.",
    )
    @click.option(
        "--target",
        "targets",
        type=click.Choice(TARGET_CHOICES, case_sensitive=False),
        multiple=True,
        default=["all"],
        help="Deployment target(s) to render (default: all).",
    )
    @click.option(
        "--print",
        "print_content",
        is_flag=True,
        default=False,
        help="Print rendered content to stdout.",
    )
    @click.option(
        "--output",
        type=click.Path(path_type=Path),
        default=None,
        help="Directory to write rendered files into.",
    )
    @click.option(
        "--user", "user_unit", is_flag=True, default=False, help="Generate user systemd units."
    )
    @click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
    @click.pass_context
    def deploy_render(
        ctx: click.Context,
        mode: str,
        targets: tuple[str, ...],
        print_content: bool,
        output: Path | None,
        user_unit: bool,
        json_mode: bool,
    ) -> None:
        """Render deployment files for the specified mode and target(s)."""
        cli_ctx: CliContext = ctx.obj
        json_mode = json_mode or cli_ctx.json_mode

        effective_mode = "user" if user_unit else mode

        try:
            app = cli_ctx.ensure_app_context()
            with app.app_context():
                from app.services.operations.deploy import deploy_render as svc_render

                result = svc_render(effective_mode, targets=list(targets))
        except ImportError as e:
            r = Result.failure(
                code="deploy.render.missing_module",
                summary=f"Deploy service not available: {e}",
                exit_code=ExitCode.MISSING_DEPENDENCY,
                remediation="Ensure app.services.operations.deploy is installed.",
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)
        except Exception as e:
            r = Result.failure(
                code="deploy.render.unexpected",
                summary=f"Unexpected error: {e}",
                exit_code=ExitCode.GENERAL_FAILURE,
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

        if not result.ok:
            r = Result.failure(
                code=result.code,
                summary=result.summary,
                exit_code=ExitCode.GENERAL_FAILURE,
                details={"mode": effective_mode, "targets": list(targets)},
                warnings=result.warnings,
                remediation=result.remediation,
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

        files: list[dict[str, Any]] = []
        for f in result.files:
            entry: dict[str, Any] = {
                "target": f.get("target", ""),
                "filename": f.get("filename", ""),
                "description": f.get("description", ""),
            }
            if print_content and f.get("content"):
                entry["content"] = f["content"]
            files.append(entry)

        if output and not print_content:
            output.mkdir(parents=True, exist_ok=True)
            for f in result.files:
                if f.get("filename") and f.get("content"):
                    target = f.get("target", "unknown")
                    fname = Path(f["filename"]).name
                    dest = output / f"{target}-{fname}"
                    dest.write_text(f["content"])

        summary_parts = [f"{len(files)} file(s) rendered for {effective_mode}"]
        if result.warnings:
            summary_parts.append(f"{len(result.warnings)} warning(s)")
        summary = " | ".join(summary_parts)

        details: dict[str, Any] = {
            "mode": effective_mode,
            "targets": result.details.get("targets", list(targets)),
            "files": files,
        }

        if result.warnings:
            r = Result.degraded(
                code=result.code,
                summary=summary,
                details=details,
                warnings=result.warnings,
            )
        else:
            r = Result.success(
                code=result.code,
                summary=summary,
                details=details,
            )

        render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
        raise SystemExit(r.exit_code)


def _add_install_command(group: click.Group) -> None:
    @group.command("install")
    @click.option(
        "--mode",
        type=click.Choice(MODE_CHOICES, case_sensitive=False),
        required=True,
        help="Installation mode.",
    )
    @click.option(
        "--target",
        "targets",
        type=click.Choice(TARGET_CHOICES, case_sensitive=False),
        multiple=True,
        default=None,
        help="Target(s) to install (default: all).",
    )
    @click.option("--force", is_flag=True, default=False, help="Overwrite existing files.")
    @click.option("--dry-run", is_flag=True, default=False, help="Show plan without applying.")
    @click.option(
        "--base-dir",
        type=click.Path(path_type=Path),
        default=None,
        help="Base directory for deployment files.",
    )
    @click.option(
        "--user", "user_unit", is_flag=True, default=False, help="Install user systemd units."
    )
    @click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
    @click.pass_context
    def deploy_install(
        ctx: click.Context,
        mode: str,
        targets: tuple[str, ...],
        force: bool,
        dry_run: bool,
        base_dir: Path | None,
        user_unit: bool,
        json_mode: bool,
    ) -> None:
        """Install deployment files for the specified mode."""
        cli_ctx: CliContext = ctx.obj
        json_mode = json_mode or cli_ctx.json_mode

        effective_mode = "user" if user_unit else mode
        target_list = list(targets) if targets else None

        try:
            app = cli_ctx.ensure_app_context()
            with app.app_context():
                from app.services.operations.deploy import deploy_install as svc_install

                result = svc_install(
                    effective_mode,
                    targets=target_list,
                    force=force,
                    dry_run=dry_run,
                    base_dir=str(base_dir) if base_dir else None,
                )
        except ImportError as e:
            r = Result.failure(
                code="deploy.install.missing_module",
                summary=f"Deploy service not available: {e}",
                exit_code=ExitCode.MISSING_DEPENDENCY,
                remediation="Ensure app.services.operations.deploy is installed.",
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)
        except Exception as e:
            r = Result.failure(
                code="deploy.install.unexpected",
                summary=f"Unexpected error: {e}",
                exit_code=ExitCode.GENERAL_FAILURE,
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

        details: dict[str, Any] = {
            "mode": effective_mode,
            "dry_run": dry_run,
            "force": force,
            **result.details,
            "installed_files": list(result.installed_files),
        }
        if result.ok:
            r = Result.success(
                code=result.code,
                summary=result.summary,
                details=details,
                warnings=result.warnings,
            )
        else:
            r = Result.failure(
                code=result.code,
                summary=result.summary,
                exit_code=ExitCode.GENERAL_FAILURE,
                details=details,
                warnings=result.warnings,
                remediation=result.remediation,
            )

        render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
        raise SystemExit(r.exit_code)


def _add_check_command(group: click.Group) -> None:
    @group.command("check")
    @click.option(
        "--mode",
        type=click.Choice(MODE_CHOICES, case_sensitive=False),
        required=True,
        help="Installation mode to check.",
    )
    @click.option(
        "--base-dir",
        type=click.Path(path_type=Path),
        default=None,
        help="Base directory to check against.",
    )
    @click.option(
        "--user", "user_unit", is_flag=True, default=False, help="Check user systemd units."
    )
    @click.option("--json", "json_mode", is_flag=True, default=False, help="Output in JSON format.")
    @click.pass_context
    def deploy_check(
        ctx: click.Context,
        mode: str,
        base_dir: Path | None,
        user_unit: bool,
        json_mode: bool,
    ) -> None:
        """Check for deployment drift in installed files."""
        cli_ctx: CliContext = ctx.obj
        json_mode = json_mode or cli_ctx.json_mode

        effective_mode = "user" if user_unit else mode

        try:
            app = cli_ctx.ensure_app_context()
            with app.app_context():
                from app.services.operations.deploy import deploy_check as svc_check

                result = svc_check(effective_mode, base_dir=str(base_dir) if base_dir else None)
        except ImportError as e:
            r = Result.failure(
                code="deploy.check.missing_module",
                summary=f"Deploy service not available: {e}",
                exit_code=ExitCode.MISSING_DEPENDENCY,
                remediation="Ensure app.services.operations.deploy is installed.",
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)
        except Exception as e:
            r = Result.failure(
                code="deploy.check.unexpected",
                summary=f"Unexpected error: {e}",
                exit_code=ExitCode.GENERAL_FAILURE,
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

        summary_parts = [result.summary]
        if result.warnings:
            summary_parts.append(f"{len(result.warnings)} warning(s)")
        summary = " | ".join(summary_parts)

        details: dict[str, Any] = {
            "mode": effective_mode,
            **result.details,
        }

        if not result.ok:
            r = Result.failure(
                code=result.code,
                summary=summary,
                exit_code=ExitCode.GENERAL_FAILURE,
                details=details,
                warnings=result.warnings,
                remediation=result.remediation,
            )
        elif result.warnings:
            r = Result.degraded(
                code=result.code,
                summary=summary,
                details=details,
                warnings=result.warnings,
            )
        else:
            r = Result.success(
                code=result.code,
                summary=summary,
                details=details,
            )

        render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
        raise SystemExit(r.exit_code)


def register_deploy_commands(group: click.Group) -> None:
    """Register deployment subcommands with the deploy click group."""
    _add_render_command(group)
    _add_install_command(group)
    _add_check_command(group)
