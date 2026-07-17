from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from app.filesystem.layout import InstallationMetadata, InstallMode


class ServiceBackend(Enum):
    SYSTEMD = "systemd"
    SYSTEMD_USER = "systemd_user"
    DOCKER = "docker"
    FOREGROUND = "foreground"
    UNKNOWN = "unknown"


class ServiceStatus(Enum):
    INSTALLED = "installed"
    RUNNING = "running"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNMANAGED = "unmanaged"


@dataclass(frozen=True)
class LifecycleStatus:
    backend: ServiceBackend
    status: ServiceStatus
    version: str = ""
    pid: int | None = None
    uptime: str = ""
    health: str = ""
    details: dict[str, str] = field(default_factory=dict)


def run_command(cmd: list[str], *, timeout: int = 30) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -2, "", f"Command timed out after {timeout}s"


def detect_backend(
    metadata: InstallationMetadata | None,
    mode: InstallMode,
) -> ServiceBackend:
    if mode == InstallMode.DOCKER:
        return ServiceBackend.DOCKER
    if mode == InstallMode.DEVELOPMENT:
        return ServiceBackend.FOREGROUND
    if mode == InstallMode.SYSTEM:
        return ServiceBackend.SYSTEMD
    if mode == InstallMode.USER:
        return ServiceBackend.SYSTEMD_USER
    if metadata is not None:
        if metadata.mode == InstallMode.DOCKER:
            return ServiceBackend.DOCKER
        if metadata.mode == InstallMode.SYSTEM:
            return ServiceBackend.SYSTEMD
        if metadata.mode == InstallMode.USER:
            return ServiceBackend.SYSTEMD_USER
    return ServiceBackend.UNKNOWN


def _systemctl_cmd(*, user_unit: bool = False) -> list[str]:
    if user_unit:
        return ["systemctl", "--user"]
    return ["systemctl"]


def _docker_compose_cmd(*, project_dir: Path | None = None) -> list[str]:
    base = ["docker", "compose"]
    if project_dir is not None:
        base.extend(["--project-directory", str(project_dir)])
    return base


def get_service_status(
    backend: ServiceBackend,
    *,
    user_unit: bool = False,
    compose_dir: Path | None = None,
) -> LifecycleStatus:
    if backend == ServiceBackend.SYSTEMD or backend == ServiceBackend.SYSTEMD_USER:
        use_user = backend == ServiceBackend.SYSTEMD_USER or user_unit
        base = _systemctl_cmd(user_unit=use_user)
        rc, stdout, stderr = run_command([*base, "is-active", "devlog-web.service"])
        active = stdout.strip() if rc == 0 else ""
        if active == "active":
            status = ServiceStatus.RUNNING
        elif active in ("activating", "reloading"):
            status = ServiceStatus.DEGRADED
        elif active == "failed":
            status = ServiceStatus.FAILED
        elif active == "inactive":
            status = ServiceStatus.INSTALLED
        else:
            status = ServiceStatus.UNMANAGED

        pid: int | None = None
        if status == ServiceStatus.RUNNING:
            rc_pid, out_pid, _ = run_command(
                [*base, "show", "devlog-web.service", "--property=MainPID", "--value"]
            )
            if rc_pid == 0:
                try:
                    pid = int(out_pid.strip())
                except (ValueError, TypeError):
                    pid = None

        uptime_str = ""
        if status == ServiceStatus.RUNNING and pid is not None:
            rc_uptime, out_uptime, _ = run_command(["ps", "-o", "etime=", "-p", str(pid)])
            if rc_uptime == 0:
                uptime_str = out_uptime.strip()

        return LifecycleStatus(
            backend=backend,
            status=status,
            pid=pid,
            uptime=uptime_str,
            details={"active_state": active, "stderr": stderr.strip() if stderr else ""},
        )

    if backend == ServiceBackend.DOCKER:
        base = _docker_compose_cmd(project_dir=compose_dir)
        rc, stdout, stderr = run_command([*base, "ps", "--format", "json"])
        if rc != 0:
            return LifecycleStatus(
                backend=backend,
                status=ServiceStatus.UNMANAGED,
                details={"error": stderr.strip()},
            )

        statuses: dict[str, str] = {}
        for line in stdout.strip().splitlines():
            if not line.strip():
                continue
            try:
                svc = json.loads(line)
                name = svc.get("Service", svc.get("Name", ""))
                state = svc.get("State", "")
                statuses[name] = state
            except json.JSONDecodeError:
                continue

        web_state = statuses.get("web", statuses.get("app", ""))
        if web_state == "running":
            status = ServiceStatus.RUNNING
        elif web_state in ("restarting", "starting"):
            status = ServiceStatus.DEGRADED
        elif web_state in ("exited", "dead"):
            status = ServiceStatus.FAILED
        elif web_state == "created":
            status = ServiceStatus.INSTALLED
        else:
            status = ServiceStatus.UNMANAGED

        return LifecycleStatus(
            backend=backend,
            status=status,
            details={"containers": json.dumps(statuses)},
        )

    if backend == ServiceBackend.FOREGROUND:
        return LifecycleStatus(
            backend=backend,
            status=ServiceStatus.UNMANAGED,
            details={
                "hint": (
                    "Development mode: run with 'python run.py' directly. "
                    "No service manager to query."
                )
            },
        )

    return LifecycleStatus(
        backend=backend,
        status=ServiceStatus.UNMANAGED,
        details={"hint": "Unknown service backend; cannot determine status."},
    )


