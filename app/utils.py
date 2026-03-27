import re
import unicodedata
from datetime import datetime, timezone

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def utc_now() -> datetime:
    """Return current UTC time as a naive datetime (matching SQLite storage)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
