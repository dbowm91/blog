from __future__ import annotations

import enum
import importlib.resources
import logging
import os
import stat
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

_MAX_THEME_NAME_LEN = 200
_MAX_EXTERNAL_FILE_SIZE = 1_048_576


class ThemeSource(enum.Enum):
    BUNDLED = "bundled"
    EXTERNAL = "external"


@dataclass(frozen=True, slots=True)
class ThemeFileInfo:
    canonical_name: str
    filename: str
    source: ThemeSource
    path: Path
    size_bytes: int
    mtime: float


def validate_theme_name(name: str) -> str:
    if not name:
        raise ValueError("theme name must not be empty")
    if "/" in name or "\\" in name:
        raise ValueError("theme name must not contain path separators")
    if ".." in name.split("/"):
        raise ValueError("theme name must not contain '..' path segment")
    if os.path.isabs(name):
        raise ValueError("theme name must not be an absolute path")
    if any(ord(c) < 32 or c == "\x00" for c in name):
        raise ValueError("theme name must not contain NUL or control characters")
    if len(name) > _MAX_THEME_NAME_LEN:
        raise ValueError(f"theme name must not exceed {_MAX_THEME_NAME_LEN} characters")
    p = Path(name)
    stem = p.stem
    if not stem:
        raise ValueError("theme name must resolve to a valid stem")
    return stem


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _candidate_files(directory: Path) -> list[Path]:
    results: list[Path] = []
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                name = entry.name
                if name.startswith("."):
                    continue
                if not name.endswith(".toml"):
                    continue
                try:
                    entry_stat = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                if not stat.S_ISREG(entry_stat.st_mode):
                    continue
                results.append(Path(entry.path))
    except (FileNotFoundError, PermissionError, NotADirectoryError):
        pass
    return sorted(results, key=lambda p: p.name)


def _build_file_info(path: Path, source: ThemeSource) -> ThemeFileInfo | None:
    try:
        resolved = path.resolve()
        stat = resolved.stat()
        return ThemeFileInfo(
            canonical_name=resolved.stem,
            filename=resolved.name,
            source=source,
            path=resolved,
            size_bytes=stat.st_size,
            mtime=stat.st_mtime,
        )
    except OSError:
        return None


def discover_bundled(bundled_root: Path) -> list[ThemeFileInfo]:
    results: list[ThemeFileInfo] = []
    for path in _candidate_files(bundled_root):
        info = _build_file_info(path, ThemeSource.BUNDLED)
        if info is not None:
            results.append(info)
    return results


def discover_bundled_package() -> list[ThemeFileInfo]:
    results: list[ThemeFileInfo] = []
    try:
        bundled_dir = importlib.resources.files("app.themes").joinpath("bundled")
        for item in bundled_dir.iterdir():
            if not item.name.endswith(".toml") or item.name.startswith("."):
                continue
            try:
                content = item.read_bytes()
            except (OSError, TypeError):
                continue
            results.append(
                ThemeFileInfo(
                    canonical_name=Path(item.name).stem,
                    filename=item.name,
                    source=ThemeSource.BUNDLED,
                    path=Path(str(item)),
                    size_bytes=len(content),
                    mtime=0.0,
                )
            )
    except (TypeError, ModuleNotFoundError):
        pass
    return sorted(results, key=lambda info: info.filename)


def discover_external(external_root: Path) -> list[ThemeFileInfo]:
    try:
        resolved_root = external_root.resolve()
        if not resolved_root.is_dir():
            return []
        if not os.access(resolved_root, os.R_OK | os.X_OK):
            return []
    except (FileNotFoundError, PermissionError, OSError):
        return []

    results: list[ThemeFileInfo] = []
    for path in _candidate_files(external_root):
        resolved = path.resolve()
        if not _is_inside(resolved, resolved_root):
            log.warning("skipping theme outside external root: %s", path)
            continue
        try:
            stat = resolved.stat()
        except OSError:
            continue
        if stat.st_size > _MAX_EXTERNAL_FILE_SIZE:
            log.warning("skipping oversized theme: %s (%d bytes)", path, stat.st_size)
            continue
        info = _build_file_info(path, ThemeSource.EXTERNAL)
        if info is not None:
            results.append(info)
    return results


__all__ = [
    "ThemeFileInfo",
    "ThemeSource",
    "discover_bundled",
    "discover_bundled_package",
    "discover_external",
    "validate_theme_name",
]
