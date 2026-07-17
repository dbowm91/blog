from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class DriftStatus(Enum):
    MISSING = "missing"
    MODIFIED = "modified"
    UNMANAGED = "unmanaged"
    STALE = "stale"


@dataclass(frozen=True)
class DriftItem:
    path: Path
    status: DriftStatus
    expected_hash: str | None = None
    actual_hash: str | None = None
    description: str = ""


@dataclass(frozen=True)
class DriftReport:
    items: list[DriftItem] = field(default_factory=list)
    clean: bool = True
    managed_count: int = 0
    drift_count: int = 0
    unmanaged_count: int = 0


def compute_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def check_drift(
    managed_files: dict[Path, str],
    scan_dir: Path,
) -> DriftReport:
    items: list[DriftItem] = []
    managed_count = len(managed_files)
    drift_count = 0
    unmanaged_count = 0

    for expected_path, expected_hash in managed_files.items():
        if not expected_path.exists():
            items.append(
                DriftItem(
                    path=expected_path,
                    status=DriftStatus.MISSING,
                    expected_hash=expected_hash,
                    description=f"Expected file missing: {expected_path}",
                )
            )
            drift_count += 1
            continue

        try:
            actual_content = expected_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            items.append(
                DriftItem(
                    path=expected_path,
                    status=DriftStatus.MODIFIED,
                    expected_hash=expected_hash,
                    description=f"Cannot read file: {expected_path}",
                )
            )
            drift_count += 1
            continue

        actual_hash = compute_content_hash(actual_content)
        if actual_hash != expected_hash:
            items.append(
                DriftItem(
                    path=expected_path,
                    status=DriftStatus.MODIFIED,
                    expected_hash=expected_hash,
                    actual_hash=actual_hash,
                    description=f"Content mismatch: {expected_path}",
                )
            )
            drift_count += 1

    if scan_dir.exists():
        for child in scan_dir.iterdir():
            if not child.is_file():
                continue
            if child.suffix in (".bak", ".tmp"):
                continue
            if child not in managed_files:
                items.append(
                    DriftItem(
                        path=child,
                        status=DriftStatus.UNMANAGED,
                        description=f"Unmanaged file found: {child}",
                    )
                )
                unmanaged_count += 1

    return DriftReport(
        items=items,
        clean=drift_count == 0 and unmanaged_count == 0,
        managed_count=managed_count,
        drift_count=drift_count,
        unmanaged_count=unmanaged_count,
    )


def load_managed_manifest(manifest_path: Path) -> dict[Path, str]:
    if not manifest_path.exists():
        return {}
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        return {Path(k): v for k, v in raw.items()}
    except (json.JSONDecodeError, OSError):
        return {}


def save_managed_manifest(manifest_path: Path, files: dict[Path, str]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {str(k): v for k, v in sorted(files.items(), key=lambda x: str(x[0]))}
    tmp_path = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    try:
        tmp_path.write_text(
            json.dumps(serializable, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(str(tmp_path), str(manifest_path))
    except BaseException:
        if tmp_path.exists():
            tmp_path.unlink()
        raise
