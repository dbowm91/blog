"""Subscription routes - subscribe, confirm, unsubscribe."""

import uuid
import time
from flask import current_app

from flask import (
    render_template,
    redirect,
    url_for,
    request,
    flash,
    Response,
)
from sqlalchemy import select

from app.extensions import db
from app.models import Subscriber
from app.config import CONFIRMATION_EXPIRY_HOURS, TOKEN_ENUMERATION_DELAY
from app.tasks import send_confirmation_task
from app.csrf import validate_csrf_token
from app.utils import is_valid_email, utc_now
from app import limiter

logger = logging.getLogger(__name__)


def _try_send_confirmation(subscriber):
    """Queue confirmation email task. Returns True (task queued)."""
    send_confirmation_task.delay(subscriber.id)
    return True


def _reset_subscriber_token(subscriber):
    """Reset subscriber token and expiry for new confirmation."""
    subscriber.token = uuid.uuid4().hex
    subscriber.expires_at = utc_now() + timedelta(hours=CONFIRMATION_EXPIRY_HOURS)


def _send_or_flash_confirmation(subscriber, skip_conflict=False):
    """Send confirmation and flash appropriate message. Returns redirect target."""
    if _try_send_confirmation(subscriber):
        flash("Check your inbox to confirm your subscription.", "success")
    else:
        flash("Subscribed, but confirmation email could not be sent.", "error")
    return redirect(_safe_redirect_url())


def register_subscribe_routes(public):
    """Register subscription-related routes on the Blueprint."""

    @public.route("/subscribe", methods=["POST"])
    @limiter.limit("10 per minute")
    def subscribe() -> Response:
        """Subscribe to the newsletter."""
        validate_csrf_token()

        email = request.form.get("email", "").strip().lower()[:256]
        if not is_valid_email(email):
            flash("Please enter a valid email address.", "error")
            return redirect(_safe_redirect_url())

        existing = db.session.execute(
            select(Subscriber).filter_by(email=email)
        ).scalar_one_or_none()
        if existing:
            if existing.unsubscribed_at:
                existing.unsubscribed_at = None
                existing.confirmed = False
                _reset_subscriber_token(existing)
                db.session.commit()
                return _send_or_flash_confirmation(existing)
            elif existing.confirmed:
                logger.info("Already-subscribed user %s attempted to resubscribe", email)
                flash("You're already subscribed!", "info")
                return redirect(_safe_redirect_url())
            else:
                _reset_subscriber_token(existing)
                db.session.commit()
                return _send_or_flash_confirmation(existing)

        sub = Subscriber(
            email=email, expires_at=utc_now() + timedelta(hours=CONFIRMATION_EXPIRY_HOURS)
        )
        db.session.add(sub)
        try:
            db.session.commit()
            return _send_or_flash_confirmation(sub)
        except (IntegrityError, OperationalError):
            db.session.rollback()
            existing = db.session.execute(
                select(Subscriber).filter_by(email=email)
            ).scalar_one_or_none()
            if not existing:
                flash("Please enter a valid email address.", "error")
                return redirect(_safe_redirect_url())
            if existing.confirmed:
                flash("Check your inbox to confirm your subscription.", "success")
                return redirect(_safe_redirect_url())
            if existing.expires_at and existing.expires_at < utc_now():
                db.session.delete(existing)
                db.session.commit()
                sub = Subscriber(
                    email=email,
                    expires_at=utc_now() + timedelta(hours=CONFIRMATION_EXPIRY_HOURS),
                )
                db.session.add(sub)
                db.session.commit()
                return _send_or_flash_confirmation(sub)
            _reset_subscriber_token(existing)
            db.session.commit()
            return _send_or_flash_confirmation(existing)

    @public.route("/confirm/<token>")
    @limiter.limit("5 per minute")
    def confirm(token) -> Response:
        """Confirm newsletter subscription via token."""
        time.sleep(TOKEN_ENUMERATION_DELAY)
        sub = db.session.execute(
            select(Subscriber).filter_by(token=token)
        ).scalar_one_or_none()
        if not sub:
            logger.warning(
                "Confirm enumeration attempt with invalid token from %s",
                request.remote_addr,
            )
            flash("Subscription confirmed! You'll receive our newsletter.", "success")
            return redirect("/")
        if sub.expires_at and sub.expires_at < utc_now():
            try:
                db.session.delete(sub)
                db.session.commit()
            except (IntegrityError, OperationalError):
                db.session.rollback()
            logger.info("Removed expired unconfirmed subscriber: %s", sub.email)
            flash("This confirmation link has expired. Please subscribe again.", "warning")
            return redirect("/")
        if sub.confirmed:
            flash("Already confirmed.", "info")
            return redirect("/")
        sub.confirmed = True
        db.session.commit()
        flash("Subscription confirmed! You'll receive our newsletter.", "success")
        return redirect("/")

    @public.route("/unsubscribe/<token>")
    @limiter.limit("5 per minute")
    def unsubscribe(token) -> Response:
        """Unsubscribe from the newsletter via token."""
        time.sleep(TOKEN_ENUMERATION_DELAY)
        sub = db.session.execute(
            select(Subscriber).filter_by(token=token)
        ).scalar_one_or_none()
        if not sub:
            logger.warning(
                "Unsubscribe enumeration attempt with invalid token from %s",
                request.remote_addr,
            )
            flash("You have been unsubscribed.", "success")
            return redirect("/")
        sub_email = sub.email
        sub.unsubscribed_at = utc_now()
        sub.confirmed = False
        db.session.commit()
        logger.info("Unsubscribed: email=%s", sub_email)
        flash("You have been unsubscribed.", "success")
        return redirect("/")
