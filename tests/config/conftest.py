from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Generator

import pytest


SAMPLE_TOML_DICT: dict = {
    "version": 1,
    "app": {
        "title": "Test Blog",
        "description": "A test blog",
        "posts_per_page": 10,
        "max_viewed_posts": 100,
        "session_lifetime_hours": 24,
        "session_ip_binding": "warn",
        "tag_cache_ttl_seconds": 60,
        "dashboard_per_page": 20,
        "subscribers_per_page": 50,
        "media_per_page": 50,
        "media_max_files": 1000,
        "max_upload_size": 10485760,
        "export_batch_size": 500,
        "fts_result_limit": 100,
        "page_view_buffer_size": 0,
        "token_enumeration_delay": 0.1,
        "login_failure_delay": 0.05,
        "preview_token_expiry_days": 7,
        "analytics_days_min": 7,
        "analytics_days_max": 365,
    },
    "admin": {"username": "admin"},
    "server": {"host": "0.0.0.0", "port": 5000, "debug": False},
    "author": {"name": "", "role": "", "avatar": ""},
    "site": {"base_url": "http://localhost:5000", "cdn_url": "", "related_posts_count": 3},
    "email": {
        "smtp_host": "",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_password": "",
        "from_address": "blog@example.com",
        "smtp_timeout": 30,
    },
    "newsletter": {
        "send_time": "08:00",
        "confirmation_expiry_hours": 1,
        "max_retry_attempts": 5,
    },
    "comments": {
        "min_length": 3,
        "max_length": 5000,
        "rate_limit_per_ip": "5 per minute",
        "rate_limit_per_post": "3 per minute",
        "notify_pending": False,
        "spam_words": "",
    },
    "themes": {
        "external_dir": "",
        "allow_external": True,
        "strict_validation": False,
        "default_dark": "Catppuccin Mocha",
        "default_light": "Catppuccin Latte",
        "default_scheme": "system",
    },
}


def _toml_from_dict(d: dict) -> str:
    lines: list[str] = []
    for key, value in d.items():
        if isinstance(value, dict):
            lines.append(f"[{key}]")
            for k, v in value.items():
                lines.append(_format_toml_line(k, v))
            lines.append("")
        else:
            lines.append(_format_toml_line(key, value))
    return "\n".join(lines) + "\n"


def _format_toml_line(key: str, value: object) -> str:
    if isinstance(value, bool):
        return f"{key} = {'true' if value else 'false'}"
    if isinstance(value, str):
        return f'{key} = "{value}"'
    return f"{key} = {value}"


@pytest.fixture
def sample_toml_dict() -> dict:
    return dict(SAMPLE_TOML_DICT)


@pytest.fixture
def sample_toml_content() -> str:
    return _toml_from_dict(SAMPLE_TOML_DICT)


@pytest.fixture
def minimal_toml_content() -> str:
    return textwrap.dedent("""\
        [app]
        title = "Minimal"

        [admin]
        username = "admin"

        [server]
        host = "0.0.0.0"
        port = 5000
        debug = false

        [author]
        name = ""

        [site]
        base_url = "http://localhost:5000"

        [email]
        smtp_host = ""

        [newsletter]
        send_time = "08:00"

        [themes]
        default_dark = "Catppuccin Mocha"
        default_light = "Catppuccin Latte"
        default_scheme = "system"
    """)


@pytest.fixture
def invalid_toml_content() -> str:
    return "[broken\ncan't parse this"


@pytest.fixture
def tmp_config_file(tmp_path: Path, sample_toml_content: str) -> Path:
    config_file = tmp_path / "config.toml"
    config_file.write_text(sample_toml_content)
    return config_file


@pytest.fixture
def tmp_env_file(tmp_path: Path) -> Path:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SECRET_KEY=test-secret-key-for-env-file-testing-123\n"
        "ADMIN_PASSWORD=env-file-password\n"
        "SMTP_HOST=smtp.env.example.com\n"
    )
    return env_file


@pytest.fixture
def patched_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("DEVLOG_CONFIG", raising=False)
    monkeypatch.delenv("DEVLOG_ENV_FILE", raising=False)
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)
    monkeypatch.delenv("BASE_URL", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("ENABLE_SCHEDULER", raising=False)
    monkeypatch.delenv("ENABLE_METRICS", raising=False)
    monkeypatch.delenv("METRICS_SECRET", raising=False)
    monkeypatch.delenv("HEALTH_CHECK_SECRET", raising=False)
    monkeypatch.delenv("WEBHOOK_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("BACKUP_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    monkeypatch.delenv("FLASK_DEBUG", raising=False)
    monkeypatch.delenv("TESTING", raising=False)
    yield
