from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.filesystem.layout import InstallMode, RuntimePaths


@dataclass(frozen=True)
class DirectorySpec:
    path: Path
    owner: str | None
    group: str | None
    mode: int
    created_during: str
    contains_secrets: bool
    symlinks_allowed: bool


def get_directory_specs(mode: InstallMode) -> dict[str, DirectorySpec]:
    if mode == InstallMode.SYSTEM:
        return {
            "data_dir": DirectorySpec(
                path=Path("/var/lib/devlog"),
                owner="devlog",
                group="devlog",
                mode=0o750,
                created_during="onboarding",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
            "uploads_dir": DirectorySpec(
                path=Path("/var/lib/devlog/uploads"),
                owner="devlog",
                group="devlog",
                mode=0o750,
                created_during="runtime",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
            "themes_dir": DirectorySpec(
                path=Path("/var/lib/devlog/themes"),
                owner="devlog",
                group="devlog",
                mode=0o750,
                created_during="runtime",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
            "backups_dir": DirectorySpec(
                path=Path("/var/lib/devlog/backups"),
                owner="devlog",
                group="devlog",
                mode=0o750,
                created_during="runtime",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
            "exports_dir": DirectorySpec(
                path=Path("/var/lib/devlog/exports"),
                owner="devlog",
                group="devlog",
                mode=0o750,
                created_during="runtime",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
            "log_dir": DirectorySpec(
                path=Path("/var/log/devlog"),
                owner="devlog",
                group="devlog",
                mode=0o750,
                created_during="onboarding",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
            "runtime_dir": DirectorySpec(
                path=Path("/run/devlog"),
                owner="devlog",
                group="devlog",
                mode=0o755,
                created_during="runtime",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
        }
    if mode == InstallMode.DOCKER:
        return {
            "data_dir": DirectorySpec(
                path=Path("/data"),
                owner=None,
                group=None,
                mode=0o755,
                created_during="onboarding",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
            "uploads_dir": DirectorySpec(
                path=Path("/data/uploads"),
                owner=None,
                group=None,
                mode=0o755,
                created_during="runtime",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
            "themes_dir": DirectorySpec(
                path=Path("/data/themes"),
                owner=None,
                group=None,
                mode=0o755,
                created_during="runtime",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
            "backups_dir": DirectorySpec(
                path=Path("/data/backups"),
                owner=None,
                group=None,
                mode=0o755,
                created_during="runtime",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
            "exports_dir": DirectorySpec(
                path=Path("/data/exports"),
                owner=None,
                group=None,
                mode=0o755,
                created_during="runtime",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
            "log_dir": DirectorySpec(
                path=Path("/var/log/devlog"),
                owner=None,
                group=None,
                mode=0o755,
                created_during="onboarding",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
            "runtime_dir": DirectorySpec(
                path=Path("/run/devlog"),
                owner=None,
                group=None,
                mode=0o755,
                created_during="runtime",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
        }
    if mode == InstallMode.USER:
        return {
            "data_dir": DirectorySpec(
                path=Path("~/.local/share/devlog").expanduser(),
                owner=None,
                group=None,
                mode=0o700,
                created_during="onboarding",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
            "uploads_dir": DirectorySpec(
                path=Path("~/.local/share/devlog/uploads").expanduser(),
                owner=None,
                group=None,
                mode=0o700,
                created_during="runtime",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
            "themes_dir": DirectorySpec(
                path=Path("~/.local/share/devlog/themes").expanduser(),
                owner=None,
                group=None,
                mode=0o700,
                created_during="runtime",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
            "backups_dir": DirectorySpec(
                path=Path("~/.local/share/devlog/backups").expanduser(),
                owner=None,
                group=None,
                mode=0o700,
                created_during="runtime",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
            "exports_dir": DirectorySpec(
                path=Path("~/.local/share/devlog/exports").expanduser(),
                owner=None,
                group=None,
                mode=0o700,
                created_during="runtime",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
            "log_dir": DirectorySpec(
                path=Path("~/.local/state/devlog/logs").expanduser(),
                owner=None,
                group=None,
                mode=0o700,
                created_during="onboarding",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
            "runtime_dir": DirectorySpec(
                path=Path("~/.local/state/devlog").expanduser(),
                owner=None,
                group=None,
                mode=0o700,
                created_during="runtime",
                contains_secrets=False,
                symlinks_allowed=False,
            ),
        }
    return {
        "data_dir": DirectorySpec(
            path=Path.cwd() / "data",
            owner=None,
            group=None,
            mode=0o755,
            created_during="onboarding",
            contains_secrets=False,
            symlinks_allowed=False,
        ),
        "uploads_dir": DirectorySpec(
            path=Path.cwd() / "data" / "uploads",
            owner=None,
            group=None,
            mode=0o755,
            created_during="runtime",
            contains_secrets=False,
            symlinks_allowed=False,
        ),
        "themes_dir": DirectorySpec(
            path=Path.cwd() / "data" / "themes",
            owner=None,
            group=None,
            mode=0o755,
            created_during="runtime",
            contains_secrets=False,
            symlinks_allowed=False,
        ),
        "backups_dir": DirectorySpec(
            path=Path.cwd() / "data" / "backups",
            owner=None,
            group=None,
            mode=0o755,
            created_during="runtime",
            contains_secrets=False,
            symlinks_allowed=False,
        ),
        "exports_dir": DirectorySpec(
            path=Path.cwd() / "data" / "exports",
            owner=None,
            group=None,
            mode=0o755,
            created_during="runtime",
            contains_secrets=False,
            symlinks_allowed=False,
        ),
        "log_dir": DirectorySpec(
            path=Path.cwd() / "logs",
            owner=None,
            group=None,
            mode=0o755,
            created_during="onboarding",
            contains_secrets=False,
            symlinks_allowed=False,
        ),
        "runtime_dir": DirectorySpec(
            path=Path.cwd() / "instance",
            owner=None,
            group=None,
            mode=0o755,
            created_during="runtime",
            contains_secrets=False,
            symlinks_allowed=False,
        ),
    }


def _validate_path_safety(base: Path, target: Path) -> None:
    resolved_base = base.resolve()
    resolved_target = target.resolve()
    try:
        resolved_target.relative_to(resolved_base)
    except ValueError:
        raise ValueError(f"Path traversal rejected: {target} escapes base {base}")


def _check_parent_ownership(path: Path) -> None:
    parent = path.parent
    if not parent.exists():
        return
    try:
        st = parent.stat()
        uid = os.getuid()
        if uid != 0 and st.st_uid != uid:
            return
    except (OSError, AttributeError):
        return


def _find_spec(specs: dict[str, DirectorySpec], path: Path) -> DirectorySpec | None:
    resolved = path.resolve()
    for spec in specs.values():
        spec_resolved = spec.path.expanduser().resolve()
        if spec_resolved == resolved or resolved.is_relative_to(spec_resolved):
            return spec
    return None


def prepare_directories(
    paths: RuntimePaths,
    *,
    mode: InstallMode,
    dry_run: bool = False,
) -> list[Path]:
    specs = get_directory_specs(mode)
    managed_with_specs = [
        (paths.data_dir.path, "data_dir"),
        (paths.uploads_dir.path, "uploads_dir"),
        (paths.themes_dir.path, "themes_dir"),
        (paths.backups_dir.path, "backups_dir"),
        (paths.exports_dir.path, "exports_dir"),
        (paths.log_dir.path, "log_dir"),
        (paths.runtime_dir.path, "runtime_dir"),
    ]
    created: list[Path] = []
    for p, spec_name in managed_with_specs:
        if not p.exists():
            if not dry_run:
                _validate_path_safety(p.parent, p)
                _check_parent_ownership(p)
                p.mkdir(parents=True, exist_ok=True)
                spec = specs.get(spec_name)
                if spec is not None:
                    os.chmod(p, spec.mode)
                    if spec.owner is not None and os.getuid() == 0:
                        try:
                            import grp
                            import pwd

                            uid = pwd.getpwnam(spec.owner).pw_uid
                            gid = grp.getgrnam(spec.group).gr_gid if spec.group else uid
                            os.chown(p, uid, gid)
                        except (KeyError, OSError):
                            pass
                else:
                    os.chmod(p, 0o755)
            created.append(p)
    return created
