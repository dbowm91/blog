"""The typed configuration model's own helpers.

The dataclasses in `app/config/model.py` are the canonical description of
every configuration field. Their environment readers and their redacting
`__repr__` decide what the application reads at start-up and what a log line
or a diagnostic dump is allowed to show, so both are worth pinning down.
"""

from __future__ import annotations

import pytest

from app.config.model import (
    BackupConfig,
    DevLogConfig,
    EmailConfig,
    HealthConfig,
    MetricsConfig,
    StorageConfig,
    WebhookConfig,
    _env_bool,
    _env_float,
    _env_int,
    _env_str,
    _redacted_repr,
    _safe_repr,
)

# Fixture values with no entropy of their own. They stand in for credentials
# without looking like one, so a secret scanner reads the file as a test and
# not as a leaked credential.
SMTP_PASSWORD = "x" * 8
ACCESS_KEY = "x" * 8
SECRET_KEY = "x" * 8
HEALTH_SECRET = "x" * 8
METRICS_SECRET = "x" * 8
BACKUP_KEY = "x" * 8
WEBHOOK_KEY = "x" * 8
TOP_SECRET = "x" * 8
ADMIN_PASSWORD = "x" * 8


class TestEnvironmentReaders:
    def test_env_str_reads_a_present_value(self, monkeypatch):
        monkeypatch.setenv("DEVLOG_TEST_STR", "value")

        assert _env_str("DEVLOG_TEST_STR") == "value"

    def test_env_str_treats_an_empty_value_as_unset(self, monkeypatch):
        monkeypatch.setenv("DEVLOG_TEST_STR", "")

        assert _env_str("DEVLOG_TEST_STR", "fallback") == "fallback"

    def test_env_str_falls_back_when_the_variable_is_absent(self, monkeypatch):
        monkeypatch.delenv("DEVLOG_TEST_STR", raising=False)

        assert _env_str("DEVLOG_TEST_STR", "fallback") == "fallback"

    @pytest.mark.parametrize("raw", ["true", "TRUE", "1", "yes", "Yes"])
    def test_env_bool_reads_a_true_value(self, monkeypatch, raw):
        monkeypatch.setenv("DEVLOG_TEST_BOOL", raw)

        assert _env_bool("DEVLOG_TEST_BOOL") is True

    @pytest.mark.parametrize("raw", ["false", "0", "no", "anything"])
    def test_env_bool_reads_a_false_value(self, monkeypatch, raw):
        monkeypatch.setenv("DEVLOG_TEST_BOOL", raw)

        assert _env_bool("DEVLOG_TEST_BOOL") is False

    def test_env_bool_falls_back_when_the_variable_is_absent(self, monkeypatch):
        monkeypatch.delenv("DEVLOG_TEST_BOOL", raising=False)

        assert _env_bool("DEVLOG_TEST_BOOL", True) is True

    def test_env_int_reads_an_integer(self, monkeypatch):
        monkeypatch.setenv("DEVLOG_TEST_INT", "42")

        assert _env_int("DEVLOG_TEST_INT") == 42

    def test_env_int_falls_back_for_a_value_that_is_not_a_number(self, monkeypatch):
        monkeypatch.setenv("DEVLOG_TEST_INT", "not-a-number")

        assert _env_int("DEVLOG_TEST_INT", 7) == 7

    def test_env_int_falls_back_when_the_variable_is_absent(self, monkeypatch):
        monkeypatch.delenv("DEVLOG_TEST_INT", raising=False)

        assert _env_int("DEVLOG_TEST_INT", 7) == 7

    def test_env_float_reads_a_float(self, monkeypatch):
        monkeypatch.setenv("DEVLOG_TEST_FLOAT", "1.5")

        assert _env_float("DEVLOG_TEST_FLOAT") == 1.5

    def test_env_float_falls_back_for_a_value_that_is_not_a_number(self, monkeypatch):
        monkeypatch.setenv("DEVLOG_TEST_FLOAT", "not-a-number")

        assert _env_float("DEVLOG_TEST_FLOAT", 2.5) == 2.5

    def test_env_float_falls_back_when_the_variable_is_absent(self, monkeypatch):
        monkeypatch.delenv("DEVLOG_TEST_FLOAT", raising=False)

        assert _env_float("DEVLOG_TEST_FLOAT", 2.5) == 2.5


class TestRedactedRepr:
    def test_an_empty_value_stays_empty(self):
        assert _redacted_repr("") == '""'

    def test_a_short_value_is_hidden_completely(self):
        assert _redacted_repr("abcd") == '"****"'

    def test_a_long_value_keeps_only_its_edges(self):
        assert _redacted_repr(SMTP_PASSWORD) == '"xx****xx"'


class TestSafeRepr:
    def test_a_secret_field_is_redacted(self):
        expected = "smtp_password=" + _redacted_repr(SMTP_PASSWORD)
        assert expected in repr(EmailConfig(smtp_password=SMTP_PASSWORD))

    def test_a_plain_string_is_escaped(self):
        rendered = repr(EmailConfig(from_address='a"b\\c'))

        assert 'from_address="a\\"b\\\\c"' in rendered

    def test_a_boolean_renders_as_a_boolean(self):
        assert "testing=False" in repr(DevLogConfig())

    def test_a_mapping_renders_as_a_mapping(self):
        from app.config.model import AppConfig

        rendered = repr(AppConfig())
        assert "AppConfig(" in rendered

    def test_it_redacts_the_fields_it_is_given(self):
        from dataclasses import dataclass

        @dataclass
        class _Sample:
            secret: str
            plain: str

        rendered = _safe_repr(_Sample(secret=SMTP_PASSWORD, plain="visible"), frozenset({"secret"}))

        assert "secret=" in rendered
        assert SMTP_PASSWORD not in rendered
        assert 'plain="visible"' in rendered

    def test_it_renders_a_non_string_value_with_its_repr(self):
        from dataclasses import dataclass

        @dataclass
        class _Sample:
            count: int

        assert "count=7" in _safe_repr(_Sample(count=7), frozenset())


class TestSectionReprs:
    def test_the_email_section_hides_its_password(self):
        assert SMTP_PASSWORD not in repr(EmailConfig(smtp_password=SMTP_PASSWORD))

    def test_the_storage_section_hides_its_keys(self):
        rendered = repr(StorageConfig(s3_access_key=ACCESS_KEY, s3_secret_key=SECRET_KEY))

        assert ACCESS_KEY not in rendered
        assert SECRET_KEY not in rendered

    def test_the_health_section_hides_its_secret(self):
        assert HEALTH_SECRET not in repr(HealthConfig(check_secret=HEALTH_SECRET))

    def test_the_metrics_section_hides_its_secret(self):
        assert METRICS_SECRET not in repr(MetricsConfig(secret=METRICS_SECRET))

    def test_the_backup_section_hides_its_key(self):
        assert BACKUP_KEY not in repr(BackupConfig(encryption_key=BACKUP_KEY))

    def test_the_webhook_section_hides_its_key(self):
        assert WEBHOOK_KEY not in repr(WebhookConfig(encryption_key=WEBHOOK_KEY))

    def test_the_top_level_section_hides_its_secrets(self):
        rendered = repr(
            DevLogConfig(
                secret_key=TOP_SECRET,
                admin_password=ADMIN_PASSWORD,
            )
        )

        assert TOP_SECRET not in rendered
        assert ADMIN_PASSWORD not in rendered

    def test_the_top_level_section_reports_production(self):
        assert DevLogConfig(flask_env="production").is_production() is True
        assert DevLogConfig(flask_env="development").is_production() is False
