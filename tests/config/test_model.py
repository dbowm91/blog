from __future__ import annotations

import pytest

from app.config.model import (
    CONFIG_VERSION,
    SECRET_FIELDS,
    AppConfig,
    AdminConfig,
    AuthorConfig,
    BackupConfig,
    CeleryConfig,
    CommentsConfig,
    DatabaseConfig,
    DevLogConfig,
    EmailConfig,
    HealthConfig,
    LoggingConfig,
    MetricsConfig,
    NewsletterConfig,
    RedisConfig,
    SchedulerConfig,
    SearchConfig,
    SecurityConfig,
    ServerConfig,
    SiteConfig,
    StorageConfig,
    ThemesConfig,
    WebhookConfig,
)


class TestDevLogConfigDefaults:
    def test_version_matches_constant(self) -> None:
        assert DevLogConfig().version == CONFIG_VERSION

    def test_secret_key_default_is_empty(self) -> None:
        assert DevLogConfig().secret_key == ""

    def test_admin_password_default_is_empty(self) -> None:
        assert DevLogConfig().admin_password == ""

    def test_session_cookie_secure_default(self) -> None:
        assert DevLogConfig().session_cookie_secure is True

    def test_proxy_count_default(self) -> None:
        assert DevLogConfig().proxy_count == 1

    def test_flask_env_default(self) -> None:
        assert DevLogConfig().flask_env == ""

    def test_testing_default(self) -> None:
        assert DevLogConfig().testing is False

    def test_all_section_defaults_present(self) -> None:
        config = DevLogConfig()
        assert isinstance(config.app, AppConfig)
        assert isinstance(config.admin, AdminConfig)
        assert isinstance(config.server, ServerConfig)
        assert isinstance(config.author, AuthorConfig)
        assert isinstance(config.site, SiteConfig)
        assert isinstance(config.email, EmailConfig)
        assert isinstance(config.newsletter, NewsletterConfig)
        assert isinstance(config.comments, CommentsConfig)
        assert isinstance(config.themes, ThemesConfig)
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.redis, RedisConfig)
        assert isinstance(config.celery, CeleryConfig)
        assert isinstance(config.scheduler, SchedulerConfig)
        assert isinstance(config.storage, StorageConfig)
        assert isinstance(config.health, HealthConfig)
        assert isinstance(config.metrics, MetricsConfig)
        assert isinstance(config.backup, BackupConfig)
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.webhook, WebhookConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.search, SearchConfig)


