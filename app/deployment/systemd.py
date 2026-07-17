"""Systemd unit file renderers.

Pure functions that take a DeploymentContext and return RenderResult
with the rendered unit content.
"""

from __future__ import annotations

import re

from app.deployment.model import DeploymentContext, RenderResult


_REQUIRED_SECTIONS = frozenset({"[Unit]", "[Service]", "[Install]"})
_SHELL_INTERPOLATION_RE = re.compile(r"\$\{?\w+\}?|\$\w+")


def _env_file_path(ctx: DeploymentContext) -> str:
    return str(ctx.paths.env_file.path)


def _read_write_paths(ctx: DeploymentContext) -> list[str]:
    paths = [
        str(ctx.paths.data_dir.path),
        str(ctx.paths.log_dir.path),
        str(ctx.paths.runtime_dir.path),
    ]
    return sorted(set(p for p in paths if p))


def _working_directory(ctx: DeploymentContext) -> str:
    return str(ctx.paths.data_dir.path)


def _release_exec_start(ctx: DeploymentContext) -> str:
    release_dir = ctx.paths.release_dir
    if release_dir is not None:
        release_path = release_dir.path
        return f"{release_path}/venv/bin/python -m granian --interface asgi --workers 4 --timeout 60 --host {ctx.bind_address} --port {ctx.bind_port} run:asgi_app"
    return f"devlog serve --host {ctx.bind_address} --port {ctx.bind_port}"


def _user_release_exec_start(ctx: DeploymentContext) -> str:
    return f"devlog serve --host {ctx.bind_address} --port {ctx.bind_port}"


def render_web_unit(
    ctx: DeploymentContext,
    *,
    user_unit: bool = False,
) -> RenderResult:
    warnings: list[str] = []
    unit_name = "devlog-web@.service" if user_unit else "devlog-web.service"

    env_file = _env_file_path(ctx)
    rw_paths = _read_write_paths(ctx)
    working_dir = _working_directory(ctx)
    rw_paths_str = " ".join(rw_paths)

    pre_start_lines = [
        f"ExecStartPre=/opt/devlog/current/venv/bin/devlog config check --config {ctx.paths.config_file.path}",
    ]

    for p in rw_paths:
        pre_start_lines.append(f"ExecStartPre=/usr/bin/test -d {p}")

    pre_start = "\n".join(pre_start_lines)

    if user_unit:
        exec_start = _user_release_exec_start(ctx)
        service_section = f"""[Service]
Type=simple
EnvironmentFile={env_file}
{pre_start}
ExecStart={exec_start}
WorkingDirectory={working_dir}
Restart=on-failure
RestartSec=5
TimeoutStartSec=30
Umask=0027

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={rw_paths_str}"""
        install_section = "WantedBy=default.target"
    else:
        exec_start = _release_exec_start(ctx)
        service_section = f"""[Service]
Type=simple
User={ctx.service_user}
Group={ctx.service_group}
EnvironmentFile={env_file}
{pre_start}
ExecStart={exec_start}
WorkingDirectory={working_dir}
Restart=on-failure
RestartSec=5
TimeoutStartSec=30
Umask=0027

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={rw_paths_str}"""
        install_section = "WantedBy=multi-user.target"

    content = f"""[Unit]
Description=DevLog Blog CMS (version {ctx.version})
After=network.target
Documentation=https://github.com/dbowm91/blog

{service_section}

[Install]
{install_section}
"""

    return RenderResult(
        content=content,
        filename=unit_name,
        managed=True,
        warnings=warnings,
        permissions=0o644,
        description=f"Systemd unit for the DevLog web server ({'user' if user_unit else 'system'} mode)",
    )


