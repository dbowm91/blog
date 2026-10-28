"""Foreground runner commands: ``serve``, ``worker`` and ``scheduler``.

The user-scope systemd units run these instead of a hardcoded release path,
because a user installation has no single system-wide prefix. They are also
the documented way to run the components in the foreground during an
incident.
"""

from __future__ import annotations

import signal
import subprocess
import sys
from typing import Any

import click

from devlog_cli.context import CliContext
from devlog_cli.exit_codes import ExitCode
from devlog_cli.output import render
from devlog_cli.result import Result

ASGI_TARGET = "app.asgi:asgi_app"


def _server_settings(app: Any) -> tuple[str, int]:
    """Return the host and port the application is configured to bind."""
    cfg = app.config.get("DEVLOG_CONFIG")
    host = getattr(getattr(cfg, "server", None), "host", "") or "127.0.0.1"
    port = getattr(getattr(cfg, "server", None), "port", 0) or 5000
    return str(host), int(port)


def _granian_major_version() -> int | None:
    """Return the major version of the installed granian, if it can be read."""
    try:
        import granian

        raw = str(getattr(granian, "__version__", ""))
        return int(raw.split(".")[0])
    except Exception:
        return None


def _granian_command(
    host: str,
    port: int,
    workers: int,
    timeout: int,
) -> list[str]:
    """Build the granian command line for the installed granian.

    granian 1.x takes ``--timeout``; granian 2.x replaced it with the
    per-worker blocking timeouts and rejects the option outright.
    """
    command = [
        sys.executable,
        "-m",
        "granian",
        "--interface",
        "asgi",
        "--workers",
        str(workers),
        "--host",
        host,
        "--port",
        str(port),
    ]

    if _granian_major_version() != 2:
        command.extend(["--timeout", str(timeout)])

    command.append(ASGI_TARGET)
    return command


def _run_foreground(command: list[str], *, description: str) -> None:
    """Run a command in the foreground and exit with its status."""
    try:
        completed = subprocess.run(command, check=False)
    except FileNotFoundError as e:
        r = Result.failure(
            code="serve.missing_dependency",
            summary=f"Cannot start {description}: {e}",
            exit_code=ExitCode.MISSING_DEPENDENCY,
            remediation="Install the runtime dependencies in the active virtualenv.",
        )
        render(r, json_mode=False, verbose=False)
        raise SystemExit(r.exit_code) from e

    raise SystemExit(completed.returncode)


def _add_serve_command(main: click.Group) -> None:
    @main.command("serve")
    @click.option("--host", default=None, help="Address to bind (default: from config).")
    @click.option("--port", default=None, type=int, help="Port to bind (default: from config).")
    @click.option("--workers", default=4, type=int, help="Number of worker processes.")
    @click.option("--timeout", default=60, type=int, help="Request timeout in seconds.")
    @click.pass_context
    def serve(
        ctx: click.Context,
        host: str | None,
        port: int | None,
        workers: int,
        timeout: int,
    ) -> None:
        """Run the ASGI server in the foreground."""
        cli_ctx: CliContext = ctx.obj

        app = cli_ctx.ensure_app_context()
        config_host, config_port = _server_settings(app)
        bind_host = host or config_host
        bind_port = port or config_port

        command = _granian_command(bind_host, bind_port, workers, timeout)
        _run_foreground(command, description="the ASGI server")


def _add_worker_command(main: click.Group) -> None:
    @main.command("worker")
    @click.option("--concurrency", default=1, type=int, help="Worker concurrency.")
    @click.option("--loglevel", default="info", help="Celery log level.")
    @click.pass_context
    def worker(ctx: click.Context, concurrency: int, loglevel: str) -> None:
        """Run the Celery worker in the foreground."""
        cli_ctx: CliContext = ctx.obj

        cli_ctx.ensure_app_context()

        command = [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "app.celery_app",
            "worker",
            f"--loglevel={loglevel}",
            f"--concurrency={concurrency}",
        ]
        _run_foreground(command, description="the Celery worker")


def _add_scheduler_command(main: click.Group) -> None:
    @main.command("scheduler")
    @click.pass_context
    def scheduler(ctx: click.Context) -> None:
        """Run the APScheduler jobs in the foreground."""
        cli_ctx: CliContext = ctx.obj

        app = cli_ctx.ensure_app_context()

        with app.app_context():
            from app.scheduler import init_scheduler, shutdown_scheduler

            scheduler_instance = init_scheduler(app)
            if scheduler_instance is None:
                r = Result.failure(
                    code="serve.scheduler_unavailable",
                    summary="The scheduler could not be started.",
                    exit_code=ExitCode.GENERAL_FAILURE,
                )
                render(r, json_mode=cli_ctx.json_mode, verbose=cli_ctx.verbose)
                raise SystemExit(r.exit_code)

            app.logger.info("Scheduler started; waiting for a termination signal.")

            _wait_for_signal()
            shutdown_scheduler(wait=True)
            app.logger.info("Scheduler stopped.")


def _wait_for_signal() -> None:
    """Block until SIGINT or SIGTERM arrives."""
    import threading

    event = threading.Event()

    def _handler(signum: int, frame: Any) -> None:
        event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handler)
        except ValueError:
            pass

    while not event.is_set():
        event.wait(3600)


def register_serve_commands(main: click.Group) -> None:
    """Register the foreground runner commands on the main CLI group."""
    _add_serve_command(main)
    _add_worker_command(main)
    _add_scheduler_command(main)


__all__ = ["register_serve_commands", "ASGI_TARGET"]
