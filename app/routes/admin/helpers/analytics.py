"""Analytics helpers for admin routes."""

from datetime import timedelta

from sqlalchemy import func, select
from typing import Any

from app import cache as flask_cache
from app.extensions import db
from app.models import PageView, ShareEvent, Subscriber, Post
from app.utils import utc_now
from app.routes.admin.helpers.shared import _categorize_referrer


@flask_cache.memoize(timeout=300)
def _get_analytics_data(days: int) -> dict[str, Any]:
    """Get analytics data with 5-minute cache."""
    start_date = utc_now() - timedelta(days=days)

    daily_views_cte = (
        select(
            func.date(PageView.created_at).label("date"),
            func.count(PageView.id).label("views"),
        )
        .filter(PageView.created_at >= start_date)
        .group_by(func.date(PageView.created_at))
        .cte()
    )

    daily_views = db.session.execute(
        select(daily_views_cte.c.date, daily_views_cte.c.views).order_by(
            daily_views_cte.c.date
        )
    ).all()

    total_views = (
        db.session.execute(select(func.sum(daily_views_cte.c.views))).scalar_one() or 0
    )

    top_posts_cte = (
        select(
            Post.id,
            func.count(PageView.id).label("view_count"),
        )
        .join(PageView)
        .filter(Post.published)
        .filter(PageView.created_at >= start_date)
        .group_by(Post.id)
        .order_by(func.count(PageView.id).desc())
        .limit(10)
        .cte()
    )

    top_posts = db.session.execute(
        select(Post, top_posts_cte.c.view_count)
        .join(top_posts_cte, Post.id == top_posts_cte.c.id)
        .order_by(top_posts_cte.c.view_count.desc())
    ).all()

    top_post_ids = [p.id for p, _ in top_posts]
    share_counts_analytics: dict[int, int] = {}
    if top_post_ids:
        results = db.session.execute(
            select(ShareEvent.post_id, func.count(ShareEvent.id))
            .filter(ShareEvent.post_id.in_(top_post_ids))
            .group_by(ShareEvent.post_id)
        ).all()
        share_counts_analytics = {post_id: count for post_id, count in results}

    referrer_data = db.session.execute(
        select(PageView.referrer, func.count(PageView.id).label("count"))
        .filter(PageView.referrer.isnot(None), PageView.created_at >= start_date)
        .group_by(PageView.referrer)
        .order_by(func.count(PageView.id).desc())
        .limit(15)
    ).all()

    referrer_summary: dict[str, int] = {}
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
        select(ShareEvent.platform, func.count(ShareEvent.id)).group_by(
            ShareEvent.platform
        )
    ).all()

    return {
        "daily_views": daily_views,
        "total_views": total_views,
        "top_posts": top_posts,
        "share_platforms": share_platforms,
        "share_counts_analytics": share_counts_analytics,
        "referrer_summary": referrer_summary,
        "total_subscribers": total_subscribers,
        "confirmed_subscribers": confirmed_subscribers,
    }


def invalidate_analytics_cache() -> None:
    """Clear the analytics cache. Call when post data changes."""
    flask_cache.delete_memoized(_get_analytics_data)
    from app.routes.admin.helpers.dashboard import invalidate_dashboard_cache

    invalidate_dashboard_cache()


def _clear_analytics_cache() -> None:
    """Clear all analytics cache entries (for testing)."""
    flask_cache.delete_memoized(_get_analytics_data)
