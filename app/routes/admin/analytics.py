from flask import render_template, request
from flask_login import login_required

from app.routes.admin import admin, admin_required, _get_analytics_data


@admin.route("/analytics")
@admin_required
def analytics():
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
