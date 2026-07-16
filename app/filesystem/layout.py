from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


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
            path=explicit.resolve(),
            provenance=explicit_provenance,
            source=explicit_source,
        )
    if env_var:
        val = os.environ.get(env_var, "")
        if val:
            return ResolvedPath(
                path=Path(val).resolve(),
                provenance=PathProvenance.ENV_VAR,
                source=f"environment variable {env_var}",
            )
    return ResolvedPath(
        path=default.resolve(),
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
        return explicit.resolve()
    return (data_dir / "devlog.sqlite3").resolve()


def _resolve_uploads_dir(data_dir: Path, explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return (data_dir / "uploads").resolve()


def _resolve_themes_dir(data_dir: Path, explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return (data_dir / "themes").resolve()


def _resolve_backups_dir(data_dir: Path, explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return (data_dir / "backups").resolve()


def _resolve_exports_dir(data_dir: Path, explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return (data_dir / "exports").resolve()


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
            return _resolve_system(
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
        if mode == InstallMode.USER:
            return _resolve_user(
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
        if mode == InstallMode.DOCKER:
            return _resolve_docker(
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
        return _resolve_development(
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

    @classmethod
    def for_mode(cls, mode: InstallMode) -> RuntimePaths:
        return cls.resolve(mode)

    def as_dict(self) -> dict[str, str]:
        return {
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

    def all_paths(self) -> list[tuple[str, Path]]:
        return [
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
        path=(resolved_data.path / ".devlog-installation.json").resolve(),
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
            path=runtime_dir.resolve(),
            provenance=PathProvenance.EXPLICIT,
            source="explicit override",
        )
    elif runtime_home is not None:
        resolved_runtime = ResolvedPath(
            path=(runtime_home / "devlog").resolve(),
            provenance=PathProvenance.XDG_DEFAULT,
            source=f"XDG_RUNTIME_DIR ({runtime_home})",
        )
    else:
        resolved_runtime = ResolvedPath(
            path=app_state_dir.resolve(),
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
        path=(resolved_data.path / ".devlog-installation.json").resolve(),
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
        path=(resolved_data.path / ".devlog-installation.json").resolve(),
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
        path=(resolved_data.path / ".devlog-installation.json").resolve(),
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
