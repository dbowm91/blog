from __future__ import annotations

from app.config.model import (
    CeleryConfig,
    DevLogConfig,
    EmailConfig,
    RedisConfig,
    SchedulerConfig,
)
from app.deployment.compose import render_compose, render_compose_env
from app.deployment.model import DeploymentContext
from app.filesystem.layout import InstallMode


def _make_ctx(
    app, *, celery_broker="", scheduler_enabled=False, redis_url="redis://localhost:6379/0"
):
    config = DevLogConfig(
        celery=CeleryConfig(broker_url=celery_broker),
        scheduler=SchedulerConfig(enabled=scheduler_enabled),
    )
    return DeploymentContext.from_config(config, mode=InstallMode.DOCKER)


class TestRenderCompose:
    def test_basic_structure(self, app):
        ctx = _make_ctx(app)
        result = render_compose(ctx)
        assert result.filename == "docker-compose.yml"
        assert result.managed is True
        assert "services:" in result.content
        assert "volumes:" in result.content

    def test_web_service_always_present(self, app):
        ctx = _make_ctx(app)
        result = render_compose(ctx)
        assert "web:" in result.content
        assert "restart: unless-stopped" in result.content

    def test_redis_service_when_has_redis(self, app):
        ctx = _make_ctx(app, redis_url="redis://localhost:6379/0")
        result = render_compose(ctx)
        assert "redis:" in result.content
        assert "redis:7-alpine" in result.content

    def test_redis_service_absent_when_no_redis(self, app):
        config = DevLogConfig(redis=RedisConfig(url=""))
        ctx = DeploymentContext.from_config(config, mode=InstallMode.DOCKER)
        result = render_compose(ctx)
        assert "redis:" not in result.content
        assert any("Redis is not configured" in w for w in result.warnings)

    def test_celery_service_when_has_celery(self, app):
        ctx = _make_ctx(app, celery_broker="redis://localhost:6379/0")
        result = render_compose(ctx)
        assert "celery:" in result.content

    def test_celery_service_absent_when_no_celery(self, app):
        ctx = _make_ctx(app, celery_broker="")
        result = render_compose(ctx)
        assert "celery:" not in result.content

    def test_scheduler_service_when_enabled(self, app):
        ctx = _make_ctx(app, scheduler_enabled=True)
        result = render_compose(ctx)
        assert "scheduler:" in result.content

    def test_scheduler_service_absent_when_disabled(self, app):
        ctx = _make_ctx(app, scheduler_enabled=False)
        result = render_compose(ctx)
        assert "scheduler:" not in result.content

    def test_ports_loopback_only(self, app):
        ctx = _make_ctx(app)
        result = render_compose(ctx)
        assert "127.0.0.1:" in result.content

    def test_env_file_reference(self, app):
        ctx = _make_ctx(app)
        result = render_compose(ctx)
        assert "env_file:" in result.content
        assert ".env" in result.content

    def test_volumes_declared(self, app):
        ctx = _make_ctx(app)
        result = render_compose(ctx)
        assert "devlog_data:" in result.content
        assert "devlog_config:" in result.content
        assert "devlog_logs:" in result.content

    def test_healthcheck_present(self, app):
        ctx = _make_ctx(app)
        result = render_compose(ctx)
        assert "healthcheck:" in result.content

    def test_resource_limits(self, app):
        ctx = _make_ctx(app)
        result = render_compose(ctx)
        assert "memory: 512M" in result.content

    def test_no_secrets_in_output(self, app):
        ctx = _make_ctx(app)
        result = render_compose(ctx)
        assert "SECRET_KEY" not in result.content
        assert "ADMIN_PASSWORD" not in result.content


class TestRenderComposeEnv:
    def test_basic_variables(self, app):
        ctx = _make_ctx(app)
        result = render_compose_env(ctx)
        assert result.filename == "docker-compose.env"
        assert result.permissions == 0o600
        assert "FLASK_APP=" in result.content
        assert "FLASK_ENV=" in result.content
        assert "SERVER_HOST=" in result.content
        assert "SERVER_PORT=" in result.content

    def test_no_secret_key(self, app):
        ctx = _make_ctx(app)
        result = render_compose_env(ctx)
        lines = [line for line in result.content.splitlines() if not line.startswith("#")]
        secret_vars = {"SECRET_KEY=", "ADMIN_PASSWORD=", "SMTP_PASSWORD="}
        for line in lines:
            for var in secret_vars:
                assert not line.startswith(var), f"Secret variable found: {line}"

    def test_redis_url_included(self, app):
        ctx = _make_ctx(app)
        result = render_compose_env(ctx)
        assert "REDIS_URL=" in result.content
        assert "CELERY_BROKER_URL=" in result.content

    def test_smtp_vars_when_configured(self, app):
        config = DevLogConfig(
            email=EmailConfig(smtp_host="smtp.example.com", smtp_port=587),
        )
        ctx = DeploymentContext.from_config(config, mode=InstallMode.DOCKER)
        result = render_compose_env(ctx)
        assert "SMTP_HOST=smtp.example.com" in result.content
        assert "SMTP_PORT=587" in result.content

    def test_empty_values_not_included(self, app):
        config = DevLogConfig(email=EmailConfig(smtp_host=""))
        ctx = DeploymentContext.from_config(config, mode=InstallMode.DOCKER)
        result = render_compose_env(ctx)
        lines = [line for line in result.content.splitlines() if not line.startswith("#")]
        for line in lines:
            assert not line.startswith("SMTP_HOST="), f"SMTP_HOST should not be in output: {line}"

    def test_scheduler_flag(self, app):
        ctx = _make_ctx(app, scheduler_enabled=True)
        result = render_compose_env(ctx)
        assert "ENABLE_SCHEDULER=true" in result.content

    def test_auto_generated_header(self, app):
        ctx = _make_ctx(app)
        result = render_compose_env(ctx)
        assert "Auto-generated" in result.content
