"""Shared helpers for admin routes.

Extracted from admin/helpers.py into a subpackage for better organization.
"""

import os
import re
import logging

from flask import current_app

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
TAG_NAME_REGEX = re.compile(r"^[a-zA-Z0-9\s\-]+$")
BACKUP_FILENAME_RE = re.compile(r"^blog_\d{8}_\d{6}\.db(\.gz)?(\.gpg)?$")

logger = logging.getLogger(__name__)


def validate_backup_filename(filename: str) -> bool:
    """Validate backup filename matches expected pattern.

    Args:
        filename: The filename to validate

    Returns:
        True if valid, False otherwise
    """
    return bool(BACKUP_FILENAME_RE.match(filename))


def _categorize_referrer(url: str | None) -> str:
    if not url:
        return "Direct"
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.lower()
    except ValueError:
        return "Other"
    search_domains = {
        "google.com",
        "google.co",
        "bing.com",
        "yahoo.com",
        "duckduckgo.com",
    }
    social_domains = {
        "twitter.com",
        "x.com",
        "facebook.com",
        "linkedin.com",
        "reddit.com",
    }
    for sd in search_domains:
        if domain == sd or domain.endswith("." + sd):
            return "Search"
    for sd in social_domains:
        if domain == sd or domain.endswith("." + sd):
            return "Social"
    return "Other"


def _check_password_complexity(password: str) -> bool:
    if len(password) < 8:
        return False
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    return sum((has_lower, has_upper, has_digit, has_special)) >= 3


def _resolve_database_path() -> str:
    """Return the SQLite file the application actually uses.

    The admin backup actions and the backup services have to act on the same
    file, so the path is resolved once, from the live configuration.
    """
    from app.services.backup import resolve_database_file

    db_path = resolve_database_file(current_app)
    if db_path:
        return db_path
    return os.path.join(current_app.instance_path, "blog.db")


def _get_backup_dir() -> str:
    """Return the directory that holds database backups.

    The admin UI and the backup services must agree on one directory, so this
    resolves it the same way they do.
    """
    from app.services.backup import resolve_backup_dir

    return resolve_backup_dir(current_app)
