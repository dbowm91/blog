from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

from devlog_cli.main import main

_TEST_ENV = {
    "SECRET_KEY": "test-secret-key-for-cli-testing-1234567890",
    "ADMIN_PASSWORD": "test-admin-password-1234567890",
}


@pytest.fixture
def runner():
    return CliRunner(env=_TEST_ENV)


def _write_config(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _minimal_toml() -> str:
    return textwrap.dedent("""\
        config_version = 1

        [app]
        title = "Test Blog"
        description = "A test blog"
        posts_per_page = 10
        max_viewed_posts = 100
        session_lifetime_hours = 24
        session_ip_binding = "warn"
        tag_cache_ttl_seconds = 60
        dashboard_per_page = 20
        subscribers_per_page = 50
        media_per_page = 50
        media_max_files = 1000
        max_upload_size = 10485760
        export_batch_size = 500
        fts_result_limit = 100
        page_view_buffer_size = 0
        token_enumeration_delay = 0.1
        login_failure_delay = 0.1
        preview_token_expiry_days = 7
        analytics_days_min = 7
        analytics_days_max = 365

        [admin]
        username = "admin"

        [server]
        host = "0.0.0.0"
        port = 5000
        debug = false

        [author]
        name = ""
        role = ""
        avatar = ""

        [site]
        base_url = "http://localhost:5000"
        cdn_url = ""
        related_posts_count = 3

        [email]
        smtp_host = ""
        smtp_port = 587
        smtp_user = ""
        smtp_password = ""
        from_address = "blog@example.com"
        smtp_timeout = 30

        [newsletter]
        send_time = "08:00"
        confirmation_expiry_hours = 1
        max_retry_attempts = 5

        [comments]
        min_length = 3
        max_length = 5000
        rate_limit_per_ip = "5 per minute"
        rate_limit_per_post = "3 per minute"
        notify_pending = false
        spam_words = ""

        [themes]
        external_dir = ""
        allow_external = true
        strict_validation = false
        default_dark = "Catppuccin Mocha"
        default_light = "Catppuccin Latte"
        default_scheme = "system"

        [database]
        uri = ""
        pool_size = 10
        max_overflow = 20
        pool_recycle = 3600

        [redis]
        url = "redis://localhost:6379/0"
        cache_url = ""
        rate_limit_url = ""

        [celery]
        broker_url = ""

        [scheduler]
        enabled = false

        [storage]
        backend = "local"
        s3_bucket = ""
        s3_region = ""
        s3_access_key = ""
        s3_secret_key = ""
        s3_endpoint = ""
        s3_public_url = ""

        [health]
        check_secret = ""

        [metrics]
        enabled = false
        secret = ""

        [backup]
        data_backup_dir = "backups"
        encryption_key = ""

        [security]
        max_failed_attempts = 5
        lockout_duration_minutes = 15

        [webhook]
        timeout = 10
        encryption_key = ""

        [logging]
        level = "INFO"

        [search]
        provider = "sqlite"
    """)


class TestConfigCheck:
    def test_check_ok(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        result = runner.invoke(
            main,
            ["config", "check", "--config", str(config_file), "--no-filesystem"],
        )
        assert result.exit_code == 0

    def test_check_json_output(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        result = runner.invoke(
            main,
            ["--json", "config", "check", "--config", str(config_file), "--no-filesystem"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["code"] in ("config.check.ok", "config.check.warnings")
        assert "findings" in data["details"]

    def test_check_production_elevates_warnings(self, runner, tmp_path):
        toml = (
            _minimal_toml()
            .replace("debug = false", "debug = true")
            .replace(
                'base_url = "http://localhost:5000"',
                'base_url = "https://example.com"',
            )
        )
        config_file = _write_config(tmp_path / "config.toml", toml)
        result = runner.invoke(
            main,
            ["config", "check", "--config", str(config_file), "--production"],
            env={"FLASK_ENV": "production"},
        )
        assert result.exit_code != 0

    def test_check_no_filesystem(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        result = runner.invoke(
            main,
            ["config", "check", "--config", str(config_file), "--no-filesystem"],
        )
        assert result.exit_code == 0

    def test_check_missing_secret_key(self, runner, tmp_path):
        toml = _minimal_toml()
        config_file = _write_config(tmp_path / "config.toml", toml)
        result = runner.invoke(
            main,
            ["config", "check", "--config", str(config_file)],
            env={"SECRET_KEY": "", "ADMIN_PASSWORD": "test-password-123"},
        )
        assert result.exit_code != 0

    def test_check_json_failure(self, runner, tmp_path):
        toml = _minimal_toml()
        config_file = _write_config(tmp_path / "config.toml", toml)
        result = runner.invoke(
            main,
            ["--json", "config", "check", "--config", str(config_file)],
            env={"SECRET_KEY": "", "ADMIN_PASSWORD": "test-password-123"},
        )
        data = json.loads(result.output)
        assert data["ok"] is False
        assert data["code"] == "config.check.failed"
        assert len(data["details"]["findings"]) > 0


class TestConfigShow:
    def test_show_redacts_secrets(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        env_file = _write_config(
            tmp_path / ".env",
            "SECRET_KEY=my-super-secret-key-123456789012\n"
            "ADMIN_PASSWORD=my-admin-password-1234567890\n",
        )
        result = runner.invoke(
            main,
            [
                "--config",
                str(config_file),
                "--env-file",
                str(env_file),
                "config",
                "show",
            ],
        )
        assert result.exit_code == 0
        assert "my-super-secret-key" not in result.output
        assert "my-admin-password" not in result.output

    def test_show_json_output(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        result = runner.invoke(
            main,
            ["--config", str(config_file), "--json", "config", "show"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["code"] == "config.show"
        assert "details" in data

    def test_show_effective(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        result = runner.invoke(
            main,
            ["--config", str(config_file), "config", "show", "--effective"],
        )
        assert result.exit_code == 0

    def test_show_json_effective(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        result = runner.invoke(
            main,
            ["--config", str(config_file), "--json", "config", "show", "--effective"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["code"] == "config.show.effective"


class TestConfigExplain:
    def test_explain_valid_field(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        result = runner.invoke(
            main,
            ["--config", str(config_file), "config", "explain", "email.smtp_host"],
        )
        assert result.exit_code == 0
        assert "email.smtp_host" in result.output

    def test_explain_json_output(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        result = runner.invoke(
            main,
            ["--config", str(config_file), "--json", "config", "explain", "server.debug"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["code"] == "config.explain"
        assert data["details"]["type"] == "bool"
        assert data["details"]["default"] is False

    def test_explain_secret_field_redacted(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        env_file = _write_config(
            tmp_path / ".env",
            "SECRET_KEY=my-super-secret-key-123456789012\n",
        )
        result = runner.invoke(
            main,
            [
                "--config",
                str(config_file),
                "--env-file",
                str(env_file),
                "config",
                "explain",
                "email.smtp_password",
            ],
        )
        assert result.exit_code == 0
        assert "my-super-secret-key" not in result.output

    def test_explain_invalid_field_path(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        result = runner.invoke(
            main,
            ["--config", str(config_file), "config", "explain", "invalid"],
        )
        assert result.exit_code != 0

    def test_explain_unknown_field(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        result = runner.invoke(
            main,
            ["--config", str(config_file), "config", "explain", "nonexistent.field"],
        )
        assert result.exit_code != 0


class TestConfigPaths:
    def test_paths_shows_config(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        result = runner.invoke(
            main,
            ["--config", str(config_file), "config", "paths"],
        )
        assert result.exit_code == 0
        assert str(config_file) in result.output

    def test_paths_json_output(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        result = runner.invoke(
            main,
            ["--config", str(config_file), "--json", "config", "paths"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["code"] == "config.paths"
        assert "config_file" in data["details"]
        assert "env_file" in data["details"]
        assert data["details"]["config_file"]["selected"] == str(config_file)

    def test_paths_no_config_found(self, runner, tmp_path):
        result = runner.invoke(
            main,
            ["config", "paths"],
        )
        assert result.exit_code == 0

    def test_paths_with_env_file(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        env_file = _write_config(tmp_path / ".env", "SECRET_KEY=test\n")
        result = runner.invoke(
            main,
            [
                "--config",
                str(config_file),
                "--env-file",
                str(env_file),
                "config",
                "paths",
            ],
        )
        assert result.exit_code == 0
        assert str(env_file) in result.output


class TestConfigInit:
    def test_init_creates_config(self, runner, tmp_path):
        output = tmp_path / "config.toml"
        result = runner.invoke(
            main,
            ["config", "init", "--profile", "development", "--output", str(output)],
        )
        assert result.exit_code == 0
        assert output.exists()
        content = output.read_text()
        assert "config_version" in content
        assert "[server]" in content

    def test_init_json_output(self, runner, tmp_path):
        output = tmp_path / "config.toml"
        result = runner.invoke(
            main,
            ["--json", "config", "init", "--profile", "development", "--output", str(output)],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["code"] == "config.init.ok"
        assert data["details"]["profile"] == "development"

    def test_init_refuses_overwrite_without_force(self, runner, tmp_path):
        output = tmp_path / "config.toml"
        output.write_text("existing content")
        result = runner.invoke(
            main,
            ["config", "init", "--profile", "development", "--output", str(output)],
        )
        assert result.exit_code != 0
        assert output.read_text() == "existing content"

    def test_init_force_overwrites_with_backup(self, runner, tmp_path):
        output = tmp_path / "config.toml"
        output.write_text("existing content")
        result = runner.invoke(
            main,
            ["config", "init", "--profile", "development", "--output", str(output), "--force"],
        )
        assert result.exit_code == 0
        assert output.read_text() != "existing content"
        backups = list(tmp_path.glob("config.toml.backup.*"))
        assert len(backups) == 1
        assert backups[0].read_text() == "existing content"

    def test_init_all_profiles(self, runner, tmp_path):
        for profile in ["development", "native-production", "docker-production", "minimal", "full"]:
            output = tmp_path / f"{profile}.toml"
            result = runner.invoke(
                main,
                ["config", "init", "--profile", profile, "--output", str(output)],
            )
            assert result.exit_code == 0, f"Profile {profile} failed"
            assert output.exists()

    def test_init_invalid_profile(self, runner, tmp_path):
        result = runner.invoke(
            main,
            ["config", "init", "--profile", "nonexistent"],
        )
        assert result.exit_code != 0


class TestConfigMigrate:
    def test_migrate_dry_run(self, runner, tmp_path):
        toml = _minimal_toml().replace("config_version = 1", "# no version")
        config_file = _write_config(tmp_path / "config.toml", toml)
        result = runner.invoke(
            main,
            ["config", "migrate", "--config", str(config_file), "--dry-run"],
        )
        assert result.exit_code == 0
        assert "dry_run" in result.output or "Migration plan" in result.output

    def test_migrate_dry_run_json(self, runner, tmp_path):
        toml = _minimal_toml().replace("config_version = 1", "# no version")
        config_file = _write_config(tmp_path / "config.toml", toml)
        result = runner.invoke(
            main,
            ["--json", "config", "migrate", "--config", str(config_file), "--dry-run"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["code"] == "config.migrate.dry_run"
        assert "needs_migration" in data["details"]

    def test_migrate_already_current(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        result = runner.invoke(
            main,
            ["config", "migrate", "--config", str(config_file)],
        )
        assert result.exit_code == 0
        assert "no migration needed" in result.output or "current" in result.output

    def test_migrate_no_config_specified(self, runner, tmp_path):
        result = runner.invoke(
            main,
            ["config", "migrate"],
        )
        assert result.exit_code != 0

    def test_migrate_config_not_found(self, runner, tmp_path):
        result = runner.invoke(
            main,
            ["config", "migrate", "--config", str(tmp_path / "nonexistent.toml")],
        )
        assert result.exit_code != 0


class TestConfigHelp:
    def test_config_help(self, runner):
        result = runner.invoke(main, ["config", "--help"])
        assert result.exit_code == 0
        assert "check" in result.output
        assert "show" in result.output
        assert "explain" in result.output
        assert "paths" in result.output
        assert "init" in result.output
        assert "migrate" in result.output

    def test_config_check_help(self, runner):
        result = runner.invoke(main, ["config", "check", "--help"])
        assert result.exit_code == 0
        assert "--production" in result.output
        assert "--json" in result.output
        assert "--no-filesystem" in result.output

    def test_config_show_help(self, runner):
        result = runner.invoke(main, ["config", "show", "--help"])
        assert result.exit_code == 0
        assert "--effective" in result.output
        assert "--json" in result.output

    def test_config_explain_help(self, runner):
        result = runner.invoke(main, ["config", "explain", "--help"])
        assert result.exit_code == 0
        assert "FIELD" in result.output

    def test_config_paths_help(self, runner):
        result = runner.invoke(main, ["config", "paths", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output

    def test_config_init_help(self, runner):
        result = runner.invoke(main, ["config", "init", "--help"])
        assert result.exit_code == 0
        assert "--profile" in result.output
        assert "--force" in result.output
        assert "--output" in result.output

    def test_config_migrate_help(self, runner):
        result = runner.invoke(main, ["config", "migrate", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.output
        assert "--config" in result.output


class TestConfigGlobalOptions:
    def test_json_flag_passthrough(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        result = runner.invoke(
            main,
            ["--json", "config", "check", "--config", str(config_file), "--no-filesystem"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "ok" in data

    def test_verbose_flag(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        result = runner.invoke(
            main,
            ["--verbose", "config", "check", "--config", str(config_file), "--no-filesystem"],
        )
        assert result.exit_code == 0

    def test_no_color_flag(self, runner, tmp_path):
        config_file = _write_config(tmp_path / "config.toml", _minimal_toml())
        result = runner.invoke(
            main,
            ["--no-color", "config", "check", "--config", str(config_file), "--no-filesystem"],
        )
        assert result.exit_code == 0
