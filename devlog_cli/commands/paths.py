"""CLI commands for filesystem path management."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any

import click

from devlog_cli.context import CliContext
from devlog_cli.exit_codes import ExitCode
from devlog_cli.output import render
from devlog_cli.result import Result


def _add_status_command(group: click.Group) -> None:
    @group.command("status")
    @click.option(
        "--json", "json_mode", is_flag=True, default=False, help="Output in JSON format."
    )
    @click.option(
        "--mode",
        type=click.Choice(
            ["system", "user", "docker", "development"], case_sensitive=False
        ),
        default="development",
        help="Installation mode to report paths for.",
    )
    @click.pass_context
    def paths_status(ctx: click.Context, json_mode: bool, mode: str) -> None:
        """Report all resolved paths with provenance, existence, and permissions."""
        cli_ctx: CliContext = ctx.obj
        json_mode = json_mode or cli_ctx.json_mode

        try:
            from app.filesystem.layout import InstallMode, RuntimePaths

            install_mode = InstallMode(mode)
            paths_obj = RuntimePaths.for_mode(install_mode)

            path_entries: list[dict[str, Any]] = []
            for name, resolved in paths_obj.all_paths():
                entry: dict[str, Any] = {
                    "name": name,
                    "path": str(resolved),
                    "provenance": paths_obj.provenance_for(name),
                    "exists": resolved.exists(),
                }
                if resolved.exists():
                    entry["type"] = "dir" if resolved.is_dir() else "file"
                    try:
                        mode_bits = stat.S_IMODE(os.stat(resolved).st_mode)
                        entry["permissions"] = oct(mode_bits)
                        entry["writable"] = os.access(resolved, os.W_OK)
                    except OSError:
                        entry["permissions"] = "unknown"
                        entry["writable"] = False
                path_entries.append(entry)

            summary = f"Mode: {mode} | {len(path_entries)} path(s) resolved"
            r = Result.success(
                code="paths.status",
                summary=summary,
                details={"mode": mode, "paths": path_entries},
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

        except SystemExit:
            raise
        except ImportError as e:
            r = Result.failure(
                code="paths.status.missing_module",
                summary=f"Filesystem modules not available: {e}",
                exit_code=ExitCode.MISSING_DEPENDENCY,
                remediation="Ensure app.filesystem package is installed.",
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)
        except Exception as e:
            r = Result.failure(
                code="paths.status.unexpected",
                summary=f"Unexpected error: {e}",
                exit_code=ExitCode.GENERAL_FAILURE,
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)


def _add_discover_legacy_command(group: click.Group) -> None:
    @group.command("discover-legacy")
    @click.option(
        "--json", "json_mode", is_flag=True, default=False, help="Output in JSON format."
    )
    @click.option(
        "--search-root",
        type=click.Path(exists=True, path_type=Path),
        default=None,
        help="Root directory to search for legacy state (default: cwd).",
    )
    @click.pass_context
    def paths_discover_legacy(
        ctx: click.Context, json_mode: bool, search_root: Path | None
    ) -> None:
        """Read-only discovery of existing DevLog state in the current directory."""
        cli_ctx: CliContext = ctx.obj
        json_mode = json_mode or cli_ctx.json_mode

        try:
            from app.filesystem.discovery import discover_legacy_layout

            effective_root = search_root or Path.cwd()
            discovery = discover_legacy_layout(effective_root)

            confirmed: list[dict[str, str]] = []
            likely: list[dict[str, str]] = []
            unknown: list[dict[str, str]] = []

            for db_file in discovery.database_files:
                likely.append({"path": str(db_file), "type": "database"})
            for upload_dir in discovery.upload_dirs:
                likely.append({"path": str(upload_dir), "type": "uploads"})
            for backup_dir in discovery.backup_dirs:
                likely.append({"path": str(backup_dir), "type": "backups"})
            for theme_dir in discovery.theme_dirs:
                likely.append({"path": str(theme_dir), "type": "themes"})
            for log_dir in discovery.log_dirs:
                likely.append({"path": str(log_dir), "type": "logs"})
            for config_file in discovery.config_files:
                confirmed.append({"path": str(config_file), "type": "config"})
            for env_file in discovery.env_files:
                confirmed.append({"path": str(env_file), "type": "env"})
            for meta_file in discovery.metadata_files:
                confirmed.append({"path": str(meta_file), "type": "metadata"})

            total = len(confirmed) + len(likely) + len(unknown)
            summary_parts = [f"{total} item(s) found"]
            if confirmed:
                summary_parts.append(f"{len(confirmed)} confirmed")
            if likely:
                summary_parts.append(f"{len(likely)} likely")
            summary = " | ".join(summary_parts)

            details: dict[str, Any] = {
                "search_root": str(effective_root),
                "confirmed": confirmed,
                "likely": likely,
                "unknown": unknown,
            }

            r = Result.success(
                code="paths.discover_legacy",
                summary=summary,
                details=details,
            )

            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

        except SystemExit:
            raise
        except ImportError as e:
            r = Result.failure(
                code="paths.discover_legacy.missing_module",
                summary=f"Filesystem modules not available: {e}",
                exit_code=ExitCode.MISSING_DEPENDENCY,
                remediation="Ensure app.filesystem package is installed.",
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)
        except Exception as e:
            r = Result.failure(
                code="paths.discover_legacy.unexpected",
                summary=f"Unexpected error: {e}",
                exit_code=ExitCode.GENERAL_FAILURE,
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)


def _add_migrate_command(group: click.Group) -> None:
    @group.command("migrate")
    @click.option(
        "--from-mode",
        "source_mode",
        type=click.Choice(
            ["system", "user", "docker", "development"], case_sensitive=False
        ),
        required=True,
        help="Source layout mode.",
    )
    @click.option(
        "--to-mode",
        "target_mode",
        type=click.Choice(
            ["system", "user", "docker", "development"], case_sensitive=False
        ),
        required=True,
        help="Target layout mode.",
    )
    @click.option(
        "--json", "json_mode", is_flag=True, default=False, help="Output in JSON format."
    )
    @click.pass_context
    def paths_migrate(
        ctx: click.Context,
        source_mode: str,
        target_mode: str,
        json_mode: bool,
    ) -> None:
        """Plan filesystem migration (dry-run only)."""
        cli_ctx: CliContext = ctx.obj
        json_mode = json_mode or cli_ctx.json_mode

        try:
            from app.filesystem.layout import InstallMode, RuntimePaths
            from app.filesystem.migration import plan_migration

            src = InstallMode(source_mode)
            tgt = InstallMode(target_mode)
            source_paths = RuntimePaths.for_mode(src)
            target_paths = RuntimePaths.for_mode(tgt)

            plan = plan_migration(source_paths, target_paths)

            steps = [
                {
                    "action": step.action.value,
                    "source": str(step.source) if step.source else None,
                    "target": str(step.target),
                    "description": step.description,
                }
                for step in plan.steps
            ]

            summary_parts = [f"Migration plan: {source_mode} -> {target_mode}"]
            summary_parts.append(f"{len(steps)} step(s)")
            if plan.warnings:
                summary_parts.append(f"{len(plan.warnings)} warning(s)")
            summary = " | ".join(summary_parts)

            details: dict[str, Any] = {
                "source_mode": source_mode,
                "target_mode": target_mode,
                "steps": steps,
                "warnings": plan.warnings,
                "requires_downtime": plan.requires_downtime,
                "dry_run": True,
            }

            if plan.warnings:
                r = Result.degraded(
                    code="paths.migrate.plan",
                    summary=summary,
                    details=details,
                    warnings=plan.warnings,
                )
            else:
                r = Result.success(
                    code="paths.migrate.plan",
                    summary=summary,
                    details=details,
                )

            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

        except SystemExit:
            raise
        except ImportError as e:
            r = Result.failure(
                code="paths.migrate.missing_module",
                summary=f"Filesystem modules not available: {e}",
                exit_code=ExitCode.MISSING_DEPENDENCY,
                remediation="Ensure app.filesystem package is installed.",
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)
        except Exception as e:
            r = Result.failure(
                code="paths.migrate.unexpected",
                summary=f"Unexpected error: {e}",
                exit_code=ExitCode.GENERAL_FAILURE,
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)


def _add_check_command(group: click.Group) -> None:
    @group.command("check")
    @click.option(
        "--json", "json_mode", is_flag=True, default=False, help="Output in JSON format."
    )
    @click.option(
        "--mode",
        type=click.Choice(
            ["system", "user", "docker", "development"], case_sensitive=False
        ),
        default="development",
        help="Installation mode to check.",
    )
    @click.pass_context
    def paths_check(ctx: click.Context, json_mode: bool, mode: str) -> None:
        """Quick health check of all resolved filesystem paths."""
        cli_ctx: CliContext = ctx.obj
        json_mode = json_mode or cli_ctx.json_mode

        try:
            from app.filesystem.layout import InstallMode, RuntimePaths
            from app.filesystem.verification import verify_migration

            install_mode = InstallMode(mode)
            paths_obj = RuntimePaths.for_mode(install_mode)
            verification = verify_migration(paths_obj)

            summary = (
                f"{len(verification.errors)} error(s), "
                f"{len(verification.warnings)} warning(s)"
            )
            details: dict[str, Any] = {
                "success": verification.success,
                "errors": verification.errors,
                "warnings": verification.warnings,
                "path_checks": verification.path_checks,
            }

            if not verification.success:
                r = Result.failure(
                    code="paths.check.failed",
                    summary=summary,
                    exit_code=ExitCode.GENERAL_FAILURE,
                    details=details,
                    warnings=verification.warnings,
                )
            elif verification.warnings:
                r = Result.degraded(
                    code="paths.check.degraded",
                    summary=summary,
                    details=details,
                    warnings=verification.warnings,
                )
            else:
                r = Result.success(
                    code="paths.check.ok",
                    summary=summary,
                    details=details,
                )

            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)

        except SystemExit:
            raise
        except ImportError as e:
            r = Result.failure(
                code="paths.check.missing_module",
                summary=f"Filesystem modules not available: {e}",
                exit_code=ExitCode.MISSING_DEPENDENCY,
                remediation="Ensure app.filesystem package is installed.",
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)
        except Exception as e:
            r = Result.failure(
                code="paths.check.unexpected",
                summary=f"Unexpected error: {e}",
                exit_code=ExitCode.GENERAL_FAILURE,
            )
            render(r, json_mode=json_mode, verbose=cli_ctx.verbose)
            raise SystemExit(r.exit_code)


def register_paths_commands(group: click.Group) -> None:
    """Register path subcommands with the paths click group."""
    _add_status_command(group)
    _add_discover_legacy_command(group)
    _add_migrate_command(group)
    _add_check_command(group)
