from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PathCandidate:
    path: Path
    source: str
    exists: bool
    is_file: bool
    is_symlink: bool
    readable: bool
    writable: bool


@dataclass
class PathResolution:
    selected: PathCandidate | None
    candidates: list[PathCandidate]
    reason: str


def _make_candidate(path: Path, source: str) -> PathCandidate:
    return PathCandidate(
        path=path,
        source=source,
        exists=path.exists(),
        is_file=path.is_file() if path.exists() else False,
        is_symlink=path.is_symlink() if path.exists() else False,
        readable=os.access(path, os.R_OK) if path.exists() else False,
        writable=os.access(path, os.W_OK) if path.exists() else False,
    )


def _xdg_config_home() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".config"


def _build_config_candidates(
    cli_path: Path | None,
    *,
    system_mode: bool,
) -> list[PathCandidate]:
    candidates: list[PathCandidate] = []

    if cli_path is not None:
        candidates.append(_make_candidate(cli_path, "cli"))

    env_var = os.environ.get("DEVLOG_CONFIG")
    if env_var:
        candidates.append(_make_candidate(Path(env_var), "env_var"))

    if system_mode:
        candidates.append(_make_candidate(Path("/etc/devlog/config.toml"), "system"))

    xdg_base = _xdg_config_home()
    candidates.append(_make_candidate(xdg_base / "devlog" / "config.toml", "xdg"))

    candidates.append(_make_candidate(Path.home() / ".config" / "devlog" / "config.toml", "home"))

    candidates.append(_make_candidate(Path("config.toml"), "cwd"))

    return candidates


def _build_env_file_candidates(
    cli_path: Path | None,
    *,
    system_mode: bool,
) -> list[PathCandidate]:
    candidates: list[PathCandidate] = []

    if cli_path is not None:
        candidates.append(_make_candidate(cli_path, "cli"))

    env_var = os.environ.get("DEVLOG_ENV_FILE")
    if env_var:
        candidates.append(_make_candidate(Path(env_var), "env_var"))

    if system_mode:
        candidates.append(_make_candidate(Path("/etc/devlog/devlog.env"), "system"))

    xdg_base = _xdg_config_home()
    candidates.append(_make_candidate(xdg_base / "devlog" / "devlog.env", "xdg"))

    candidates.append(_make_candidate(Path.home() / ".config" / "devlog" / "devlog.env", "home"))

    candidates.append(_make_candidate(Path(".env"), "cwd"))

    return candidates


def _select_first_valid(
    candidates: list[PathCandidate],
    kind: str,
) -> PathResolution:
    for candidate in candidates:
        if candidate.exists and candidate.is_file and candidate.readable:
            return PathResolution(
                selected=candidate,
                candidates=candidates,
                reason=f"Selected {kind} from {candidate.source}: {candidate.path}",
            )

    source_names = [f"{c.source} ({c.path})" for c in candidates]
    return PathResolution(
        selected=None,
        candidates=candidates,
        reason=f"No valid {kind} found among candidates: {', '.join(source_names)}",
    )


def resolve_config_path(
    cli_path: Path | None = None,
    *,
    system_mode: bool = False,
) -> PathResolution:
    candidates = _build_config_candidates(cli_path, system_mode=system_mode)
    return _select_first_valid(candidates, "config file")


def resolve_env_file_path(
    cli_path: Path | None = None,
    *,
    system_mode: bool = False,
) -> PathResolution:
    candidates = _build_env_file_candidates(cli_path, system_mode=system_mode)
    return _select_first_valid(candidates, "env file")
