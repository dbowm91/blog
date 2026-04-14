from flask import redirect, url_for, request, flash
from flask_login import login_required
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.extensions import db
from app.models import Post, User
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import logger
from app.email import send_newsletter
from app.config import FROM_ADDRESS
from app.utils import is_valid_email
from sqlalchemy import select


@dataclass
class FakeSubscriber:
    email: str
    token: str = "test"
    confirmed: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    unsubscribed_at: datetime | None = None


@admin.route("/newsletter-test", methods=["POST"])
@admin_required
def newsletter_test():
    posts = (
        db.session.execute(
            select(Post)
            .filter_by(published=True)
            .order_by(Post.created_at.desc())
            .limit(3)
        )
        .scalars()
        .all()
    )
    if not posts:
        flash("No published posts to send.", "error")
        return redirect(url_for("admin.dashboard"))

    admin_user = (
        db.session.execute(select(User).filter_by(is_admin=True)).scalars().first()
    )
    if not admin_user:
        flash("No admin user found.", "error")
        return redirect(url_for("admin.dashboard"))
    test_email = request.form.get("test_email", "").strip()
    if not test_email:
        test_email = (
            FROM_ADDRESS.split("<")[-1].rstrip(">")
            if "<" in FROM_ADDRESS
            else FROM_ADDRESS
        )
    if not is_valid_email(test_email):
        flash("Invalid email address.", "error")
        return redirect(url_for("admin.dashboard"))
    fake_sub = FakeSubscriber(email=test_email)
    try:
        send_newsletter(posts, [fake_sub])
        flash(f"Test newsletter sent to {test_email}.", "success")
    except Exception as e:
        flash(f"Failed to send test newsletter: {e}", "error")
    return redirect(url_for("admin.dashboard"))
