"""CSRF token generation and validation.

Tokens are stored in the Flask session and checked on every POST request.
The token is available both as a form field (csrf_token) and as an HTTP
header (X-CSRF-Token) for JSON API calls. Validation is skipped when
TESTING=True and CSRF_ENABLED=False.
"""
import secrets
import hmac

from flask import session, request, abort, current_app


def generate_csrf_token() -> str:
    """Generate a CSRF token for the current session."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def validate_csrf_token() -> None:
    """Validate the CSRF token from the request."""
    # Skip CSRF validation if testing
    if current_app.config.get('TESTING') and not current_app.config.get('CSRF_ENABLED', True):
        return
    
    token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not token or not hmac.compare_digest(token, session.get("csrf_token", "")):
        abort(403)

