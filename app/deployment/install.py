from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from app.deployment.model import RenderResult


@dataclass(frozen=True)
class ManagedFile:
    path: Path
    content: str
    permissions: int
    backup_path: Path | None = None


@dataclass(frozen=True)
class InstallPlan:
    files: list[ManagedFile] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dry_run: bool = False


@dataclass(frozen=True)
class InstallResult:
    ok: bool
    installed_files: list[Path] = field(default_factory=list)
    backed_up_files: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _resolve_install_path(
    rendered: RenderResult,
    base_dir: Path,
) -> Path:
    if rendered.filename.startswith("/"):
        return Path(rendered.filename)
    return base_dir / rendered.filename


def plan_installation(
    rendered_files: list[RenderResult],
    *,
    force: bool = False,
    base_dir: Path | None = None,
) -> InstallPlan:
    install_base = base_dir or Path("/etc/devlog")
    managed: list[ManagedFile] = []
    warnings: list[str] = []

    for rendered in rendered_files:
        target = _resolve_install_path(rendered, install_base)
        backup: Path | None = None

        if target.exists():
            if force:
                warnings.append(f"Overwriting existing file: {target}")
                backup = _backup_file(target)
            else:
                warnings.append(f"File already exists, skipping: {target}")
                continue

        managed.append(
            ManagedFile(
                path=target,
                content=rendered.content,
                permissions=rendered.permissions,
                backup_path=backup,
            )
        )

    return InstallPlan(
        files=managed,
        warnings=warnings,
        dry_run=False,
    )


def _backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup_path = path.with_suffix(path.suffix + ".bak")
    try:
        shutil.copy2(str(path), str(backup_path))
        return backup_path
    except OSError:
        return None


def backup_file(path: Path) -> Path | None:
    return _backup_file(path)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp_path.write_text(content)
        os.replace(str(tmp_path), str(path))
    except BaseException:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def _restore_backups(backups: list[tuple[Path, Path]]) -> bool:
    all_ok = True
    for original, backup in backups:
        if backup is None or not backup.exists():
            all_ok = False
            continue
        try:
            shutil.copy2(str(backup), str(original))
        except OSError:
            all_ok = False
    return all_ok


def restore_backups(backups: list[tuple[Path, Path]]) -> bool:
    return _restore_backups(backups)


def execute_installation(
    plan: InstallPlan,
    *,
    dry_run: bool = False,
) -> InstallResult:
    if dry_run:
        return InstallResult(
            ok=True,
            installed_files=[mf.path for mf in plan.files],
            backed_up_files=[mf.backup_path for mf in plan.files if mf.backup_path],
            warnings=plan.warnings + ["Dry run; no files were written"],
        )

    installed: list[Path] = []
    backed_up: list[Path] = []
    errors: list[str] = []
    rollback_pairs: list[tuple[Path, Path]] = []

    for managed in plan.files:
        try:
            if managed.backup_path is not None:
                backed_up.append(managed.backup_path)
                rollback_pairs.append((managed.path, managed.backup_path))

            _atomic_write(managed.path, managed.content)
            os.chmod(str(managed.path), managed.permissions)
            installed.append(managed.path)
        except OSError as exc:
            errors.append(f"Failed to write {managed.path}: {exc}")
            break

    if errors:
        _restore_backups(rollback_pairs)
        return InstallResult(
            ok=False,
            installed_files=installed,
            backed_up_files=backed_up,
            errors=errors,
            warnings=plan.warnings,
        )

    return InstallResult(
        ok=True,
        installed_files=installed,
        backed_up_files=backed_up,
        warnings=plan.warnings,
    )
