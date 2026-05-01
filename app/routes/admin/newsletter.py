from __future__ import annotations
from flask import redirect, url_for, request, flash, Response, render_template
from flask_login import login_required
from datetime import datetime, timezone
import smtplib
import logging

from app.extensions import db
from app.models import Post, User
from app.routes.admin import admin, admin_required
from app.routes.admin.helpers import logger
from app.email import send_newsletter
from app.config import FROM_ADDRESS, APP_TITLE, BASE_URL
from app.utils import is_valid_email
from sqlalchemy import select


class FakeSubscriber:
    """Minimal subscriber-like object for test newsletter sending."""
    def __init__(self, email: str):
        self.email = email
        self.token = "test"


@admin.route("/newsletter-test", methods=["POST"])
@admin_required
def newsletter_test() -> Response:
    """
    Send a test newsletter to a specific email.

    Methods: POST
    POST: Sends test newsletter with 3 most recent published posts to test address.
    Requires: Admin authentication.
    Form params: test_email (optional) - Email address to send test to.
                 Defaults to FROM_ADDRESS from config.
    """
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
        send_newsletter(posts, [fake_sub], total_subscribers=1)
        flash(f"Test newsletter sent to {test_email}.", "success")
    except (smtplib.SMTPException, OSError) as e:
        logger.error("Failed to send test newsletter: %s", e)
        flash("Failed to send test newsletter. Please try again later.", "error")
    return redirect(url_for("admin.dashboard"))


@admin.route("/newsletter/preview")
@admin_required
def newsletter_preview() -> Response:
    """Preview the newsletter email with recent posts.
    
    Methods: GET
    Returns: HTML preview of the newsletter email.
    Requires: Admin authentication.
    """
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
        flash("No published posts to preview.", "warning")
        return redirect(url_for("admin.dashboard"))
    
    # Render the newsletter email template
    html = render_template(
        "email/newsletter.html",
        posts=posts,
        site_title=APP_TITLE,
        base_url=BASE_URL,
        unsubscribe_url="#preview-mode",
    )
    
    return Response(html, mimetype="text/html")
