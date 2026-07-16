from __future__ import annotations

import os
import stat

from app.onboarding.secrets import (
    generate_health_secret,
    generate_metrics_secret,
    generate_secret_key,
    read_env_file,
    resolve_secrets,
    write_env_file,
)


class TestGenerateSecretKey:
    def test_length_is_64_hex(self):
        key = generate_secret_key()

        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_unique_values(self):
        keys = {generate_secret_key() for _ in range(10)}

        assert len(keys) == 10


class TestGenerateHealthSecret:
    def test_length_is_urlsafe(self):
        secret = generate_health_secret()

        assert len(secret) > 0
        assert len(secret) <= 64

    def test_unique_values(self):
        secrets_set = {generate_health_secret() for _ in range(10)}

        assert len(secrets_set) == 10


class TestGenerateMetricsSecret:
    def test_length_is_urlsafe(self):
        secret = generate_metrics_secret()

        assert len(secret) > 0
        assert len(secret) <= 64

    def test_unique_values(self):
        secrets_set = {generate_metrics_secret() for _ in range(10)}

        assert len(secrets_set) == 10


class TestResolveSecretsFresh:
    def test_generates_new_secrets(self):
        inp = type(
            "Input",
            (),
            {
                "admin_password": "pw",
                "enable_newsletter": False,
                "smtp_host": "",
                "enable_backup_encryption": False,
                "storage_backend": "local",
            },
        )()
        result = resolve_secrets(inp)

        assert len(result["SECRET_KEY"]) == 64
        assert result["ADMIN_PASSWORD"] == "pw"
        assert "HEALTH_CHECK_SECRET" in result
        assert "METRICS_SECRET" in result

    def test_preserves_existing_secret_key(self):
        inp = type(
            "Input",
            (),
            {
                "admin_password": "pw",
                "enable_newsletter": False,
                "smtp_host": "",
                "enable_backup_encryption": False,
                "storage_backend": "local",
            },
        )()
        existing = {"SECRET_KEY": "my-existing-key"}
        result = resolve_secrets(inp, existing=existing)

        assert result["SECRET_KEY"] == "my-existing-key"

    def test_preserves_existing_admin_password(self):
        inp = type(
            "Input",
            (),
            {
                "admin_password": "",
                "enable_newsletter": False,
                "smtp_host": "",
                "enable_backup_encryption": False,
                "storage_backend": "local",
            },
        )()
        existing = {"ADMIN_PASSWORD": "existing-pw"}
        result = resolve_secrets(inp, existing=existing)

        assert result["ADMIN_PASSWORD"] == "existing-pw"

    def test_preserves_existing_health_secret(self):
        inp = type(
            "Input",
            (),
            {
                "admin_password": "pw",
                "enable_newsletter": False,
                "smtp_host": "",
                "enable_backup_encryption": False,
                "storage_backend": "local",
            },
        )()
        existing = {"HEALTH_CHECK_SECRET": "my-health-secret"}
        result = resolve_secrets(inp, existing=existing)

        assert result["HEALTH_CHECK_SECRET"] == "my-health-secret"

    def test_preserves_existing_metrics_secret(self):
        inp = type(
            "Input",
            (),
            {
                "admin_password": "pw",
                "enable_newsletter": False,
                "smtp_host": "",
                "enable_backup_encryption": False,
                "storage_backend": "local",
            },
        )()
        existing = {"METRICS_SECRET": "my-metrics-secret"}
        result = resolve_secrets(inp, existing=existing)

        assert result["METRICS_SECRET"] == "my-metrics-secret"

    def test_newsletter_adds_smtp_password(self):
        inp = type(
            "Input",
            (),
            {
                "admin_password": "pw",
                "enable_newsletter": True,
                "smtp_host": "smtp.example.com",
                "smtp_password": "smtp-pw",
                "enable_backup_encryption": False,
                "storage_backend": "local",
            },
        )()
        result = resolve_secrets(inp)

        assert "SMTP_PASSWORD" in result
        assert result["SMTP_PASSWORD"] == "smtp-pw"

    def test_backup_encryption_adds_key(self):
        inp = type(
            "Input",
            (),
            {
                "admin_password": "pw",
                "enable_newsletter": False,
                "smtp_host": "",
                "enable_backup_encryption": True,
                "storage_backend": "local",
            },
        )()
        result = resolve_secrets(inp)

        assert "BACKUP_ENCRYPTION_KEY" in result
        assert len(result["BACKUP_ENCRYPTION_KEY"]) == 64

    def test_s3_storage_adds_s3_keys(self):
        inp = type(
            "Input",
            (),
            {
                "admin_password": "pw",
                "enable_newsletter": False,
                "smtp_host": "",
                "enable_backup_encryption": False,
                "storage_backend": "s3",
                "s3_access_key": "ak",
                "s3_secret_key": "sk",
            },
        )()
        result = resolve_secrets(inp)

        assert result["S3_ACCESS_KEY"] == "ak"
        assert result["S3_SECRET_KEY"] == "sk"


