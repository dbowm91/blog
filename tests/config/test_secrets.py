from __future__ import annotations

from app.config.model import DevLogConfig
from app.config.secrets import is_secret_field, redact_config, redact_value


class TestIsSecretField:
    def test_secret_key(self) -> None:
        assert is_secret_field("secret_key") is True

    def test_admin_password(self) -> None:
        assert is_secret_field("admin_password") is True

    def test_smtp_password(self) -> None:
        assert is_secret_field("smtp_password") is True

    def test_smtp_user(self) -> None:
        assert is_secret_field("smtp_user") is True

    def test_health_check_secret(self) -> None:
        assert is_secret_field("health_check_secret") is True

    def test_metrics_secret(self) -> None:
        assert is_secret_field("metrics_secret") is True

    def test_webhook_encryption_key(self) -> None:
        assert is_secret_field("webhook_encryption_key") is True

    def test_non_secret_field(self) -> None:
        assert is_secret_field("app.title") is False

    def test_dotted_path_with_secret(self) -> None:
        assert is_secret_field("email.smtp_password") is True

    def test_dotted_path_no_secret(self) -> None:
        assert is_secret_field("server.port") is False

    def test_empty_string(self) -> None:
        assert is_secret_field("") is False


class TestRedactValue:
    def test_empty_string(self) -> None:
        assert redact_value("") == ""

    def test_short_value(self) -> None:
        assert redact_value("abc") == "****"

    def test_exactly_four_chars(self) -> None:
        assert redact_value("abcd") == "****"

    def test_long_value(self) -> None:
        result = redact_value("supersecretvalue")
        assert result.startswith("su")
        assert result.endswith("ue")
        assert "*" in result
        assert len(result) == len("supersecretvalue")

    def test_preserves_length(self) -> None:
        value = "abcdefghijklmnopqrstuvwxyz"
        result = redact_value(value)
        assert len(result) == len(value)

    def test_first_two_and_last_two_preserved(self) -> None:
        value = "abcdefghij"
        result = redact_value(value)
        assert result[:2] == "ab"
        assert result[-2:] == "ij"


class TestRedactConfig:
    def test_all_secret_fields_redacted(self) -> None:
        config = DevLogConfig(
            secret_key="my-secret-key-12345678",
            admin_password="my-admin-password",
        )
        result = redact_config(config)
        assert "secret_key" in result
        assert "admin_password" in result
        assert result["secret_key"] != "my-secret-key-12345678"
        assert result["admin_password"] != "my-admin-password"

    def test_non_secret_fields_not_in_result(self) -> None:
        config = DevLogConfig()
        result = redact_config(config)
        assert "app" not in result
        assert "server" not in result

    def test_empty_secrets_stay_empty(self) -> None:
        config = DevLogConfig()
        result = redact_config(config)
        assert result["secret_key"] == ""
        assert result["admin_password"] == ""

    def test_nested_secret_fields(self) -> None:
        config = DevLogConfig(
            email=__import__("app.config.model", fromlist=["EmailConfig"]).EmailConfig(
                smtp_user="user@example.com",
                smtp_password="pass123",
            ),
        )
        result = redact_config(config)
        assert "email.smtp_user" in result
        assert "email.smtp_password" in result
        assert result["email.smtp_user"] != "user@example.com"

    def test_webhook_encryption_key_is_redacted(self) -> None:
        from app.config.model import WebhookConfig

        config = DevLogConfig(
            webhook=WebhookConfig(encryption_key="key1234567890"),
        )
        result = redact_config(config)
        assert "webhook.encryption_key" in result
        assert result["webhook.encryption_key"] != "key1234567890"

    def test_top_level_webhook_encryption_key_not_in_dataclass(self) -> None:
        from app.config.model import WebhookConfig

        config = DevLogConfig(
            webhook=WebhookConfig(encryption_key="key1234567890"),
        )
        result = redact_config(config)
        assert all("webhook_encryption_key" not in k for k in result.keys())
