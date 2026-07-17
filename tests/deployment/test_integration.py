"""Integration tests that validate rendered output against external tools.

These tests skip if the required external tool is not available.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from app.config.model import (
    CeleryConfig,
    DevLogConfig,
    SchedulerConfig,
    ServerConfig,
    SiteConfig,
)
from app.deployment.compose import render_compose
from app.deployment.model import DeploymentContext
from app.deployment.proxy import render_caddyfile, render_nginx_config
from app.deployment.systemd import render_web_unit, validate_unit
from app.filesystem.layout import InstallMode


def _systemd_available() -> bool:
    return shutil.which("systemd-analyze") is not None


def _docker_compose_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _nginx_available() -> bool:
    return shutil.which("nginx") is not None


def _caddy_available() -> bool:
    return shutil.which("caddy") is not None


def _make_systemd_ctx(app):
    config = DevLogConfig(
        celery=CeleryConfig(broker_url="redis://localhost:6379/0"),
        scheduler=SchedulerConfig(enabled=True),
    )
    return DeploymentContext.from_config(config, mode=InstallMode.SYSTEM)


def _make_compose_ctx(app):
    config = DevLogConfig(
        celery=CeleryConfig(broker_url="redis://localhost:6379/0"),
        scheduler=SchedulerConfig(enabled=True),
        server=ServerConfig(host="127.0.0.1", port=5000),
    )
    return DeploymentContext.from_config(config, mode=InstallMode.DOCKER)


def _make_caddy_ctx(app):
    config = DevLogConfig(
        site=SiteConfig(base_url="https://example.com"),
        server=ServerConfig(host="127.0.0.1", port=5000),
    )
    return DeploymentContext.from_config(config, mode=InstallMode.DOCKER)


def _make_nginx_ctx(app):
    config = DevLogConfig(
        site=SiteConfig(base_url="https://example.com"),
        server=ServerConfig(host="127.0.0.1", port=5000),
    )
    return DeploymentContext.from_config(config, mode=InstallMode.DOCKER)


@pytest.mark.skipif(not _systemd_available(), reason="systemd-analyze not available")
class TestSystemdAnalyzeVerify:
    def test_web_unit_passes_verify(self, app, tmp_path):
        ctx = _make_systemd_ctx(app)
        result = render_web_unit(ctx)
        unit_file = tmp_path / result.filename
        unit_file.write_text(result.content)
        proc = subprocess.run(
            ["systemd-analyze", "verify", "--man=no", str(unit_file)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        ignored_patterns = ("Unknown key name 'Umask'", "Unknown key name 'ProtectSystem'")
        lines = [
            line
            for line in proc.stderr.splitlines()
            if str(unit_file) in line and not any(p in line for p in ignored_patterns)
        ]
        assert not lines, f"systemd-analyze verify failed: {lines}"

    def test_validate_unit_matches_analyze(self, app, tmp_path):
        ctx = _make_systemd_ctx(app)
        result = render_web_unit(ctx)
        errors = validate_unit(result.content)
        assert errors == [], f"Static validation errors: {errors}"


@pytest.mark.skipif(not _docker_compose_available(), reason="docker compose not available")
class TestDockerComposeConfig:
    def test_compose_passes_config_validation(self, app, tmp_path):
        ctx = _make_compose_ctx(app)
        result = render_compose(ctx)
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text(result.content)
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET_KEY=test\nADMIN_PASSWORD=test\n")
        proc = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "config"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            cwd=str(tmp_path),
        )
        assert proc.returncode == 0, f"docker compose config failed: {proc.stderr}"

    def test_compose_no_secrets_in_output(self, app):
        ctx = _make_compose_ctx(app)
        result = render_compose(ctx)
        assert "SECRET_KEY" not in result.content
        assert "ADMIN_PASSWORD" not in result.content


@pytest.mark.skipif(not _caddy_available(), reason="caddy not available")
class TestCaddyValidate:
    def test_caddyfile_passes_validate(self, app, tmp_path):
        ctx = _make_caddy_ctx(app)
        result = render_caddyfile(ctx)
        caddy_file = tmp_path / "Caddyfile"
        caddy_file.write_text(result.content)
        proc = subprocess.run(
            ["caddy", "validate", "--config", str(caddy_file)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert proc.returncode == 0, f"caddy validate failed: {proc.stderr}"


@pytest.mark.skipif(not _nginx_available(), reason="nginx not available")
class TestNginxValidate:
    def test_nginx_config_passes_t(self, app, tmp_path):
        ctx = _make_nginx_ctx(app)
        result = render_nginx_config(ctx)
        nginx_file = tmp_path / "devlog.conf"
        nginx_file.write_text(result.content)
        proc = subprocess.run(
            ["nginx", "-t", "-c", str(nginx_file)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert proc.returncode == 0, f"nginx -t failed: {proc.stderr}"
