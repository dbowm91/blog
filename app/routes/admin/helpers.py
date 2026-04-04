"""Shared helpers for admin routes.

Extracted from admin/__init__.py to reduce coupling and eliminate star imports.
"""

import os
import re
import threading
import time
import uuid
import logging

from flask import current_app, flash
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, OperationalError

from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import Post, Tag, User, PageView, ShareEvent, Subscriber
from app.utils import utc_now, safe_delete_file
from app.config import (
    DASHBOARD_PER_PAGE,
    MAX_UPLOAD_SIZE,
)
from app.cache import invalidate_tag_cache
from app.search import sync_fts, remove_fts

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
TAG_NAME_REGEX = re.compile(r"^[a-zA-Z0-9\s\-]+$")
BACKUP_FILENAME_RE = re.compile(r"^blog_\d{8}_\d{6}\.db(\.gz)?$")

logger = logging.getLogger(__name__)

_analytics_cache = {}
_analytics_cache_lock = threading.Lock()
_ANALYTICS_CACHE_TTL = 300
_ANALYTICS_MAX_SIZE = 16


def _categorize_referrer(url):
    if not url:
        return "Direct"
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.lower()
    except Exception:
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


def _get_posts_query(status: str, search: str, order_by=None):
    base_q = select(Post)
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search_term = f"%{escaped}%"
        base_q = base_q.filter(Post.title.ilike(search_term, escape="\\"))
    if status == "published":
        base_q = base_q.filter(Post.published == True)
    elif status == "draft":
        base_q = base_q.filter(Post.published == False)
    if order_by is None:
        order_by = Post.updated_at.desc()
    return base_q.order_by(order_by)


def _get_analytics_data(days: int):
    cache_key = days
    now = time.time()

    with _analytics_cache_lock:
        cached = _analytics_cache.get(cache_key)
        if cached and (now - cached["timestamp"]) < _ANALYTICS_CACHE_TTL:
            return cached["data"]

    start_date = utc_now() - timedelta(days=days)

    daily_views = db.session.execute(
        select(
            func.date(PageView.created_at).label("date"),
            func.count(PageView.id).label("views"),
        )
        .filter(PageView.created_at >= start_date)
        .group_by(func.date(PageView.created_at))
        .order_by(func.date(PageView.created_at))
    ).all()

    top_posts = db.session.execute(
        select(Post, func.count(PageView.id).label("view_count"))
        .join(PageView)
        .filter(Post.published == True)
        .filter(PageView.created_at >= start_date)
        .group_by(Post.id)
        .order_by(func.count(PageView.id).desc())
        .limit(10)
    ).all()

    top_post_ids = [p.id for p, _ in top_posts]
    if top_post_ids:
        share_counts_analytics = dict(
            db.session.execute(
                select(ShareEvent.post_id, func.count(ShareEvent.id))
                .filter(ShareEvent.post_id.in_(top_post_ids))
                .group_by(ShareEvent.post_id)
            ).all()
        )
    else:
        share_counts_analytics = {}

    referrer_data = db.session.execute(
        select(PageView.referrer, func.count(PageView.id).label("count"))
        .filter(PageView.referrer != None, PageView.created_at >= start_date)
        .group_by(PageView.referrer)
        .order_by(func.count(PageView.id).desc())
        .limit(15)
    ).all()

    referrer_summary = {}
    for url, count in referrer_data:
        category = _categorize_referrer(url)
        referrer_summary[category] = referrer_summary.get(category, 0) + count

    subscriber_stats = db.session.execute(
        select(
            func.count(Subscriber.id),
            func.sum(Subscriber.confirmed.cast(db.Integer)),
        )
    ).one()
    total_subscribers = subscriber_stats[0] or 0
    confirmed_subscribers = subscriber_stats[1] or 0

    share_platforms = db.session.execute(
        select(ShareEvent.platform, func.count(ShareEvent.id).label("count")).group_by(
            ShareEvent.platform
        )
    ).all()

    total_views = (
        db.session.execute(
            select(func.count(PageView.id)).filter(PageView.created_at >= start_date)
        ).scalar_one()
        or 0
    )

    data = {
        "daily_views": daily_views,
        "total_views": total_views,
        "top_posts": top_posts,
        "share_platforms": share_platforms,
        "share_counts_analytics": share_counts_analytics,
        "referrer_summary": referrer_summary,
        "total_subscribers": total_subscribers,
        "confirmed_subscribers": confirmed_subscribers,
    }

    with _analytics_cache_lock:
        if len(_analytics_cache) >= _ANALYTICS_MAX_SIZE:
            oldest = min(
                _analytics_cache, key=lambda k: _analytics_cache[k]["timestamp"]
            )
            del _analytics_cache[oldest]
        _analytics_cache[cache_key] = {"timestamp": now, "data": data}

    return data


