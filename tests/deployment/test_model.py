from __future__ import annotations

from app.config.model import (
    CeleryConfig,
    DevLogConfig,
    SchedulerConfig,
)
from app.deployment.model import DeploymentContext, RenderResult, validate_deployment_context
from app.filesystem.layout import InstallMode, RuntimePaths


class TestDeploymentContextFromConfig:
    def test_default_mode_is_development(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config)
        assert ctx.mode == InstallMode.DEVELOPMENT

    def test_explicit_system_mode(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.SYSTEM)
        assert ctx.mode == InstallMode.SYSTEM

    def test_explicit_user_mode(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.USER)
        assert ctx.mode == InstallMode.USER

    def test_explicit_docker_mode(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.DOCKER)
        assert ctx.mode == InstallMode.DOCKER

    def test_paths_are_resolved(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.DEVELOPMENT)
        assert isinstance(ctx.paths, RuntimePaths)
        assert ctx.paths.data_dir.path.exists()

    def test_version_populated(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config)
        assert ctx.version

    def test_metadata_none_when_no_file(self, app, tmp_path):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.DEVELOPMENT)
        assert ctx.metadata is None


class TestDeploymentContextProperties:
    def test_is_system(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.SYSTEM)
        assert ctx.is_system is True
        assert ctx.is_user is False
        assert ctx.is_docker is False
        assert ctx.is_development is False

    def test_is_user(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.USER)
        assert ctx.is_user is True
        assert ctx.is_system is False

    def test_is_docker(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.DOCKER)
        assert ctx.is_docker is True
        assert ctx.is_system is False

    def test_is_development(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.DEVELOPMENT)
        assert ctx.is_development is True
        assert ctx.is_system is False

    def test_service_user_system_mode(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.SYSTEM)
        assert ctx.service_user == "devlog"
        assert ctx.service_group == "devlog"

    def test_service_user_non_system_mode(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.USER)
        import getpass

        expected = getpass.getuser()
        assert ctx.service_user == expected
        assert ctx.service_group == expected


class TestDeploymentContextFeatureFlags:
    def test_has_redis_default(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config)
        assert ctx.has_redis is True

    def test_has_redis_empty(self, app):
        from app.config.model import RedisConfig

        config = DevLogConfig(redis=RedisConfig(url=""))
        ctx = DeploymentContext.from_config(config)
        assert ctx.has_redis is False

    def test_has_celery_default(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config)
        assert ctx.has_celery is False

    def test_has_celery_configured(self, app):
        from app.config.model import CeleryConfig

        config = DevLogConfig(celery=CeleryConfig(broker_url="redis://localhost:6379/0"))
        ctx = DeploymentContext.from_config(config)
        assert ctx.has_celery is True

    def test_has_scheduler_default(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config)
        assert ctx.has_scheduler is False

    def test_has_scheduler_enabled(self, app):
        from app.config.model import SchedulerConfig

        config = DevLogConfig(scheduler=SchedulerConfig(enabled=True))
        ctx = DeploymentContext.from_config(config)
        assert ctx.has_scheduler is True

    def test_has_smtp_default(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config)
        assert ctx.has_smtp is False

    def test_has_smtp_configured(self, app):
        from app.config.model import EmailConfig

        config = DevLogConfig(email=EmailConfig(smtp_host="smtp.example.com"))
        ctx = DeploymentContext.from_config(config)
        assert ctx.has_smtp is True

    def test_bind_address(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config)
        assert ctx.bind_address == config.server.host

    def test_bind_port(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config)
        assert ctx.bind_port == config.server.port

    def test_public_url(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config)
        assert ctx.public_url == config.site.base_url

    def test_is_production_false(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config)
        assert ctx.is_production is False

    def test_is_production_true(self, app):
        config = DevLogConfig(flask_env="production")
        ctx = DeploymentContext.from_config(config)
        assert ctx.is_production is True


class TestRenderResult:
    def test_creation(self):
        result = RenderResult(content="test", filename="test.txt", managed=True)
        assert result.content == "test"
        assert result.filename == "test.txt"
        assert result.managed is True
        assert result.warnings == []
        assert result.permissions == 0o644
        assert result.description == ""

    def test_defaults(self):
        result = RenderResult(content="", filename="f", managed=False)
        assert result.warnings == []
        assert result.permissions == 0o644
        assert result.description == ""

    def test_with_warnings(self):
        result = RenderResult(content="c", filename="f", managed=True, warnings=["warn1", "warn2"])
        assert len(result.warnings) == 2

    def test_custom_permissions(self):
        result = RenderResult(content="c", filename="f", managed=True, permissions=0o600)
        assert result.permissions == 0o600


class TestValidateDeploymentContext:
    def test_scheduler_without_broker(self, app):
        config = DevLogConfig(
            scheduler=SchedulerConfig(enabled=True),
            celery=CeleryConfig(broker_url=""),
        )
        ctx = DeploymentContext.from_config(config, mode=InstallMode.SYSTEM)
        errors = validate_deployment_context(ctx)
        assert any("celery broker" in e.lower() for e in errors)

    def test_scheduler_with_broker(self, app):
        config = DevLogConfig(
            scheduler=SchedulerConfig(enabled=True),
            celery=CeleryConfig(broker_url="redis://localhost:6379/0"),
        )
        ctx = DeploymentContext.from_config(config, mode=InstallMode.SYSTEM)
        errors = validate_deployment_context(ctx)
        assert errors == []

    def test_scheduler_in_development_mode(self, app):
        config = DevLogConfig(scheduler=SchedulerConfig(enabled=True))
        ctx = DeploymentContext.from_config(config, mode=InstallMode.DEVELOPMENT)
        errors = validate_deployment_context(ctx)
        assert any("development mode" in e.lower() for e in errors)

    def test_no_scheduler_no_errors(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.SYSTEM)
        errors = validate_deployment_context(ctx)
        assert errors == []
