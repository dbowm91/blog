import re
import unicodedata
from datetime import datetime, timezone

from sqlalchemy import TypeDecorator, DateTime

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

__all__ = ["utc_now", "UTCDateTime", "is_valid_email", "generate_slug", "xml_escape"]


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
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")
