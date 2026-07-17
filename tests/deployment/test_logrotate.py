from __future__ import annotations

from app.config.model import DevLogConfig, LoggingConfig
from app.deployment.logrotate import render_logrotate
from app.deployment.model import DeploymentContext
from app.filesystem.layout import InstallMode


class TestRenderLogrotate:
    def test_returns_none_when_not_log_to_file(self, app, tmp_path):
        config = DevLogConfig(logging=LoggingConfig(level="DEBUG"))
        ctx = DeploymentContext.from_config(config, mode=InstallMode.DOCKER)
        log_path = ctx.paths.log_dir.path
        if log_path.exists():
            import shutil

            shutil.rmtree(log_path)
        result = render_logrotate(ctx)
        assert result is None

    def test_renders_when_log_to_file(self, app, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        config = DevLogConfig(logging=LoggingConfig(level="INFO"))
        ctx = DeploymentContext.from_config(config, mode=InstallMode.SYSTEM)
        result = render_logrotate(ctx)
        assert result is not None
        assert result.filename == "devlog"

    def test_daily_rotation(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.SYSTEM)
        result = render_logrotate(ctx)
        assert "daily" in result.content

    def test_rotate_14(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.SYSTEM)
        result = render_logrotate(ctx)
        assert "rotate 14" in result.content

    def test_compression(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.SYSTEM)
        result = render_logrotate(ctx)
        assert "compress" in result.content
        assert "delaycompress" in result.content

    def test_create_directive_ownership(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.SYSTEM)
        result = render_logrotate(ctx)
        assert "create 0640" in result.content
        assert "devlog devlog" in result.content

    def test_missingok_notifempty(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.SYSTEM)
        result = render_logrotate(ctx)
        assert "missingok" in result.content
        assert "notifempty" in result.content

    def test_postrotate(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.SYSTEM)
        result = render_logrotate(ctx)
        assert "postrotate" in result.content
        assert "endscript" in result.content

    def test_managed_true(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.SYSTEM)
        result = render_logrotate(ctx)
        assert result.managed is True

    def test_permissions(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.SYSTEM)
        result = render_logrotate(ctx)
        assert result.permissions == 0o644

    def test_no_warnings(self, app):
        config = DevLogConfig()
        ctx = DeploymentContext.from_config(config, mode=InstallMode.SYSTEM)
        result = render_logrotate(ctx)
        assert result.warnings == []
