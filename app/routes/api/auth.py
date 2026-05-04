"""API authentication and shared utilities."""

import os
import hmac
from functools import wraps
from typing import Any

from flask import request, jsonify

API_KEY = os.environ.get("API_KEY", "")


def require_api_key(f: Any) -> Any:
    """Decorator to require API key authentication."""

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        if not API_KEY:
            return jsonify({"error": "API not configured"}), 503

        provided = request.headers.get("X-API-Key", "")
        if not provided or not hmac.compare_digest(provided, API_KEY):
            return jsonify({"error": "Invalid or missing API key"}), 401

        return f(*args, **kwargs)

    return decorated