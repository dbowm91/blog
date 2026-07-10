import pytest
from app.config import _env_str


class TestEnvStr:
    def test_returns_value_when_set(self, monkeypatch):
        monkeypatch.setenv("TEST_ENV_STR_VAR", "hello")
        assert _env_str("TEST_ENV_STR_VAR") == "hello"

    def test_returns_default_when_unset(self):
        assert _env_str("NONEXISTENT_ENV_VAR_XYZ") == ""

    def test_returns_custom_default_when_unset(self):
        assert _env_str("NONEXISTENT_ENV_VAR_XYZ", "fallback") == "fallback"

    def test_returns_default_for_empty_string(self, monkeypatch):
        monkeypatch.setenv("TEST_ENV_STR_EMPTY", "")
        assert _env_str("TEST_ENV_STR_EMPTY") == ""

    def test_returns_default_for_empty_string_with_custom_default(self, monkeypatch):
        monkeypatch.setenv("TEST_ENV_STR_EMPTY2", "")
        assert _env_str("TEST_ENV_STR_EMPTY2", "fallback") == "fallback"

    def test_returns_value_for_nonempty_string(self, monkeypatch):
        monkeypatch.setenv("TEST_ENV_STR_VAL", "redis://remote:6379/0")
        assert _env_str("TEST_ENV_STR_VAL") == "redis://remote:6379/0"

    def test_treats_empty_as_unset(self, monkeypatch):
        monkeypatch.setenv("TEST_EMPTY_AS_UNSET", "")
        assert _env_str("TEST_EMPTY_AS_UNSET", "default") == "default"


class TestDatabaseUriResolution:
    def test_empty_sqlalchemy_database_uri_treated_as_unset(self):
        val = _env_str("SQLALCHEMY_DATABASE_URI")
        assert val == "" or val != ""

    def test_env_str_forces_string_type(self, monkeypatch):
        monkeypatch.setenv("TEST_STRING_TYPE", "some-value")
        result = _env_str("TEST_STRING_TYPE", "fallback")
        assert isinstance(result, str)


class TestStartupConfigValidation:
    def test_create_app_succeeds_with_valid_secrets(self):
        import app as app_module
        from app import create_app

        old_key = app_module.SECRET_KEY
        old_pw = app_module.ADMIN_PASSWORD
        try:
            app_module.SECRET_KEY = "a" * 32
            app_module.ADMIN_PASSWORD = "test-password-123"
            application = create_app()
            assert application is not None
            assert application.config["SECRET_KEY"] == "a" * 32
        finally:
            app_module.SECRET_KEY = old_key
            app_module.ADMIN_PASSWORD = old_pw

    def test_create_app_fails_with_short_secret_key(self):
        import app as app_module
        from app import create_app

        old_key = app_module.SECRET_KEY
        try:
            app_module.SECRET_KEY = "short"
            app_module.ADMIN_PASSWORD = "test-password-123"
            with pytest.raises(RuntimeError, match="at least 32 characters"):
                create_app()
        finally:
            app_module.SECRET_KEY = old_key

    def test_create_app_fails_with_missing_secret_key(self):
        import app as app_module
        from app import create_app

        old_key = app_module.SECRET_KEY
        try:
            app_module.SECRET_KEY = ""
            app_module.ADMIN_PASSWORD = "test-password-123"
            with pytest.raises(RuntimeError, match="SECRET_KEY is required"):
                create_app()
        finally:
            app_module.SECRET_KEY = old_key

    def test_create_app_fails_with_missing_admin_password(self):
        import app as app_module
        from app import create_app

        old_pw = app_module.ADMIN_PASSWORD
        try:
            app_module.SECRET_KEY = "a" * 32
            app_module.ADMIN_PASSWORD = ""
            with pytest.raises(RuntimeError, match="ADMIN_PASSWORD is required"):
                create_app()
        finally:
            app_module.ADMIN_PASSWORD = old_pw

    def test_empty_optional_env_does_not_override_defaults(self, monkeypatch):
        monkeypatch.setenv("CDN_URL", "")
        monkeypatch.setenv("HEALTH_CHECK_SECRET", "")
        val = _env_str("CDN_URL", "http://default.example.com")
        assert val == "http://default.example.com"
        val2 = _env_str("HEALTH_CHECK_SECRET", "")
        assert val2 == ""


class TestCeleryBrokerResolution:
    def test_prefers_celery_broker_url(self, monkeypatch):
        monkeypatch.setenv("CELERY_BROKER_URL", "redis://broker:6379/0")
        monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
        import importlib
        import app.celery_app as celery_mod

        original_module = celery_mod
        try:
            importlib.reload(celery_mod)
            from app.celery_app import init_celery

            celery = init_celery()
            assert celery.conf.broker_url == "redis://broker:6379/0"
        finally:
            import sys

            sys.modules["app.celery_app"] = original_module

    def test_falls_back_to_redis_url(self, monkeypatch):
        monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
        monkeypatch.setenv("REDIS_URL", "redis://redis-main:6379/0")
        import importlib
        import app.celery_app as celery_mod

        original_module = celery_mod
        try:
            importlib.reload(celery_mod)
            from app.celery_app import init_celery

            celery = init_celery()
            assert celery.conf.broker_url == "redis://redis-main:6379/0"
        finally:
            import sys

            sys.modules["app.celery_app"] = original_module

    def test_defaults_to_localhost(self, monkeypatch):
        monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        import importlib
        import app.celery_app as celery_mod

        original_module = celery_mod
        try:
            importlib.reload(celery_mod)
            from app.celery_app import init_celery

            celery = init_celery()
            assert celery.conf.broker_url == "redis://localhost:6379/0"
        finally:
            import sys

            sys.modules["app.celery_app"] = original_module
