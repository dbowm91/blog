import html as _html
import logging
import os
import re
import unicodedata
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, TypeVar

from sqlalchemy import TypeDecorator, DateTime

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

__all__ = [
    "utc_now",
    "UTCDateTime",
    "is_valid_email",
    "generate_slug",
    "xml_escape",
    "safe_delete_file",
    "sanitize_css",
    "log_storage_error",
    "log_security_event",
    "log_scheduler_error",
    "handle_error",
    "unified_error_handler",
    "is_safe_webhook_url",
]

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class ErrorLogContext:
    """Context for structured error logging with event categorization."""

    STORAGE = "storage"
    SECURITY = "security"
    SCHEDULER = "scheduler"
    DATABASE = "database"
    GENERAL = "general"


def log_storage_error(operation: str, detail: str, exc: Exception | None = None) -> None:
    """Log a storage-related error with structured parameters.

    Args:
        operation: The storage operation that failed (e.g., 'upload', 'delete', 'list').
        detail: Human-readable description of what was being attempted.
        exc: The exception that was raised, if any.
    """
    msg = f"storage_error: operation={operation} detail={detail}"
    if exc:
        logger.error("%s exception=%s: %s", msg, type(exc).__name__, exc)
    else:
        logger.error("%s", msg)


def log_security_event(event: str, **kwargs: Any) -> None:
    """Log a security-related event with structured parameters.

    Args:
        event: The security event type (e.g., 'login_failed', 'csrf_violation', 'token_enumeration').
        **kwargs: Additional context fields (e.g., user_id, ip_address, token_hash).
    """
    parts = [f"event={event}"]
    parts.extend(f"{k}={v!r}" for k, v in kwargs.items())
    logger.warning("security_event: " + " ".join(parts))


def log_scheduler_error(operation: str, detail: str, exc: Exception | None = None) -> None:
    """Log a scheduler-related error with structured parameters.

    Args:
        operation: The scheduler operation that failed (e.g., 'newsletter_send', 'backup').
        detail: Human-readable description of what was being attempted.
        exc: The exception that was raised, if any.
    """
    msg = f"scheduler_error: operation={operation} detail={detail}"
    if exc:
        logger.error("%s exception=%s: %s", msg, type(exc).__name__, exc)
    else:
        logger.error("%s", msg)


def handle_error(
    context: str,
    operation: str,
    detail: str,
    exc: Exception | None = None,
    reraise: bool = False,
    default: Any = None,
) -> Any:
    """Unified error handling utility for storage, security, and scheduler events.

    Logs the error with structured parameters and optionally re-raises or returns a default value.

    Args:
        context: Error context (ErrorLogContext.STORAGE, SECURITY, SCHEDULER, DATABASE, GENERAL).
        operation: The operation that failed.
        detail: Human-readable description of what was being attempted.
        exc: The exception that was raised, if any.
        reraise: If True, re-raise the original exception after logging.
        default: Value to return if not reraising.

    Returns:
        The default value if reraise is False, otherwise None.
    """
    if context == ErrorLogContext.STORAGE:
        log_storage_error(operation, detail, exc)
    elif context == ErrorLogContext.SCHEDULER:
        log_scheduler_error(operation, detail, exc)
    elif context == ErrorLogContext.SECURITY:
        log_security_event(operation, detail=detail, exc_type=type(exc).__name__ if exc else None)
    else:
        msg = f"{context}_error: operation={operation} detail={detail}"
        if exc:
            logger.error("%s exception=%s: %s", msg, type(exc).__name__, exc)
        else:
            logger.error("%s", msg)

    if reraise:
        if exc:
            raise exc
        raise RuntimeError(f"{operation} failed: {detail}")
    return default


def unified_error_handler(
    context: str,
    operation: str,
    detail: str,
    reraise: bool = False,
    default: Any = None,
) -> Callable[[F], F]:
    """Decorator for uniform error handling across functions.

    Args:
        context: Error context (ErrorLogContext.STORAGE, SECURITY, SCHEDULER, DATABASE, GENERAL).
        operation: The operation being performed.
        detail: Human-readable description of what the function does.
        reraise: If True, re-raise the original exception after logging.
        default: Value to return if not reraising.

    Returns:
        Decorated function with error handling.
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                handle_error(context, operation, detail, exc, reraise=reraise, default=default)
                return default
        return wrapper
    return decorator


def safe_delete_file(filepath: str) -> bool:
    """Delete a file, returning True if deleted or False on error. Logs failures."""
    import logging

    logger = logging.getLogger(__name__)
    try:
        from app.storage import get_storage

        storage = get_storage()
        if hasattr(storage, "base_dir") and filepath.startswith(storage.base_dir):
            filename = os.path.basename(filepath)
            return storage.delete(filename)
        os.remove(filepath)
        return True
    except FileNotFoundError:
        return True
    except OSError as e:
        logger.error("Failed to delete file %s: %s", filepath, e)
        return False


def utc_now() -> datetime:
    """Return current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """DateTime stored as naive UTC in SQLite, always returned as timezone-aware UTC.

    This ensures consistent timezone-aware comparisons while remaining
    compatible with SQLite (which stores datetimes as text).
    Existing naive rows are interpreted as UTC on read.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


def is_valid_email(email: str) -> bool:
    """Check if an email address is valid."""
    return bool(email and EMAIL_REGEX.match(email))


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a string."""
    if not name:
        return "untitled"
    # Normalize unicode (e.g., é -> e)
    slug = unicodedata.normalize("NFKD", name)
    slug = slug.encode("ascii", "ignore").decode("ascii")
    slug = slug.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug if slug else "untitled"


