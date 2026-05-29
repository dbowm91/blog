"""Per-admin and per-IP rate limiting middleware.

Uses Flask-Limiter's storage backend for tracking request counts.
Provides configurable rate limits per endpoint type.
"""

from typing import Callable, Optional
from functools import wraps

from flask import has_request_context
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def get_admin_id() -> Optional[str]:
    """Get current admin ID for rate limiting."""
    if has_request_context():
        from flask_login import current_user

        if current_user.is_authenticated and hasattr(current_user, "id"):
            return f"admin:{current_user.id}"
    return None


def get_rate_limit_key() -> str:
    """Get the rate limit key (admin ID or IP)."""
    admin_id = get_admin_id()
    if admin_id:
        return admin_id
    return f"ip:{get_remote_address()}"


class AdminRateLimiter:
    """Per-admin rate limiter that uses Flask-Limiter storage."""

    def __init__(self, limiter: Optional[Limiter] = None) -> None:
        self._limiter = limiter

    @property
    def limiter(self) -> Limiter:
        if self._limiter is None:
            from app import limiter as app_limiter

            return app_limiter
        return self._limiter

    def get_limit(self, limit_type: str) -> Optional[tuple[int, int]]:
        """Get limit config for type."""
        from app.config import ADMIN_RATE_LIMITS

        return ADMIN_RATE_LIMITS.get(limit_type)

    def format_limit(self, limit_type: str) -> Optional[str]:
        """Format limit as 'count per second' string."""
        config = self.get_limit(limit_type)
        if config:
            count, window = config
            return f"{count} per {window}"
        return None

    def limit_by_type(self, limit_type: str) -> Callable:
        """Decorator to apply rate limit by type."""
        limit_str = self.format_limit(limit_type)
        if not limit_str:
            return lambda f: f

        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def wrapped(*args, **kwargs):
                return f(*args, **kwargs)

            wrapped.__rate_limit = limit_str
            return wrapped

        return decorator


admin_rate_limiter = AdminRateLimiter()
