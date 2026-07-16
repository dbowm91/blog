from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config.model import (
    AdminConfig,
    AppConfig,
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


@dataclass(frozen=True)
class OnboardingInput:
    mode: str = "native"
    profile: str = "development"
    site_title: str = "DevLog"
    site_description: str = "A place for thoughts on code"
    base_url: str = "http://localhost:5000"
    bind_host: str = "127.0.0.1"
    bind_port: int = 5000
    behind_reverse_proxy: bool = False
    admin_username: str = "admin"
    admin_password: str = ""
    enable_newsletter: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_address: str = "blog@example.com"
    enable_scheduler: bool = False
    enable_redis: bool = False
    storage_backend: str = "local"
    backup_dir: str = "backups"
    enable_backup_encryption: bool = False
    theme_dark: str = "Catppuccin Mocha"
    theme_light: str = "Catppuccin Latte"
    theme_scheme: str = "system"
    dry_run: bool = False
    non_interactive: bool = False
    accept_defaults: bool = False


def build_config_from_input(inp: OnboardingInput) -> DevLogConfig:
    is_production = inp.profile in ("native-production", "docker-production")
    use_https = inp.base_url.startswith("https://")

    if inp.mode == "docker":
        host = "0.0.0.0"
    else:
        host = inp.bind_host

    db_uri = ""
    if inp.mode == "docker":
        db_uri = "sqlite:///data/blog.db"
    else:
        data_dir = Path("data")
        db_uri = f"sqlite:///{data_dir.resolve()}/blog.db"

    redis_url = "redis://localhost:6379/0"
    cache_url = ""
    rate_limit_url = ""
    celery_broker = ""
    if inp.enable_redis:
        cache_url = redis_url
        rate_limit_url = redis_url
        celery_broker = redis_url

    return DevLogConfig(
        version=1,
        app=AppConfig(
            title=inp.site_title,
            description=inp.site_description,
        ),
        admin=AdminConfig(inp.admin_username),
        server=ServerConfig(
            host=host,
            port=inp.bind_port,
            debug=not is_production,
        ),
        site=SiteConfig(base_url=inp.base_url),
        email=EmailConfig(
            smtp_host=inp.smtp_host,
            smtp_port=inp.smtp_port,
            smtp_user=inp.smtp_user,
            smtp_password=inp.smtp_password,
            from_address=inp.from_address,
        ),
        newsletter=NewsletterConfig(),
        comments=CommentsConfig(),
        themes=ThemesConfig(
            default_dark=inp.theme_dark,
            default_light=inp.theme_light,
            default_scheme=inp.theme_scheme,
        ),
        database=DatabaseConfig(uri=db_uri),
        redis=RedisConfig(
            url=redis_url,
            cache_url=cache_url,
            rate_limit_url=rate_limit_url,
        ),
        celery=CeleryConfig(broker_url=celery_broker),
        scheduler=SchedulerConfig(enabled=inp.enable_scheduler),
        storage=StorageConfig(backend=inp.storage_backend),
        health=HealthConfig(),
        metrics=MetricsConfig(),
        backup=BackupConfig(data_backup_dir=inp.backup_dir),
        security=SecurityConfig(),
        webhook=WebhookConfig(),
        logging=LoggingConfig(),
        search=SearchConfig(),
        secret_key="",
        admin_password=inp.admin_password,
        session_cookie_secure=use_https or is_production,
        proxy_count=2 if inp.behind_reverse_proxy else 1,
        flask_env="production" if is_production else "",
        testing=False,
    )