def xml_escape(s: str) -> str:
    """Escape special characters for XML output."""
    if not s:
        return ""
    return _html.escape(s, quote=True)


def sanitize_css(css_text: str) -> str:
    """Sanitize custom CSS by removing potentially dangerous properties.

    Strips url() references (data exfiltration vector), expression() (IE only),
    and content property (can inject invisible text). Also removes IE-specific
    behaviors like behavior:, and mso- prefixes. Uses improved regex patterns
    that handle edge cases and are harder to bypass.

    Note: For better security, consider using a proper CSS parser library like
    tinycss2 with an allowlist of safe properties. This regex approach is a
    compromise between security and simplicity for admin-provided CSS.
    """
    if not css_text:
        return ""

    css_text = re.sub(r"url\s*\([^)]*\)", "", css_text, flags=re.IGNORECASE)
    css_text = re.sub(r"url\s*\(\s*\)", "", css_text, flags=re.IGNORECASE)

    css_text = re.sub(r"expression\s*\([^)]*\)", "", css_text, flags=re.IGNORECASE)

    css_text = re.sub(
        r"content\s*:\s*[^;]*;",
        "content: none;",
        css_text,
        flags=re.IGNORECASE,
    )

    css_text = re.sub(r"behavior\s*:\s*[^;]*;", "", css_text, flags=re.IGNORECASE)

    css_text = re.sub(r"mso-[^\s:;]*\s*:\s*[^\s;]*;", "", css_text, flags=re.IGNORECASE)

    css_text = re.sub(r"@import\s+", "", css_text, flags=re.IGNORECASE)

    css_text = re.sub(r"-webkit-text-security\s*:\s*[^\s;]+", "", css_text, flags=re.IGNORECASE)

    css_text = re.sub(r"unicode-bidi\s*:\s*(?:isolate|embed|bidi-override)", "", css_text, flags=re.IGNORECASE)

    css_text = re.sub(r"direction\s*:\s*[^\s;]+", "", css_text, flags=re.IGNORECASE)

    return css_text.strip()

def is_safe_webhook_url(url: str) -> tuple[bool, str]:
    """Check if a URL is safe for webhook delivery (SSRF protection).

    Validates the URL to prevent Server-Side Request Forgery (SSRF) attacks by:
    1. Ensuring the URL uses HTTP or HTTPS scheme
    2. Resolving the hostname to IP addresses using socket.getaddrinfo
    3. Blocking requests to private, loopback, link-local, and metadata IPs
    4. Using ipaddress.is_global to verify the IP is publicly routable

    Args:
        url: The URL to validate

    Returns:
        A tuple of (is_safe: bool, reason: str)
        - If safe: (True, "URL is safe")
        - If unsafe: (False, "Reason why unsafe")
    """
    import socket
    import ipaddress
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    # Check scheme - only allow http and https
    if parsed.scheme not in ("http", "https"):
        return False, f"Unsupported scheme: {parsed.scheme}"

    # Must have a hostname
    if not parsed.hostname:
        return False, "No hostname in URL"

    # Block URLs with userinfo (security concern)
    if parsed.username or parsed.password:
        return False, "URL contains userinfo (username/password)"

    hostname = parsed.hostname

    # Block suspicious hostnames
    if hostname in ("127.0.0.1", "::1", "localhost", "0.0.0.0"):
        return False, f"Blocked loopback hostname: {hostname}"

    # Resolve hostname to IP addresses
    try:
        # Get all address info (handles both IPv4 and IPv6)
        addr_infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        return False, f"Cannot resolve hostname: {hostname}"

    if not addr_infos:
        return False, f"No IP addresses found for: {hostname}"

    # Check each resolved IP address
    for addr_info in addr_infos:
        sockaddr = addr_info[4]
        ip_str = sockaddr[0]

        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, f"Invalid IP address: {ip_str}"

        # Block loopback addresses
        if ip.is_loopback:
            return False, f"Blocked loopback IP: {ip_str}"

        # Block private addresses (RFC 1918)
        if ip.is_private:
            return False, f"Blocked private IP: {ip_str}"

        # Block link-local addresses
        if ip.is_link_local:
            return False, f"Blocked link-local IP: {ip_str}"

        # Block reserved addresses
        if ip.is_reserved:
            return False, f"Blocked reserved IP: {ip_str}"

        # Block multicast addresses
        if ip.is_multicast:
            return False, f"Blocked multicast IP: {ip_str}"

        # Block IPv4-mapped IPv6 addresses that map to private IPv4
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            mapped_ip = ip.ipv4_mapped
            if mapped_ip.is_private or mapped_ip.is_loopback:
                return False, f"Blocked IPv4-mapped IPv6 to private IP: {mapped_ip}"

        # Specifically block AWS metadata endpoint (169.254.169.254)
        if ip_str == "169.254.169.254":
            return False, "Blocked cloud metadata endpoint"

        # Specifically block Google Cloud metadata (metadata.google.internal)
        if hostname == "metadata.google.internal":
            return False, "Blocked Google Cloud metadata endpoint"

        # Must be globally routable (public)
        if not ip.is_global:
            return False, f"Blocked non-global IP: {ip_str}"

    return True, "URL is safe"
