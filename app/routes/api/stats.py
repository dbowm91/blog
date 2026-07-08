"""Stats API endpoint."""

from datetime import timedelta

from flask import jsonify
from sqlalchemy import text

from app.extensions import db
from app.utils import utc_now
from app import limiter
from app.routes.api import api
from app.routes.api.auth import require_api_key, require_scope

DEFAULT_LIMIT = "20 per minute"


@api.route("/stats", methods=["GET"])
@require_api_key
@require_scope("analytics:read")
@limiter.limit(DEFAULT_LIMIT)
def get_stats() -> any:
    """Get dashboard statistics.

    Returns:
        JSON with total views, posts, shares, subscribers, and trends
    """
    now = utc_now()
    thirty_days_ago = now - timedelta(days=30)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    counts = db.session.execute(
        text("""
            SELECT
                (SELECT COUNT(*) FROM page_views) as total_views,
                (SELECT COUNT(*) FROM posts WHERE published = 1) as total_posts,
                (SELECT COUNT(*) FROM share_events) as total_shares,
                (SELECT COUNT(*) FROM subscribers WHERE confirmed = 1) as total_subscribers,
                (SELECT COUNT(*) FROM page_views WHERE created_at >= :thirty_days_ago) as views_this_month,
                (SELECT COUNT(*) FROM subscribers WHERE created_at >= :month_start) as new_subscribers_this_month
        """),
        {"thirty_days_ago": thirty_days_ago, "month_start": month_start},
    ).fetchone()

    if counts is None:
        return jsonify(
            {
                "total_views": 0,
                "total_posts": 0,
                "total_shares": 0,
                "total_subscribers": 0,
                "views_this_month": 0,
                "new_subscribers_this_month": 0,
            }
        )
    return jsonify(
        {
            "total_views": counts[0] or 0,
            "total_posts": counts[1] or 0,
            "total_shares": counts[2] or 0,
            "total_subscribers": counts[3] or 0,
            "views_this_month": counts[4] or 0,
            "new_subscribers_this_month": counts[5] or 0,
        }
    )
