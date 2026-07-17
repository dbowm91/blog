"""Deployment context and rendering result types.

Aggregates configuration, paths, and mode into a single context object
that renderers consume to produce deployment artifacts.
"""

from __future__ import annotations

import getpass
import importlib.metadata
from dataclasses import dataclass, field

from app.config.model import DevLogConfig
from app.filesystem.layout import InstallationMetadata, InstallMode, RuntimePaths


def _current_user() -> str:
    try:
        return getpass.getuser()
    except KeyError:
        return "devlog"


def _app_version() -> str:
    try:
        return importlib.metadata.version("devlog")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0"


@dataclass(frozen=True)
class DeploymentContext:
    mode: InstallMode
    config: DevLogConfig
    paths: RuntimePaths
    metadata: InstallationMetadata | None
    version: str

    @property
    def is_system(self) -> bool:
        return self.mode == InstallMode.SYSTEM

    @property
    def is_user(self) -> bool:
        return self.mode == InstallMode.USER

    @property
    def is_docker(self) -> bool:
        return self.mode == InstallMode.DOCKER

    @property
    def is_development(self) -> bool:
        return self.mode == InstallMode.DEVELOPMENT

    @property
    def service_user(self) -> str:
        if self.mode == InstallMode.SYSTEM:
            return "devlog"
        return _current_user()

    @property
    def service_group(self) -> str:
        if self.mode == InstallMode.SYSTEM:
            return "devlog"
        return _current_user()

    @property
    def bind_address(self) -> str:
        return self.config.server.host

    @property
    def bind_port(self) -> int:
        return self.config.server.port

    @property
    def public_url(self) -> str:
        return self.config.site.base_url

    @property
    def has_redis(self) -> bool:
        return bool(self.config.redis.url)

    @property
    def has_celery(self) -> bool:
        return bool(self.config.celery.broker_url)

    @property
    def has_scheduler(self) -> bool:
        return self.config.scheduler.enabled

    @property
    def has_smtp(self) -> bool:
        return bool(self.config.email.smtp_host)

    @property
    def is_production(self) -> bool:
        return self.config.is_production()

    @property
    def log_to_file(self) -> bool:
        return self.config.logging.level != "DEBUG" or self.paths.log_dir.path.exists()

    @classmethod
    def from_config(
        cls,
        config: DevLogConfig,
        mode: InstallMode | None = None,
    ) -> DeploymentContext:
        resolved_mode = mode or InstallMode.DEVELOPMENT
        paths = RuntimePaths.for_mode(resolved_mode)

        metadata: InstallationMetadata | None = None
        meta_path = paths.installation_metadata.path
        if meta_path.exists():
            metadata = InstallationMetadata.load(meta_path)

        return cls(
            mode=resolved_mode,
            config=config,
            paths=paths,
            metadata=metadata,
            version=_app_version(),
        )


@dataclass(frozen=True)
class RenderResult:
    content: str
    filename: str
    managed: bool
    warnings: list[str] = field(default_factory=list)
    permissions: int = 0o644
    description: str = ""


def validate_deployment_context(ctx: DeploymentContext) -> list[str]:
    errors: list[str] = []
    if ctx.has_scheduler and not ctx.has_celery:
        errors.append(
            "Scheduler is enabled but celery broker URL is not configured; "
            "scheduled jobs will not execute without a broker"
        )
    if ctx.has_scheduler and ctx.mode == InstallMode.DEVELOPMENT:
        errors.append(
            "Scheduler is enabled in development mode; "
            "scheduler unit will not be generated for foreground deployment"
        )
    return errors
