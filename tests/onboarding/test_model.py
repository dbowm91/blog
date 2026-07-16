from __future__ import annotations

from app.onboarding.model import OnboardingInput, build_config_from_input


class TestBuildConfigFromInput:
    def test_native_development(self):
        inp = OnboardingInput(mode="native", profile="development")
        config = build_config_from_input(inp)

        assert config.server.host == "127.0.0.1"
        assert config.server.debug is True
        assert config.flask_env == ""
        assert config.session_cookie_secure is False

    def test_docker_production(self):
        inp = OnboardingInput(mode="docker", profile="docker-production")
        config = build_config_from_input(inp)

        assert config.server.host == "0.0.0.0"
        assert config.server.debug is False
        assert config.flask_env == "production"
        assert config.session_cookie_secure is True
        assert config.database.uri == "sqlite:///data/blog.db"

    def test_native_production(self):
        inp = OnboardingInput(mode="native", profile="native-production")
        config = build_config_from_input(inp)

        assert config.server.host == "127.0.0.1"
        assert config.server.debug is False
        assert config.flask_env == "production"
        assert config.session_cookie_secure is True

    def test_behind_reverse_proxy_sets_proxy_count_2(self):
        inp = OnboardingInput(mode="native", profile="development", behind_reverse_proxy=True)
        config = build_config_from_input(inp)

        assert config.proxy_count == 2

    def test_not_behind_reverse_proxy_sets_proxy_count_1(self):
        inp = OnboardingInput(mode="native", profile="development", behind_reverse_proxy=False)
        config = build_config_from_input(inp)

        assert config.proxy_count == 1

    def test_redis_enabled_populates_urls(self):
        inp = OnboardingInput(mode="native", profile="development", enable_redis=True)
        config = build_config_from_input(inp)

        assert config.redis.cache_url == "redis://localhost:6379/0"
        assert config.redis.rate_limit_url == "redis://localhost:6379/0"
        assert config.celery.broker_url == "redis://localhost:6379/0"

    def test_redis_disabled_empty_urls(self):
        inp = OnboardingInput(mode="native", profile="development", enable_redis=False)
        config = build_config_from_input(inp)

        assert config.redis.cache_url == ""
        assert config.redis.rate_limit_url == ""
        assert config.celery.broker_url == ""

    def test_newsletter_disabled_email_defaults(self):
        inp = OnboardingInput(
            mode="native",
            profile="development",
            enable_newsletter=False,
            smtp_host="",
        )
        config = build_config_from_input(inp)

        assert config.email.smtp_host == ""
        assert config.email.smtp_port == 587
        assert config.email.from_address == "blog@example.com"

    def test_newsletter_enabled_email_config(self):
        inp = OnboardingInput(
            mode="native",
            profile="development",
            enable_newsletter=True,
            smtp_host="smtp.example.com",
            smtp_port=465,
            smtp_user="user",
            smtp_password="pass",
            from_address="blog@example.com",
        )
        config = build_config_from_input(inp)

        assert config.email.smtp_host == "smtp.example.com"
        assert config.email.smtp_port == 465
        assert config.email.smtp_user == "user"

    def test_scheduler_enabled(self):
        inp = OnboardingInput(mode="native", profile="development", enable_scheduler=True)
        config = build_config_from_input(inp)

        assert config.scheduler.enabled is True

    def test_scheduler_disabled(self):
        inp = OnboardingInput(mode="native", profile="development", enable_scheduler=False)
        config = build_config_from_input(inp)

        assert config.scheduler.enabled is False

    def test_theme_settings(self):
        inp = OnboardingInput(
            mode="native",
            profile="development",
            theme_dark="Dracula",
            theme_light="Catppuccin Latte",
            theme_scheme="dark",
        )
        config = build_config_from_input(inp)

        assert config.themes.default_dark == "Dracula"
        assert config.themes.default_light == "Catppuccin Latte"
        assert config.themes.default_scheme == "dark"

    def test_storage_backend(self):
        inp = OnboardingInput(mode="native", profile="development", storage_backend="s3")
        config = build_config_from_input(inp)

        assert config.storage.backend == "s3"

    def test_backup_dir(self):
        inp = OnboardingInput(mode="native", profile="development", backup_dir="/backups")
        config = build_config_from_input(inp)

        assert config.backup.data_backup_dir == "/backups"

    def test_admin_username(self):
        inp = OnboardingInput(mode="native", profile="development", admin_username="superadmin")
        config = build_config_from_input(inp)

        assert config.admin.username == "superadmin"

    def test_site_title_and_description(self):
        inp = OnboardingInput(
            mode="native",
            profile="development",
            site_title="My Blog",
            site_description="Thoughts on code",
        )
        config = build_config_from_input(inp)

        assert config.app.title == "My Blog"
        assert config.app.description == "Thoughts on code"

    def test_base_url(self):
        inp = OnboardingInput(
            mode="native",
            profile="development",
            base_url="https://blog.example.com",
        )
        config = build_config_from_input(inp)

        assert config.site.base_url == "https://blog.example.com"
        assert config.session_cookie_secure is True

    def test_docker_mode_db_uri(self):
        inp = OnboardingInput(mode="docker", profile="development")
        config = build_config_from_input(inp)

        assert config.database.uri == "sqlite:///data/blog.db"

    def test_native_mode_db_uri(self):
        inp = OnboardingInput(mode="native", profile="development")
        config = build_config_from_input(inp)

        assert "sqlite:///" in config.database.uri
        assert "blog.db" in config.database.uri


class TestOnboardingInputDefaults:
    def test_mode_defaults_to_native(self):
        inp = OnboardingInput()
        assert inp.mode == "native"

    def test_profile_defaults_to_development(self):
        inp = OnboardingInput()
        assert inp.profile == "development"

    def test_site_title_defaults(self):
        inp = OnboardingInput()
        assert inp.site_title == "DevLog"

    def test_base_url_defaults_to_localhost(self):
        inp = OnboardingInput()
        assert inp.base_url == "http://localhost:5000"

    def test_bind_port_defaults(self):
        inp = OnboardingInput()
        assert inp.bind_port == 5000

    def test_enable_newsletter_defaults_false(self):
        inp = OnboardingInput()
        assert inp.enable_newsletter is False

    def test_enable_redis_defaults_false(self):
        inp = OnboardingInput()
        assert inp.enable_redis is False

    def test_enable_scheduler_defaults_false(self):
        inp = OnboardingInput()
        assert inp.enable_scheduler is False

    def test_storage_backend_defaults_local(self):
        inp = OnboardingInput()
        assert inp.storage_backend == "local"

    def test_theme_dark_default(self):
        inp = OnboardingInput()
        assert inp.theme_dark == "Catppuccin Mocha"

    def test_theme_light_default(self):
        inp = OnboardingInput()
        assert inp.theme_light == "Catppuccin Latte"

    def test_theme_scheme_default(self):
        inp = OnboardingInput()
        assert inp.theme_scheme == "system"

    def test_dry_run_defaults_false(self):
        inp = OnboardingInput()
        assert inp.dry_run is False

    def test_non_interactive_defaults_false(self):
        inp = OnboardingInput()
        assert inp.non_interactive is False

    def test_admin_password_default_empty(self):
        inp = OnboardingInput()
        assert inp.admin_password == ""
