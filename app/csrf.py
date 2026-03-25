import secrets

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
    if not token or token != session.get("csrf_token"):
        abort(403)


def csrf_exempt(f):
    """Decorator to exempt a route from CSRF validation."""
    f._csrf_exempt = True
    return f
