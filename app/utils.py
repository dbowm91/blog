import html as _html
import os
import re
import unicodedata
from datetime import datetime, timezone

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
]


def safe_delete_file(filepath: str) -> bool:
    """Delete a file, returning True if deleted or False on error. Logs failures."""
    import logging

    logger = logging.getLogger(__name__)
    try:
        from app.storage import get_storage
        storage = get_storage()
        filename = os.path.basename(filepath)
        storage.delete(filename)
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