class TestSectionDefaults:
    def test_app_defaults(self) -> None:
        app = AppConfig()
        assert app.title == "DevLog"
        assert app.description == "A place for thoughts on code"
        assert app.posts_per_page == 10
        assert app.max_viewed_posts == 100
        assert app.session_lifetime_hours == 24
        assert app.session_ip_binding == "warn"
        assert app.tag_cache_ttl_seconds == 60
        assert app.dashboard_per_page == 20
        assert app.subscribers_per_page == 50
        assert app.media_per_page == 50
        assert app.media_max_files == 1000
        assert app.max_upload_size == 10485760
        assert app.export_batch_size == 500
        assert app.fts_result_limit == 100
        assert app.page_view_buffer_size == 0
        assert app.token_enumeration_delay == 0.1
        assert app.login_failure_delay == 0.05
        assert app.preview_token_expiry_days == 7
        assert app.analytics_days_min == 7
        assert app.analytics_days_max == 365

    def test_server_defaults(self) -> None:
        server = ServerConfig()
        assert server.host == "0.0.0.0"
        assert server.port == 5000
        assert server.debug is False

    def test_site_defaults(self) -> None:
        site = SiteConfig()
        assert site.base_url == "http://localhost:5000"
        assert site.cdn_url == ""
        assert site.related_posts_count == 3

    def test_email_defaults(self) -> None:
        email = EmailConfig()
        assert email.smtp_host == ""
        assert email.smtp_port == 587
        assert email.smtp_user == ""
        assert email.smtp_password == ""
        assert email.from_address == "blog@example.com"
        assert email.smtp_timeout == 30

    def test_newsletter_defaults(self) -> None:
        nl = NewsletterConfig()
        assert nl.send_time == "08:00"
        assert nl.confirmation_expiry_hours == 1
        assert nl.max_retry_attempts == 5

    def test_comments_defaults(self) -> None:
        comments = CommentsConfig()
        assert comments.min_length == 3
        assert comments.max_length == 5000
        assert comments.rate_limit_per_ip == "5 per minute"
        assert comments.rate_limit_per_post == "3 per minute"
        assert comments.notify_pending is False
        assert comments.spam_words == ""

    def test_themes_defaults(self) -> None:
        themes = ThemesConfig()
        assert themes.external_dir == ""
        assert themes.allow_external is True
        assert themes.strict_validation is False
        assert themes.default_dark == "Catppuccin Mocha"
        assert themes.default_light == "Catppuccin Latte"
        assert themes.default_scheme == "system"

    def test_database_defaults(self) -> None:
        db = DatabaseConfig()
        assert db.uri == ""
        assert db.pool_size == 10
        assert db.max_overflow == 20
        assert db.pool_recycle == 3600

    def test_redis_defaults(self) -> None:
        redis = RedisConfig()
        assert redis.url == "redis://localhost:6379/0"
        assert redis.cache_url == ""
        assert redis.rate_limit_url == ""

    def test_storage_defaults(self) -> None:
        storage = StorageConfig()
        assert storage.backend == "local"
        assert storage.s3_bucket == ""
        assert storage.s3_region == ""
        assert storage.s3_access_key == ""
        assert storage.s3_secret_key == ""
        assert storage.s3_endpoint == ""
        assert storage.s3_public_url == ""

    def test_security_defaults(self) -> None:
        sec = SecurityConfig()
        assert sec.max_failed_attempts == 5
        assert sec.lockout_duration_minutes == 15

    def test_backup_defaults(self) -> None:
        backup = BackupConfig()
        assert backup.data_backup_dir == "backups"
        assert backup.encryption_key == ""

    def test_logging_defaults(self) -> None:
        log = LoggingConfig()
        assert log.level == "INFO"

    def test_search_defaults(self) -> None:
        search = SearchConfig()
        assert search.provider == "sqlite"
        assert search.config == {}

    def test_webhook_defaults(self) -> None:
        wh = WebhookConfig()
        assert wh.timeout == 10
        assert wh.encryption_key == ""

    def test_health_defaults(self) -> None:
        h = HealthConfig()
        assert h.check_secret == ""

    def test_metrics_defaults(self) -> None:
        m = MetricsConfig()
        assert m.enabled is False
        assert m.secret == ""

    def test_scheduler_defaults(self) -> None:
        s = SchedulerConfig()
        assert s.enabled is False

    def test_celery_defaults(self) -> None:
        c = CeleryConfig()
        assert c.broker_url == ""

    def test_author_defaults(self) -> None:
        a = AuthorConfig()
        assert a.name == ""
        assert a.role == ""
        assert a.avatar == ""

    def test_admin_defaults(self) -> None:
        a = AdminConfig()
        assert a.username == "admin"


class TestSecretFields:
    def test_contains_expected_fields(self) -> None:
        expected = {
            "secret_key",
            "admin_password",
            "smtp_password",
            "smtp_user",
            "health_check_secret",
            "metrics_secret",
            "webhook_encryption_key",
            "check_secret",
            "secret",
            "encryption_key",
            "s3_access_key",
            "s3_secret_key",
        }
        assert SECRET_FIELDS == expected

    def test_is_frozen(self) -> None:
        assert isinstance(SECRET_FIELDS, frozenset)


class TestIsProduction:
    def test_production_true(self) -> None:
        config = DevLogConfig(flask_env="production")
        assert config.is_production() is True

    def test_production_false_default(self) -> None:
        config = DevLogConfig()
        assert config.is_production() is False

    def test_production_false_development(self) -> None:
        config = DevLogConfig(flask_env="development")
        assert config.is_production() is False

    def test_production_false_empty_string(self) -> None:
        config = DevLogConfig(flask_env="")
        assert config.is_production() is False


class TestFrozenDataclasses:
    def test_devlog_config_frozen(self) -> None:
        config = DevLogConfig()
        with pytest.raises(AttributeError):
            config.secret_key = "new"  # type: ignore[misc]

    def test_app_config_frozen(self) -> None:
        app = AppConfig()
        with pytest.raises(AttributeError):
            app.title = "new"  # type: ignore[misc]

    def test_server_config_frozen(self) -> None:
        server = ServerConfig()
        with pytest.raises(AttributeError):
            server.port = 8080  # type: ignore[misc]

    def test_site_config_frozen(self) -> None:
        site = SiteConfig()
        with pytest.raises(AttributeError):
            site.base_url = "new"  # type: ignore[misc]

    def test_email_config_frozen(self) -> None:
        email = EmailConfig()
        with pytest.raises(AttributeError):
            email.smtp_host = "new"  # type: ignore[misc]

    def test_storage_config_frozen(self) -> None:
        storage = StorageConfig()
        with pytest.raises(AttributeError):
            storage.backend = "s3"  # type: ignore[misc]