class TestWriteEnvFile:
    def test_creates_file(self, tmp_path):
        env_path = tmp_path / ".env"
        secrets_dict = {"SECRET_KEY": "abc123", "ADMIN_PASSWORD": "pw"}

        write_env_file(env_path, secrets_dict)

        assert env_path.exists()

    def test_file_permissions(self, tmp_path):
        env_path = tmp_path / ".env"
        secrets_dict = {"SECRET_KEY": "abc123", "ADMIN_PASSWORD": "pw"}

        write_env_file(env_path, secrets_dict)

        mode = stat.S_IMODE(os.stat(env_path).st_mode)
        assert mode == 0o600

    def test_content_includes_secrets(self, tmp_path):
        env_path = tmp_path / ".env"
        secrets_dict = {"SECRET_KEY": "mykey", "ADMIN_PASSWORD": "mypass"}

        write_env_file(env_path, secrets_dict)

        content = env_path.read_text()
        assert "SECRET_KEY=mykey" in content
        assert "ADMIN_PASSWORD=mypass" in content

    def test_includes_health_secret_when_present(self, tmp_path):
        env_path = tmp_path / ".env"
        secrets_dict = {"SECRET_KEY": "k", "ADMIN_PASSWORD": "p", "HEALTH_CHECK_SECRET": "hs"}

        write_env_file(env_path, secrets_dict)

        content = env_path.read_text()
        assert "HEALTH_CHECK_SECRET=hs" in content

    def test_includes_metrics_secret_when_present(self, tmp_path):
        env_path = tmp_path / ".env"
        secrets_dict = {"SECRET_KEY": "k", "ADMIN_PASSWORD": "p", "METRICS_SECRET": "ms"}

        write_env_file(env_path, secrets_dict)

        content = env_path.read_text()
        assert "METRICS_SECRET=ms" in content

    def test_creates_parent_directories(self, tmp_path):
        env_path = tmp_path / "subdir" / ".env"
        secrets_dict = {"SECRET_KEY": "k", "ADMIN_PASSWORD": "p"}

        write_env_file(env_path, secrets_dict)

        assert env_path.exists()


class TestReadEnvFile:
    def test_roundtrip(self, tmp_path):
        env_path = tmp_path / ".env"
        secrets_dict = {
            "SECRET_KEY": "my-secret",
            "ADMIN_PASSWORD": "my-pass",
            "HEALTH_CHECK_SECRET": "hs123",
        }
        write_env_file(env_path, secrets_dict)
        result = read_env_file(env_path)

        assert result["SECRET_KEY"] == "my-secret"
        assert result["ADMIN_PASSWORD"] == "my-pass"
        assert result["HEALTH_CHECK_SECRET"] == "hs123"

    def test_missing_file_returns_empty(self, tmp_path):
        result = read_env_file(tmp_path / "noexist.env")

        assert result == {}

    def test_skips_comments(self, tmp_path):
        env_path = tmp_path / ".env"
        env_path.write_text("# comment\nSECRET_KEY=key\n# another\n")

        result = read_env_file(env_path)

        assert result == {"SECRET_KEY": "key"}

    def test_skips_blank_lines(self, tmp_path):
        env_path = tmp_path / ".env"
        env_path.write_text("\n\nSECRET_KEY=key\n\n\n")

        result = read_env_file(env_path)

        assert result == {"SECRET_KEY": "key"}

    def test_handles_quoted_values(self, tmp_path):
        env_path = tmp_path / ".env"
        env_path.write_text('SECRET_KEY="quoted-value"\n')

        result = read_env_file(env_path)

        assert result["SECRET_KEY"] == "quoted-value"

    def test_handles_single_quoted_values(self, tmp_path):
        env_path = tmp_path / ".env"
        env_path.write_text("SECRET_KEY='single-quoted'\n")

        result = read_env_file(env_path)

        assert result["SECRET_KEY"] == "single-quoted"

    def test_skips_lines_without_equals(self, tmp_path):
        env_path = tmp_path / ".env"
        env_path.write_text("INVALID_LINE\nSECRET_KEY=key\n")

        result = read_env_file(env_path)

        assert "INVALID_LINE" not in result
        assert result["SECRET_KEY"] == "key"
