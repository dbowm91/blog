"""Configuration profiles for different deployment scenarios."""

from __future__ import annotations

from dataclasses import dataclass

from app.config.model import (
    AppConfig,
    DevLogConfig,
    SchedulerConfig,
    ServerConfig,
    SiteConfig,
)


@dataclass(frozen=True)
class Profile:
    name: str
    description: str
    config: DevLogConfig


PROFILES: dict[str, Profile] = {
    "development": Profile(
        name="development",
        description="Local development with sensible defaults",
        config=DevLogConfig(
            app=AppConfig(posts_per_page=10, page_view_buffer_size=0),
            server=ServerConfig(host="127.0.0.1", port=5000, debug=True),
            site=SiteConfig(base_url="http://localhost:5000"),
            session_cookie_secure=False,
            proxy_count=1,
            scheduler=SchedulerConfig(enabled=False),
        ),
    ),
    "native-production": Profile(
        name="native-production",
        description="Production on bare metal or VM behind reverse proxy",
        config=DevLogConfig(
            server=ServerConfig(host="127.0.0.1", port=5000, debug=False),
            site=SiteConfig(base_url="https://example.com"),
            session_cookie_secure=True,
            proxy_count=1,
            scheduler=SchedulerConfig(enabled=True),
        ),
    ),
    "docker-production": Profile(
        name="docker-production",
        description="Production in Docker container",
        config=DevLogConfig(
            server=ServerConfig(host="0.0.0.0", port=5000, debug=False),
            site=SiteConfig(base_url="https://example.com"),
            session_cookie_secure=True,
            proxy_count=1,
            scheduler=SchedulerConfig(enabled=False),
        ),
    ),
    "minimal": Profile(
        name="minimal",
        description="Minimal configuration for testing",
        config=DevLogConfig(
            server=ServerConfig(host="127.0.0.1", port=5000, debug=False),
            site=SiteConfig(base_url="http://localhost:5000"),
            session_cookie_secure=False,
        ),
    ),
    "full": Profile(
        name="full",
        description="Full configuration with all sections documented",
        config=DevLogConfig(
            server=ServerConfig(host="0.0.0.0", port=5000, debug=False),
            site=SiteConfig(base_url="https://example.com"),
            session_cookie_secure=True,
            scheduler=SchedulerConfig(enabled=True),
        ),
    ),
}


def get_profile(name: str) -> Profile | None:
    return PROFILES.get(name)


def list_profiles() -> list[dict[str, str]]:
    return [{"name": p.name, "description": p.description} for p in PROFILES.values()]
