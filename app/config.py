import os
import tomllib
from typing import Any
from urllib.parse import urlparse

__all__ = [
    "APP_TITLE",
    "APP_DESCRIPTION",
    "POSTS_PER_PAGE",
    "SECRET_KEY",
    "MAX_VIEWED_POSTS",
    "SESSION_LIFETIME_HOURS",
    "ADMIN_USERNAME",
    "ADMIN_PASSWORD",
    "SERVER_HOST",
    "SERVER_PORT",
    "DEBUG",
    "AUTHOR_NAME",
    "AUTHOR_ROLE",
    "AUTHOR_AVATAR",
    "BASE_URL",
    "RELATED_POSTS_COUNT",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "FROM_ADDRESS",
    "SMTP_TIMEOUT",
    "NEWSLETTER_SEND_TIME",
    "CONFIRMATION_EXPIRY_HOURS",
    "TAG_CACHE_TTL_SECONDS",
    "NEWSLETTER_MAX_RETRY_ATTEMPTS",
    "DASHBOARD_PER_PAGE",
    "SUBSCRIBERS_PER_PAGE",
    "MEDIA_PER_PAGE",
    "MEDIA_MAX_FILES",
    "MAX_UPLOAD_SIZE",
    "EXPORT_BATCH_SIZE",
    "FTS_RESULT_LIMIT",
    "TOKEN_ENUMERATION_DELAY",
]


def _env(key: str, default: Any = None) -> Any:
    """Get environment variable with optional default."""
    val = os.environ.get(key)
    if val is not None:
        return val
    return default


def load_config() -> dict[str, Any]:
    """Load configuration from TOML file."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config.toml"
    )
    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        raise RuntimeError(
            f"Configuration file not found: {config_path}\n"
            "Copy config.toml.example to config.toml and edit it."
        )


_config = load_config()

APP_TITLE = _config["app"]["title"]
APP_DESCRIPTION = _config["app"]["description"]
POSTS_PER_PAGE = _config["app"]["posts_per_page"]
SECRET_KEY = _env("SECRET_KEY")
MAX_VIEWED_POSTS = int(_config["app"].get("max_viewed_posts", 100))
SESSION_LIFETIME_HOURS = int(_config["app"].get("session_lifetime_hours", 24))

ADMIN_USERNAME = _env("ADMIN_USERNAME", _config["admin"]["username"])
ADMIN_PASSWORD = _env("ADMIN_PASSWORD")

SERVER_HOST = _config["server"]["host"]
SERVER_PORT = int(_config["server"]["port"])
DEBUG = _config["server"].get("debug", False)

AUTHOR_NAME = _config["author"]["name"]
AUTHOR_ROLE = _config["author"]["role"]
AUTHOR_AVATAR = _config["author"].get("avatar", "")

BASE_URL = _config.get("site", {}).get("base_url", "http://localhost:5000").rstrip("/")
RELATED_POSTS_COUNT = _config["site"]["related_posts_count"]

SMTP_HOST = _config["email"]["smtp_host"]
SMTP_PORT = int(_config["email"]["smtp_port"])
SMTP_USER = _env("SMTP_USER", _config["email"].get("smtp_user", ""))
SMTP_PASSWORD = _env("SMTP_PASSWORD", _config["email"].get("smtp_password", ""))
FROM_ADDRESS = _config["email"]["from_address"]

NEWSLETTER_SEND_TIME = _config["newsletter"]["send_time"]
CONFIRMATION_EXPIRY_HOURS = int(
    _config["newsletter"].get("confirmation_expiry_hours", 1)
)
NEWSLETTER_MAX_RETRY_ATTEMPTS = int(_config["newsletter"].get("max_retry_attempts", 5))
TAG_CACHE_TTL_SECONDS = int(_config["app"].get("tag_cache_ttl_seconds", 60))

DASHBOARD_PER_PAGE = int(_config["app"].get("dashboard_per_page", 20))
SUBSCRIBERS_PER_PAGE = int(_config["app"].get("subscribers_per_page", 50))
MEDIA_PER_PAGE = int(_config["app"].get("media_per_page", 50))
MEDIA_MAX_FILES = int(_config["app"].get("media_max_files", 1000))
MAX_UPLOAD_SIZE = int(_config["app"].get("max_upload_size", 10485760))
EXPORT_BATCH_SIZE = int(_config["app"].get("export_batch_size", 500))
FTS_RESULT_LIMIT = int(_config["app"].get("fts_result_limit", 100))
TOKEN_ENUMERATION_DELAY = float(_config["app"].get("token_enumeration_delay", 0.1))

SMTP_TIMEOUT = int(_config["email"].get("smtp_timeout", 30))


def _validate_config(config: dict) -> None:
    errors = []

    send_time = config.get("newsletter", {}).get("send_time", "08:00")
    try:
        parts = send_time.split(":")
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
    except (ValueError, IndexError):
        errors.append(f"Invalid newsletter send_time: {send_time}. Expected HH:MM")

    per_page = config.get("app", {}).get("posts_per_page", 10)
    if not isinstance(per_page, int) or per_page < 1 or per_page > 100:
        errors.append(f"Invalid posts_per_page: {per_page}. Must be 1-100")

    expiry_hours = config.get("newsletter", {}).get("confirmation_expiry_hours", 1)
    try:
        expiry_hours = int(expiry_hours)
        if expiry_hours < 1:
            raise ValueError
    except (ValueError, TypeError):
        errors.append(
            f"Invalid confirmation_expiry_hours: {expiry_hours}. Must be a positive integer"
        )

    smtp_host = config.get("email", {}).get("smtp_host", "")
    smtp_port = config.get("email", {}).get("smtp_port", 587)
    if smtp_host:
        try:
            smtp_port = int(smtp_port)
            if not (1 <= smtp_port <= 65535):
                raise ValueError
        except (ValueError, TypeError):
            errors.append(f"Invalid smtp_port: {smtp_port}. Must be 1-65535")

    for key in [
        "dashboard_per_page",
        "subscribers_per_page",
        "media_per_page",
        "media_max_files",
        "max_upload_size",
        "export_batch_size",
        "fts_result_limit",
    ]:
        val = config.get("app", {}).get(key)
        if val is not None:
            try:
                val_int = int(val)
                if val_int < 1:
                    raise ValueError
            except (ValueError, TypeError):
                errors.append(f"Invalid {key}: {val}. Must be a positive integer")

    token_delay = config.get("app", {}).get("token_enumeration_delay")
    if token_delay is not None:
        try:
            delay = float(token_delay)
            if delay <= 0:
                raise ValueError
        except (ValueError, TypeError):
            errors.append(
                f"Invalid token_enumeration_delay: {token_delay}. Must be a positive number"
            )

    smtp_timeout = config.get("email", {}).get("smtp_timeout")
    if smtp_timeout is not None:
        try:
            timeout = int(smtp_timeout)
            if timeout < 1:
                raise ValueError
        except (ValueError, TypeError):
            errors.append(
                f"Invalid smtp_timeout: {smtp_timeout}. Must be a positive integer"
            )

    base_url = config.get("site", {}).get("base_url", "")
    if base_url:
        parsed = urlparse(base_url)
        if not parsed.scheme or not parsed.netloc:
            errors.append(
                f"Invalid base_url: {base_url}. Must be a full URL with scheme (http:// or https://) and domain"
            )

    if errors:
        raise RuntimeError("Config errors:\n" + "\n".join(errors))
