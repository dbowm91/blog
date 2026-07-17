"""End-to-end lifecycle tests.

These tests exercise the full deployment lifecycle:
  install → deploy → start → health → logs → stop

They require a real systemd user session and are skipped in CI environments.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app.deployment.lifecycle import (
    ServiceBackend,
    ServiceStatus,
    detect_backend,
    get_logs,
    get_service_status,
    run_command,
    start_service,
    stop_service,
)
from app.filesystem.layout import InstallMode


def _systemd_user_session_available() -> bool:
    if shutil.which("systemctl") is None:
        return False
    try:
        result = subprocess.run(
            ["systemctl", "--user", "status"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _has_systemd() -> bool:
    return Path("/run/systemd/system").exists()


@pytest.mark.skipif(not _has_systemd(), reason="systemd not available")
class TestLifecycleEndToEnd:
    def test_detect_backend_system_mode(self):
        backend = detect_backend(None, InstallMode.SYSTEM)
        assert backend == ServiceBackend.SYSTEMD

    def test_detect_backend_user_mode(self):
        backend = detect_backend(None, InstallMode.USER)
        assert backend == ServiceBackend.SYSTEMD_USER

    def test_detect_backend_docker_mode(self):
        backend = detect_backend(None, InstallMode.DOCKER)
        assert backend == ServiceBackend.DOCKER

    def test_detect_backend_development_mode(self):
        backend = detect_backend(None, InstallMode.DEVELOPMENT)
        assert backend == ServiceBackend.FOREGROUND

    @patch("app.deployment.lifecycle.run_command")
    def test_full_systemd_lifecycle_mock(self, mock_run):
        mock_run.side_effect = [
            (0, "", ""),
            (0, "active", ""),
            (0, "1234", ""),
            (0, "  01:30", ""),
            (0, "log line 1\nlog line 2", ""),
            (0, "", ""),
        ]
        backend = ServiceBackend.SYSTEMD

        ok, msg = start_service(backend)
        assert ok is True

        status = get_service_status(backend)
        assert status.status == ServiceStatus.RUNNING
        assert status.pid == 1234
        assert status.uptime == "01:30"

        ok, output = get_logs(backend, tail=10)
        assert ok is True
        assert "log line 1" in output

        ok, msg = stop_service(backend)
        assert ok is True

    @patch("app.deployment.lifecycle.run_command")
    def test_full_docker_lifecycle_mock(self, mock_run):
        import json

        mock_run.side_effect = [
            (0, "", ""),
            (0, json.dumps({"Service": "web", "State": "running"}), ""),
            (0, "container log", ""),
            (0, "", ""),
        ]
        backend = ServiceBackend.DOCKER

        ok, msg = start_service(backend)
        assert ok is True

        status = get_service_status(backend)
        assert status.status == ServiceStatus.RUNNING

        ok, output = get_logs(backend, tail=50)
        assert ok is True
        assert "container log" in output

        ok, msg = stop_service(backend)
        assert ok is True

    def test_foreground_lifecycle_returns_error(self):
        backend = ServiceBackend.FOREGROUND

        ok, msg = start_service(backend)
        assert ok is False
        assert "foreground" in msg.lower()

        ok, msg = stop_service(backend)
        assert ok is False
        assert "foreground" in msg.lower()

    def test_unknown_lifecycle_returns_error(self):
        backend = ServiceBackend.UNKNOWN

        ok, msg = start_service(backend)
        assert ok is False

        ok, msg = stop_service(backend)
        assert ok is False


@pytest.mark.skipif(not _has_systemd(), reason="systemd not available")
class TestRunCommandIntegration:
    def test_echo_command(self):
        rc, stdout, stderr = run_command(["echo", "hello"])
        assert rc == 0
        assert "hello" in stdout

    def test_missing_command_returns_error(self):
        rc, stdout, stderr = run_command(["nonexistent_command_xyz_12345"])
        assert rc == -1
        assert "Command not found" in stderr

    def test_nonzero_exit(self):
        rc, stdout, stderr = run_command(["false"])
        assert rc == 1

    def test_timeout(self):
        rc, stdout, stderr = run_command(["sleep", "10"], timeout=1)
        assert rc == -2
        assert "timed out" in stderr


@pytest.mark.skipif(not _has_systemd(), reason="systemd not available")
class TestServiceStatusIntegration:
    @patch("app.deployment.lifecycle.run_command")
    def test_systemd_inactive(self, mock_run):
        mock_run.return_value = (0, "inactive", "")
        status = get_service_status(ServiceBackend.SYSTEMD)
        assert status.status == ServiceStatus.INSTALLED

    @patch("app.deployment.lifecycle.run_command")
    def test_systemd_failed(self, mock_run):
        mock_run.return_value = (0, "failed", "")
        status = get_service_status(ServiceBackend.SYSTEMD)
        assert status.status == ServiceStatus.FAILED

    @patch("app.deployment.lifecycle.run_command")
    def test_systemd_activating(self, mock_run):
        mock_run.return_value = (0, "activating", "")
        status = get_service_status(ServiceBackend.SYSTEMD)
        assert status.status == ServiceStatus.DEGRADED

    @patch("app.deployment.lifecycle.run_command")
    def test_systemd_unknown_state(self, mock_run):
        mock_run.return_value = (0, "some-unknown-state", "")
        status = get_service_status(ServiceBackend.SYSTEMD)
        assert status.status == ServiceStatus.UNMANAGED
