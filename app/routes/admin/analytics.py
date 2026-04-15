from flask import render_template, request
from flask_login import login_required

from app.routes.admin import admin, admin_required
from app.routes.admin.helpers.analytics import _get_analytics_data


@admin.route("/analytics")
@admin_required
def analytics():
    """
    Analytics dashboard - view post views and shares statistics.

    Methods: GET
    GET: Renders analytics page with daily views, top posts, share platforms.
    Query params: days - Time range (7-365, default 30, capped)
    Requires: Admin authentication.
    Template context: daily_views, total_views, top_posts, share_platforms,
                      share_counts, referrer_summary, total_subscribers, confirmed_subscribers.
    """
    days = request.args.get("days", 30, type=int)
    days = min(max(days, 7), 365)

    data = _get_analytics_data(days)

    return render_template(
        "admin/analytics.html",
        days=days,
        daily_views=data["daily_views"],
        total_views=data["total_views"],
        top_posts=data["top_posts"],
        share_platforms=data["share_platforms"],
        share_counts=data["share_counts_analytics"],
        referrer_summary=data["referrer_summary"],
        total_subscribers=data["total_subscribers"],
        confirmed_subscribers=data["confirmed_subscribers"],
    )
