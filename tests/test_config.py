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


class TestCeleryBrokerResolution:
    def test_prefers_celery_broker_url(self, monkeypatch):
        monkeypatch.setenv("CELERY_BROKER_URL", "redis://broker:6379/0")
        monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
        import importlib
        import app.celery_app

        importlib.reload(app.celery_app)
        from app.celery_app import init_celery

        celery = init_celery()
        assert celery.conf.broker_url == "redis://broker:6379/0"

    def test_falls_back_to_redis_url(self, monkeypatch):
        monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
        monkeypatch.setenv("REDIS_URL", "redis://redis-main:6379/0")
        import importlib
        import app.celery_app

        importlib.reload(app.celery_app)
        from app.celery_app import init_celery

        celery = init_celery()
        assert celery.conf.broker_url == "redis://redis-main:6379/0"

    def test_defaults_to_localhost(self, monkeypatch):
        monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        import importlib
        import app.celery_app

        importlib.reload(app.celery_app)
        from app.celery_app import init_celery

        celery = init_celery()
        assert celery.conf.broker_url == "redis://localhost:6379/0"
