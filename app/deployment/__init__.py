from __future__ import annotations

from app.deployment.drift import (
    DriftItem,
    DriftReport,
    DriftStatus,
    check_drift,
    compute_content_hash,
    load_managed_manifest,
    save_managed_manifest,
)
from app.deployment.install import (
    InstallPlan,
    InstallResult,
    ManagedFile,
    backup_file,
    execute_installation,
    plan_installation,
    restore_backups,
)
from app.deployment.lifecycle import (
    LifecycleStatus,
    ServiceBackend,
    ServiceStatus,
    detect_backend,
    get_logs,
    get_service_status,
    restart_service,
    run_command,
    start_service,
    stop_service,
)
from app.deployment.logrotate import render_logrotate
from app.deployment.model import DeploymentContext, RenderResult
from app.deployment.proxy import (
    render_caddyfile,
    render_nginx_config,
    validate_caddyfile,
    validate_nginx_config,
)

__all__ = [
    "DeploymentContext",
    "DriftItem",
    "DriftReport",
    "DriftStatus",
    "InstallPlan",
    "InstallResult",
    "LifecycleStatus",
    "ManagedFile",
    "RenderResult",
    "ServiceBackend",
    "ServiceStatus",
    "backup_file",
    "check_drift",
    "compute_content_hash",
    "detect_backend",
    "execute_installation",
    "get_logs",
    "get_service_status",
    "load_managed_manifest",
    "plan_installation",
    "render_caddyfile",
    "render_logrotate",
    "render_nginx_config",
    "restart_service",
    "restore_backups",
    "run_command",
    "save_managed_manifest",
    "start_service",
    "stop_service",
    "validate_caddyfile",
    "validate_nginx_config",
]
