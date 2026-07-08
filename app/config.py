from dotenv import load_dotenv

load_dotenv()

import logging  # noqa: E402
import os  # noqa: E402
import tomllib  # noqa: E402
from typing import Any  # noqa: E402
from urllib.parse import urlparse  # noqa: E402

__all__ = [
    "APP_TITLE",
    "APP_DESCRIPTION",
    "POSTS_PER_PAGE",
    "SECRET_KEY",
    "MAX_VIEWED_POSTS",
    "SESSION_LIFETIME_HOURS",
    "SESSION_IP_BINDING",
    "ADMIN_USERNAME",
    "ADMIN_PASSWORD",
    "SERVER_HOST",
    "SERVER_PORT",
    "DEBUG",
    "AUTHOR_NAME",
    "AUTHOR_ROLE",
    "AUTHOR_AVATAR",
    "BASE_URL",
    "CDN_URL",
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
    "PAGE_VIEW_BUFFER_SIZE",
    "ANALYTICS_DAYS_MIN",
    "ANALYTICS_DAYS_MAX",
    "TOKEN_ENUMERATION_DELAY",
    "LOGIN_FAILURE_DELAY",
    "PREVIEW_TOKEN_EXPIRY_DAYS",
    "HEALTH_CHECK_SECRET",
    "METRICS_SECRET",
    "ENABLE_METRICS",
    "RATE_LIMIT_STORAGE_URI",
    "REDIS_URL",
    "DATA_BACKUP_DIR",
    "WEBHOOK_TIMEOUT",
    "WEBHOOK_ENCRYPTION_KEY",
    "COMPRESS_ALGORITHM",
    "COMMENT_MIN_LENGTH",
    "COMMENT_MAX_LENGTH",
    "COMMENT_RATE_LIMIT_PER_IP",
    "COMMENT_RATE_LIMIT_PER_POST",
    "COMMENT_NOTIFY_PENDING",
    "COMMENT_SPAM_WORDS",
    "SEARCH_PROVIDER",
    "SEARCH_CONFIG",
    "ENABLE_SCHEDULER",
]


def _env(key: str, default: Any = None) -> Any:
    """Get environment variable with optional default."""
    val = os.environ.get(key)
    if val is not None:
        return val
    return default


def _env_str(key: str, default: str = "") -> str:
    """Get a string environment variable, treating empty strings as unset."""
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value


def _env_bool(key: str, default: bool = False) -> bool:
    """Get a boolean environment variable."""
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value.lower() in ("true", "1", "yes")


def load_config() -> dict[str, Any]:
    """Load configuration from TOML file."""
    project_root = os.path.dirname(os.path.dirname(__file__))
    config_path = os.path.join(project_root, "config.toml")
    if os.path.exists(config_path):
        with open(config_path, "rb") as f:
            return tomllib.load(f)

    fallback_path = os.path.join(project_root, "config.toml.example")
    if os.path.exists(fallback_path):
        logging.warning(
            "config.toml not found; using config.toml.example as fallback. "
            "Copy config.toml.example to config.toml and customize."
        )
        with open(fallback_path, "rb") as f:
            return tomllib.load(f)

    raise RuntimeError(
        "Configuration file not found: config.toml\n"
        "Copy config.toml.example to config.toml and edit it."
    )


_config = load_config()

APP_TITLE = _config["app"]["title"]
APP_DESCRIPTION = _config["app"]["description"]
POSTS_PER_PAGE = _config["app"]["posts_per_page"]
SECRET_KEY = _env("SECRET_KEY")
MAX_VIEWED_POSTS = int(_config["app"].get("max_viewed_posts", 100))
SESSION_LIFETIME_HOURS = int(_config["app"].get("session_lifetime_hours", 24))
SESSION_IP_BINDING = _config["app"].get("session_ip_binding", "warn")

ADMIN_USERNAME = _env("ADMIN_USERNAME", _config["admin"]["username"])
ADMIN_PASSWORD = _env("ADMIN_PASSWORD")

SERVER_HOST = _config["server"]["host"]
SERVER_PORT = int(_config["server"]["port"])
DEBUG = _config["server"].get("debug", False)

AUTHOR_NAME = _config["author"]["name"]
AUTHOR_ROLE = _config["author"]["role"]
AUTHOR_AVATAR = _config["author"].get("avatar", "")

BASE_URL = _config.get("site", {}).get("base_url", "http://localhost:5000").rstrip("/")
CDN_URL = _env("CDN_URL", _config.get("site", {}).get("cdn_url", "")).rstrip("/") or ""
RELATED_POSTS_COUNT = _config["site"]["related_posts_count"]

SMTP_HOST = _config["email"]["smtp_host"]
SMTP_PORT = int(_config["email"]["smtp_port"])
SMTP_USER = _env("SMTP_USER", _config["email"].get("smtp_user", ""))
SMTP_PASSWORD = _env("SMTP_PASSWORD", _config["email"].get("smtp_password", ""))
FROM_ADDRESS = _config["email"]["from_address"]

