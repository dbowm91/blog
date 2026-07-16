"""Legacy configuration compatibility layer.

DEPRECATED: This module exists only for backward compatibility with code that
imports legacy configuration globals directly. New code should use the typed
configuration system in app.config.loader and app.config.model.

All remaining consumers:
- app/config/__init__.py — re-exports legacy globals for backward compat
- app/__init__.py — may use legacy globals during init transition
- tests/test_config.py — tests legacy helper functions

This module does NOT independently parse configuration. It projects values
from the typed loader (app.config.loader.load_effective_config).

Removal condition: When all legacy global imports are migrated to typed config,
this module can be deleted. Target: Release 2.
"""

from dotenv import load_dotenv

load_dotenv()

import os  # noqa: E402
import warnings  # noqa: E402
from typing import Any  # noqa: E402

warnings.warn(
    "app.config_legacy is deprecated. Use app.config.loader and app.config.model instead.",
    DeprecationWarning,
    stacklevel=2,
)

from app.config.loader import load_effective_config  # noqa: E402

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
    "THEME_EXTERNAL_DIR",
    "THEME_ALLOW_EXTERNAL",
    "THEME_STRICT_VALIDATION",
    "THEME_DEFAULT_DARK",
    "THEME_DEFAULT_LIGHT",
    "THEME_DEFAULT_SCHEME",
    "DEVLOG_DATA_DIR",
    "DEVLOG_LOG_DIR",
    "DEVLOG_RUNTIME_DIR",
    "DEVLOG_DATABASE_PATH",
    "DEVLOG_UPLOADS_DIR",
    "DEVLOG_THEMES_DIR",
    "DEVLOG_BACKUPS_DIR",
    "DEVLOG_EXPORTS_DIR",
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


def is_production() -> bool:
    return os.environ.get("FLASK_ENV") == "production"


try:
    _typed_config = load_effective_config()
except Exception:
    _typed_config = None

if _typed_config is not None:
    _c = _typed_config
    APP_TITLE = _c.app.title
    APP_DESCRIPTION = _c.app.description
    POSTS_PER_PAGE = _c.app.posts_per_page
    SECRET_KEY = _c.secret_key
    MAX_VIEWED_POSTS = _c.app.max_viewed_posts
    SESSION_LIFETIME_HOURS = _c.app.session_lifetime_hours
    SESSION_IP_BINDING = _c.app.session_ip_binding
    ADMIN_USERNAME = _c.admin.username
    ADMIN_PASSWORD = _c.admin_password
    SERVER_HOST = _c.server.host
    SERVER_PORT = _c.server.port
    DEBUG = _c.server.debug
    AUTHOR_NAME = _c.author.name
    AUTHOR_ROLE = _c.author.role
    AUTHOR_AVATAR = _c.author.avatar
    BASE_URL = _c.site.base_url.rstrip("/")
    CDN_URL = (_c.site.cdn_url or "").rstrip("/") or ""
    RELATED_POSTS_COUNT = _c.site.related_posts_count
    SMTP_HOST = _c.email.smtp_host
    SMTP_PORT = _c.email.smtp_port
    SMTP_USER = _c.email.smtp_user
    SMTP_PASSWORD = _c.email.smtp_password
    FROM_ADDRESS = _c.email.from_address
    SMTP_TIMEOUT = _c.email.smtp_timeout
    NEWSLETTER_SEND_TIME = _c.newsletter.send_time
    CONFIRMATION_EXPIRY_HOURS = _c.newsletter.confirmation_expiry_hours
    TAG_CACHE_TTL_SECONDS = _c.app.tag_cache_ttl_seconds
    NEWSLETTER_MAX_RETRY_ATTEMPTS = _c.newsletter.max_retry_attempts
    DASHBOARD_PER_PAGE = _c.app.dashboard_per_page
    SUBSCRIBERS_PER_PAGE = _c.app.subscribers_per_page
    MEDIA_PER_PAGE = _c.app.media_per_page
    MEDIA_MAX_FILES = _c.app.media_max_files
    MAX_UPLOAD_SIZE = _c.app.max_upload_size
    EXPORT_BATCH_SIZE = _c.app.export_batch_size
    FTS_RESULT_LIMIT = _c.app.fts_result_limit
    PAGE_VIEW_BUFFER_SIZE = _c.app.page_view_buffer_size
    ANALYTICS_DAYS_MIN = _c.app.analytics_days_min
    ANALYTICS_DAYS_MAX = _c.app.analytics_days_max
    TOKEN_ENUMERATION_DELAY = _c.app.token_enumeration_delay
    LOGIN_FAILURE_DELAY = max(_c.app.login_failure_delay, 0.1)
    PREVIEW_TOKEN_EXPIRY_DAYS = _c.app.preview_token_expiry_days
    HEALTH_CHECK_SECRET = _c.health.check_secret
    METRICS_SECRET = _c.metrics.secret
    ENABLE_METRICS = _c.metrics.enabled
    RATE_LIMIT_STORAGE_URI = _c.redis.rate_limit_url or _env(
        "RATE_LIMIT_STORAGE_URI",
        "redis://localhost:6379/1" if is_production() else "memory://",
    )
    REDIS_URL = _c.redis.url
    DATA_BACKUP_DIR = _c.backup.data_backup_dir
    WEBHOOK_TIMEOUT = _c.webhook.timeout
    WEBHOOK_ENCRYPTION_KEY = _c.webhook.encryption_key
    COMPRESS_ALGORITHM = ["zstd", "br", "gzip"]
    COMMENT_MIN_LENGTH = _c.comments.min_length
    COMMENT_MAX_LENGTH = _c.comments.max_length
    COMMENT_RATE_LIMIT_PER_IP = _c.comments.rate_limit_per_ip
    COMMENT_RATE_LIMIT_PER_POST = _c.comments.rate_limit_per_post
    COMMENT_NOTIFY_PENDING = _c.comments.notify_pending
    COMMENT_SPAM_WORDS = _c.comments.spam_words
    SEARCH_PROVIDER = _c.search.provider
    SEARCH_CONFIG = _c.search.config
    ENABLE_SCHEDULER = _c.scheduler.enabled
    DEVLOG_DATA_DIR = _c.paths.data_dir
    DEVLOG_LOG_DIR = _c.paths.log_dir
    DEVLOG_RUNTIME_DIR = _c.paths.runtime_dir
    DEVLOG_DATABASE_PATH = _c.paths.database_path
    DEVLOG_UPLOADS_DIR = _c.paths.uploads_dir
    DEVLOG_THEMES_DIR = _c.paths.themes_dir
    DEVLOG_BACKUPS_DIR = _c.paths.backups_dir
    DEVLOG_EXPORTS_DIR = _c.paths.exports_dir
    THEME_EXTERNAL_DIR = _c.themes.external_dir
    THEME_ALLOW_EXTERNAL = _c.themes.allow_external
    THEME_STRICT_VALIDATION = _c.themes.strict_validation
    THEME_DEFAULT_DARK = _c.themes.default_dark
    THEME_DEFAULT_LIGHT = _c.themes.default_light
    THEME_DEFAULT_SCHEME = _c.themes.default_scheme
    MAX_FAILED_ATTEMPTS = _c.security.max_failed_attempts
    LOCKOUT_DURATION_MINUTES = _c.security.lockout_duration_minutes
