"""CSRF token generation and validation.

Tokens are stored in the Flask session and checked on every POST request.
The token is available both as a form field (csrf_token) and as an HTTP
header (X-CSRF-Token) for JSON API calls. Validation is skipped when
TESTING=True and CSRF_ENABLED=False.

Implements a sliding window of 5 valid tokens per session:
1. Store multiple valid tokens in session (sliding window)
2. Check submitted token is in valid set
3. Remove used token after successful validation
4. Rotate token after each successful validation
"""

import secrets
import hmac

from flask import session, request, abort, current_app

CSRF_TOKEN_WINDOW_SIZE = 5


def generate_csrf_token() -> str:
    """Generate a CSRF token for the current session.

    Maintains a sliding window of up to 5 valid tokens. Each call generates
    a new token and adds it to the window. Old tokens are removed when the
    window exceeds its maximum size.
    """
    tokens = session.get("csrf_tokens", [])
    new_token = secrets.token_hex(32)
    tokens.append(new_token)
    if len(tokens) > CSRF_TOKEN_WINDOW_SIZE:
        tokens = tokens[-CSRF_TOKEN_WINDOW_SIZE:]
    session["csrf_tokens"] = tokens
    return new_token


def validate_csrf_token() -> None:
    """Validate the CSRF token from the request.

    Checks if the submitted token is in the valid set. If valid, removes it
    from the set (preventing replay) and generates a new token (rotation).
    """
    if current_app.config.get("TESTING") and not current_app.config.get("CSRF_ENABLED", True):
        return

    token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not token:
        abort(403)

    tokens = session.get("csrf_tokens", [])
    for i, t in enumerate(tokens):
        if hmac.compare_digest(token, t):
            tokens.pop(i)
            tokens.append(secrets.token_hex(32))
            if len(tokens) > CSRF_TOKEN_WINDOW_SIZE:
                tokens = tokens[-CSRF_TOKEN_WINDOW_SIZE:]
            session["csrf_tokens"] = tokens
            return

    abort(403)