NEWSLETTER_SEND_TIME = _config["newsletter"]["send_time"]
CONFIRMATION_EXPIRY_HOURS = int(_config["newsletter"].get("confirmation_expiry_hours", 1))
NEWSLETTER_MAX_RETRY_ATTEMPTS = int(_config["newsletter"].get("max_retry_attempts", 5))
ENABLE_SCHEDULER = _env_bool("ENABLE_SCHEDULER", default=False)
TAG_CACHE_TTL_SECONDS = int(_config["app"].get("tag_cache_ttl_seconds", 60))

DASHBOARD_PER_PAGE = int(_config["app"].get("dashboard_per_page", 20))
SUBSCRIBERS_PER_PAGE = int(_config["app"].get("subscribers_per_page", 50))
MEDIA_PER_PAGE = int(_config["app"].get("media_per_page", 50))
MEDIA_MAX_FILES = int(_config["app"].get("media_max_files", 1000))
MAX_UPLOAD_SIZE = int(_config["app"].get("max_upload_size", 10485760))
EXPORT_BATCH_SIZE = int(_config["app"].get("export_batch_size", 500))
FTS_RESULT_LIMIT = int(_config["app"].get("fts_result_limit", 100))
ANALYTICS_DAYS_MIN = int(_config["app"].get("analytics_days_min", 7))
ANALYTICS_DAYS_MAX = int(_config["app"].get("analytics_days_max", 365))
PAGE_VIEW_BUFFER_SIZE = int(
    os.environ.get("PAGE_VIEW_BUFFER_SIZE", _config["app"].get("page_view_buffer_size", 0))
)
TOKEN_ENUMERATION_DELAY = float(_config["app"].get("token_enumeration_delay", 0.1))
PREVIEW_TOKEN_EXPIRY_DAYS = int(_config["app"].get("preview_token_expiry_days", 7))

COMMENT_MIN_LENGTH = int(_config.get("comments", {}).get("min_length", 3))
COMMENT_MAX_LENGTH = int(_config.get("comments", {}).get("max_length", 5000))
COMMENT_RATE_LIMIT_PER_IP = _config.get("comments", {}).get("rate_limit_per_ip", "5 per minute")
COMMENT_RATE_LIMIT_PER_POST = _config.get("comments", {}).get("rate_limit_per_post", "3 per minute")
COMMENT_NOTIFY_PENDING = bool(_config.get("comments", {}).get("notify_pending", False))
COMMENT_SPAM_WORDS = _config.get("comments", {}).get("spam_words", "")

HEALTH_CHECK_SECRET = _env("HEALTH_CHECK_SECRET", "")
METRICS_SECRET = _env("METRICS_SECRET", "")
ENABLE_METRICS = _env_bool("ENABLE_METRICS", default=False)


def is_production() -> bool:
    return os.environ.get("FLASK_ENV") == "production"


LOGIN_FAILURE_DELAY = float(
    _env("LOGIN_FAILURE_DELAY", _config["app"].get("login_failure_delay", 0.05))
)
LOGIN_FAILURE_DELAY = max(LOGIN_FAILURE_DELAY, 0.1)
RATE_LIMIT_STORAGE_URI = _env(
    "RATE_LIMIT_STORAGE_URI",
    "redis://localhost:6379/1" if os.environ.get("FLASK_ENV") == "production" else "memory://",
)

REDIS_URL = _env("REDIS_URL", "redis://localhost:6379/0")
DATA_BACKUP_DIR = _config.get("backup", {}).get("data_backup_dir", "backups")
WEBHOOK_TIMEOUT = int(_config.get("webhook", {}).get("timeout", 10))
WEBHOOK_ENCRYPTION_KEY = _env("WEBHOOK_ENCRYPTION_KEY", "")
COMPRESS_ALGORITHM = ["zstd", "br", "gzip"]

SMTP_TIMEOUT = int(_config["email"].get("smtp_timeout", 30))

MAX_FAILED_ATTEMPTS = int(_config.get("security", {}).get("max_failed_attempts", 5))
LOCKOUT_DURATION_MINUTES = int(_config.get("security", {}).get("lockout_duration_minutes", 15))

ADMIN_RATE_LIMITS = {
    "login": (5, 60),
    "api_write": (100, 60),
    "api_read": (500, 60),
    "settings": (50, 60),
    "post_create": (100, 60),
    "post_update": (100, 60),
}

SEARCH_PROVIDER = _config.get("search", {}).get("provider", "sqlite")
SEARCH_CONFIG = _config.get("search", {}).get("config", {})


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
            errors.append(f"Invalid smtp_timeout: {smtp_timeout}. Must be a positive integer")

    base_url = config.get("site", {}).get("base_url", "")
    if base_url:
        parsed = urlparse(base_url)
        if not parsed.scheme or not parsed.netloc:
            errors.append(
                f"Invalid base_url: {base_url}. Must be a full URL with scheme (http:// or https://) and domain"
            )

    if errors:
        raise RuntimeError("Config errors:\n" + "\n".join(errors))
