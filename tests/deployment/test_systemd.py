from __future__ import annotations

from app.config.model import (
    CeleryConfig,
    DevLogConfig,
    SchedulerConfig,
)
from app.deployment.model import DeploymentContext
from app.deployment.systemd import (
    render_web_unit,
    render_worker_unit,
    render_scheduler_unit,
    validate_unit,
)
from app.filesystem.layout import InstallMode


def _make_ctx(app, *, mode=InstallMode.SYSTEM, celery_broker="", scheduler_enabled=False):
    config = DevLogConfig(
        celery=CeleryConfig(broker_url=celery_broker),
        scheduler=SchedulerConfig(enabled=scheduler_enabled),
    )
    return DeploymentContext.from_config(config, mode=mode)


class TestRenderWebUnit:
    def test_system_mode_has_user_group(self, app):
        ctx = _make_ctx(app, mode=InstallMode.SYSTEM)
        result = render_web_unit(ctx)
        assert "User=devlog" in result.content
        assert "Group=devlog" in result.content

    def test_system_mode_wanted_by_multi_user(self, app):
        ctx = _make_ctx(app, mode=InstallMode.SYSTEM)
        result = render_web_unit(ctx)
        assert "WantedBy=multi-user.target" in result.content

    def test_user_mode_wanted_by_default(self, app):
        ctx = _make_ctx(app, mode=InstallMode.USER)
        result = render_web_unit(ctx, user_unit=True)
        assert "WantedBy=default.target" in result.content

    def test_user_mode_no_user_group(self, app):
        ctx = _make_ctx(app, mode=InstallMode.USER)
        result = render_web_unit(ctx, user_unit=True)
        assert "User=" not in result.content
        assert "Group=" not in result.content

    def test_required_sections_present(self, app):
        ctx = _make_ctx(app)
        result = render_web_unit(ctx)
        assert "[Unit]" in result.content
        assert "[Service]" in result.content
        assert "[Install]" in result.content

    def test_hardening_directives(self, app):
        ctx = _make_ctx(app)
        result = render_web_unit(ctx)
        assert "NoNewPrivileges=true" in result.content
        assert "PrivateTmp=true" in result.content
        assert "ProtectSystem=strict" in result.content
        assert "ProtectHome=true" in result.content

    def test_read_write_paths_present(self, app):
        ctx = _make_ctx(app)
        result = render_web_unit(ctx)
        assert "ReadWritePaths=" in result.content

    def test_env_file_reference(self, app):
        ctx = _make_ctx(app)
        result = render_web_unit(ctx)
        assert "EnvironmentFile=" in result.content

    def test_filename_system(self, app):
        ctx = _make_ctx(app, mode=InstallMode.SYSTEM)
        result = render_web_unit(ctx)
        assert result.filename == "devlog-web.service"

    def test_filename_user(self, app):
        ctx = _make_ctx(app, mode=InstallMode.USER)
        result = render_web_unit(ctx, user_unit=True)
        assert result.filename == "devlog-web@.service"

    def test_managed_true(self, app):
        ctx = _make_ctx(app)
        result = render_web_unit(ctx)
        assert result.managed is True

    def test_permissions(self, app):
        ctx = _make_ctx(app)
        result = render_web_unit(ctx)
        assert result.permissions == 0o644


class TestRenderWorkerUnit:
    def test_returns_none_without_celery(self, app):
        ctx = _make_ctx(app, celery_broker="")
        result = render_worker_unit(ctx)
        assert result is None

    def test_renders_when_celery_configured(self, app):
        ctx = _make_ctx(app, celery_broker="redis://localhost:6379/0")
        result = render_worker_unit(ctx)
        assert result is not None
        assert "celery" in result.content.lower() or "worker" in result.content.lower()

    def test_system_mode_user_group(self, app):
        ctx = _make_ctx(app, celery_broker="redis://localhost:6379/0", mode=InstallMode.SYSTEM)
        result = render_worker_unit(ctx)
        assert "User=devlog" in result.content
        assert "Group=devlog" in result.content

    def test_user_mode_no_user_group(self, app):
        ctx = _make_ctx(app, celery_broker="redis://localhost:6379/0", mode=InstallMode.USER)
        result = render_worker_unit(ctx, user_unit=True)
        assert "User=" not in result.content

    def test_required_sections(self, app):
        ctx = _make_ctx(app, celery_broker="redis://localhost:6379/0")
        result = render_worker_unit(ctx)
        assert "[Unit]" in result.content
        assert "[Service]" in result.content
        assert "[Install]" in result.content

    def test_filename_system(self, app):
        ctx = _make_ctx(app, celery_broker="redis://localhost:6379/0")
        result = render_worker_unit(ctx)
        assert result.filename == "devlog-worker.service"

    def test_filename_user(self, app):
        ctx = _make_ctx(app, celery_broker="redis://localhost:6379/0")
        result = render_worker_unit(ctx, user_unit=True)
        assert result.filename == "devlog-worker@.service"


