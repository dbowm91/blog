"""Dashboard metrics helpers for admin routes."""

import time
from datetime import timedelta

from sqlalchemy import func, select, text

from app import cache as flask_cache
from app.extensions import db
from app.models import PageView, ShareEvent, Subscriber, Post
from app.utils import utc_now


def _get_daily_views(days: int = 30):
    """Get daily view counts for the last N days.

    Returns list of dicts with 'date' and 'count' keys, oldest first.
    """
    now = utc_now()
    start_date = now - timedelta(days=days - 1)
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    rows = db.session.execute(
        select(
            func.date(PageView.created_at).label("date"),
            func.count(PageView.id).label("count"),
        )
        .filter(PageView.created_at >= start_date)
        .group_by(func.date(PageView.created_at))
        .order_by(func.date(PageView.created_at))
    ).all()

    views_by_date = {row.date: row.count for row in rows}

    result = []
    current = start_date
    while current <= now:
        date_str = current.strftime("%Y-%m-%d")
        result.append({
            "date": date_str,
            "day": current.strftime("%b %d"),
            "count": views_by_date.get(date_str, 0),
        })
        current += timedelta(days=1)

    return result


def _get_top_posts_by_shares(limit: int = 5):
    """Get top posts by share count."""
    thirty_days_ago = utc_now() - timedelta(days=30)
    return db.session.execute(
        select(Post, func.count(ShareEvent.id).label("share_count"))
        .join(ShareEvent)
        .filter(Post.published == True)
        .filter(ShareEvent.created_at >= thirty_days_ago)
        .group_by(Post.id)
        .order_by(func.count(ShareEvent.id).desc())
        .limit(limit)
    ).all()


@flask_cache.memoize(timeout=120)
def _get_dashboard_metrics_cached():
    """Get dashboard metrics with 2-minute cache."""
    thirty_days_ago = utc_now() - timedelta(days=30)
    month_start = utc_now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    sixty_days_ago = utc_now() - timedelta(days=60)
    now = utc_now()
    
    counts = db.session.execute(
        text("""
            SELECT
                (SELECT COUNT(*) FROM page_views) as total_views,
                (SELECT COUNT(*) FROM posts WHERE published = 1) as total_posts,
                (SELECT COUNT(*) FROM share_events) as total_shares,
                (SELECT COUNT(*) FROM subscribers WHERE confirmed = 1) as total_subscribers,
                (SELECT COUNT(*) FROM subscribers WHERE created_at >= :month_start) as new_this_month,
                (SELECT COUNT(*) FROM page_views WHERE created_at >= :sixty_days_ago AND created_at < :thirty_days_ago) as views_last_period
        """),
        {"month_start": month_start, "sixty_days_ago": sixty_days_ago, "thirty_days_ago": thirty_days_ago}
    ).fetchone()
    
    total_views = counts[0] or 0
    total_posts = counts[1] or 0
    total_shares = counts[2] or 0
    total_subscribers = counts[3] or 0
    new_this_month = counts[4] or 0
    views_last_period = counts[5] or 0
    
    # Get scheduled posts count (scheduled but not yet published)
    scheduled_count = db.session.execute(
        select(func.count(Post.id)).filter(
            Post.scheduled_publish_at != None,
            Post.scheduled_publish_at <= now,
            Post.published == False
        )
    ).scalar() or 0

    trending = db.session.execute(
        select(Post, func.count(PageView.id).label("view_count"))
        .join(PageView)
        .filter(Post.published == True)
        .filter(PageView.created_at >= thirty_days_ago)
        .group_by(Post.id)
        .order_by(func.count(PageView.id).desc())
        .limit(5)
    ).all()

    top_shares = _get_top_posts_by_shares(5)
    daily_views = _get_daily_views(30)

    views_this_period = total_views
    views_trend = None
    if views_last_period > 0:
        change = ((views_this_period - views_last_period) / views_last_period) * 100
        views_trend = round(change, 1)
    elif views_this_period > 0:
        views_trend = 100.0

    return {
        "total_views": total_views,
        "total_posts": total_posts,
        "total_shares": total_shares,
        "total_subscribers": total_subscribers,
        "trending": trending,
        "top_shares": top_shares,
        "daily_views": daily_views,
        "new_this_month": new_this_month,
        "views_trend": views_trend,
        "scheduled_posts_count": scheduled_count,
    }


def _get_dashboard_metrics():
    """Get dashboard metrics (uses cached version)."""
    return _get_dashboard_metrics_cached()


def invalidate_dashboard_cache():
    """Clear the dashboard metrics cache."""
    flask_cache.delete_memoized(_get_dashboard_metrics_cached)


def _clear_dashboard_cache():
    """Clear all dashboard cache entries (for testing)."""
    flask_cache.delete_memoized(_get_dashboard_metrics_cached)
