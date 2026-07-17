"""Deployment operational service — structured results for deployment rendering, installation, drift checking, and lifecycle management."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from flask import current_app

from app.services.operations.results import OperationResult


@dataclass(frozen=True)
class DeployRenderResult(OperationResult):
    files: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class DeployInstallResult(OperationResult):
    installed_files: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DeployCheckResult(OperationResult):
    clean: bool = True
    drift_count: int = 0


@dataclass(frozen=True)
class LifecycleResult(OperationResult):
    status: str = ""
    backend: str = ""
    details: dict[str, Any] = field(default_factory=dict)


def _build_context(mode: str):
    from app.deployment.model import DeploymentContext
    from app.filesystem.layout import InstallMode

    config = current_app.config["DEVLOG_CONFIG"]
    install_mode = InstallMode(mode)
    return DeploymentContext.from_config(config, install_mode)


def _render_target(ctx, target: str):
    renderers: dict[str, Any] = {
        "systemd": _render_systemd,
        "compose": _render_compose,
        "caddy": _render_caddy,
        "nginx": _render_nginx,
        "logrotate": _render_logrotate,
    }
    renderer = renderers.get(target)
    if renderer is None:
        return []
    return renderer(ctx)


def _render_systemd(ctx) -> list:
    from app.deployment.systemd import (
        render_web_unit,
        render_worker_unit,
        render_scheduler_unit,
    )

    user_unit = ctx.is_user
    results = [render_web_unit(ctx, user_unit=user_unit)]
    worker = render_worker_unit(ctx, user_unit=user_unit)
    if worker is not None:
        results.append(worker)
    scheduler = render_scheduler_unit(ctx, user_unit=user_unit)
    if scheduler is not None:
        results.append(scheduler)
    return results


def _render_compose(ctx) -> list:
    from app.deployment.compose import render_compose, render_compose_env

    return [render_compose(ctx), render_compose_env(ctx)]


def _render_caddy(ctx) -> list:
    from app.deployment.proxy import render_caddyfile

    return [render_caddyfile(ctx)]


def _render_nginx(ctx) -> list:
    from app.deployment.proxy import render_nginx_config

    return [render_nginx_config(ctx)]


def _render_logrotate(ctx) -> list:
    from app.deployment.logrotate import render_logrotate

    result = render_logrotate(ctx)
    if result is None:
        return []
    return [result]


ALL_TARGETS = ["systemd", "compose", "caddy", "nginx", "logrotate"]


def _rendered_to_dict(rendered) -> dict[str, Any]:
    return {
        "content": rendered.content,
        "filename": rendered.filename,
        "managed": rendered.managed,
        "permissions": oct(rendered.permissions),
        "description": rendered.description,
        "warnings": list(rendered.warnings),
    }


def deploy_render(
    mode: str,
    *,
    targets: list[str] | None = None,
) -> DeployRenderResult:
    try:
        ctx = _build_context(mode)
    except (ValueError, OSError) as e:
        return DeployRenderResult(
            ok=False,
            code="deploy.render.context_error",
            summary=f"Failed to build deployment context: {e}",
            remediation=["Check that the deployment mode is valid and config is accessible."],
        )

    active_targets = targets or ALL_TARGETS
    all_rendered = []
    all_warnings: list[str] = []

    for target in active_targets:
        try:
            rendered_items = _render_target(ctx, target)
            for r in rendered_items:
                all_rendered.append(_rendered_to_dict(r))
                all_warnings.extend(r.warnings)
        except ImportError:
            all_warnings.append(f"Deployment module for '{target}' is not available")
        except Exception as e:
            all_warnings.append(f"Failed to render {target}: {e}")

    return DeployRenderResult(
        ok=True,
        code="deploy.render.ok",
        summary=f"Rendered {len(all_rendered)} file(s) for targets: {', '.join(active_targets)}.",
        files=all_rendered,
        details={"mode": mode, "targets": active_targets},
        warnings=all_warnings,
    )


def deploy_install(
    mode: str,
    *,
    targets: list[str] | None = None,
    force: bool = False,
    dry_run: bool = False,
    base_dir: str | None = None,
) -> DeployInstallResult:
    try:
        ctx = _build_context(mode)
    except (ValueError, OSError) as e:
        return DeployInstallResult(
            ok=False,
            code="deploy.install.context_error",
            summary=f"Failed to build deployment context: {e}",
            remediation=["Check that the deployment mode is valid and config is accessible."],
        )

    active_targets = targets or ALL_TARGETS
    all_rendered = []
    all_warnings: list[str] = []

    for target in active_targets:
        try:
            rendered_items = _render_target(ctx, target)
            all_rendered.extend(rendered_items)
        except ImportError:
            all_warnings.append(f"Deployment module for '{target}' is not available")
        except Exception as e:
            all_warnings.append(f"Failed to render {target}: {e}")

    if not all_rendered:
        return DeployInstallResult(
            ok=False,
            code="deploy.install.no_files",
            summary="No files were rendered for installation.",
            warnings=all_warnings,
            remediation=["Check deployment targets and configuration."],
        )

    from app.deployment.install import plan_installation, execute_installation

    install_base = Path(base_dir) if base_dir else None
    plan = plan_installation(all_rendered, force=force, base_dir=install_base)
    all_warnings.extend(plan.warnings)

    result = execute_installation(plan, dry_run=dry_run)

    installed = [str(p) for p in result.installed_files]

    summary = f"{'Dry run: ' if dry_run else ''}Installed {len(installed)} file(s)."
    if result.errors:
        summary += f" {len(result.errors)} error(s)."

    return DeployInstallResult(
        ok=result.ok,
        code="deploy.install.ok" if result.ok else "deploy.install.failed",
        summary=summary,
        installed_files=installed,
        details={
            "mode": mode,
            "targets": active_targets,
            "force": force,
            "dry_run": dry_run,
            "base_dir": str(install_base) if install_base else None,
            "backed_up": [str(p) for p in result.backed_up_files],
            "errors": result.errors,
        },
        warnings=all_warnings,
    )


def deploy_check(
    mode: str,
    *,
    base_dir: str | None = None,
) -> DeployCheckResult:
    try:
        ctx = _build_context(mode)
    except (ValueError, OSError) as e:
        return DeployCheckResult(
            ok=False,
            code="deploy.check.context_error",
            summary=f"Failed to build deployment context: {e}",
            remediation=["Check that the deployment mode is valid and config is accessible."],
        )

    from app.deployment.drift import check_drift, load_managed_manifest, compute_content_hash

    active_targets = ALL_TARGETS
    all_rendered = []
    all_warnings: list[str] = []

    for target in active_targets:
        try:
            rendered_items = _render_target(ctx, target)
            all_rendered.extend(rendered_items)
        except ImportError:
            pass
        except Exception as e:
            all_warnings.append(f"Failed to render {target}: {e}")

    install_base = Path(base_dir) if base_dir else Path("/etc/devlog")
    managed_manifest_path = install_base / ".devlog-manifest.json"
    manifest = load_managed_manifest(managed_manifest_path)

    if not manifest and all_rendered:
        expected_hashes: dict[Path, str] = {}
        for rendered in all_rendered:
            if rendered.filename.startswith("/"):
                target_path = Path(rendered.filename)
            else:
                target_path = install_base / rendered.filename
            expected_hashes[target_path] = compute_content_hash(rendered.content)
        manifest = expected_hashes

    report = check_drift(manifest, install_base)

    return DeployCheckResult(
        ok=report.clean,
        code="deploy.check.clean" if report.clean else "deploy.check.drift",
        summary=(
            "No drift detected."
            if report.clean
            else f"Drift detected: {report.drift_count} file(s) modified or missing."
        ),
        clean=report.clean,
        drift_count=report.drift_count,
        details={
            "mode": mode,
            "managed_count": report.managed_count,
            "unmanaged_count": report.unmanaged_count,
            "items": [
                {
                    "path": str(item.path),
                    "status": item.status.value,
                    "description": item.description,
                }
                for item in report.items
            ],
        },
        warnings=all_warnings,
    )


def _lifecycle_ctx():
    from app.deployment.lifecycle import detect_backend
    from app.filesystem.layout import InstallMode, RuntimePaths

    config = current_app.config["DEVLOG_CONFIG"]
    mode_str = config.server.mode if hasattr(config.server, "mode") else "development"
    try:
        install_mode = InstallMode(mode_str)
    except ValueError:
        install_mode = InstallMode.DEVELOPMENT

    paths = RuntimePaths.for_mode(install_mode)
    metadata = None
    meta_path = paths.installation_metadata.path
    if meta_path.exists():
        from app.filesystem.layout import InstallationMetadata

        metadata = InstallationMetadata.load(meta_path)

    backend = detect_backend(metadata, install_mode)
    user_unit = backend.value == "systemd_user"
    compose_dir = None
    return backend, user_unit, compose_dir


def lifecycle_status() -> LifecycleResult:
    try:
        from app.deployment.lifecycle import get_service_status

        backend, user_unit, compose_dir = _lifecycle_ctx()
        status = get_service_status(backend, user_unit=user_unit, compose_dir=compose_dir)

        return LifecycleResult(
            ok=True,
            code="lifecycle.status.ok",
            summary=f"Service backend: {backend.value}, status: {status.status.value}.",
            status=status.status.value,
            backend=backend.value,
            details={
                "pid": status.pid,
                "uptime": status.uptime,
                "health": status.health,
                **status.details,
            },
        )
    except Exception as e:
        return LifecycleResult(
            ok=False,
            code="lifecycle.status.error",
            summary=f"Failed to get service status: {e}",
        )


def lifecycle_start() -> LifecycleResult:
    try:
        from app.deployment.lifecycle import start_service

        backend, user_unit, compose_dir = _lifecycle_ctx()
        ok, message = start_service(backend, user_unit=user_unit, compose_dir=compose_dir)

        return LifecycleResult(
            ok=ok,
            code="lifecycle.start.ok" if ok else "lifecycle.start.failed",
            summary=message or ("Service started." if ok else "Failed to start service."),
            backend=backend.value,
        )
    except Exception as e:
        return LifecycleResult(
            ok=False,
            code="lifecycle.start.error",
            summary=f"Failed to start service: {e}",
        )


def lifecycle_stop() -> LifecycleResult:
    try:
        from app.deployment.lifecycle import stop_service

        backend, user_unit, compose_dir = _lifecycle_ctx()
        ok, message = stop_service(backend, user_unit=user_unit, compose_dir=compose_dir)

        return LifecycleResult(
            ok=ok,
            code="lifecycle.stop.ok" if ok else "lifecycle.stop.failed",
            summary=message or ("Service stopped." if ok else "Failed to stop service."),
            backend=backend.value,
        )
    except Exception as e:
        return LifecycleResult(
            ok=False,
            code="lifecycle.stop.error",
            summary=f"Failed to stop service: {e}",
        )


def lifecycle_restart() -> LifecycleResult:
    try:
        from app.deployment.lifecycle import restart_service

        backend, user_unit, compose_dir = _lifecycle_ctx()
        ok, message = restart_service(backend, user_unit=user_unit, compose_dir=compose_dir)

        return LifecycleResult(
            ok=ok,
            code="lifecycle.restart.ok" if ok else "lifecycle.restart.failed",
            summary=message or ("Service restarted." if ok else "Failed to restart service."),
            backend=backend.value,
        )
    except Exception as e:
        return LifecycleResult(
            ok=False,
            code="lifecycle.restart.error",
            summary=f"Failed to restart service: {e}",
        )


def lifecycle_logs(
    *,
    follow: bool = False,
    tail: int = 50,
    component: str = "web",
) -> LifecycleResult:
    try:
        from app.deployment.lifecycle import get_logs

        backend, user_unit, compose_dir = _lifecycle_ctx()
        ok, output = get_logs(
            backend,
            follow=follow,
            tail=tail,
            component=component,
            user_unit=user_unit,
            compose_dir=compose_dir,
        )

        return LifecycleResult(
            ok=ok,
            code="lifecycle.logs.ok" if ok else "lifecycle.logs.failed",
            summary=f"Logs for component '{component}' ({tail} lines{' with follow' if follow else ''}).",
            backend=backend.value,
            details={"component": component, "output": output},
        )
    except Exception as e:
        return LifecycleResult(
            ok=False,
            code="lifecycle.logs.error",
            summary=f"Failed to get logs: {e}",
        )