class TestRenderSchedulerUnit:
    def test_returns_none_without_scheduler(self, app):
        ctx = _make_ctx(app, scheduler_enabled=False)
        result = render_scheduler_unit(ctx)
        assert result is None

    def test_renders_when_scheduler_enabled(self, app):
        ctx = _make_ctx(app, scheduler_enabled=True)
        result = render_scheduler_unit(ctx)
        assert result is not None
        assert "scheduler" in result.content.lower()

    def test_system_mode_user_group(self, app):
        ctx = _make_ctx(app, scheduler_enabled=True, mode=InstallMode.SYSTEM)
        result = render_scheduler_unit(ctx)
        assert "User=devlog" in result.content

    def test_user_mode_no_user_group(self, app):
        ctx = _make_ctx(app, scheduler_enabled=True, mode=InstallMode.USER)
        result = render_scheduler_unit(ctx, user_unit=True)
        assert "User=" not in result.content

    def test_required_sections(self, app):
        ctx = _make_ctx(app, scheduler_enabled=True)
        result = render_scheduler_unit(ctx)
        assert "[Unit]" in result.content
        assert "[Service]" in result.content
        assert "[Install]" in result.content

    def test_filename_system(self, app):
        ctx = _make_ctx(app, scheduler_enabled=True)
        result = render_scheduler_unit(ctx)
        assert result.filename == "devlog-scheduler.service"

    def test_filename_user(self, app):
        ctx = _make_ctx(app, scheduler_enabled=True)
        result = render_scheduler_unit(ctx, user_unit=True)
        assert result.filename == "devlog-scheduler@.service"


class TestValidateUnit:
    def test_valid_unit_no_errors(self):
        content = """[Unit]
Description=Test

[Service]
Type=simple
ExecStart=/usr/bin/test

[Install]
WantedBy=multi-user.target
"""
        errors = validate_unit(content)
        assert errors == []

    def test_missing_unit_section(self):
        content = """[Service]
Type=simple
ExecStart=/usr/bin/test

[Install]
WantedBy=multi-user.target
"""
        errors = validate_unit(content)
        assert any("Missing required section: [Unit]" in e for e in errors)

    def test_missing_service_section(self):
        content = """[Unit]
Description=Test

[Install]
WantedBy=multi-user.target
"""
        errors = validate_unit(content)
        assert any("Missing required section: [Service]" in e for e in errors)

    def test_missing_install_section(self):
        content = """[Unit]
Description=Test

[Service]
Type=simple
ExecStart=/usr/bin/test
"""
        errors = validate_unit(content)
        assert any("Missing required section: [Install]" in e for e in errors)

    def test_shell_interpolation_detected(self):
        content = """[Unit]
Description=Test

[Service]
Type=simple
ExecStart=/bin/sh -c $HOME/script.sh

[Install]
WantedBy=multi-user.target
"""
        errors = validate_unit(content)
        assert any("Shell interpolation" in e for e in errors)

    def test_shell_variable_braces_detected(self):
        content = """[Unit]
Description=Test

[Service]
Type=simple
ExecStart=${MY_VAR}

[Install]
WantedBy=multi-user.target
"""
        errors = validate_unit(content)
        assert any("Shell interpolation" in e for e in errors)

    def test_safe_exec_start(self):
        content = """[Unit]
Description=Test

[Service]
Type=simple
ExecStart=/opt/devlog/current/venv/bin/python -m granian

[Install]
WantedBy=multi-user.target
"""
        errors = validate_unit(content)
        assert not any("Shell interpolation" in e for e in errors)


class TestNoSecretsInOutput:
    def test_web_unit_no_secrets(self, app):
        ctx = _make_ctx(app)
        result = render_web_unit(ctx)
        assert "SECRET_KEY" not in result.content
        assert "ADMIN_PASSWORD" not in result.content

    def test_worker_unit_no_secrets(self, app):
        ctx = _make_ctx(app, celery_broker="redis://localhost:6379/0")
        result = render_worker_unit(ctx)
        assert "SECRET_KEY" not in result.content
        assert "ADMIN_PASSWORD" not in result.content

    def test_scheduler_unit_no_secrets(self, app):
        ctx = _make_ctx(app, scheduler_enabled=True)
        result = render_scheduler_unit(ctx)
        assert "SECRET_KEY" not in result.content
        assert "ADMIN_PASSWORD" not in result.content
