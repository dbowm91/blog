from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


METADATA_VERSION = 1


@dataclass(frozen=True)
class OnboardingMetadata:
    version: int
    mode: str
    profile: str
    package_version: str
    completed_at: str
    config_path: str
    data_path: str
    managed_paths: list[str]
    admin_username: str
    last_completed_step: int = -1
    stopped_at: str = ""
    stopped_reason: str = ""


def load_metadata(data_path: Path) -> OnboardingMetadata | None:
    meta_file = data_path / "onboarding-metadata.json"
    if not meta_file.exists():
        return None
    try:
        with open(meta_file) as f:
            data = json.load(f)
        if data.get("version") != METADATA_VERSION:
            return None
        return OnboardingMetadata(
            version=data["version"],
            mode=data.get("mode", ""),
            profile=data.get("profile", ""),
            package_version=data.get("package_version", ""),
            completed_at=data.get("completed_at", ""),
            config_path=data.get("config_path", ""),
            data_path=data.get("data_path", ""),
            managed_paths=data.get("managed_paths", []),
            admin_username=data.get("admin_username", ""),
            last_completed_step=data.get("last_completed_step", -1),
            stopped_at=data.get("stopped_at", ""),
            stopped_reason=data.get("stopped_reason", ""),
        )
    except (OSError, json.JSONDecodeError, KeyError):
        return None


def save_metadata(data_path: Path, metadata: OnboardingMetadata) -> None:
    data_path.mkdir(parents=True, exist_ok=True)
    meta_file = data_path / "onboarding-metadata.json"
    tmp = meta_file.with_suffix(".tmp")
    try:
        with open(tmp, "w") as f:
            json.dump(asdict(metadata), f, indent=2)
            f.write("\n")
        os.replace(tmp, meta_file)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def is_complete(metadata: OnboardingMetadata | None) -> bool:
    if metadata is None:
        return False
    return metadata.version == METADATA_VERSION and bool(metadata.completed_at)
