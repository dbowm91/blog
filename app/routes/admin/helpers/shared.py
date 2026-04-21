"""Shared helpers for admin routes.

Extracted from admin/helpers.py into a subpackage for better organization.
"""

import os
import re
import logging

from flask import current_app

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
TAG_NAME_REGEX = re.compile(r"^[a-zA-Z0-9\s\-]+$")
BACKUP_FILENAME_RE = re.compile(r"^blog_\d{8}_\d{6}\.db(\.gz)?$")

logger = logging.getLogger(__name__)


def _categorize_referrer(url):
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


def _get_backup_dir():
    return os.path.join(current_app.instance_path, "backups")
