"""API authentication and shared utilities."""

import os
import hmac
import hashlib
import secrets
from functools import wraps
from typing import Any, Optional

from flask import request, jsonify

from app.extensions import db
from app.models import ApiToken
from app.utils import utc_now

API_KEY = os.environ.get("API_KEY", "")

SCOPES = {
    "posts:read",
    "posts:write",
    "media:read",
    "media:write",
    "subscribers:read",
    "subscribers:write",
    "newsletter:send",
    "analytics:read",
    "tags:read",
    "tags:write",
    "pages:read",
    "pages:write",
    "series:read",
    "series:write",
    "admin:*",
}


def _hash_token(token: str) -> str:
    """Hash a token using SHA-256."""
    return hashlib.sha256(token.encode()).hexdigest()


def _verify_api_key() -> Optional[dict]:
    """Verify legacy API_KEY. Returns None if invalid or not configured."""
    if not API_KEY:
        return None
    provided = request.headers.get("X-API-Key", "")
    if not provided or not hmac.compare_digest(provided, API_KEY):
        return None
    return {"type": "legacy", "scopes": list(SCOPES)}


def _verify_token() -> Optional[dict]:
    """Verify a scoped API token. Returns token info if valid, None otherwise."""
    provided = request.headers.get("X-API-Key", "")
    if not provided:
        return None

    token_hash = _hash_token(provided)
    token = db.session.execute(
        db.select(ApiToken).filter(ApiToken.token_hash == token_hash)
    ).scalar_one_or_none()

    if not token:
        return None

    if not token.is_valid():
        return None

    token.last_used_at = utc_now()
    db.session.commit()

    return {"type": "token", "token_id": token.id, "scopes": token.scopes}


def require_api_key(f: Any) -> Any:
    """Decorator to require API key authentication (legacy or scoped)."""

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        auth_info = _verify_api_key() or _verify_token()

        if auth_info is None:
            return jsonify({"error": "Invalid or missing API key"}), 401

        request.api_auth = auth_info
        return f(*args, **kwargs)

    return decorated


def require_scope(scope: str) -> Any:
    """Decorator to require a specific scope in addition to API key auth."""

    def decorator(f: Any) -> Any:
        @wraps(f)
        def decorated(*args: Any, **kwargs: Any) -> Any:
            auth_info = getattr(request, "api_auth", None)
            if auth_info is None:
                return jsonify({"error": "Invalid or missing API key"}), 401

            if scope not in auth_info["scopes"]:
                return jsonify({"error": f"Missing scope: {scope}"}), 403

            return f(*args, **kwargs)

        return decorated

    return decorator


def generate_token() -> str:
    """Generate a new secure random token."""
    return secrets.token_urlsafe(32)