def validate_tag_name(name: str) -> tuple[bool, str]:
    if not name or not TAG_NAME_REGEX.match(name):
        return (
            False,
            "Invalid tag name. Use only ASCII letters, numbers, spaces, and hyphens.",
        )
    if len(name) > 50:
        return False, "Tag name must be 50 characters or fewer."
    return True, ""


def _detect_image_type(header):
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if header[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if header[:3] == b"GIF" and header[3:6] in (b"87a", b"89a"):
        return "gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _generate_unique_slug(title, exclude_id=None):
    slug = Post.generate_slug(title)
    base_slug = slug
    counter = 2
    while counter <= 100:
        q = select(Post).filter(Post.slug == slug)
        if exclude_id is not None:
            q = q.filter(Post.id != exclude_id)
        if not db.session.execute(q).scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1
    if counter > 100:
        slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"
    return slug


def _save_image(file):
    if file and file.filename and _allowed_file(file.filename):
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        if size > MAX_UPLOAD_SIZE:
            return (
                None,
                f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024 * 1024)}MB.",
            )
        header = file.read(32)
        file.seek(0)
        detected = _detect_image_type(header)
        if detected not in ("png", "jpeg", "gif", "webp"):
            return None, "Uploaded file is not a valid image."
        ext = detected
        filename = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
        return filename, None
    return None, None


def _cleanup_orphan_tags():
    from app.models import post_tags

    orphan_tag_ids = (
        db.session.execute(
            select(Tag.id)
            .outerjoin(post_tags, Tag.id == post_tags.c.tag_id)
            .filter(post_tags.c.post_id.is_(None))
        )
        .scalars()
        .all()
    )
    if orphan_tag_ids:
        db.session.execute(delete(Tag).where(Tag.id.in_(orphan_tag_ids)))


def _get_or_create_tags(names):
    tags = []
    invalid_tags = []
    for name in names:
        name = name.strip()[:50]
        if not name:
            continue
        is_valid, _ = validate_tag_name(name)
        if not is_valid:
            invalid_tags.append(name)
            continue
        slug = Tag.generate_slug(name)
        tag = db.session.execute(select(Tag).filter_by(slug=slug)).scalar_one_or_none()
        if not tag:
            tag = Tag(name=name, slug=slug)
            db.session.add(tag)
        tags.append(tag)
    if invalid_tags:
        flash(f"Invalid tag names (skipped): {', '.join(invalid_tags)}", "warning")
    return tags


def _apply_post_updates(
    post,
    title,
    body,
    summary,
    published,
    was_published,
    scheduled_publish_at,
    tag_names,
):
    post.title = title
    post.body = body
    post.summary = summary
    post.published = published
    post.scheduled_publish_at = scheduled_publish_at
    if published and not was_published:
        post.published_at = utc_now()
    post.tags = _get_or_create_tags(tag_names)
    return post


def invalidate_analytics_cache():
    """Clear the analytics cache. Call when post data changes."""
    with _analytics_cache_lock:
        _analytics_cache.clear()


def _get_backup_dir():
    return os.path.join(current_app.instance_path, "backups")
