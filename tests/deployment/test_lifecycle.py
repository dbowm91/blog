from __future__ import annotations

from unittest.mock import patch

from app.deployment.lifecycle import (
    ServiceBackend,
    ServiceStatus,
    detect_backend,
    get_service_status,
    get_logs,
    restart_service,
    run_command,
    start_service,
    stop_service,
)
from app.filesystem.layout import InstallationMetadata, InstallMode


class TestDetectBackend:
    def test_docker_mode(self):
        result = detect_backend(None, InstallMode.DOCKER)
        assert result == ServiceBackend.DOCKER

    def test_development_mode(self):
        result = detect_backend(None, InstallMode.DEVELOPMENT)
        assert result == ServiceBackend.FOREGROUND

    def test_system_mode(self):
        result = detect_backend(None, InstallMode.SYSTEM)
        assert result == ServiceBackend.SYSTEMD

    def test_user_mode(self):
        result = detect_backend(None, InstallMode.USER)
        assert result == ServiceBackend.SYSTEMD_USER

    def test_metadata_docker(self):
        meta = InstallationMetadata(mode=InstallMode.DOCKER, version="1.0.0")
        result = detect_backend(meta, InstallMode.DOCKER)
        assert result == ServiceBackend.DOCKER

    def test_metadata_system(self):
        meta = InstallationMetadata(mode=InstallMode.SYSTEM, version="1.0.0")
        result = detect_backend(meta, InstallMode.SYSTEM)
        assert result == ServiceBackend.SYSTEMD

    def test_metadata_user(self):
        meta = InstallationMetadata(mode=InstallMode.USER, version="1.0.0")
        result = detect_backend(meta, InstallMode.USER)
        assert result == ServiceBackend.SYSTEMD_USER

    def test_metadata_does_not_override_mode(self):
        meta = InstallationMetadata(mode=InstallMode.DOCKER, version="1.0.0")
        result = detect_backend(meta, InstallMode.SYSTEM)
        assert result == ServiceBackend.SYSTEMD

    def test_no_metadata_development(self):
        result = detect_backend(None, InstallMode.DEVELOPMENT)
        assert result == ServiceBackend.FOREGROUND


class TestRunCommand:
    def test_successful_command(self):
        rc, stdout, stderr = run_command(["echo", "hello"])
        assert rc == 0
        assert "hello" in stdout

    def test_missing_command(self):
        rc, stdout, stderr = run_command(["nonexistent_command_xyz"])
        assert rc == -1
        assert "Command not found" in stderr

    def test_timeout(self):
        rc, stdout, stderr = run_command(["sleep", "10"], timeout=1)
        assert rc == -2
        assert "timed out" in stderr

    def test_nonzero_exit(self):
        rc, stdout, stderr = run_command(["false"])
        assert rc == 1


class TestGetServiceStatus:
    @patch("app.deployment.lifecycle.run_command")
    def test_systemd_running(self, mock_run):
        mock_run.side_effect = [
            (0, "active", ""),
            (0, "1234", ""),
            (0, "  01:30", ""),
        ]
        status = get_service_status(ServiceBackend.SYSTEMD)
        assert status.status == ServiceStatus.RUNNING
        assert status.pid == 1234
        assert status.uptime == "01:30"

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

    @patch("app.deployment.lifecycle.run_command")
    def test_docker_running(self, mock_run):
        import json

        ps_output = json.dumps({"Service": "web", "State": "running"})
        mock_run.return_value = (0, ps_output, "")
        status = get_service_status(ServiceBackend.DOCKER)
        assert status.status == ServiceStatus.RUNNING

    @patch("app.deployment.lifecycle.run_command")
    def test_docker_failed(self, mock_run):
        import json

        ps_output = json.dumps({"Service": "web", "State": "exited"})
        mock_run.return_value = (0, ps_output, "")
        status = get_service_status(ServiceBackend.DOCKER)
        assert status.status == ServiceStatus.FAILED

    @patch("app.deployment.lifecycle.run_command")
    def test_docker_error(self, mock_run):
        mock_run.return_value = (1, "", "error")
        status = get_service_status(ServiceBackend.DOCKER)
        assert status.status == ServiceStatus.UNMANAGED

    def test_foreground(self):
        status = get_service_status(ServiceBackend.FOREGROUND)
        assert status.status == ServiceStatus.UNMANAGED
        assert "hint" in status.details

    def test_unknown_backend(self):
        status = get_service_status(ServiceBackend.UNKNOWN)
        assert status.status == ServiceStatus.UNMANAGED


