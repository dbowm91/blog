import time
from typing import Optional
from flask import request, flash, render_template, jsonify


_lockouts: dict[str, float] = {}
_attempts: dict[str, list[float]] = {}
_last_cleanup: float = 0


def _cleanup_expired_entries(window: int = 300) -> None:
    """Periodically clean up expired entries to prevent memory growth."""
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup < window:
        return
    _last_cleanup = now
    # Clean attempts older than window
    for ip in list(_attempts.keys()):
        _attempts[ip] = [t for t in _attempts[ip] if now - t < window]
        if not _attempts[ip]:
            del _attempts[ip]
    # Clean expired lockouts
    for ip in list(_lockouts.keys()):
        if now >= _lockouts[ip]:
            del _lockouts[ip]


def check_rate_limit(max_attempts: int = 5, window: int = 300, lockout: int = 300) -> Optional[tuple]:
    """Check if the current IP is rate limited."""
    _cleanup_expired_entries(window)
    ip = request.remote_addr or "unknown"
    now = time.time()

    if ip in _lockouts and now < _lockouts[ip]:
        remaining = int(_lockouts[ip] - now)
        flash(f"Too many attempts. Try again in {remaining}s.", "error")
        return render_template("admin/login.html"), 429

    _attempts[ip] = [t for t in _attempts.get(ip, []) if now - t < window]
    return None


def record_failed_attempt(max_attempts: int = 5, window: int = 300, lockout: int = 300) -> None:
    """Record a failed login attempt."""
    ip = request.remote_addr or "unknown"
    now = time.time()
    _attempts.setdefault(ip, []).append(now)
    if len(_attempts[ip]) >= max_attempts:
        _lockouts[ip] = now + lockout


def clear_attempts() -> None:
    """Clear failed attempts for the current IP."""
    ip = request.remote_addr or "unknown"
    _attempts.pop(ip, None)
    _lockouts.pop(ip, None)


def clear_all() -> None:
    """Clear all rate limit state. For testing only."""
    _attempts.clear()
    _lockouts.clear()


def api_rate_limit(max_requests: int = 60, window: int = 60) -> Optional[tuple]:
    """Rate limit API requests."""
    _cleanup_expired_entries(window)
    ip = request.remote_addr or "unknown"
    now = time.time()
    key = f"api:{ip}"
    _attempts[key] = [t for t in _attempts.get(key, []) if now - t < window]
    if len(_attempts[key]) >= max_requests:
        return jsonify({"error": "rate limited"}), 429
    _attempts.setdefault(key, []).append(now)
    return None
