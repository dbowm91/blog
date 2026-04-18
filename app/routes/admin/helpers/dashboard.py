"""Dashboard metrics helpers for admin routes."""

import time
import threading
from datetime import timedelta

from sqlalchemy import func, select

from app.extensions import db
from app.models import PageView, ShareEvent, Subscriber, Post
from app.utils import utc_now

_dashboard_cache = {}
_dashboard_cache_lock = threading.Lock()
_DASHBOARD_CACHE_TTL = 120


def _get_dashboard_metrics():
    """Get dashboard metrics with 2-minute cache."""
    now = time.time()

    with _dashboard_cache_lock:
        cached = _dashboard_cache.get("metrics")
        if cached and (now - cached["timestamp"]) < _DASHBOARD_CACHE_TTL:
            return cached["data"]

    thirty_days_ago = utc_now() - timedelta(days=30)
    month_start = utc_now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_views = db.session.execute(select(func.count(PageView.id))).scalar_one() or 0
    total_posts = (
        db.session.execute(
            select(func.count(Post.id)).filter(Post.published == True)
        ).scalar_one()
        or 0
    )
    total_shares = (
        db.session.execute(select(func.count(ShareEvent.id))).scalar_one() or 0
    )
    total_subscribers = (
        db.session.execute(
            select(func.count(Subscriber.id)).filter(Subscriber.confirmed == True)
        ).scalar_one()
        or 0
    )

    trending = db.session.execute(
        select(Post, func.count(PageView.id).label("view_count"))
        .join(PageView)
        .filter(Post.published == True)
        .filter(PageView.created_at >= thirty_days_ago)
        .group_by(Post.id)
        .order_by(func.count(PageView.id).desc())
        .limit(5)
    ).all()

    new_this_month = (
        db.session.execute(
            select(func.count(Subscriber.id)).filter(
                Subscriber.created_at >= month_start
            )
        ).scalar_one()
        or 0
    )

    views_trend = None
    views_this_period = total_views
    sixty_days_ago = utc_now() - timedelta(days=60)
    views_last_period = (
        db.session.execute(
            select(func.count(PageView.id)).filter(
                PageView.created_at >= sixty_days_ago,
                PageView.created_at < thirty_days_ago,
            )
        ).scalar_one()
        or 0
    )
    if views_last_period > 0:
        change = ((views_this_period - views_last_period) / views_last_period) * 100
        views_trend = round(change, 1)
    elif views_this_period > 0:
        views_trend = 100.0

    data = {
        "total_views": total_views,
        "total_posts": total_posts,
        "total_shares": total_shares,
        "total_subscribers": total_subscribers,
        "trending": trending,
        "new_this_month": new_this_month,
        "views_trend": views_trend,
    }

    with _dashboard_cache_lock:
        _dashboard_cache["metrics"] = {"timestamp": now, "data": data}

    return data


def _invalidate_dashboard_cache():
    """Clear the dashboard metrics cache."""
    with _dashboard_cache_lock:
        _dashboard_cache.clear()


def invalidate_dashboard_cache():
    """Public function to invalidate dashboard metrics cache."""
    _invalidate_dashboard_cache()
