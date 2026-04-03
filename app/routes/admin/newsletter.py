from flask import redirect, url_for, request, flash
from flask_login import login_required

from app.extensions import db
from app.models import Post, User
from app.routes.admin import admin, admin_required
from app.email import send_newsletter
from app.config import FROM_ADDRESS
from sqlalchemy import select


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

    admin_user = db.session.execute(select(User)).scalars().first()
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
    fake_sub = type(
        "FakeSub",
        (),
        {
            "email": test_email,
            "token": "test",
        },
    )()
    try:
        send_newsletter(posts, [fake_sub])
        flash(f"Test newsletter sent to {test_email}.", "success")
    except Exception as e:
        flash(f"Failed to send test newsletter: {e}", "error")
    return redirect(url_for("admin.dashboard"))