def render_worker_unit(
    ctx: DeploymentContext,
    *,
    user_unit: bool = False,
) -> RenderResult | None:
    if not ctx.has_celery:
        return None

    warnings: list[str] = []
    unit_name = "devlog-worker@.service" if user_unit else "devlog-worker.service"

    env_file = _env_file_path(ctx)
    rw_paths = _read_write_paths(ctx)
    working_dir = _working_directory(ctx)
    rw_paths_str = " ".join(rw_paths)

    if user_unit:
        exec_start = "devlog worker"
        service_section = f"""[Service]
Type=simple
EnvironmentFile={env_file}
ExecStart={exec_start}
WorkingDirectory={working_dir}
Restart=on-failure
RestartSec=5
TimeoutStartSec=30
Umask=0027

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={rw_paths_str}"""
        install_section = "WantedBy=default.target"
    else:
        release_venv = "/opt/devlog/current/venv/bin"
        exec_start = (
            f"{release_venv}/celery -A app.celery_app worker --loglevel=info --concurrency=1"
        )
        service_section = f"""[Service]
Type=simple
User={ctx.service_user}
Group={ctx.service_group}
EnvironmentFile={env_file}
ExecStart={exec_start}
WorkingDirectory={working_dir}
Restart=on-failure
RestartSec=5
TimeoutStartSec=30
Umask=0027

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={rw_paths_str}"""
        install_section = "WantedBy=multi-user.target"

    content = f"""[Unit]
Description=DevLog Celery Worker (version {ctx.version})
After=network.target devlog-web.service
Documentation=https://github.com/dbowm91/blog

{service_section}

[Install]
{install_section}
"""

    return RenderResult(
        content=content,
        filename=unit_name,
        managed=True,
        warnings=warnings,
        permissions=0o644,
        description=f"Systemd unit for the DevLog Celery worker ({'user' if user_unit else 'system'} mode)",
    )


def render_scheduler_unit(
    ctx: DeploymentContext,
    *,
    user_unit: bool = False,
) -> RenderResult | None:
    if not ctx.has_scheduler:
        return None

    warnings: list[str] = []
    unit_name = "devlog-scheduler@.service" if user_unit else "devlog-scheduler.service"

    env_file = _env_file_path(ctx)
    rw_paths = _read_write_paths(ctx)
    working_dir = _working_directory(ctx)
    rw_paths_str = " ".join(rw_paths)

    if user_unit:
        exec_start = "devlog scheduler"
        service_section = f"""[Service]
Type=simple
EnvironmentFile={env_file}
ExecStart={exec_start}
WorkingDirectory={working_dir}
Restart=on-failure
RestartSec=5
TimeoutStartSec=30
Umask=0027

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={rw_paths_str}"""
        install_section = "WantedBy=default.target"
    else:
        release_venv = "/opt/devlog/current/venv/bin"
        exec_start = f"{release_venv}/flask scheduler-start"
        service_section = f"""[Service]
Type=simple
User={ctx.service_user}
Group={ctx.service_group}
EnvironmentFile={env_file}
ExecStart={exec_start}
WorkingDirectory={working_dir}
Restart=on-failure
RestartSec=5
TimeoutStartSec=30
Umask=0027

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={rw_paths_str}"""
        install_section = "WantedBy=multi-user.target"

    content = f"""[Unit]
Description=DevLog Scheduler (version {ctx.version})
After=network.target devlog-web.service
Documentation=https://github.com/dbowm91/blog

{service_section}

[Install]
{install_section}
"""

    return RenderResult(
        content=content,
        filename=unit_name,
        managed=True,
        warnings=warnings,
        permissions=0o644,
        description=f"Systemd unit for the DevLog APScheduler ({'user' if user_unit else 'system'} mode)",
    )


def validate_unit(content: str) -> list[str]:
    errors: list[str] = []
    lines = content.strip().splitlines()
    sections_found: set[str] = set()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            sections_found.add(stripped)

    for section in _REQUIRED_SECTIONS:
        if section not in sections_found:
            errors.append(f"Missing required section: {section}")

    in_service = False
    for line in lines:
        stripped = line.strip()
        if stripped == "[Service]":
            in_service = True
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            in_service = False
            continue
        if in_service and stripped.startswith("ExecStart="):
            value = stripped[len("ExecStart=") :]
            if _SHELL_INTERPOLATION_RE.search(value):
                errors.append(f"Shell interpolation in ExecStart: {stripped}")

    return errors
