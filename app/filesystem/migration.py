from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from app.filesystem.layout import InstallMode, RuntimePaths


class MigrationAction(Enum):
    COPY = "copy"
    MOVE = "move"
    SKIP = "skip"
    CONFLICT = "conflict"
    CREATE_DIR = "create_dir"


@dataclass(frozen=True)
class MigrationStep:
    action: MigrationAction
    source: Path | None
    target: Path
    description: str


@dataclass
class MigrationPlan:
    steps: list[MigrationStep] = field(default_factory=list)
    source_mode: InstallMode = InstallMode.DEVELOPMENT
    target_mode: InstallMode = InstallMode.DEVELOPMENT
    warnings: list[str] = field(default_factory=list)
    requires_downtime: bool = False


@dataclass
class MigrationExecutionResult:
    ok: bool
    completed_steps: int
    total_steps: int
    errors: list[str] = field(default_factory=list)
    completed_paths: list[str] = field(default_factory=list)


def _plan_file_transfer(
    source_path: Path,
    target_path: Path,
    label: str,
) -> MigrationStep:
    if not source_path.exists():
        return MigrationStep(
            action=MigrationAction.SKIP,
            source=source_path,
            target=target_path,
            description=f"{label}: source does not exist, skipping",
        )
    if target_path.exists():
        return MigrationStep(
            action=MigrationAction.CONFLICT,
            source=source_path,
            target=target_path,
            description=f"{label}: target already exists",
        )
    return MigrationStep(
        action=MigrationAction.MOVE,
        source=source_path,
        target=target_path,
        description=f"{label}: move from {source_path} to {target_path}",
    )


def _plan_dir_transfer(
    source_path: Path,
    target_path: Path,
    label: str,
) -> list[MigrationStep]:
    steps: list[MigrationStep] = []
    if not source_path.exists():
        return steps
    if not target_path.exists():
        steps.append(
            MigrationStep(
                action=MigrationAction.CREATE_DIR,
                source=None,
                target=target_path,
                description=f"{label}: create directory {target_path}",
            )
        )
    for item in source_path.iterdir():
        dest = target_path / item.name
        if item.is_file():
            steps.append(_plan_file_transfer(item, dest, label))
        elif item.is_dir():
            steps.extend(_plan_dir_transfer(item, dest, label))
    return steps


def plan_migration(
    source: RuntimePaths,
    target: RuntimePaths,
    *,
    source_mode: InstallMode | None = None,
    target_mode: InstallMode | None = None,
    include_logs: bool = False,
) -> MigrationPlan:
    warnings: list[str] = []
    steps: list[MigrationStep] = []

    steps.append(
        _plan_file_transfer(source.config_file.path, target.config_file.path, "Config file")
    )
    steps.append(_plan_file_transfer(source.env_file.path, target.env_file.path, "Env file"))
    steps.append(_plan_file_transfer(source.database.path, target.database.path, "Database"))
    steps.extend(_plan_dir_transfer(source.uploads_dir.path, target.uploads_dir.path, "Uploads"))
    steps.extend(_plan_dir_transfer(source.themes_dir.path, target.themes_dir.path, "Themes"))
    steps.extend(_plan_dir_transfer(source.backups_dir.path, target.backups_dir.path, "Backups"))
    steps.extend(_plan_dir_transfer(source.exports_dir.path, target.exports_dir.path, "Exports"))

    if include_logs:
        steps.extend(_plan_dir_transfer(source.log_dir.path, target.log_dir.path, "Logs"))

    steps.append(
        _plan_file_transfer(
            source.installation_metadata.path,
            target.installation_metadata.path,
            "Installation metadata",
        )
    )

    requires_downtime = any(s.action in (MigrationAction.MOVE, MigrationAction.COPY) for s in steps)

    if source.data_dir.path == target.data_dir.path:
        warnings.append("Source and target data directories are identical")

    if any(s.action == MigrationAction.CONFLICT for s in steps):
        warnings.append("One or more target paths already exist; manual resolution required")

    return MigrationPlan(
        steps=steps,
        source_mode=source_mode or InstallMode.DEVELOPMENT,
        target_mode=target_mode or InstallMode.DEVELOPMENT,
        warnings=warnings,
        requires_downtime=requires_downtime,
    )


def _checkpoint_sqlite(db_path: Path) -> bool:
    try:
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
        return True
    except Exception:
        return False


def execute_migration(
    plan: MigrationPlan,
    *,
    dry_run: bool = False,
    stop_on_conflict: bool = True,
) -> MigrationExecutionResult:
    completed = 0
    errors: list[str] = []
    completed_paths: list[str] = []

    db_source = None
    for step in plan.steps:
        if (
            step.source
            and step.source.name in ("blog.db", "devlog.sqlite3")
            and step.source.exists()
        ):
            db_source = step.source
            break

    if db_source and not dry_run:
        _checkpoint_sqlite(db_source)

    for step in plan.steps:
        if dry_run:
            completed += 1
            continue

        if step.action == MigrationAction.SKIP:
            completed += 1
            continue

        if step.action == MigrationAction.CONFLICT:
            if stop_on_conflict:
                errors.append(step.description)
                break
            completed += 1
            continue

        if step.action == MigrationAction.CREATE_DIR:
            try:
                step.target.mkdir(parents=True, exist_ok=True)
                completed += 1
                completed_paths.append(str(step.target))
            except OSError as e:
                errors.append(f"Failed to create {step.target}: {e}")
                break
            continue

        if step.action in (MigrationAction.MOVE, MigrationAction.COPY):
            if step.source is None or not step.source.exists():
                errors.append(f"Source missing for {step.description}")
                break

            try:
                step.target.parent.mkdir(parents=True, exist_ok=True)
                if step.action == MigrationAction.MOVE:
                    shutil.move(str(step.source), str(step.target))
                else:
                    if step.source.is_dir():
                        shutil.copytree(str(step.source), str(step.target))
                    else:
                        shutil.copy2(str(step.source), str(step.target))
                completed += 1
                completed_paths.append(str(step.target))
            except OSError as e:
                errors.append(f"Failed: {step.description}: {e}")
                break

    return MigrationExecutionResult(
        ok=len(errors) == 0,
        completed_steps=completed,
        total_steps=len(plan.steps),
        errors=errors,
        completed_paths=completed_paths,
    )
