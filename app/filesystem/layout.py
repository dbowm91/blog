from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path


def _absolute(path: Path) -> Path:
    """Make a path absolute without dereferencing symlinks.

    ``Path.resolve()`` rewrites ``/etc/devlog`` into ``/private/etc/devlog``
    wherever ``/etc`` is a symlink, so a resolved path would no longer be the
    path the operator configured or the mode default documents.
    """
    return Path(os.path.abspath(path))


class InstallMode(Enum):
    SYSTEM = "system"
    USER = "user"
    DOCKER = "docker"
    DEVELOPMENT = "development"


class PathProvenance(Enum):
    EXPLICIT = "explicit"
    METADATA = "metadata"
    ENV_VAR = "env_var"
    SYSTEM_DEFAULT = "system_default"
    XDG_DEFAULT = "xdg_default"
    DOCKER_DEFAULT = "docker_default"
    DEVELOPMENT_FALLBACK = "development_fallback"


@dataclass(frozen=True)
class ResolvedPath:
    path: Path
    provenance: PathProvenance
    source: str


@dataclass(frozen=True)
class InstallationMetadata:
    mode: InstallMode
    version: str
    data_dir: Path | None = None
    config_file: Path | None = None
    env_file: Path | None = None
    install_root: Path | None = None

    @classmethod
    def load(cls, path: Path) -> InstallationMetadata | None:
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text())
            mode = InstallMode(raw["mode"])
            version = raw.get("version", "unknown")
            data_dir = Path(raw["data_dir"]) if "data_dir" in raw else None
            config_file = Path(raw["config_file"]) if "config_file" in raw else None
            env_file = Path(raw["env_file"]) if "env_file" in raw else None
            install_root = Path(raw["install_root"]) if "install_root" in raw else None
            return cls(
                mode=mode,
                version=version,
                data_dir=data_dir,
                config_file=config_file,
                env_file=env_file,
                install_root=install_root,
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return None


def _resolve_path(
    explicit: Path | None,
    env_var: str | None,
    default: Path,
    explicit_provenance: PathProvenance,
    default_provenance: PathProvenance,
    explicit_source: str,
    default_source: str,
) -> ResolvedPath:
    if explicit is not None:
        return ResolvedPath(
            path=_absolute(explicit),
            provenance=explicit_provenance,
            source=explicit_source,
        )
    if env_var:
        val = os.environ.get(env_var, "")
        if val:
            return ResolvedPath(
                path=_absolute(Path(val)),
                provenance=PathProvenance.ENV_VAR,
                source=f"environment variable {env_var}",
            )
    return ResolvedPath(
        path=_absolute(default),
        provenance=default_provenance,
        source=default_source,
    )


def _xdg_config_home(override: Path | None = None) -> Path:
    if override is not None:
        return override
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".config"


def _xdg_data_home(override: Path | None = None) -> Path:
    if override is not None:
        return override
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".local" / "share"


def _xdg_state_home(override: Path | None = None) -> Path:
    if override is not None:
        return override
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".local" / "state"


def _xdg_runtime_dir(override: Path | None = None) -> Path | None:
    if override is not None:
        return override
    xdg = os.environ.get("XDG_RUNTIME_DIR")
    if xdg:
        return Path(xdg)
    return None


def _resolve_database_path(data_dir: Path, explicit: Path | None = None) -> Path:
    if explicit is not None:
        return _absolute(explicit)
    return _absolute(data_dir / "devlog.sqlite3")


def _resolve_uploads_dir(data_dir: Path, explicit: Path | None = None) -> Path:
    if explicit is not None:
        return _absolute(explicit)
    return _absolute(data_dir / "uploads")


def _resolve_themes_dir(data_dir: Path, explicit: Path | None = None) -> Path:
    if explicit is not None:
        return _absolute(explicit)
    return _absolute(data_dir / "themes")


def _resolve_backups_dir(data_dir: Path, explicit: Path | None = None) -> Path:
    if explicit is not None:
        return _absolute(explicit)
    return _absolute(data_dir / "backups")


def _resolve_exports_dir(data_dir: Path, explicit: Path | None = None) -> Path:
    if explicit is not None:
        return _absolute(explicit)
    return _absolute(data_dir / "exports")


def resolve_migrations_directory() -> str:
    """Resolve the Alembic migrations directory to an absolute path.

    Flask-Migrate resolves its ``directory`` against the current working
    directory, so a pip-installed DevLog never finds the migrations it ships
    and ``devlog db status`` fails outside a source checkout. The migrations
    sit next to the ``app`` package: in a source checkout that is the
    repository root, and in a wheel install it is ``site-packages/migrations``.
    """
    candidate = Path(__file__).resolve().parents[2] / "migrations"
    if (candidate / "env.py").is_file():
        return str(candidate)
    return "migrations"


@dataclass(frozen=True)
class ModeDetectionResult:
    detected_mode: InstallMode
    source: str
    ambiguous: bool = False
    candidates: list[tuple[InstallMode, str]] | None = None


def detect_mode_from_metadata(search_root: Path | None = None) -> ModeDetectionResult | None:
    root = (search_root or Path.cwd()).resolve()
    metadata_locations = [
        root / ".devlog-installation.json",
        root / "data" / ".devlog-installation.json",
    ]
    for meta_path in metadata_locations:
        meta = InstallationMetadata.load(meta_path)
        if meta is not None:
            return ModeDetectionResult(
                detected_mode=meta.mode,
                source=f"metadata file {meta_path}",
            )
    parent = root.parent
    if parent != root:
        parent_meta = parent / ".devlog-installation.json"
        meta = InstallationMetadata.load(parent_meta)
        if meta is not None:
            return ModeDetectionResult(
                detected_mode=meta.mode,
                source=f"metadata file {parent_meta}",
            )
    return None


def detect_mode(search_root: Path | None = None) -> ModeDetectionResult:
    root = (search_root or Path.cwd()).resolve()
    candidates: list[tuple[InstallMode, str]] = []

    meta_result = detect_mode_from_metadata(root)
    if meta_result is not None:
        candidates.append((meta_result.detected_mode, meta_result.source))

    docker_env = os.environ.get("DEVLOG_DOCKER")
    if docker_env:
        candidates.append((InstallMode.DOCKER, "DEVLOG_DOCKER env var"))
    elif Path("/.dockerenv").exists():
        candidates.append((InstallMode.DOCKER, "Docker container detected"))

    if os.environ.get("DEVLOG_MODE"):
        candidates.append((InstallMode(os.environ["DEVLOG_MODE"]), "DEVLOG_MODE env var"))

    system_paths = [Path("/etc/devlog/config.toml"), Path("/var/lib/devlog")]
    for sp in system_paths:
        if sp.exists():
            candidates.append((InstallMode.SYSTEM, f"system path {sp}"))
            break

    if candidates:
        if len(candidates) == 1:
            mode, source = candidates[0]
            return ModeDetectionResult(detected_mode=mode, source=source)
        primary_mode, primary_source = candidates[0]
        other_modes = [(m, s) for m, s in candidates[1:] if m != primary_mode]
        if other_modes:
            return ModeDetectionResult(
                detected_mode=primary_mode,
                source=primary_source,
                ambiguous=True,
                candidates=candidates,
            )
        return ModeDetectionResult(detected_mode=primary_mode, source=primary_source)

    return ModeDetectionResult(
        detected_mode=InstallMode.DEVELOPMENT,
        source="no metadata or system paths found, defaulting to development",
    )


@dataclass(frozen=True)
class RuntimePaths:
    config_file: ResolvedPath
    env_file: ResolvedPath
    data_dir: ResolvedPath
    database: ResolvedPath
    uploads_dir: ResolvedPath
    themes_dir: ResolvedPath
    backups_dir: ResolvedPath
    exports_dir: ResolvedPath
    log_dir: ResolvedPath
    runtime_dir: ResolvedPath
    installation_metadata: ResolvedPath
    release_dir: ResolvedPath | None = None
    mode: InstallMode = InstallMode.DEVELOPMENT

    @classmethod
    def resolve(
        cls,
        mode: InstallMode,
        *,
        config_file: Path | None = None,
        env_file: Path | None = None,
        data_dir: Path | None = None,
        log_dir: Path | None = None,
        runtime_dir: Path | None = None,
        uploads_dir: Path | None = None,
        themes_dir: Path | None = None,
        backups_dir: Path | None = None,
        exports_dir: Path | None = None,
        database_path: Path | None = None,
        xdg_config_home: Path | None = None,
        xdg_data_home: Path | None = None,
        xdg_state_home: Path | None = None,
        xdg_runtime_dir: Path | None = None,
        install_root: Path | None = None,
    ) -> RuntimePaths:
        if mode == InstallMode.SYSTEM:
            paths = _resolve_system(
                config_file=config_file,
                env_file=env_file,
                data_dir=data_dir,
                log_dir=log_dir,
                runtime_dir=runtime_dir,
                uploads_dir=uploads_dir,
                themes_dir=themes_dir,
                backups_dir=backups_dir,
                exports_dir=exports_dir,
                database_path=database_path,
                install_root=install_root,
            )
        elif mode == InstallMode.USER:
            paths = _resolve_user(
                config_file=config_file,
                env_file=env_file,
                data_dir=data_dir,
                log_dir=log_dir,
                runtime_dir=runtime_dir,
                uploads_dir=uploads_dir,
                themes_dir=themes_dir,
                backups_dir=backups_dir,
                exports_dir=exports_dir,
                database_path=database_path,
                xdg_config_home=xdg_config_home,
                xdg_data_home=xdg_data_home,
                xdg_state_home=xdg_state_home,
                xdg_runtime_dir=xdg_runtime_dir,
            )
        elif mode == InstallMode.DOCKER:
            paths = _resolve_docker(
                config_file=config_file,
                env_file=env_file,
                data_dir=data_dir,
                log_dir=log_dir,
                runtime_dir=runtime_dir,
                uploads_dir=uploads_dir,
                themes_dir=themes_dir,
                backups_dir=backups_dir,
                exports_dir=exports_dir,
                database_path=database_path,
            )
        else:
            paths = _resolve_development(
                config_file=config_file,
                env_file=env_file,
                data_dir=data_dir,
                log_dir=log_dir,
                runtime_dir=runtime_dir,
                uploads_dir=uploads_dir,
                themes_dir=themes_dir,
                backups_dir=backups_dir,
                exports_dir=exports_dir,
                database_path=database_path,
            )
        return replace(paths, mode=mode)

    @classmethod
    def for_mode(cls, mode: InstallMode) -> RuntimePaths:
        return cls.resolve(mode)

    @classmethod
    def from_metadata(
        cls,
        metadata_path: Path,
        *,
        config_file: Path | None = None,
        env_file: Path | None = None,
        data_dir: Path | None = None,
        log_dir: Path | None = None,
        runtime_dir: Path | None = None,
        uploads_dir: Path | None = None,
        themes_dir: Path | None = None,
        backups_dir: Path | None = None,
        exports_dir: Path | None = None,
        database_path: Path | None = None,
    ) -> RuntimePaths | None:
        meta = InstallationMetadata.load(metadata_path)
        if meta is None:
            return None
        explicit_overrides: dict[str, Path | None] = {
            "config_file": config_file or meta.config_file,
            "env_file": env_file or meta.env_file,
            "data_dir": data_dir or meta.data_dir,
        }
        return cls.resolve(
            meta.mode,
            config_file=explicit_overrides["config_file"],
            env_file=explicit_overrides["env_file"],
            data_dir=explicit_overrides["data_dir"],
            log_dir=log_dir,
            runtime_dir=runtime_dir,
            uploads_dir=uploads_dir,
            themes_dir=themes_dir,
            backups_dir=backups_dir,
            exports_dir=exports_dir,
            database_path=database_path,
            install_root=meta.install_root,
        )

    def as_dict(self) -> dict[str, str]:
        result = {
            "config_file": str(self.config_file.path),
            "env_file": str(self.env_file.path),
            "data_dir": str(self.data_dir.path),
            "database": str(self.database.path),
            "uploads_dir": str(self.uploads_dir.path),
            "themes_dir": str(self.themes_dir.path),
            "backups_dir": str(self.backups_dir.path),
            "exports_dir": str(self.exports_dir.path),
            "log_dir": str(self.log_dir.path),
            "runtime_dir": str(self.runtime_dir.path),
            "installation_metadata": str(self.installation_metadata.path),
        }
        if self.release_dir is not None:
            result["release_dir"] = str(self.release_dir.path)
        return result

    def all_paths(self) -> list[tuple[str, Path]]:
        paths = [
            ("config_file", self.config_file.path),
            ("env_file", self.env_file.path),
            ("data_dir", self.data_dir.path),
            ("database", self.database.path),
            ("uploads_dir", self.uploads_dir.path),
            ("themes_dir", self.themes_dir.path),
            ("backups_dir", self.backups_dir.path),
            ("exports_dir", self.exports_dir.path),
            ("log_dir", self.log_dir.path),
            ("runtime_dir", self.runtime_dir.path),
            ("installation_metadata", self.installation_metadata.path),
        ]
        if self.release_dir is not None:
            paths.append(("release_dir", self.release_dir.path))
        return paths

    def provenance_for(self, name: str) -> str:
        rp = getattr(self, name, None)
        if rp is None or not isinstance(rp, ResolvedPath):
            return "unknown"
        return f"{rp.provenance.value}: {rp.source}"


def _resolve_system(
    *,
    config_file: Path | None,
    env_file: Path | None,
    data_dir: Path | None,
    log_dir: Path | None,
    runtime_dir: Path | None,
    uploads_dir: Path | None,
    themes_dir: Path | None,
    backups_dir: Path | None,
    exports_dir: Path | None,
    database_path: Path | None,
    install_root: Path | None,
) -> RuntimePaths:
    root = install_root or Path("/etc/devlog")
    data_root = Path("/var/lib/devlog")
    log_root = Path("/var/log/devlog")
    runtime_root = Path("/run/devlog")

    resolved_data = _resolve_path(
        data_dir,
        "DEVLOG_DATA_DIR",
        data_root,
        PathProvenance.EXPLICIT,
        PathProvenance.SYSTEM_DEFAULT,
        "explicit override",
        "system default /var/lib/devlog",
    )
    resolved_config = _resolve_path(
        config_file,
        "DEVLOG_CONFIG_FILE",
        root / "config.toml",
        PathProvenance.EXPLICIT,
        PathProvenance.SYSTEM_DEFAULT,
        "explicit override",
        "system default /etc/devlog/config.toml",
    )
    resolved_env = _resolve_path(
        env_file,
        "DEVLOG_ENV_FILE",
        root / ".env",
        PathProvenance.EXPLICIT,
        PathProvenance.SYSTEM_DEFAULT,
        "explicit override",
        "system default /etc/devlog/.env",
    )
    resolved_log = _resolve_path(
        log_dir,
        "DEVLOG_LOG_DIR",
        log_root,
        PathProvenance.EXPLICIT,
        PathProvenance.SYSTEM_DEFAULT,
        "explicit override",
        "system default /var/log/devlog",
    )
    resolved_runtime = _resolve_path(
        runtime_dir,
        "DEVLOG_RUNTIME_DIR",
        runtime_root,
        PathProvenance.EXPLICIT,
        PathProvenance.SYSTEM_DEFAULT,
        "explicit override",
        "system default /run/devlog",
    )
    resolved_db = ResolvedPath(
        path=_resolve_database_path(resolved_data.path, database_path),
        provenance=PathProvenance.EXPLICIT if database_path else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not database_path
        else "explicit override",
    )
    resolved_uploads = ResolvedPath(
        path=_resolve_uploads_dir(resolved_data.path, uploads_dir),
        provenance=PathProvenance.EXPLICIT if uploads_dir else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not uploads_dir
        else "explicit override",
    )
    resolved_themes = ResolvedPath(
        path=_resolve_themes_dir(resolved_data.path, themes_dir),
        provenance=PathProvenance.EXPLICIT if themes_dir else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not themes_dir
        else "explicit override",
    )
    resolved_backups = ResolvedPath(
        path=_resolve_backups_dir(resolved_data.path, backups_dir),
        provenance=PathProvenance.EXPLICIT if backups_dir else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not backups_dir
        else "explicit override",
    )
    resolved_exports = ResolvedPath(
        path=_resolve_exports_dir(resolved_data.path, exports_dir),
        provenance=PathProvenance.EXPLICIT if exports_dir else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not exports_dir
        else "explicit override",
    )
    resolved_metadata = ResolvedPath(
        path=_absolute(resolved_data.path / ".devlog-installation.json"),
        provenance=resolved_data.provenance,
        source=resolved_data.source,
    )
    release_root = Path("/opt/devlog") / "current"
    release_env = os.environ.get("DEVLOG_RELEASE_DIR", "")
    if release_env:
        resolved_release = ResolvedPath(
            path=_absolute(Path(release_env)),
            provenance=PathProvenance.ENV_VAR,
            source="environment variable DEVLOG_RELEASE_DIR",
        )
    else:
        resolved_release = ResolvedPath(
            path=_absolute(release_root),
            provenance=PathProvenance.SYSTEM_DEFAULT,
            source=f"system default {release_root}",
        )
    return RuntimePaths(
        config_file=resolved_config,
        env_file=resolved_env,
        data_dir=resolved_data,
        database=resolved_db,
        uploads_dir=resolved_uploads,
        themes_dir=resolved_themes,
        backups_dir=resolved_backups,
        exports_dir=resolved_exports,
        log_dir=resolved_log,
        runtime_dir=resolved_runtime,
        installation_metadata=resolved_metadata,
        release_dir=resolved_release,
    )


def _resolve_user(
    *,
    config_file: Path | None,
    env_file: Path | None,
    data_dir: Path | None,
    log_dir: Path | None,
    runtime_dir: Path | None,
    uploads_dir: Path | None,
    themes_dir: Path | None,
    backups_dir: Path | None,
    exports_dir: Path | None,
    database_path: Path | None,
    xdg_config_home: Path | None,
    xdg_data_home: Path | None,
    xdg_state_home: Path | None,
    xdg_runtime_dir: Path | None,
) -> RuntimePaths:
    cfg_home = _xdg_config_home(xdg_config_home)
    data_home = _xdg_data_home(xdg_data_home)
    state_home = _xdg_state_home(xdg_state_home)
    runtime_home = _xdg_runtime_dir(xdg_runtime_dir)

    app_config_dir = cfg_home / "devlog"
    app_data_dir = data_home / "devlog"
    app_state_dir = state_home / "devlog"

    resolved_data = _resolve_path(
        data_dir,
        "DEVLOG_DATA_DIR",
        app_data_dir,
        PathProvenance.EXPLICIT,
        PathProvenance.XDG_DEFAULT,
        "explicit override",
        f"XDG default {app_data_dir}",
    )
    resolved_config = _resolve_path(
        config_file,
        "DEVLOG_CONFIG_FILE",
        app_config_dir / "config.toml",
        PathProvenance.EXPLICIT,
        PathProvenance.XDG_DEFAULT,
        "explicit override",
        f"XDG default {app_config_dir / 'config.toml'}",
    )
    resolved_env = _resolve_path(
        env_file,
        "DEVLOG_ENV_FILE",
        app_config_dir / ".env",
        PathProvenance.EXPLICIT,
        PathProvenance.XDG_DEFAULT,
        "explicit override",
        f"XDG default {app_config_dir / '.env'}",
    )
    resolved_log = _resolve_path(
        log_dir,
        "DEVLOG_LOG_DIR",
        app_state_dir / "logs",
        PathProvenance.EXPLICIT,
        PathProvenance.XDG_DEFAULT,
        "explicit override",
        f"XDG default {app_state_dir / 'logs'}",
    )

    if runtime_dir is not None:
        resolved_runtime = ResolvedPath(
            path=_absolute(runtime_dir),
            provenance=PathProvenance.EXPLICIT,
            source="explicit override",
        )
    elif runtime_home is not None:
        resolved_runtime = ResolvedPath(
            path=_absolute(runtime_home / "devlog"),
            provenance=PathProvenance.XDG_DEFAULT,
            source=f"XDG_RUNTIME_DIR ({runtime_home})",
        )
    else:
        resolved_runtime = ResolvedPath(
            path=_absolute(app_state_dir),
            provenance=PathProvenance.XDG_DEFAULT,
            source=f"fallback to XDG_STATE_HOME/devlog ({app_state_dir})",
        )

    resolved_db = ResolvedPath(
        path=_resolve_database_path(resolved_data.path, database_path),
        provenance=PathProvenance.EXPLICIT if database_path else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not database_path
        else "explicit override",
    )
    resolved_uploads = ResolvedPath(
        path=_resolve_uploads_dir(resolved_data.path, uploads_dir),
        provenance=PathProvenance.EXPLICIT if uploads_dir else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not uploads_dir
        else "explicit override",
    )
    resolved_themes = ResolvedPath(
        path=_resolve_themes_dir(resolved_data.path, themes_dir),
        provenance=PathProvenance.EXPLICIT if themes_dir else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not themes_dir
        else "explicit override",
    )
    resolved_backups = ResolvedPath(
        path=_resolve_backups_dir(resolved_data.path, backups_dir),
        provenance=PathProvenance.EXPLICIT if backups_dir else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not backups_dir
        else "explicit override",
    )
    resolved_exports = ResolvedPath(
        path=_resolve_exports_dir(resolved_data.path, exports_dir),
        provenance=PathProvenance.EXPLICIT if exports_dir else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not exports_dir
        else "explicit override",
    )
    resolved_metadata = ResolvedPath(
        path=_absolute(resolved_data.path / ".devlog-installation.json"),
        provenance=resolved_data.provenance,
        source=resolved_data.source,
    )
    return RuntimePaths(
        config_file=resolved_config,
        env_file=resolved_env,
        data_dir=resolved_data,
        database=resolved_db,
        uploads_dir=resolved_uploads,
        themes_dir=resolved_themes,
        backups_dir=resolved_backups,
        exports_dir=resolved_exports,
        log_dir=resolved_log,
        runtime_dir=resolved_runtime,
        installation_metadata=resolved_metadata,
    )


def _resolve_docker(
    *,
    config_file: Path | None,
    env_file: Path | None,
    data_dir: Path | None,
    log_dir: Path | None,
    runtime_dir: Path | None,
    uploads_dir: Path | None,
    themes_dir: Path | None,
    backups_dir: Path | None,
    exports_dir: Path | None,
    database_path: Path | None,
) -> RuntimePaths:
    resolved_data = _resolve_path(
        data_dir,
        "DEVLOG_DATA_DIR",
        Path("/data"),
        PathProvenance.EXPLICIT,
        PathProvenance.DOCKER_DEFAULT,
        "explicit override",
        "Docker default /data",
    )
    resolved_config = _resolve_path(
        config_file,
        "DEVLOG_CONFIG_FILE",
        Path("/etc/devlog/config.toml"),
        PathProvenance.EXPLICIT,
        PathProvenance.DOCKER_DEFAULT,
        "explicit override",
        "Docker default /etc/devlog/config.toml",
    )
    resolved_env = _resolve_path(
        env_file,
        "DEVLOG_ENV_FILE",
        Path("/etc/devlog/.env"),
        PathProvenance.EXPLICIT,
        PathProvenance.DOCKER_DEFAULT,
        "explicit override",
        "Docker default /etc/devlog/.env",
    )
    resolved_log = _resolve_path(
        log_dir,
        "DEVLOG_LOG_DIR",
        Path("/var/log/devlog"),
        PathProvenance.EXPLICIT,
        PathProvenance.DOCKER_DEFAULT,
        "explicit override",
        "Docker default /var/log/devlog",
    )
    resolved_runtime = _resolve_path(
        runtime_dir,
        "DEVLOG_RUNTIME_DIR",
        Path("/run/devlog"),
        PathProvenance.EXPLICIT,
        PathProvenance.DOCKER_DEFAULT,
        "explicit override",
        "Docker default /run/devlog",
    )
    resolved_db = ResolvedPath(
        path=_resolve_database_path(resolved_data.path, database_path),
        provenance=PathProvenance.EXPLICIT if database_path else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not database_path
        else "explicit override",
    )
    resolved_uploads = ResolvedPath(
        path=_resolve_uploads_dir(resolved_data.path, uploads_dir),
        provenance=PathProvenance.EXPLICIT if uploads_dir else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not uploads_dir
        else "explicit override",
    )
    resolved_themes = ResolvedPath(
        path=_resolve_themes_dir(resolved_data.path, themes_dir),
        provenance=PathProvenance.EXPLICIT if themes_dir else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not themes_dir
        else "explicit override",
    )
    resolved_backups = ResolvedPath(
        path=_resolve_backups_dir(resolved_data.path, backups_dir),
        provenance=PathProvenance.EXPLICIT if backups_dir else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not backups_dir
        else "explicit override",
    )
    resolved_exports = ResolvedPath(
        path=_resolve_exports_dir(resolved_data.path, exports_dir),
        provenance=PathProvenance.EXPLICIT if exports_dir else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not exports_dir
        else "explicit override",
    )
    resolved_metadata = ResolvedPath(
        path=_absolute(resolved_data.path / ".devlog-installation.json"),
        provenance=resolved_data.provenance,
        source=resolved_data.source,
    )
    return RuntimePaths(
        config_file=resolved_config,
        env_file=resolved_env,
        data_dir=resolved_data,
        database=resolved_db,
        uploads_dir=resolved_uploads,
        themes_dir=resolved_themes,
        backups_dir=resolved_backups,
        exports_dir=resolved_exports,
        log_dir=resolved_log,
        runtime_dir=resolved_runtime,
        installation_metadata=resolved_metadata,
    )


def _resolve_development(
    *,
    config_file: Path | None,
    env_file: Path | None,
    data_dir: Path | None,
    log_dir: Path | None,
    runtime_dir: Path | None,
    uploads_dir: Path | None,
    themes_dir: Path | None,
    backups_dir: Path | None,
    exports_dir: Path | None,
    database_path: Path | None,
) -> RuntimePaths:
    repo_root = Path.cwd()
    resolved_data = _resolve_path(
        data_dir,
        "DEVLOG_DATA_DIR",
        repo_root / "data",
        PathProvenance.EXPLICIT,
        PathProvenance.DEVELOPMENT_FALLBACK,
        "explicit override",
        f"development fallback {repo_root / 'data'}",
    )
    resolved_config = _resolve_path(
        config_file,
        "DEVLOG_CONFIG_FILE",
        repo_root / "config.toml",
        PathProvenance.EXPLICIT,
        PathProvenance.DEVELOPMENT_FALLBACK,
        "explicit override",
        f"development fallback {repo_root / 'config.toml'}",
    )
    resolved_env = _resolve_path(
        env_file,
        "DEVLOG_ENV_FILE",
        repo_root / ".env",
        PathProvenance.EXPLICIT,
        PathProvenance.DEVELOPMENT_FALLBACK,
        "explicit override",
        f"development fallback {repo_root / '.env'}",
    )
    resolved_log = _resolve_path(
        log_dir,
        "DEVLOG_LOG_DIR",
        repo_root / "logs",
        PathProvenance.EXPLICIT,
        PathProvenance.DEVELOPMENT_FALLBACK,
        "explicit override",
        f"development fallback {repo_root / 'logs'}",
    )
    resolved_runtime = _resolve_path(
        runtime_dir,
        "DEVLOG_RUNTIME_DIR",
        repo_root / "instance",
        PathProvenance.EXPLICIT,
        PathProvenance.DEVELOPMENT_FALLBACK,
        "explicit override",
        f"development fallback {repo_root / 'instance'}",
    )
    resolved_db = ResolvedPath(
        path=_resolve_database_path(resolved_data.path, database_path),
        provenance=PathProvenance.EXPLICIT if database_path else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not database_path
        else "explicit override",
    )
    resolved_uploads = ResolvedPath(
        path=_resolve_uploads_dir(resolved_data.path, uploads_dir),
        provenance=PathProvenance.EXPLICIT if uploads_dir else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not uploads_dir
        else "explicit override",
    )
    resolved_themes = ResolvedPath(
        path=_resolve_themes_dir(resolved_data.path, themes_dir),
        provenance=PathProvenance.EXPLICIT if themes_dir else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not themes_dir
        else "explicit override",
    )
    resolved_backups = ResolvedPath(
        path=_resolve_backups_dir(resolved_data.path, backups_dir),
        provenance=PathProvenance.EXPLICIT if backups_dir else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not backups_dir
        else "explicit override",
    )
    resolved_exports = ResolvedPath(
        path=_resolve_exports_dir(resolved_data.path, exports_dir),
        provenance=PathProvenance.EXPLICIT if exports_dir else resolved_data.provenance,
        source=f"derived from data_dir ({resolved_data.source})"
        if not exports_dir
        else "explicit override",
    )
    resolved_metadata = ResolvedPath(
        path=_absolute(resolved_data.path / ".devlog-installation.json"),
        provenance=resolved_data.provenance,
        source=resolved_data.source,
    )
    return RuntimePaths(
        config_file=resolved_config,
        env_file=resolved_env,
        data_dir=resolved_data,
        database=resolved_db,
        uploads_dir=resolved_uploads,
        themes_dir=resolved_themes,
        backups_dir=resolved_backups,
        exports_dir=resolved_exports,
        log_dir=resolved_log,
        runtime_dir=resolved_runtime,
        installation_metadata=resolved_metadata,
    )
