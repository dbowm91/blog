"""CSRF token generation and validation.

Tokens are stored in the Flask session and checked on every POST request
except API-key authenticated endpoints. The token is available both as a
form field (csrf_token) and as an HTTP header (X-CSRF-Token) for JSON
API calls. Validation is skipped when TESTING=True and CSRF_ENABLED=False.

API-key requests are bearer-token requests protected by token secrecy,
HTTPS, scopes, rate limits, and audit logging — not browser CSRF tokens.

Implements a sliding window of up to 5 valid tokens per session:
1. Store multiple valid tokens in session (sliding window)
2. Check the submitted token is in the valid set
3. A token stays valid until it ages out of the window

A token is deliberately *not* consumed on use. A rendered page regularly
needs more than one request — the theme preview endpoint and the form
below it, for example — and consuming the token on the first request made
every subsequent request from that page fail with a 403.
"""

import secrets
import hmac

from flask import session, request, abort, current_app

CSRF_TOKEN_WINDOW_SIZE = 5

#: Single source of truth for the HTTP header that carries the CSRF token.
#: Client-side code must not hard-code the name; it is published to templates
#: as ``csrf_header_name`` and reaches the browser via the ``data-csrf-header``
#: attribute on the root element.
CSRF_HEADER_NAME = "X-CSRF-Token"


def should_skip_csrf() -> bool:
    """Return True if the current request should skip CSRF validation.

    API-key authenticated requests (blueprint "api") are exempt from CSRF.
    They are protected by token secrecy, HTTPS, scopes, and audit logging
    instead of browser-session CSRF tokens.
    """
    if request.blueprint == "api":
        return True
    return False


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

    The submitted token must be one of the tokens issued to this session.
    """
    if current_app.config.get("TESTING") and not current_app.config.get("CSRF_ENABLED", True):
        return

    token = request.form.get("csrf_token") or request.headers.get(CSRF_HEADER_NAME)
    if not token:
        abort(403)

    tokens = session.get("csrf_tokens", [])
    for t in tokens:
        if hmac.compare_digest(token, t):
            return

    abort(403)