def start_service(
    backend: ServiceBackend,
    *,
    user_unit: bool = False,
    compose_dir: Path | None = None,
) -> tuple[bool, str]:
    if backend == ServiceBackend.SYSTEMD or backend == ServiceBackend.SYSTEMD_USER:
        use_user = backend == ServiceBackend.SYSTEMD_USER or user_unit
        base = _systemctl_cmd(user_unit=use_user)
        rc, stdout, stderr = run_command([*base, "start", "devlog-web.service"])
        return rc == 0, stderr.strip() or stdout.strip()

    if backend == ServiceBackend.DOCKER:
        base = _docker_compose_cmd(project_dir=compose_dir)
        rc, stdout, stderr = run_command([*base, "up", "-d", "web"])
        return rc == 0, stderr.strip() or stdout.strip()

    if backend == ServiceBackend.FOREGROUND:
        return False, "Cannot start foreground service via service manager."

    return False, "Unknown service backend."


def stop_service(
    backend: ServiceBackend,
    *,
    user_unit: bool = False,
    compose_dir: Path | None = None,
) -> tuple[bool, str]:
    if backend == ServiceBackend.SYSTEMD or backend == ServiceBackend.SYSTEMD_USER:
        use_user = backend == ServiceBackend.SYSTEMD_USER or user_unit
        base = _systemctl_cmd(user_unit=use_user)
        rc, stdout, stderr = run_command([*base, "stop", "devlog-web.service"])
        return rc == 0, stderr.strip() or stdout.strip()

    if backend == ServiceBackend.DOCKER:
        base = _docker_compose_cmd(project_dir=compose_dir)
        rc, stdout, stderr = run_command([*base, "stop", "web"])
        return rc == 0, stderr.strip() or stdout.strip()

    if backend == ServiceBackend.FOREGROUND:
        return False, "Cannot stop foreground service via service manager."

    return False, "Unknown service backend."


def restart_service(
    backend: ServiceBackend,
    *,
    user_unit: bool = False,
    compose_dir: Path | None = None,
) -> tuple[bool, str]:
    if backend == ServiceBackend.SYSTEMD or backend == ServiceBackend.SYSTEMD_USER:
        use_user = backend == ServiceBackend.SYSTEMD_USER or user_unit
        base = _systemctl_cmd(user_unit=use_user)
        rc, stdout, stderr = run_command([*base, "restart", "devlog-web.service"])
        return rc == 0, stderr.strip() or stdout.strip()

    if backend == ServiceBackend.DOCKER:
        base = _docker_compose_cmd(project_dir=compose_dir)
        rc, stdout, stderr = run_command([*base, "restart", "web"])
        return rc == 0, stderr.strip() or stdout.strip()

    if backend == ServiceBackend.FOREGROUND:
        return False, "Cannot restart foreground service via service manager."

    return False, "Unknown service backend."


def get_logs(
    backend: ServiceBackend,
    *,
    follow: bool = False,
    tail: int = 50,
    component: str = "web",
    user_unit: bool = False,
    compose_dir: Path | None = None,
) -> tuple[bool, str]:
    if backend == ServiceBackend.SYSTEMD or backend == ServiceBackend.SYSTEMD_USER:
        use_user = backend == ServiceBackend.SYSTEMD_USER or user_unit
        base = _systemctl_cmd(user_unit=use_user)
        unit_name = f"devlog-{component}.service"
        cmd = ["journalctl", "-u", unit_name, "--no-pager", "-n", str(tail)]
        if follow:
            cmd.append("-f")
        rc, stdout, stderr = run_command(cmd, timeout=10 if follow else 30)
        return rc == 0, stdout or stderr

    if backend == ServiceBackend.DOCKER:
        base = _docker_compose_cmd(project_dir=compose_dir)
        cmd = [*base, "logs", f"--tail={tail}", component]
        if follow:
            cmd.append("--follow")
        rc, stdout, stderr = run_command(cmd, timeout=10 if follow else 30)
        return rc == 0, stdout or stderr

    if backend == ServiceBackend.FOREGROUND:
        return False, "No service logs available for foreground mode."

    return False, "Unknown service backend."