else:
    APP_TITLE = _env("APP_TITLE", "DevLog")
    APP_DESCRIPTION = _env("APP_DESCRIPTION", "A place for thoughts on code")
    POSTS_PER_PAGE = int(_env("POSTS_PER_PAGE", "10"))
    SECRET_KEY = _env("SECRET_KEY", "")
    MAX_VIEWED_POSTS = int(_env("MAX_VIEWED_POSTS", "100"))
    SESSION_LIFETIME_HOURS = int(_env("SESSION_LIFETIME_HOURS", "24"))
    SESSION_IP_BINDING = _env("SESSION_IP_BINDING", "warn")
    ADMIN_USERNAME = _env("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = _env("ADMIN_PASSWORD", "")
    SERVER_HOST = _env("SERVER_HOST", "0.0.0.0")
    SERVER_PORT = int(_env("SERVER_PORT", "5000"))
    DEBUG = _env_bool("DEBUG")
    AUTHOR_NAME = _env("AUTHOR_NAME", "")
    AUTHOR_ROLE = _env("AUTHOR_ROLE", "")
    AUTHOR_AVATAR = _env("AUTHOR_AVATAR", "")
    BASE_URL = _env("BASE_URL", "http://localhost:5000").rstrip("/")
    CDN_URL = _env("CDN_URL", "").rstrip("/") or ""
    RELATED_POSTS_COUNT = int(_env("RELATED_POSTS_COUNT", "3"))
    SMTP_HOST = _env("SMTP_HOST", "")
    SMTP_PORT = int(_env("SMTP_PORT", "587"))
    SMTP_USER = _env("SMTP_USER", "")
    SMTP_PASSWORD = _env("SMTP_PASSWORD", "")
    FROM_ADDRESS = _env("FROM_ADDRESS", "")
    SMTP_TIMEOUT = int(_env("SMTP_TIMEOUT", "30"))
    NEWSLETTER_SEND_TIME = _env("NEWSLETTER_SEND_TIME", "08:00")
    CONFIRMATION_EXPIRY_HOURS = int(_env("CONFIRMATION_EXPIRY_HOURS", "1"))
    TAG_CACHE_TTL_SECONDS = int(_env("TAG_CACHE_TTL_SECONDS", "60"))
    NEWSLETTER_MAX_RETRY_ATTEMPTS = int(_env("NEWSLETTER_MAX_RETRY_ATTEMPTS", "5"))
    DASHBOARD_PER_PAGE = int(_env("DASHBOARD_PER_PAGE", "20"))
    SUBSCRIBERS_PER_PAGE = int(_env("SUBSCRIBERS_PER_PAGE", "50"))
    MEDIA_PER_PAGE = int(_env("MEDIA_PER_PAGE", "50"))
    MEDIA_MAX_FILES = int(_env("MEDIA_MAX_FILES", "1000"))
    MAX_UPLOAD_SIZE = int(_env("MAX_UPLOAD_SIZE", "10485760"))
    EXPORT_BATCH_SIZE = int(_env("EXPORT_BATCH_SIZE", "500"))
    FTS_RESULT_LIMIT = int(_env("FTS_RESULT_LIMIT", "100"))
    PAGE_VIEW_BUFFER_SIZE = int(_env("PAGE_VIEW_BUFFER_SIZE", "0"))
    ANALYTICS_DAYS_MIN = int(_env("ANALYTICS_DAYS_MIN", "7"))
    ANALYTICS_DAYS_MAX = int(_env("ANALYTICS_DAYS_MAX", "365"))
    TOKEN_ENUMERATION_DELAY = float(_env("TOKEN_ENUMERATION_DELAY", "0.1"))
    LOGIN_FAILURE_DELAY = max(float(_env("LOGIN_FAILURE_DELAY", "0.05")), 0.1)
    PREVIEW_TOKEN_EXPIRY_DAYS = int(_env("PREVIEW_TOKEN_EXPIRY_DAYS", "7"))
    HEALTH_CHECK_SECRET = _env("HEALTH_CHECK_SECRET", "")
    METRICS_SECRET = _env("METRICS_SECRET", "")
    ENABLE_METRICS = _env_bool("ENABLE_METRICS")
    RATE_LIMIT_STORAGE_URI = _env(
        "RATE_LIMIT_STORAGE_URI",
        "redis://localhost:6379/1" if is_production() else "memory://",
    )
    REDIS_URL = _env("REDIS_URL", "redis://localhost:6379/0")
    DATA_BACKUP_DIR = _env("DATA_BACKUP_DIR", "backups")
    WEBHOOK_TIMEOUT = int(_env("WEBHOOK_TIMEOUT", "10"))
    WEBHOOK_ENCRYPTION_KEY = _env("WEBHOOK_ENCRYPTION_KEY", "")
    COMPRESS_ALGORITHM = ["zstd", "br", "gzip"]
    COMMENT_MIN_LENGTH = int(_env("COMMENT_MIN_LENGTH", "3"))
    COMMENT_MAX_LENGTH = int(_env("COMMENT_MAX_LENGTH", "5000"))
    COMMENT_RATE_LIMIT_PER_IP = _env("COMMENT_RATE_LIMIT_PER_IP", "5 per minute")
    COMMENT_RATE_LIMIT_PER_POST = _env("COMMENT_RATE_LIMIT_PER_POST", "3 per minute")
    COMMENT_NOTIFY_PENDING = _env_bool("COMMENT_NOTIFY_PENDING")
    COMMENT_SPAM_WORDS = _env("COMMENT_SPAM_WORDS", "")
    SEARCH_PROVIDER = _env("SEARCH_PROVIDER", "sqlite")
    SEARCH_CONFIG: dict[str, Any] = {}
    ENABLE_SCHEDULER = _env_bool("ENABLE_SCHEDULER")
    DEVLOG_DATA_DIR = _env("DEVLOG_DATA_DIR", "")
    DEVLOG_LOG_DIR = _env("DEVLOG_LOG_DIR", "")
    DEVLOG_RUNTIME_DIR = _env("DEVLOG_RUNTIME_DIR", "")
    DEVLOG_DATABASE_PATH = _env("DEVLOG_DATABASE_PATH", "")
    DEVLOG_UPLOADS_DIR = _env("DEVLOG_UPLOADS_DIR", "")
    DEVLOG_THEMES_DIR = _env("DEVLOG_THEMES_DIR", "")
    DEVLOG_BACKUPS_DIR = _env("DEVLOG_BACKUPS_DIR", "")
    DEVLOG_EXPORTS_DIR = _env("DEVLOG_EXPORTS_DIR", "")
    THEME_EXTERNAL_DIR = _env("THEME_EXTERNAL_DIR", "")
    THEME_ALLOW_EXTERNAL = _env_bool("THEME_ALLOW_EXTERNAL", True)
    THEME_STRICT_VALIDATION = _env_bool("THEME_STRICT_VALIDATION")
    THEME_DEFAULT_DARK = _env("THEME_DEFAULT_DARK", "Catppuccin Mocha")
    THEME_DEFAULT_LIGHT = _env("THEME_DEFAULT_LIGHT", "Catppuccin Latte")
    THEME_DEFAULT_SCHEME = _env("THEME_DEFAULT_SCHEME", "system")
    MAX_FAILED_ATTEMPTS = int(_env("MAX_FAILED_ATTEMPTS", "5"))
    LOCKOUT_DURATION_MINUTES = int(_env("LOCKOUT_DURATION_MINUTES", "15"))

ADMIN_RATE_LIMITS = {
    "login": (5, 60),
    "api_write": (100, 60),
    "api_read": (500, 60),
    "settings": (50, 60),
    "post_create": (100, 60),
    "post_update": (100, 60),
}