class TestStartService:
    @patch("app.deployment.lifecycle.run_command")
    def test_systemd_success(self, mock_run):
        mock_run.return_value = (0, "", "")
        ok, msg = start_service(ServiceBackend.SYSTEMD)
        assert ok is True

    @patch("app.deployment.lifecycle.run_command")
    def test_systemd_failure(self, mock_run):
        mock_run.return_value = (1, "", "error")
        ok, msg = start_service(ServiceBackend.SYSTEMD)
        assert ok is False

    @patch("app.deployment.lifecycle.run_command")
    def test_docker_success(self, mock_run):
        mock_run.return_value = (0, "", "")
        ok, msg = start_service(ServiceBackend.DOCKER)
        assert ok is True

    def test_foreground(self):
        ok, msg = start_service(ServiceBackend.FOREGROUND)
        assert ok is False
        assert "foreground" in msg.lower()

    def test_unknown(self):
        ok, msg = start_service(ServiceBackend.UNKNOWN)
        assert ok is False


class TestStopService:
    @patch("app.deployment.lifecycle.run_command")
    def test_systemd_success(self, mock_run):
        mock_run.return_value = (0, "", "")
        ok, msg = stop_service(ServiceBackend.SYSTEMD)
        assert ok is True

    @patch("app.deployment.lifecycle.run_command")
    def test_docker_success(self, mock_run):
        mock_run.return_value = (0, "", "")
        ok, msg = stop_service(ServiceBackend.DOCKER)
        assert ok is True

    def test_foreground(self):
        ok, msg = stop_service(ServiceBackend.FOREGROUND)
        assert ok is False


class TestRestartService:
    @patch("app.deployment.lifecycle.run_command")
    def test_systemd_success(self, mock_run):
        mock_run.return_value = (0, "", "")
        ok, msg = restart_service(ServiceBackend.SYSTEMD)
        assert ok is True

    @patch("app.deployment.lifecycle.run_command")
    def test_docker_success(self, mock_run):
        mock_run.return_value = (0, "", "")
        ok, msg = restart_service(ServiceBackend.DOCKER)
        assert ok is True

    def test_foreground(self):
        ok, msg = restart_service(ServiceBackend.FOREGROUND)
        assert ok is False


class TestGetLogs:
    @patch("app.deployment.lifecycle.run_command")
    def test_systemd_logs(self, mock_run):
        mock_run.return_value = (0, "log line 1\nlog line 2", "")
        ok, output = get_logs(ServiceBackend.SYSTEMD, tail=10)
        assert ok is True
        assert "log line 1" in output

    @patch("app.deployment.lifecycle.run_command")
    def test_docker_logs(self, mock_run):
        mock_run.return_value = (0, "container log", "")
        ok, output = get_logs(ServiceBackend.DOCKER, tail=50)
        assert ok is True
        assert "container log" in output

    def test_foreground_logs(self):
        ok, output = get_logs(ServiceBackend.FOREGROUND)
        assert ok is False
        assert "foreground" in output.lower()

    @patch("app.deployment.lifecycle.run_command")
    def test_follow_mode(self, mock_run):
        mock_run.return_value = (0, "follow output", "")
        ok, output = get_logs(ServiceBackend.SYSTEMD, follow=True)
        assert ok is True

    @patch("app.deployment.lifecycle.run_command")
    def test_component_selection(self, mock_run):
        mock_run.return_value = (0, "scheduler logs", "")
        ok, output = get_logs(ServiceBackend.SYSTEMD, component="scheduler")
        assert ok is True
